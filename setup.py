#!/usr/bin/env python
# coding=utf-8

"""
Setup script for cards.py.

https://github.com/jhauberg/cards.py

Copyright 2015 Jacob Hauberg Hansen.
License: MIT (see LICENSE)
"""

import sys
import re

from setuptools import setup

if sys.version_info < (3, 5):
    sys.exit('Python 3.5 or newer is required for cards.py')

version = open('cards/version.py', 'rt').read()
version_search = r'^__version__ = [\'"]([^\'"]*)[\'"]'

matches = re.search(version_search, version, re.M)

if matches:
    version_identifier = matches.group(1)
else:
    sys.exit('Version could not be determined')

setup(
    name='cards.py',
    version=version_identifier,
    description='Generate Print-and-Play cards for your board games',
    long_description=open('README.md', 'r').read(),
    url='https://github.com/jhauberg/cards.py',
    download_url='https://github.com/jhauberg/cards.py/archive/master.zip',
    author='Jacob Hauberg Hansen',
    author_email='jacob.hauberg@gmail.com',
    license='MIT',
    packages=['cards'],
    include_package_data=True,
    platforms='any',
    install_requires=[
        'docopt==0.6.2'
    ],
    entry_points={
        'console_scripts': [
            'cards = cards.__main__:main',
        ],
    }
)
