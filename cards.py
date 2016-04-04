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

from util import warn, lower_first_row, create_missing_directories_if_necessary
from meta import Metadata

from template import fill_template_field, fill_card_front, fill_card_back
from template import template_from_data, template_from_path
from template import get_sized_card

__version_info__ = ('0', '4', '5')
__version__ = '.'.join(__version_info__)


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

    for image_path in image_paths:
        # copy each relatively specified image (if an image is specified
        # using an absolute path, assume that it should not be copied)
        if os.path.isabs(image_path):
            if verbosely:
                warn('An image was not copied to the output directory since it was specified with '
                     'an absolute path: \033[4;31m\'{0}\'\033[0m'.format(image_path))
        else:
            # if the image path is not an absolute path, assume
            # that it's located relative to where the data is
            relative_source_path = os.path.join(
                os.path.dirname(root_path), image_path)

            relative_destination_path = os.path.join(
                output_path, image_path)

            # make sure any missing directories are created as needed
            create_missing_directories_if_necessary(
                os.path.dirname(relative_destination_path))

            if os.path.isfile(relative_source_path):
                # only copy if the file actually exists
                shutil.copyfile(relative_source_path, relative_destination_path)
            else:
                warn('One or more cards contain an image reference that does not exist: '
                     '\033[4;31m\'{0}\'\033[0m'.format(relative_source_path),
                     as_error=True)


def setup_arguments(parser: argparse.ArgumentParser) -> None:
    """ Sets up required and optional program arguments. """

    # required arguments
    parser.add_argument('-f', '--input-filename', dest='input_paths', required=True, nargs='*',
                        help='One or more paths to CSV files containing card data')

    # optional arguments
    parser.add_argument('-o', '--output-folder', dest='output_path', required=False,
                        help='Path to a directory in which the pages will be generated '
                             '(a sub-directory will be created)')

    parser.add_argument('-m', '--metadata-filename', dest='metadata_path', required=False,
                        help='Path to a CSV file containing metadata')

    parser.add_argument('--force-page-breaks', dest='force_page_breaks', required=False,
                        default=False, action='store_true',
                        help='Force a page break for each datasource')

    parser.add_argument('--disable-cut-guides', dest='disable_cut_guides', required=False,
                        default=False, action='store_true',
                        help='Don\'t show cut guides on the margins of the generated pages')

    parser.add_argument('--disable-backs', dest='disable_backs', required=False,
                        default=False, action='store_true',
                        help='Don\'t generate card backs')

    parser.add_argument('--verbose', dest='verbose', required=False,
                        default=False, action='store_true',
                        help='Show more information')

    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__,
                        help='Show the program\'s version, then exit')


