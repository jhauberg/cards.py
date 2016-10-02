# coding=utf-8


class Columns:
    COUNT = '@count'                            # Determines how many cards should be generated
    TEMPLATE = '@template'                      # Determines which template to use for the front of the card (must be a filepath)
    TEMPLATE_BACK = '@template-back'            # Determines which template to use for the back of the card (must be a filepath)


class ColumnDescriptors:
    BACK_ONLY = '@back-only'                    # Descriptor that can be applied to a column to make its contents only be used when generating the back of the card


class TemplateFieldDescriptors:
    COPY_ONLY = '@copy-only'                    # Descriptor that can be applied to an image-field to prevent it from being transformed into an <img> tag (only keeping the image path and copying the image to the output directory)


class TemplateFields:
    # Required fields (system fields)
    PAGES = '_pages'                             # Field in index.html to be replaced with all generated pages
    PAGE_NUMBER = '_page_number'                 # Field in page.html to be replaced with current page number
    PAGES_TOTAL = '_pages_total'                 # Field in page.html to be replaced with total amount of pages
    CARDS = '_cards'                             # Field in page.html to be replaced with all generated cards for a single page
    CARD_SIZE = '_card_size'                     # Field in card.html to be replaced with the size-type of the card
    CARD_CONTENT = '_card_content'               # Field in card.html to be replaced with the generated content of the card

    # Optional fields (user fields)
    CARD_INDEX = '_card_index'                   # Optional field that is replaced with the index of the card (1 being the first index)
    CARD_COPY_INDEX = '_card_copy_index'         # Optional field that is replaced with the copy index of the card (1 being the first index). This is the same index for any instance of this card
    CARD_ROW_INDEX = '_card_row_index'           # Optional field that is replaced with the index of the card in the datasource (2 being the first index, since the CSV header counts as the first row)
    CARD_TEMPLATE_PATH = '_card_template_path'   # Optional field that is replaced with the path of the template used to generate the card
    CARDS_TOTAL = '_cards_total'                 # Optional field that is replaced with the total amount of all generated cards

    INCLUDE = 'include'                          # Optional field that is replaced with the contents of a file (content is copied *as is*)
    INLINE = 'inline'                            # Optional field that works like 'include', except that it strips any excess whitespace from each line in the file

    VERSION = '_version'                         # Optional field that is replaced with the version identifier of the project
    PROGRAM_VERSION = '_program_version'         # Optional field that is replaced with the version identifier of the program
    TITLE = '_title'                             # Optional field that is replaced with the title of the project
    DESCRIPTION = '_description'                 # Optional field that is replaced with the description of the project
    COPYRIGHT = '_copyright'                     # Optional field that is replaced with the copyright notice for the project


class CardSize:
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
