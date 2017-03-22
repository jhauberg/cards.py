#!/usr/bin/env python
# coding=utf-8

"""
Generate print-ready cards for your tabletop game

Usage:
  cards make [<datasource>]... [--definitions=<defs>]
             [--output-path=<path>] [--output-file=<file>] [--include-header=<template>]
             [--card-size=<size>] [--force-page-breaks] [--disable-backs] [--disable-page-sections]
             [--clean] [--preview] [--verbose]
  cards new  [<name>] [--output-path=<path>] [--verbose]
  cards -h | --help
  cards --version

Examples:
  cards make cards.csv
    Builds the 'cards.csv' datasource and outputs to the current directory.

  cards make cards.csv tokens.csv -d defs.csv -o ~/Desktop
    Builds both 'cards.csv' and 'tokens.csv' datasources with the definitions 'defs.csv',
    and outputs to the specified path (the desktop in this case).

  cards new "Empty Game"
    Creates an empty project in the current directory.

Options:
  -h --help                         Show program help
  -o --output-path=<path>           Specify output directory
  -f --output-file=<file>           Specify output filename [default: index.html]
  -p --include-header=<template>    Specify a presentation template
  -d --definitions=<defs>           Specify definitions filename
  --card-size=<size>                Specify default card size [default: standard]
                                    Other options include: \'domino\', \'jumbo\' or \'token\'
  --force-page-breaks               Force a page break after each datasource
  --disable-backs                   Do not render card backs
  --disable-page-sections           Do not render page sections
  --clean                           Automatically remove any unused resources (images)
  --preview                         Only render 1 of each card
  --verbose                         Show more information
  --version                         Show program version
"""

import os
import re

from docopt import docopt

from cards.cards import make, make_empty_project
from cards.warning import WarningDisplay

from cards.version import __version__
from cards.constants import VERSION_PATTERN

from pkg_resources import parse_version


def check_for_update():
    """ Determine whether a newer version is available remotely. """

    from urllib.request import urlopen
    from urllib.error import URLError, HTTPError

    url = 'https://raw.githubusercontent.com/jhauberg/cards.py/master/cards/version.py'

    try:
        # specify a very short timeout, as this is a non-essential feature
        # and should not stall program exit indefinitely
        with urlopen(url, timeout=5) as response:
            # we're certain this file is UTF8, so we'll decode it right away
            response_body = response.read().decode('utf8')
            # search for the version string
            matches = re.search(VERSION_PATTERN, response_body, re.M)

            if matches:
                # if found, grab it and compare to the current installation
                remote_version_identifier = matches.group(1)

                if parse_version(__version__) < parse_version(remote_version_identifier):
                    WarningDisplay.newer_version_available(
                        new_version_identifier=remote_version_identifier)
                    # end with empty break
                    print()
    except HTTPError:
        # fail silently
        pass
    except URLError:
        # fail silently
        pass


def main():
    """ Entry point for invoking the cards module. """

    arguments = docopt(__doc__, version='cards ' + __version__)

    output_path = arguments['--output-path']

    if output_path is None or len(output_path) == 0:
        output_path = os.getcwd()

    WarningDisplay.is_verbose = arguments['--verbose']

    if arguments['new']:
        make_empty_project(
            in_path=output_path,
            name=arguments['<name>'])
    elif arguments['make']:
        data_paths = arguments['<datasource>']

        output_filename = arguments['--output-file']
        header_path = arguments['--include-header']
        definitions_path = arguments['--definitions']
        default_card_size_identifier = arguments['--card-size']
        force_page_breaks = arguments['--force-page-breaks']
        disable_backs = arguments['--disable-backs']
        disable_sections = arguments['--disable-page-sections']
        is_preview = arguments['--preview']
        clean = arguments['--clean']

        make(data_paths, header_path, definitions_path,
             output_path, output_filename,
             force_page_breaks,
             disable_backs, disable_sections,
             default_card_size_identifier,
             is_preview,
             clean)

    check_for_update()


if __name__ == '__main__':
    main()
