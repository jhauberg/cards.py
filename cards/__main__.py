#!/usr/bin/env python
# coding=utf-8

import argparse

from cards.cards import generate

from cards.version import __version__


def setup_arguments(parser) -> None:
    """ Sets up required and optional program arguments. """

    # required arguments
    parser.add_argument('-f', '--input-filename', dest='input_paths', required=True, nargs='*',
                        help='One or more paths to CSV files containing card data')

    # optional arguments
    parser.add_argument('-o', '--output-folder', dest='output_path', required=False,
                        help='Path to a directory in which the pages will be generated '
                             '(a sub-directory will be created)')

    parser.add_argument('-O', '--output-filename', dest='output_filename', required=False,
                        default='index.html',
                        help='Name of the generated file')

    parser.add_argument('-d', '--definitions-filename', dest='definitions_path', required=False,
                        help='Path to a CSV file containing definitions')

    parser.add_argument('-s', '--size', dest='size_identifier', required=False,
                        help='Set the default size to use for cards (default is \'standard\'. '
                        'Other options include: \'domino\', \'jumbo\' or \'token\')')

    parser.add_argument('--force-page-breaks', dest='force_page_breaks', required=False,
                        default=False, action='store_true',
                        help='Force a page break for each datasource')

    parser.add_argument('--disable-backs', dest='disable_backs', required=False,
                        default=False, action='store_true',
                        help='Don\'t generate card backs')

    parser.add_argument('--verbose', dest='verbose', required=False,
                        default=False, action='store_true',
                        help='Show more information')

    parser.add_argument('--version', action='version', version='cards ' + __version__,
                        help='Show the program\'s version')


def main(as_module=False):
    parser = argparse.ArgumentParser(
        description='Generates print-ready cards for your tabletop game.')

    setup_arguments(parser)

    generate(vars(parser.parse_args()))

if __name__ == '__main__':
    main(as_module=True)
