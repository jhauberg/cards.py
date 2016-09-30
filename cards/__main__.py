#!/usr/bin/env python
# coding=utf-8

import argparse

from cards.cards import generate
from cards.util import terminal_supports_color

from cards.version import __version__


def pretty_description(description: str) -> str:
    apply_bold_color = '\033[1m'
    apply_normal_color = '\033[0m'

    return (apply_bold_color + description + apply_normal_color if terminal_supports_color()
            else description)


def setup_arguments(parser) -> None:
    """ Sets up required and optional program arguments. """

    # required arguments
    parser.add_argument(dest='input_paths', nargs='+',
                        help=pretty_description('specifies one or more paths to card datasources'))

    # optional arguments
    parser.add_argument('-o', '--output-path', dest='output_path', required=False,
                        help='specifies the path to the output directory '
                             '(a \'generated\' sub-directory will be created)')

    parser.add_argument('-O', '--output-filename', dest='output_filename', required=False,
                        default='index.html',
                        help='set the filename of the generated output file')

    parser.add_argument('-d', '--definitions-filename', dest='definitions_filename', required=False,
                        help='specifies the path to the definitions file')

    parser.add_argument('-s', '--size', dest='size', required=False,
                        help='set the default card size (default is \'standard\'; '
                        'other options include: \'domino\', \'jumbo\' or \'token\')')

    parser.add_argument('--force-page-breaks', dest='force_page_breaks', required=False,
                        default=False, action='store_true',
                        help='force a page break after each datasource')

    parser.add_argument('--disable-backs', dest='disable_backs', required=False,
                        default=False, action='store_true',
                        help='don\'t generate card backs')

    parser.add_argument('--preview', dest='preview', required=False,
                        default=False, action='store_true',
                        help='only render 1 of each card')

    parser.add_argument('--verbose', dest='verbose', required=False,
                        default=False, action='store_true',
                        help='show more output information')

    parser.add_argument('--version', action='version', version='cards ' + __version__,
                        help='show the program version')


def main(as_module=False):
    parser = argparse.ArgumentParser(
        prog='cards',
        description='Generates print-ready cards for your tabletop game',
        epilog='Make more cards!')

    setup_arguments(parser)

    generate(vars(parser.parse_args()))

if __name__ == '__main__':
    main(as_module=True)
