# coding=utf-8

"""
Generates print-ready cards for your tabletop game.

https://github.com/jhauberg/cards.py

Copyright 2015 Jacob Hauberg Hansen.
License: MIT (see LICENSE)
"""

import os
import sys
import argparse
import csv
import shutil
import subprocess

from urllib.parse import urlparse

from util import WarningContext, warn, lower_first_row, create_missing_directories_if_necessary

from template import fill_template_fields, fill_card_front, fill_card_back
from template import template_from_data, template_from_path
from template import get_column_content, get_sized_card

from constants import Columns, TemplateFields

__version_info__ = ('0', '4', '9')
__version__ = '.'.join(__version_info__)


def is_url(url):
    return urlparse(url).scheme != ""


def find_file_path(name: str, paths: list) -> (bool, str):
    """ Look for a path with 'name' in the filename in the specified paths.

        If found, returns the first discovered path to a file containing the specified name,
        otherwise returns the first potential path to where it looked for one.
    """

    found_path = None
    first_potential_path = None

    if len(paths) > 0:
        # first look for a file simply named exactly the specified name- we'll just use
        # the first provided path and assume that this is the main directory
        path_directory = os.path.dirname(paths[0])

        potential_path = os.path.join(path_directory, name)

        if os.path.isfile(potential_path):
            # we found one
            found_path = potential_path

    if found_path is None:
        # then attempt looking for a file named like 'some_file.the-name.csv' for each
        # provided path until a file is found, if any
        for path in paths:
            path_components = os.path.splitext(path)

            potential_path = path_components[0] + '.' + name

            if first_potential_path is None:
                first_potential_path = potential_path

            if os.path.isfile(potential_path):
                # we found one
                found_path = potential_path

                break

    return ((True, found_path) if found_path is not None else
            (False, first_potential_path))


def copy_images_to_output_directory(
        image_paths: list,
        root_path: str,
        output_path: str,
        verbosely: 'show warnings'=False) -> None:
    """ Copies all provided images to the specified output path, keeping the directory structure
        intact for each image.
    """
    context = os.path.basename(root_path)

    for image_path in image_paths:
        # copy each relatively specified image (if an image is specified
        # using an absolute path, assume that it should not be copied)
        if os.path.isabs(image_path) or is_url(image_path):
            if verbosely:
                warn('An image was not copied to the output directory since it was specified with '
                     'an absolute path: \033[4;33m\'{0}\'\033[0m'.format(image_path),
                     in_context=WarningContext(context))
        else:
            # if the image path is not an absolute path, assume
            # that it's located relative to where the data is
            relative_source_path = os.path.join(
                os.path.dirname(root_path), image_path)

            if os.path.isfile(relative_source_path):
                # only copy if the file actually exists
                relative_destination_path = os.path.join(
                    output_path, image_path)

                # make sure any missing directories are created as needed
                create_missing_directories_if_necessary(
                    os.path.dirname(relative_destination_path))

                shutil.copyfile(relative_source_path, relative_destination_path)
            else:
                warn('One or more cards contain an image reference that does not exist: '
                     '\033[4;31m\'{0}\'\033[0m'.format(relative_source_path),
                     in_context=WarningContext(context),
                     as_error=True)


def get_definitions(path: str, verbosely: 'show warnings'=False) -> dict:
    definitions = {}

    if path is not None and len(path) > 0:
        if not os.path.isfile(path):
            if verbosely:
                warn('No definitions file was found at: \033[4;31m\'{0}\'\033[0m'.format(path),
                     as_error=True)
        else:
            with open(path) as f:
                # skip the first row (column headers)
                f.readline()

                # map all rows into key-value pairs (assume no more than 2 columns are present)
                definitions = {k: v for k, v in csv.reader(f)}

    return definitions


def get_page(page_number: int, cards: str, page_template: str) -> str:
    numbered_page = fill_template_fields('page_number', str(page_number), page_template)

    return fill_template_fields(TemplateFields.CARDS, cards, numbered_page)


def fill_metadata_field(field_name: str, field_value: str, in_template: str) -> str:
    field_value = field_value.strip()
    field_visibility = 'hidden' if len(field_value) == 0 else 'visible'

    in_template = fill_template_fields('{0}_visibility'.format(field_name), field_visibility, in_template)
    in_template = fill_template_fields(field_name, field_value, in_template)

    return in_template