def main(argv):
    parser = argparse.ArgumentParser(
        description='Generates print-ready cards for your tabletop game.')

    setup_arguments(parser)

    args = vars(parser.parse_args())

    # required arguments
    data_paths = args['input_paths']

    # optional arguments
    output_path = args['output_path']
    metadata_path = args['metadata_path']
    force_page_breaks = args['force_page_breaks']
    disable_cut_guides = bool(args['disable_cut_guides'])
    disable_backs = bool(args['disable_backs'])
    is_verbose = bool(args['verbose'])

    disable_auto_templating = False

    # get the current working directory (though not the ACTUAL working directory,
    # we pretend that the location of this script file is the working directory and base path.
    # this ensures that the relative paths still work, even if this script should be executed
    # through a shell script or similar where the working directory might not be where this
    # script is located)
    cwd = os.path.dirname(os.path.realpath(__file__))

    with open(os.path.join(cwd, 'templates/card.html')) as c:
        # load the container template for a card
        card = c.read()

    with open(os.path.join(cwd, 'templates/page.html')) as p:
        # load the container template for a page
        page = p.read()

        if disable_cut_guides:
            # simply add a css rule to hide them
            cut_guides_display = 'style="display: none"'
        else:
            cut_guides_display = 'style="display: block"'

        page = page.replace('{{cut_guides_style}}', cut_guides_display)

    with open(os.path.join(cwd, 'templates/index.html')) as i:
        # load the container template for the final html file
        index = i.read()

    if metadata_path is None:
        # no metadata has been explicitly specified, so try looking for it where the data is located
        found, potential_metadata_path = find_file_path('meta.csv', data_paths)

        if potential_metadata_path is not None:
            if not found:
                if is_verbose:
                    warn('No metadata was found. You can provide it at e.g.: '
                         '\033[4;33m\'{0}\'\033[0m'.format(potential_metadata_path))
            else:
                warn('Using metadata found at: '
                     '\033[4;33m\'{0}\'\033[0m'.format(potential_metadata_path))

                metadata_path = potential_metadata_path

    metadata = Metadata.from_file(metadata_path, verbosely=is_verbose)

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
        empty_back = card.replace('{{size}}', card_size)
        empty_back = empty_back.replace('{{content}}', '')

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

            if default_template is None and '@template' not in data.fieldnames:
                if is_verbose:
                    warn('A default template was not provided and auto-templating is not enabled.'
                         'Cards will not be generated correctly.',
                         in_context=context)

            if not disable_backs and '@template-back' in data.fieldnames:
                if is_verbose:
                    warn('Assuming card backs should be generated since \'@template-back\' '
                         'appears in the data. You can disable card backs by specifying the '
                         '--disable-backs argument.',
                         in_context=context)
            else:
                if is_verbose:
                    warn('Card backs will not be generated since \'@template-back\' does not '
                         'appear in the data.',
                         in_context=context)

                disable_backs = True

            row_index = 1

            for row in data:
                # since the column names counts as a row, and most editors
                # do not use a zero-based row index, the first row == 2
                row_index += 1

                # determine how many instances of this card to generate
                # (defaults to a single instance if not specified)
                count = int(row.get('@count', 1))
                # if a negative count is specified, treat it as 0
                count = count if count > 0 else 0

                for i in range(count):
                    card_index = cards_total + 1

                    # determine which template to use for this card, if any
                    template_path = row.get('@template', None)

                    if template_path is not None and len(template_path) > 0:
                        template, not_found, template_path = template_from_path(
                            template_path, relative_to_path=data_path)

                        if not_found:
                            template = template_not_opened

                            warn('The card at #{0} (row {1}) provided a template that could not '
                                 'be opened: \033[4;31m\'{2}\'\033[0m'.format(
                                     card_index, row_index, template_path),
                                 in_context=context,
                                 as_error=True)
                        elif is_verbose and len(template) == 0:
                            warn('The template at \033[4;33m\'{0}\'\033[0;33m for the card at '
                                 '#{1} (row {2}) appears to be empty. Blank cards may occur.'
                                 .format(template_path, card_index, row_index),
                                 in_context=context)
                    else:
                        template = default_template

                    if template is None:
                        template = template_not_provided

                        warn('The card at #{0} (row {1}) did not provide a template.'
                             .format(card_index, row_index),
                             in_context=context,
                             as_error=True)

                    card_content, found_image_paths, missing_fields = fill_card_front(
                        template, template_path, row, row_index, card_index, metadata)

                    if (template is not template_not_provided and
                        template is not template_not_opened):
                        missing_fields_in_template = missing_fields[0]
                        missing_fields_in_data = missing_fields[1]

                        if len(missing_fields_in_template) > 0 and is_verbose:
                            warn('The template for the card at #{0} (row {1}) does not contain '
                                 'the fields: {2}'
                                 .format(card_index, row_index, missing_fields_in_template),
                                 in_context=context)

                        if len(missing_fields_in_data) > 0 and is_verbose:
                            warn('The template for the card at #{0} (row {1}) contains fields that '
                                 'are not present for this card: {2}'
                                 .format(card_index, row_index, missing_fields_in_data),
                                 in_context=context)

                    image_paths.extend(found_image_paths)

                    current_card = get_sized_card(card, card_size, card_content)

                    cards += current_card

                    cards_on_page += 1
                    cards_total += 1

                    if not disable_backs:
                        template_path_back = row.get('@template-back')
                        template_back = None

                        if template_path_back is not None and len(template_path_back) > 0:
                            template_back, not_found, template_path_back = template_from_path(
                                template_path_back, relative_to_path=data_path)

                            if not_found:
                                template_back = template_not_opened

                                warn('The card at #{0} (row {1}) provided a back template that '
                                     'could not be opened: \033[4;31m\'{2}\'\033[0m'.format(
                                         card_index, row_index, template_path_back),
                                     in_context=context,
                                     as_error=True)
                            elif is_verbose and len(template_back) == 0:
                                warn('The template at \033[4;33m\'{0}\'\033[0;33m for the card at '
                                     '#{1} (row {2}) appears to be empty. Blank cards may occur.'
                                     .format('template/template_path', 1, 1),
                                     in_context=context)

                        if template_back is None:
                            template_back = template_back_not_provided

                        back_content, found_image_paths, missing_fields = fill_card_back(
                            template_back, template_path_back, row, row_index, card_index, metadata)

                        if (template_back is not template_back_not_provided and
                            template_back is not template_not_opened):
                            missing_fields_in_template = missing_fields[0]
                            missing_fields_in_data = missing_fields[1]

                            if len(missing_fields_in_template) > 0 and is_verbose:
                                warn('The back template for the card at #{0} (row {1}) does not '
                                     'contain the fields: {2}'
                                     .format(card_index, row_index, missing_fields_in_template),
                                     in_context=context)

                            if len(missing_fields_in_data) > 0 and is_verbose:
                                warn('The back template for the card at #{0} (row {1}) contains '
                                     'fields that are not present for this card: {2}'
                                     .format(card_index, row_index, missing_fields_in_data),
                                     in_context=context)

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
                        pages += page.replace('{{cards}}', cards)
                        pages_total += 1

                        if not disable_backs:
                            # and one full of backs
                            pages += page.replace('{{cards}}', backs)
                            pages_total += 1

                            # reset to prepare for the next page
                            backs = ''

                        # reset to prepare for the next page
                        cards_on_page = 0
                        cards = ''

        if (force_page_breaks or data_path is data_paths[-1]) and cards_on_page > 0:
            # in case we're forcing pagebreaks for each datasource, or we're on the last datasource
            # and there's still cards remaining, then do a pagebreak and fill those into a new page
            pages += page.replace('{{cards}}', cards)
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
                pages += page.replace('{{cards}}', backs)
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

    # construct the final output path
    output_path = os.path.join(output_path, 'generated')

    # ensure all directories exist or created if missing
    create_missing_directories_if_necessary(output_path)

    # get the grammar right
    pages_or_page = 'pages' if pages_total > 1 else 'page'
    cards_or_card = 'cards' if cards_total > 1 else 'card'

    # begin writing pages to the output file (overwriting any existing file)
    with open(os.path.join(output_path, 'index.html'), 'w') as result:
        title = metadata.title

        if not title or len(title) == 0:
            title = 'cards.py: {0} {1} on {2} {3}'.format(
                cards_total, cards_or_card,
                pages_total, pages_or_page)

        # on all pages, fill any {{cards_total}} fields
        pages, occurences = fill_template_field(
            field_name='cards_total',
            field_value=str(cards_total),
            in_template=pages)

        index = index.replace('{{pages}}', pages)
        # pages must be inserted prior to filling metadata fields,
        # since each page may contain fields that should be filled
        index = index.replace('{{title}}', title)
        index = index.replace('{{description}}', metadata.description)
        index = index.replace('{{copyright}}', metadata.copyright_notice)

        result.write(index)

    # make sure to copy the css file to the output directory
    shutil.copyfile(os.path.join(cwd, 'templates/index.css'),
                    os.path.join(output_path, 'index.css'))

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

if __name__ == "__main__":
    main(sys.argv)
