#!/usr/bin/env python
# coding=utf-8

"""
Generate print-ready cards for your tabletop game

Usage:
  cards make [<datasource>]... [--definitions=<defs>]
             [--output-path=<path>] [--output-file=<file>]
             [--card-size=<size>] [--force-page-breaks] [--disable-backs]
             [--preview] [--verbose]
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
  -h --help                  Show program help
  -o --output-path=<path>    Specify output directory
  -f --output-file=<file>    Specify output filename [default: index.html]
  -d --definitions=<defs>    Specify definitions filename
  --card-size=<size>         Specify default card size [default: standard]
                             Other options include: \'domino\', \'jumbo\' or \'token\'
  --force-page-breaks        Force a page break after each datasource
  --disable-backs            Do not render card backs
  --preview                  Only render 1 of each card
  --verbose                  Show more information
  --version                  Show program version
"""

import os

from docopt import docopt

from cards.cards import make, make_empty_project
from cards.warning import WarningDisplay

from cards.version import __version__


def main():
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
        definitions_path = arguments['--definitions']
        default_card_size_identifier = arguments['--card-size']
        force_page_breaks = arguments['--force-page-breaks']
        disable_backs = arguments['--disable-backs']
        is_preview = arguments['--preview']

        make(data_paths, definitions_path,
             output_path, output_filename,
             force_page_breaks,
             disable_backs,
             default_card_size_identifier,
             is_preview)


if __name__ == '__main__':
    main()
