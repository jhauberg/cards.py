# coding=utf-8

"""
This module provides access to reserved constants; column names, card sizes and such.
"""

import datetime

FIXED_TIMESTAMP = datetime.date.today()


class Columns:  # pylint: disable=too-few-public-methods
    """ Reserved column names. """

    # Determines how many cards should be generated
    COUNT = '@count'
    # Determines which template to use for the front of the card (must be a filepath)
    TEMPLATE = '@template'
    # Determines which template to use for the back of the card (must be a filepath)
    TEMPLATE_BACK = '@template-back'


class ColumnDescriptors:  # pylint: disable=too-few-public-methods
    """ Descriptors that can be appended to columns for special processing. """

    # The content of the column should only be used when generating the back of the card
    BACK_ONLY = '@back-only'


class TemplateFieldDescriptors:  # pylint: disable=too-few-public-methods
    """ Descriptors that can be applied to template fields for special processing. """

    # An image field should copy the resource but not transform into an image tag
    COPY_ONLY = 'copy-only'


class TemplateFields:  # pylint: disable=too-few-public-methods
    """ Reserved template field names. """

    # Required fields (system fields)

    # Populated by all generated pages
    PAGES = '_pages'
    # Populated by the current page number (1 being the first)
    PAGE_NUMBER = '_page_number'
    # Populated by the total number of pages
    PAGES_TOTAL = '_pages_total'
    # Populated by all generated cards on a single page
    CARDS = '_cards'
    # Populated by the CSS size class of a single card
    CARD_SIZE = '_card_size'
    # Populated by the content of a single card
    CARD_CONTENT = '_card_content'

    # Optional fields (user fields)

    # Populated by the current card index (1 being the first, also increments for duplicates)
    CARD_INDEX = '_card_index'
    # Populated by the current card copy index (1 being the first, not incremented for duplicates)
    CARD_COPY_INDEX = '_card_copy_index'
    # Populated by the row index of the current card (2 being the first- as CSV headers counts)
    CARD_ROW_INDEX = '_card_row_index'
    # Populated by the path of the template (if any) used to generate the current card
    CARD_TEMPLATE_PATH = '_card_template_path'
    # Populated by the total number of cards (duplicates count)
    CARDS_TOTAL = '_cards_total'

    # Used to include the contents of a file (e.g. include 'path/to/file.html')
    INCLUDE = 'include'
    # Used to include the contents of a file (similar to 'include', except this strips any newlines)
    INLINE = 'inline'
    # Populated by the current time and date (can specify a date/time format; e.g. date '%d %m %Y')
    DATE = 'date'

    # Populated by the version of the project (as defined in a definitions source)
    VERSION = '_version'
    # Populated by the version of the program
    PROGRAM_VERSION = '_program_version'
    # Populated by the title of the project (as defined in a definitions source)
    TITLE = '_title'
    # Populated by the description of the project (as defined in a definitions source)
    DESCRIPTION = '_description'
    # Populated by the copyright notice of the project (as defined in a definitions source)
    COPYRIGHT = '_copyright'


class CardSize:  # pylint: disable=too-few-public-methods
    """ Represents a card size. """

    def __init__(self, identifier: str, style: str, size_in_inches: tuple):
        self.identifier = identifier
        self.style = style
        self.size_in_inches = size_in_inches

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.identifier == other.identifier

        return False

    def __ne__(self, other):
        return not self.__eq__(other)


class CardSizes:
    """ Provides functions for retrieving card size objects. """

    @staticmethod
    def get_card_size(identifier: str) -> CardSize:
        """ Return the card size that matches the identifier. """

        if identifier is not None:
            if identifier == 'token':
                return CardSize(identifier, style='card-size-075x075', size_in_inches=(.75, .75))
            elif identifier == 'standard':
                return CardSize(identifier, style='card-size-25x35', size_in_inches=(2.5, 3.5))
            elif identifier == 'square':
                return CardSize(identifier, style='card-size-25x25', size_in_inches=(2.5, 2.5))
            elif identifier == 'lsquare':
                return CardSize(identifier, style='card-size-35x35', size_in_inches=(3.5, 3.5))
            elif identifier == 'standard-landscape':
                return CardSize(identifier, style='card-size-35x25', size_in_inches=(3.5, 2.5))
            elif identifier == 'jumbo':
                return CardSize(identifier, style='card-size-35x55', size_in_inches=(3.5, 5.5))
            elif identifier == 'domino':
                return CardSize(identifier, style='card-size-175x35', size_in_inches=(1.75, 3.5))
            elif identifier == 'page':
                return CardSize(identifier, style='card-size-page', size_in_inches=(7.5, 10.5))

        return None

    @staticmethod
    def get_default_card_size() -> CardSize:
        """ Return the default card size: standard (2.5x3.5 inches). """

        return CardSizes.get_card_size('standard')

    @staticmethod
    def get_page_size() -> CardSize:
        """ Return the full page size: 7.5x10.5 inches. """

        return CardSizes.get_card_size('page')
