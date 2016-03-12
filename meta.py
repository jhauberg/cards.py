# coding=utf-8

import os
import csv

from util import warn, dict_from_string, lower_first_row


class Metadata(object):
    """ Provides metadata properties for the generated pages. """

    def __init__(
            self,
            title: str,
            description: str,
            version: str,
            copyright_notice: str,
            image_defs: list=None,
            size_defs: list=None):
        self.title = title
        self.description = description
        self.version = version
        self.copyright_notice = copyright_notice
        self.image_definitions = image_defs
        self.size_definitions = size_defs

    @staticmethod
    def from_file(path: str, verbosely: 'show warnings'=False) -> 'Metadata':
        """ Reads the specified file containing metadata into a Metadata object and returns it. """

        # default values
        title = ''
        description = ''
        version = ''
        copyright_notice = ''

        image_definitions = None
        size_definitions = None

        if path is not None and len(path) > 0:
            if not os.path.isfile(path):
                if verbosely:
                    warn('No metadata was found at: \'{0}\''.format(path))
            else:
                with open(path) as mf:
                    metadata = csv.DictReader(lower_first_row(mf))

                    for row in metadata:
                        title = row.get('@title', title)
                        description = row.get('@description', description)
                        version = row.get('@version', version)
                        copyright_notice = row.get('@copyright', copyright_notice)

                        image_definitions = dict_from_string(row.get('@images'))
                        size_definitions = dict_from_string(row.get('@sizes'))

                        # only read the first row of data
                        break

        return Metadata(title, description, version, copyright_notice,
                        image_definitions, size_definitions)
