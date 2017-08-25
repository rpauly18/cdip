import netCDF4 as nc4
import numpy as np
import requests
from lxml import html
from diskcache import Cache
import os
from .time import Date64


pkg_dir = os.path.dirname(os.path.realpath(__file__))
cache_dir = pkg_dir + '/.cache_data/'


def get_NDBCnum(cdip_metadata_link):
    page = requests.get(cdip_metadata_link)
    idx = page.content.find('NDBC')
    return int(page.content[idx + 5:idx + 10])


def load_hist_stations():

    info = requests.get('http://thredds.cdip.ucsd.edu/thredds/catalog/cdip/archive/catalog.html')
    tree = html.fromstring(info.content)

    rows = tree.getchildren()[1].getchildren()[2].getchildren()

    hist_stations = []
    for irow, row in enumerate(rows):
        try:
            t = row.getchildren()[0].getchildren()[1].getchildren()[0].text
        except:
            #print "NOTHING FOUND AT ROW {}".format(irow)
            continue
        if t.endswith('/'):
            # The first three numbers are the station ID.
            hist_stations.append(int(t[:3]))
    hist_stations = np.unique(hist_stations)
    return hist_stations


def load_realtime_stations():

    rtdat = nc4.Dataset(
        "http://thredds.cdip.ucsd.edu/thredds/dodsC/cdip/realtime/latest_3day.nc"
    )
    realtime_stations = np.sort([int(val.tostring()
                                     .rstrip(u'\x00').split('p')[0])
                                 for val in rtdat.variables['metaSiteLabel']])
    return realtime_stations


def _parse_deploy(deploy=None):
    if deploy is None:
        sufx = 'historic'
    elif deploy == 'realtime':
        sufx = 'rt'
    elif isinstance(deploy, str):
        sufx = 'd' + deploy
    else:
        sufx = 'd{:02d}'.format(deploy)
    return sufx


def get_thredd(station, deploy=None, cache_only=False):

    if cache_only:
        return CDIPbuoy(None, cache_id=(station, deploy))

    url = ('http://thredds.cdip.ucsd.edu/thredds/'
           'dodsC/cdip/archive/{st:03d}p1/'
           '{st:03d}p1_{dep}.nc'.format(st=station,
                                        dep=_parse_deploy(deploy)))

    nc = nc4.Dataset(url)
    return CDIPbuoy(nc)


def _cache_name(inval, deploy=None):
    if isinstance(inval, nc4.Dataset):
        tmpid = inval.id.split('_')
        return '{}.{}.cache'.format(tmpid[1], tmpid[2])
    return '{:03d}p1.{}.cache'.format(inval, _parse_deploy(deploy))


class CDIPbuoy(object):

    def __init__(self, ncdf, cache_id=False):
        self.ncdf = ncdf
        if ncdf is None and cache_id:
            self._data_cache = Cache(cache_dir + _cache_name(*cache_id))
            return
        self._data_cache = Cache(cache_dir + _cache_name(ncdf), tag_index=True)
        for ky in self.ncdf.variables:
            if ky.endswith('Time') and ky not in self._data_cache:
                tmp = Date64(ncdf.variables[ky][:].astype('datetime64[s]'))
                self._data_cache.set(ky, tmp)
        self.NDBC_num = get_NDBCnum(self.ncdf.metadata_link)

    def __getattr__(self, name):
        name = unicode(name)
        if name in self._data_cache:
            return self._data_cache[name]
        if name in self.variables:
            self._data_cache[name] = self.variables[name][:]
            return self._data_cache[name]
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__, name))

    def keys(self, ):
        return self.ncdf.variables.keys()

    @property
    def variables(self, ):
        return self.ncdf.variables


def calc_resourcematrix(buoy, Hs_edges, Tp_edges):
    time = Date64(np.arange(buoy.waveTime[0].astype('datetime64[M]'),
                            buoy.waveTime[-1].astype('datetime64[M]'), ))
    hs = buoy.ncdf.variables['waveHs'][:]
    tp = buoy.ncdf.variables['waveTp'][:]
    # Pad the edges with 0 and inf
    Tp_edges = np.pad(Tp_edges,
                      pad_width=(int(Tp_edges[0] > 0), int(Tp_edges[-1] != np.inf)),
                      mode='constant', constant_values=(0, np.inf))
    Hs_edges = np.pad(Hs_edges,
                      pad_width=(int(Hs_edges[0] > 0), int(Hs_edges[-1] != np.inf)),
                      mode='constant', constant_values=(0, np.inf))
    matout = np.zeros((len(time), len(Hs_edges) - 1, len(Tp_edges) - 1, ))
    num_hours = np.zeros(len(time), dtype=np.uint16)
    for itime, t in enumerate(time):
        year = int(str(t)[:4])
        month = int(str(t)[5:])
        ind = (buoy.waveTime.year == year) & (buoy.waveTime.month == month)
        h, xedg, yedg = np.histogram2d(hs[ind], tp[ind], [Hs_edges, Tp_edges, ])
        matout[itime] = h * 0.5
        # This is the number of hours at a given resource level.
        if month in [1, 3, 5, 7, 8, 10, 12]:
            dt = 31 * 24
        elif month == 2:
            dt = (np.datetime64('{}-03-01T00'.format(year)) -
                  np.datetime64('{}-02-01T00'.format(year))).astype(np.uint16)
        else:
            dt = 30 * 24
        num_hours[itime] = dt
        #return matout, time, num_hours
    return matout, time, num_hours