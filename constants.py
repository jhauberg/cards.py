# coding=utf-8


class Columns:
    COUNT = '@count'                            # Determines how many cards should be generated
    TEMPLATE = '@template'                      # Determines which template to use for the front of the card (must be a filepath)
    TEMPLATE_BACK = '@template-back'            # Determines which template to use for the back of the card (must be a filepath)


class ColumnDescriptors:
    BACK_ONLY = '@back-only'                    # Descriptor that can be applied to a column to make its contents only be used when generating the back of the card


class TemplateFields:
    # Required fields (system fields)
    PAGES = 'pages'                             # Field in index.html to be replaced with all generated pages
    CARDS = 'cards'                             # Field in page.html to be replaced with all generated cards for a single page
    CARD_SIZE = 'card_size'                     # Field in card.html to be replaced with the size-type of the card
    CARD_CONTENT = 'card_content'               # Field in card.html to be replaced with the generated content of the card

    # Optional fields (user fields)
    CARD_INDEX = 'card_index'                   # Optional field that is replaced with the index of the card (1 being the first index)
    CARD_ROW_INDEX = 'card_row_index'           # Optional field that is replaced with the index of the card in the datasource (2 being the first index, since the CSV header counts as the first row)
    CARD_TEMPLATE_PATH = 'card_template_path'   # Optional field that is replaced with the path of the template used to generate the card
    CARDS_TOTAL = 'cards_total'                 # Optional field that is replaced with the total count of all generated cards
    VERSION = 'version'                         # Optional field that is replaced with the version identifier of the project
    PROGRAM_VERSION = 'program_version'         # Optional field that is replaced with the version identifier of the program
    TITLE = 'title'                             # Optional field that is replaced with the title of the project
    DESCRIPTION = 'description'                 # Optional field that is replaced with the description of the project
    COPYRIGHT = 'copyright'                     # Optional field that is replaced with the copyright notice for the project


class TemplateFieldDescriptors:
    COPY_ONLY = '@copy-only'                    # Descriptor that can be applied to an image-field to prevent it from being transformed into an <img> tag (only keeping the image path and copying the image to the output directory)
