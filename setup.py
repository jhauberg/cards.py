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

from cards.constants import VERSION_PATTERN


def determine_version_or_exit() -> str:
    """ Determine version identifier or exit the program. """

    if sys.version_info < (3, 5):
        sys.exit('Python 3.5 or newer is required for cards.py')

    with open('cards/version.py') as file:
        version_contents = file.read()

        version_match = re.search(VERSION_PATTERN, version_contents, re.M)

        if version_match:
            return version_match.group(1)
        else:
            sys.exit('Version could not be determined')


VERSION_IDENTIFIER = determine_version_or_exit()


setup(
    name='cards.py',
    version=VERSION_IDENTIFIER,
    description='Generate Print-and-Play cards for your board games',
    long_description=open('README.md').read(),
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