def main():
    # required arguments
    data_paths = args['input_paths']

    # optional arguments
    output_path = args['output_path']
    output_filename = args['output_filename']
    definitions_path = args['definitions_path']
    force_page_breaks = args['force_page_breaks']
    disable_cut_guides = bool(args['disable_cut_guides'])
    disable_footer = bool(args['disable_footer'])
    disable_backs = bool(args['disable_backs'])
    is_verbose = bool(args['verbose'])

    disable_auto_templating = False

    if definitions_path is None:
        # no definitions file has been explicitly specified, so try looking for it automatically
        found, potential_definitions_path = find_file_path('definitions.csv', data_paths)

        if found and potential_definitions_path is not None:
            definitions_path = potential_definitions_path

            warn('No definitions have been specified. Using definitions automatically found at: '
                 '\033[4;33m\'{0}\'\033[0m'.format(definitions_path))

    definitions = get_definitions(definitions_path)

    # get the current working directory (though not the ACTUAL working directory,
    # we pretend that the location of this script file is the working directory and base path.
    # this ensures that the relative paths still work, even if this script should be executed
    # through a shell script or similar where the working directory might not be where this
    # script is located)
    cwd = os.path.dirname(os.path.realpath(__file__))

    with open(os.path.join(cwd, 'templates/card.html')) as c:
        # load the container template for a card
        card = c.read()

        cut_guides_visibility = 'hidden' if disable_cut_guides else 'visible'

        card = fill_template_fields('cut_guides_visibility', cut_guides_visibility, card)

    with open(os.path.join(cwd, 'templates/page.html')) as p:
        # load the container template for a page
        page = p.read()

        footer_visibility = 'hidden' if disable_footer else 'visible'

        page = fill_template_fields('footer_visibility', footer_visibility, page)

    with open(os.path.join(cwd, 'templates/index.html')) as i:
        # load the container template for the final html file
        index = i.read()

    # error template for the output on cards specifying a template that was not found,
    # or could not be opened
    with open(os.path.join(cwd, 'templates/error/could_not_open.html')) as e:
        template_not_opened = e.read()

    # error template for the output on cards when a default template has not been specified,
    # and the card hasn't specified one either
    with open(os.path.join(cwd, 'templates/error/not_provided.html')) as e:
        template_not_provided = e.read()

    # error template for the output on cards when a template back has not been specified,
    # and backs are not disabled
    with open(os.path.join(cwd, 'templates/error/back_not_provided.html')) as e:
        template_back_not_provided = e.read()

    CARD_SIZES = {
        '25x35': 'card-size-25x35',
        '35x55': 'card-size-35x55'
    }

    default_card_size = CARD_SIZES['25x35']

    # 3x3 cards is the ideal fit for standard sized cards on an A4 page
    MAX_CARDS_PER_ROW = 3
    MAX_CARDS_PER_COLUMN = 3
    MAX_CARDS_PER_PAGE = MAX_CARDS_PER_ROW * MAX_CARDS_PER_COLUMN

    # buffer that will contain at most MAX_CARDS_PER_PAGE amount of cards
    cards = ''
    # buffer that will contain at most MAX_CARDS_PER_PAGE amount of card backs
    backs = ''
    # buffer of a row of backs that is filled in reverse to support double-sided printing
    backs_row = ''
    # buffer for all generated pages
    pages = ''

    # incremented each time a card is generated, but reset to 0 for each page
    cards_on_page = 0
    # incremented each time a card is generated
    cards_total = 0
    # incremented each time a page is generated
    pages_total = 0

    # dict of all image paths discovered for each context during card generation
    context_image_paths = {}

    for data_path in data_paths:
        # define the context as the base filename of the current data- useful when troubleshooting
        context = os.path.basename(data_path)

        card_size = default_card_size

        # empty backs may be necessary to fill in empty spots on a page to ensure
        # that the layout remains correct
        empty_back = get_sized_card(card, card_size, content='')

        image_paths = []

        with open(data_path) as f:
            # read the csv as a dict, so that we can access each column by name
            data = csv.DictReader(lower_first_row(f))

            if disable_auto_templating:
                default_template = None
            else:
                # get a fitting template for the first row of data
                default_template = template_from_data(data)

                # reset the iterator
                f.seek(0)

                data = csv.DictReader(lower_first_row(f))

            if default_template is None and Columns.TEMPLATE not in data.fieldnames:
                if is_verbose:
                    warn('A default template was not provided and auto-templating is not enabled.'
                         'Cards will not be generated correctly.',
                         in_context=WarningContext(context))

            if not disable_backs and Columns.TEMPLATE_BACK in data.fieldnames:
                if is_verbose:
                    warn('Assuming card backs should be generated since ' +
                         '\'' + Columns.TEMPLATE_BACK + '\' appears in data. '
                         'You can disable card backs by specifying the --disable-backs argument.',
                         in_context=WarningContext(context))
            else:
                if is_verbose:
                    warn('Card backs will not be generated since '
                         '\'' + Columns.TEMPLATE_BACK + '\' does not appear in data.',
                         in_context=WarningContext(context))

                disable_backs = True

            row_index = 1

            for row in data:
                # since the column names counts as a row, and most editors
                # do not use a zero-based row index, the first row == 2
                row_index += 1

                # determine how many instances of this card to generate
                # (defaults to a single instance if not specified)
                count = row.get(Columns.COUNT, '1')

                if len(count.strip()) > 0:
                    # the count column has content, so attempt to parse it
                    try:
                        count = int(count)
                    except ValueError:
                        # count could not be determined, so default to skip this card
                        count = 0

                        warn('The card provided an indeterminable count and was was skipped.',
                             in_context=WarningContext(context, row_index))
                else:
                    # the count column did not have content, so default count to 1
                    count = 1

                # if a negative count is specified, treat it as 0
                count = count if count > 0 else 0

                if count > 1000:
                    # arbitrarily determined amount- but if the count is really high
                    # it might just be an error
                    warn('The card has specified a high count: {0}. '
                         'Are you sure you want to continue?'.format(count),
                         in_context=WarningContext(context, row_index))

                    answer = input('(Y)es or (n)o?').strip().lower()

                    if answer == 'n' or answer == 'no':
                        # break out and continue with the next card
                        continue

                for i in range(count):
                    card_index = cards_total + 1

                    # determine which template to use for this card, if any
                    template_path = get_column_content(
                        row, Columns.TEMPLATE, definitions, default_content=None)

                    if template_path is not None and len(template_path) > 0:
                        template, not_found, template_path = template_from_path(
                            template_path, relative_to_path=data_path)

                        if not_found:
                            template = template_not_opened

                            warn('The card provided a template that could not be opened: '
                                 '\033[4;31m\'{0}\'\033[0m'.format(template_path),
                                 in_context=WarningContext(context, row_index, card_index),
                                 as_error=True)
                        elif is_verbose and len(template) == 0:
                            warn('The card provided a template that appears to be empty: '
                                 '\033[4;33m\'{0}\'\033[0;33m.'.format(template_path),
                                 in_context=WarningContext(context, row_index, card_index))
                    else:
                        template = default_template

                        if template is not None and is_verbose:
                            warn('The card did not provide a template. '
                                 'The card will use an auto-template instead.'
                                 .format(template_path),
                                 in_context=WarningContext(context, row_index, card_index))

                    if template is None:
                        template = template_not_provided

                        warn('The card did not provide a template.',
                             in_context=WarningContext(context, row_index, card_index),
                             as_error=True)

                    card_content, found_image_paths, missing_fields = fill_card_front(
                        template, template_path,
                        row, row_index, card_index,
                        definitions)

                    if (template is not template_not_provided and
                        template is not template_not_opened):
                        missing_fields_in_template = missing_fields[0]
                        missing_fields_in_data = missing_fields[1]

                        if len(missing_fields_in_template) > 0 and is_verbose:
                            warn('The template does not contain the fields: {0}'
                                 .format(missing_fields_in_template),
                                 in_context=WarningContext(context, row_index, card_index))

                        if len(missing_fields_in_data) > 0 and is_verbose:
                            warn('The template contains fields that are not '
                                 'present for this card: {0}'
                                 .format(missing_fields_in_data),
                                 in_context=WarningContext(context, row_index, card_index))

                    image_paths.extend(found_image_paths)

                    current_card = get_sized_card(card, card_size, card_content)

                    cards += current_card

                    cards_on_page += 1
                    cards_total += 1

                    if not disable_backs:
                        template_path_back = get_column_content(
                            row, Columns.TEMPLATE_BACK, definitions, default_content=None)

                        template_back = None

                        if template_path_back is not None and len(template_path_back) > 0:
                            template_back, not_found, template_path_back = template_from_path(
                                template_path_back, relative_to_path=data_path)

                            if not_found:
                                template_back = template_not_opened

                                warn('The card provided a back template that could not be opened: '
                                     '\033[4;31m\'{0}\'\033[0m'.format(template_path_back),
                                     in_context=WarningContext(context, row_index, card_index),
                                     as_error=True)
                            elif is_verbose and len(template_back) == 0:
                                warn('The card provided a back template that appears to be empty: '
                                     '\033[4;33m\'{0}\'\033[0;33m.'.format(template_path_back),
                                     in_context=WarningContext(context, row_index, card_index))

                        if template_back is None:
                            template_back = template_back_not_provided

                        back_content, found_image_paths, missing_fields = fill_card_back(
                            template_back, template_path_back,
                            row, row_index, card_index,
                            definitions)

                        if (template_back is not template_back_not_provided and
                            template_back is not template_not_opened):
                            missing_fields_in_template = missing_fields[0]
                            missing_fields_in_data = missing_fields[1]

                            if len(missing_fields_in_template) > 0 and is_verbose:
                                warn('The back template does not contain the fields: {0}'
                                     .format(missing_fields_in_template),
                                     in_context=WarningContext(context, row_index, card_index))

                            if len(missing_fields_in_data) > 0 and is_verbose:
                                warn('The back template contains fields '
                                     'that are not present for this card: {0}'
                                     .format(missing_fields_in_data),
                                     in_context=WarningContext(context, row_index, card_index))

                        image_paths.extend(found_image_paths)

                        current_card_back = get_sized_card(card, card_size, back_content)

                        # prepend this card back to the current line of backs
                        backs_row = current_card_back + backs_row

                        # card backs are prepended rather than appended to
                        # ensure correct layout when printing doublesided

                        if cards_on_page % MAX_CARDS_PER_ROW is 0:
                            # a line has been filled- append the 3 card backs
                            # to the page in the right order
                            backs += backs_row

                            # reset to prepare for the next line
                            backs_row = ''

                    if cards_on_page == MAX_CARDS_PER_PAGE:
                        # add another page full of cards
                        pages += get_page(pages_total + 1, cards, page)
                        pages_total += 1

                        if not disable_backs:
                            # and one full of backs
                            pages += get_page(pages_total + 1, backs, page)
                            pages_total += 1

                            # reset to prepare for the next page
                            backs = ''

                        # reset to prepare for the next page
                        cards_on_page = 0
                        cards = ''

        if (force_page_breaks or data_path is data_paths[-1]) and cards_on_page > 0:
            # in case we're forcing pagebreaks for each datasource, or we're on the last datasource
            # and there's still cards remaining, then do a pagebreak and fill those into a new page
            pages += get_page(pages_total + 1, cards, page)
            pages_total += 1

            if not disable_backs:
                cards_on_last_row = cards_on_page % MAX_CARDS_PER_ROW

                if cards_on_last_row is not 0:
                    # less than MAX_CARDS_PER_ROW cards were added to the current line,
                    # so we have to add additional blank filler cards to ensure a correct layout

                    remaining_backs = MAX_CARDS_PER_ROW - cards_on_last_row

                    while remaining_backs > 0:
                        # keep adding empty filler card backs until we've filled a row
                        backs_row = empty_back + backs_row

                        remaining_backs -= 1

                backs += backs_row

                backs_row = ''

                # fill another page with the backs
                pages += get_page(pages_total + 1, backs, page)
                pages_total += 1

                backs = ''

            # reset to prepare for the next page
            cards_on_page = 0
            cards = ''

        # ensure there are no duplicate image paths, since that would just
        # cause unnecessary copy operations
        context_image_paths[data_path] = list(set(image_paths))

    if output_path is None:
        # output to current working directory unless otherwise specified
        output_path = ''

    output_directory_name = 'generated'

    # construct the final output path
    output_path = os.path.join(output_path, output_directory_name)

    # ensure all directories exist or created if missing
    create_missing_directories_if_necessary(output_path)

    # get the grammar right
    pages_or_page = 'pages' if pages_total > 1 else 'page'
    cards_or_card = 'cards' if cards_total > 1 else 'card'

    # begin writing pages to the output file (overwriting any existing file)
    with open(os.path.join(output_path, output_filename), 'w') as result:
        # on all pages, fill any {{ cards_total }} fields
        pages = fill_template_fields(
            field_name=TemplateFields.CARDS_TOTAL,
            field_value=str(cards_total),
            in_template=pages)

        # pages must be inserted prior to filling metadata fields,
        # since each page may contain fields that should be filled
        index = fill_template_fields(
            field_name=TemplateFields.PAGES,
            field_value=pages,
            in_template=index)

        index = fill_template_fields(
            field_name=TemplateFields.PROGRAM_VERSION,
            field_value=__version__,
            in_template=index)

        # note that most of these fields could potentially be filled already when first getting the
        # page template; however, we instead do it as the very last thing to allow cards
        # using these fields (even if that might only be on rare occasions)
        title = definitions.get(TemplateFields.TITLE, '').strip()

        if len(title) == 0:
            title = '{0} {1} on {2} {3}'.format(
                cards_total, cards_or_card,
                pages_total, pages_or_page)

        description = definitions.get(TemplateFields.DESCRIPTION, '')
        copyright_notice = definitions.get(TemplateFields.COPYRIGHT, '')
        version_identifier = definitions.get(TemplateFields.VERSION, '')

        index = fill_metadata_field(TemplateFields.TITLE, title, in_template=index)
        index = fill_metadata_field(TemplateFields.DESCRIPTION, description, in_template=index)
        index = fill_metadata_field(TemplateFields.COPYRIGHT, copyright_notice, in_template=index)
        index = fill_metadata_field(TemplateFields.VERSION, version_identifier, in_template=index)

        result.write(index)

    # make sure to copy the css file to the output directory
    shutil.copyfile(os.path.join(cwd, 'templates/index.css'),
                    os.path.join(output_path, 'index.css'))

    # and copy the additional image resources
    resources_path = os.path.join(output_path, 'resources')
    # creating the directory if needed
    create_missing_directories_if_necessary(resources_path)

    shutil.copyfile(os.path.join(cwd, 'templates/resources/guide.svg'),
                    os.path.join(resources_path, 'guide.svg'))

    shutil.copyfile(os.path.join(cwd, 'cards.svg'),
                    os.path.join(resources_path, 'cards.svg'))

    # additionally, copy all referenced images to the output directory as well
    # (making sure to keep their original directory structure in relation to their context)
    for context in context_image_paths:
        copy_images_to_output_directory(
            context_image_paths[context], context, output_path, verbosely=True)

    print('Generated {0} {1} on {2} {3}. See \033[4m\'{4}/index.html\'\033[0m.'
          .format(cards_total, cards_or_card,
                  pages_total, pages_or_page,
                  output_path))

    if sys.platform.startswith('darwin'):
        subprocess.call(('open', output_path))
    elif os.name == 'nt':
        subprocess.call(('start', output_path), shell=True)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', output_path))


def setup_arguments() -> None:
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

    parser.add_argument('--force-page-breaks', dest='force_page_breaks', required=False,
                        default=False, action='store_true',
                        help='Force a page break for each datasource')

    parser.add_argument('--disable-cut-guides', dest='disable_cut_guides', required=False,
                        default=False, action='store_true',
                        help='Don\'t show cut guides on the margins of the cards')

    parser.add_argument('--disable-footer', dest='disable_footer', required=False,
                        default=False, action='store_true',
                        help='Don\'t show a footer on the generated pages')

    parser.add_argument('--disable-backs', dest='disable_backs', required=False,
                        default=False, action='store_true',
                        help='Don\'t generate card backs')

    parser.add_argument('--verbose', dest='verbose', required=False,
                        default=False, action='store_true',
                        help='Show more information')

    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__,
                        help='Show the program\'s version')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Generates print-ready cards for your tabletop game.')

    setup_arguments()

    args = vars(parser.parse_args())

    main()
