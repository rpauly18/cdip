from setuptools import setup, find_packages
from distutils.core import Extension
import os
import re

DISTNAME = 'cdip'
PACKAGES = find_packages()
EXTENSIONS = []
DESCRIPTION = 'CDiP Reader'
AUTHOR = 'Kilcher'
MAINTAINER_EMAIL = ''

DEPENDENCIES = ['netcdf4', 
                'requests', 
                'lxml',
                'diskcache']

# use README file as the long description
file_dir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(file_dir, 'README.md'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

# get version from __init__.py
with open(os.path.join(file_dir, 'cdip', '__init__.py')) as f:
    version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        VERSION = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string.")
        
setup(name=DISTNAME,
      version=VERSION,
      packages=PACKAGES,
      ext_modules=EXTENSIONS,
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      author=AUTHOR,
      zip_safe=False,
      install_requires=DEPENDENCIES,
      scripts=[],
      include_package_data=True
  )
