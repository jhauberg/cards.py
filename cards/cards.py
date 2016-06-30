# coding=utf-8

"""
Generates print-ready cards for your tabletop game.

https://github.com/jhauberg/cards.py

Copyright 2015 Jacob Hauberg Hansen.
License: MIT (see LICENSE)
"""

import os
import sys
import csv
import shutil
import subprocess

from urllib.parse import urlparse

from cards.template import fill_template_fields, fill_card_front, fill_card_back
from cards.template import template_from_data, template_from_path
from cards.template import get_column_content, get_sized_card

from cards.constants import Columns, TemplateFields

from cards.util import (
    WarningContext, warn, lower_first_row,
    create_missing_directories_if_necessary
)

from cards.version import __version__


def is_url(url):
    return urlparse(url).scheme != ""


def open_path(path: str) -> None:
    """ Opens a path in a cross-platform manner;
        showing e.g. Finder on MacOS or Explorer on Windows
    """

    if sys.platform.startswith('darwin'):
        subprocess.call(('open', path))
    elif os.name == 'nt':
        subprocess.call(('start', path), shell=True)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', path))


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


def warn_image_not_copied(context: WarningContext, image_path: str) -> None:
    warn('An image was not copied to the output directory since it was specified with '
         'an absolute path: \033[4;33m\'{0}\'\033[0m'.format(image_path),
         in_context=context)


def warn_missing_image(context: WarningContext, image_path: str) -> None:
    warn('One or more cards contain an image reference that does not exist: '
         '\033[4;31m\'{0}\'\033[0m'.format(image_path),
         in_context=context,
         as_error=True)


def warn_bad_definitions_file(definitions_path: str) -> None:
    warn('No definitions file was found at: '
         '\033[4;31m\'{0}\'\033[0m'.format(definitions_path),
         as_error=True)


def warn_using_automatically_found_definitions(definitions_path: str) -> None:
    warn('No definitions have been specified. Using definitions automatically found at: '
         '\033[4;33m\'{0}\'\033[0m'.format(definitions_path))


def warn_assume_backs(context: WarningContext) -> None:
    warn('Assuming card backs should be generated since ' +
         '\'' + Columns.TEMPLATE_BACK + '\' appears in data. '
         'You can disable card backs by specifying the --disable-backs argument.',
         in_context=context)


def warn_no_backs(context: WarningContext) -> None:
    warn('Card backs will not be generated since \'' + Columns.TEMPLATE_BACK + '\''
         ' does not appear in data.',
         in_context=context)


def warn_indeterminable_count(context: WarningContext) -> None:
    warn('The card provided an indeterminable count and was skipped.',
         in_context=context)


def warn_missing_default_template(context: WarningContext) -> None:
    warn('A template was not provided and auto-templating is not enabled.'
         'Cards will not be generated correctly.',
         in_context=context)


def warn_missing_template(context: WarningContext) -> None:
    warn('The card did not provide a template.',
         in_context=context,
         as_error=True)


def warn_empty_template(context: WarningContext,
                        template_path: str,
                        is_back_template: bool=False) -> None:
    warning = ('The card provided a back template that appears to be empty: '
               '\033[4;33m\'{0}\'\033[0;33m.'
               if is_back_template else
               'The card provided a template that appears to be empty: '
               '\033[4;33m\'{0}\'\033[0;33m. '
               'The card will use an auto-template instead, if possible.')

    warn(warning.format(template_path), in_context=context)


def warn_using_auto_template(context: WarningContext) -> None:
    warn('The card did not provide a template. The card will use an auto-template instead.',
         in_context=context)


def warn_unknown_fields_in_template(context: WarningContext,
                                    unknown_fields: list,
                                    is_back_template: bool=False) -> None:
    warning = ('The back template contains fields that are not present for this card: {0}'
               if is_back_template else
               'The template contains fields that are not present for this card: {0}')

    warn(warning.format(unknown_fields), in_context=context)


def warn_missing_fields_in_template(context: WarningContext,
                                    missing_fields: list,
                                    is_back_template: bool=False) -> None:
    warning = ('The back template does not contain the fields: {0}'
               if is_back_template else
               'The template does not contain the fields: {0}')

    warn(warning.format(missing_fields), in_context=context)


def warn_bad_template_path(context: WarningContext,
                           template_path: str,
                           is_back: bool=False) -> None:
    warning = ('The card provided a back template that could not be opened: '
               '\033[4;31m\'{0}\'\033[0m'
               if is_back else
               'The card provided a template that could not be opened: '
               '\033[4;31m\'{0}\'\033[0m')

    warn(warning.format(template_path), in_context=context,
         as_error=True)


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
                warn_image_not_copied(WarningContext(context), image_path)
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
                warn_missing_image(WarningContext(context), relative_source_path)


def get_definitions(path: str, verbosely: 'show warnings'=False) -> dict:
    definitions = {}

    if path is not None and len(path) > 0:
        if not os.path.isfile(path):
            if verbosely:
                warn_bad_definitions_file(path)
        else:
            with open(path) as f:
                # skip the first row (column headers)
                f.readline()

                # map all rows into key-value pairs (assume no more than 2 columns are present)
                definitions = {k: v for k, v in csv.reader(f)}

    return definitions


def get_page(page_number: int, cards: str, page_template: str) -> str:
    numbered_page = fill_template_fields(
        TemplateFields.PAGE_NUMBER, str(page_number), page_template)

    return fill_template_fields(TemplateFields.CARDS, cards, numbered_page)


def fill_metadata_field(field_name: str, field_value: str, in_template: str) -> str:
    """ Fills a metadata field like e.g. `title` or `description` and determines
        whether or not the field should be displayed or hidden.
    """

    field_value = field_value.strip()
    # these are css values; 'none' means hidden and taking up no space, while 'block' is the default
    field_display = 'none' if len(field_value) == 0 else 'block'

    in_template = fill_template_fields('{0}_display'.format(field_name), field_display, in_template)
    in_template = fill_template_fields(field_name, field_value, in_template)

    return in_template


def generate(args):
    # required arguments
    data_paths = args['input_paths']

    # optional arguments
    output_path = args['output_path']
    output_filename = args['output_filename']
    definitions_path = args['definitions_path']
    force_page_breaks = args['force_page_breaks']
    disable_backs = bool(args['disable_backs'])
    is_verbose = bool(args['verbose'])

    disable_auto_templating = False

    if definitions_path is None:
        # no definitions file has been explicitly specified, so try looking for it automatically
        found, potential_definitions_path = find_file_path('definitions.csv', data_paths)

        if found and potential_definitions_path is not None:
            definitions_path = potential_definitions_path

            warn_using_automatically_found_definitions(definitions_path)

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

    with open(os.path.join(cwd, 'templates/page.html')) as p:
        # load the container template for a page
        page = p.read()

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

    card_sizes = {
        # small tokens: 0.75x0.75 inches
        'token':
            {'class': 'card-size-075x075', 'cards_per_page': (14, 10)},  # (rows, columns)
        # standard poker cards: 2.5x3.5 inches
        'standard':
            {'class': 'card-size-25x35', 'cards_per_page': (3, 3)},
        # standard poker cards in landscape: 3.5x2.5 inches
        'standard-landscape':
            {'class': 'card-size-35x25', 'cards_per_page': (4, 2)},
        # jumbo cards: 3.5x5.5 inches
        'jumbo':
            {'class': 'card-size-35x55', 'cards_per_page': (2, 1)},
        # domino cards: 1.75x3.5 inches
        'domino':
            {'class': 'card-size-175x35', 'cards_per_page': (4, 3)},
    }

    default_card_size = card_sizes['standard']

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

    previous_card_size = None

    for data_path in data_paths:
        # define the context as the base filename of the current data- useful when troubleshooting
        context = os.path.basename(data_path)

        card_size = default_card_size

        image_paths = []

        with open(data_path) as f:
            # read the csv as a dict, so that we can access each column by name
            data = csv.DictReader(lower_first_row(f))

            # get a list of all column names as they are
            column_names = [column_name.strip() for column_name in data.fieldnames]

            size_identifier = None

            for column_index in range(len(column_names)):
                column_name = column_names[column_index]

                # look for the '@template' column
                if column_name.startswith(Columns.TEMPLATE):
                    # and isn't just '@template-back'
                    if column_name != Columns.TEMPLATE_BACK:
                        # then determine preferred card size, if any.
                        # it should look like e.g. '@template:standard'
                        size_index = column_name.rfind(':')

                        if size_index != -1:
                            size_identifier = column_name[size_index + 1:]

                            column_names[column_index] = column_name[:size_index]

                        break

            data.fieldnames = column_names

            if size_identifier is not None and size_identifier in card_sizes:
                card_size = card_sizes[size_identifier]

            if card_size is not previous_card_size and cards_on_page > 0:
                # card sizing is different for this datasource, so any remaining cards
                # must be added to a new page at this point
                pages += get_page(pages_total + 1, cards, page)
                pages_total += 1

                if not disable_backs:
                    cards_on_last_row = cards_on_page % cards_per_row

                    if cards_on_last_row is not 0:
                        # less than MAX_CARDS_PER_ROW cards were added to the current line,
                        # so we have to add additional blank filler cards to ensure a correct layout

                        remaining_backs = cards_per_row - cards_on_last_row

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

            cards_per_row, cards_per_column = card_size['cards_per_page']
            max_cards_per_page = cards_per_row * cards_per_column

            card_size_class = str(card_size['class'])

            # empty backs may be necessary to fill in empty spots on a page to ensure
            # that the layout remains correct
            empty_back = get_sized_card(card, card_size_class, content='')

            if disable_auto_templating:
                default_template = None
            else:
                # get a fitting template by analyzing the content of the data
                default_template = template_from_data(data)

                # reset the iterator
                f.seek(0)

                # and start over
                data = csv.DictReader(lower_first_row(f), fieldnames=column_names)

                # setting fieldnames explicitly causes the first row
                # to be treated as data, so skip it
                next(data)

            if default_template is None and Columns.TEMPLATE not in data.fieldnames:
                if is_verbose:
                    warn_missing_default_template(WarningContext(context))

            if not disable_backs and Columns.TEMPLATE_BACK in data.fieldnames:
                if is_verbose:
                    warn_assume_backs(WarningContext(context))
            else:
                disable_backs = True

                if is_verbose:
                    warn_no_backs(WarningContext(context))

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

                        warn_indeterminable_count(WarningContext(context, row_index))
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
                        row, Columns.TEMPLATE, definitions, default_content='').strip()

                    if template_path is not None and len(template_path) > 0:
                        template, not_found, template_path = template_from_path(
                            template_path, relative_to_path=data_path)

                        if not_found:
                            template = template_not_opened

                            warn_bad_template_path(
                                WarningContext(context, row_index, card_index), template_path)
                        elif is_verbose and len(template) == 0:
                            template = default_template

                            warn_empty_template(
                                WarningContext(context, row_index, card_index), template_path)
                    else:
                        template = default_template

                        if template is not None and is_verbose:
                            warn_using_auto_template(WarningContext(context, row_index, card_index))

                    if template is None:
                        template = template_not_provided

                        warn_missing_template(WarningContext(context, row_index, card_index))

                    card_content, found_image_paths, missing_fields = fill_card_front(
                        template, template_path,
                        row, row_index, card_index,
                        definitions)

                    if (template is not template_not_provided and
                       template is not template_not_opened):
                        missing_fields_in_template = missing_fields[0]
                        missing_fields_in_data = missing_fields[1]

                        if len(missing_fields_in_template) > 0 and is_verbose:
                            warn_missing_fields_in_template(
                                WarningContext(context, row_index, card_index),
                                missing_fields_in_template)

                        if len(missing_fields_in_data) > 0 and is_verbose:
                            warn_unknown_fields_in_template(
                                WarningContext(context, row_index, card_index),
                                missing_fields_in_data)

                    image_paths.extend(found_image_paths)

                    current_card = get_sized_card(card, card_size_class, card_content)

                    cards += current_card

                    cards_on_page += 1
                    cards_total += 1

                    if not disable_backs:
                        template_path_back = get_column_content(
                            row, Columns.TEMPLATE_BACK, definitions, default_content='').strip()

                        template_back = None

                        if template_path_back is not None and len(template_path_back) > 0:
                            template_back, not_found, template_path_back = template_from_path(
                                template_path_back, relative_to_path=data_path)

                            if not_found:
                                template_back = template_not_opened

                                warn_bad_template_path(
                                    WarningContext(context, row_index, card_index),
                                    template_path_back, is_back=True)
                            elif is_verbose and len(template_back) == 0:
                                warn_empty_template(
                                    WarningContext(context, row_index, card_index),
                                    template_path_back, is_back_template=True)

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
                                warn_missing_fields_in_template(
                                    WarningContext(context, row_index, card_index),
                                    missing_fields_in_template, is_back_template=True)

                            if len(missing_fields_in_data) > 0 and is_verbose:
                                warn_unknown_fields_in_template(
                                    WarningContext(context, row_index, card_index),
                                    missing_fields_in_data, is_back_template=True)

                        image_paths.extend(found_image_paths)

                        current_card_back = get_sized_card(card, card_size_class, back_content)

                        # prepend this card back to the current line of backs
                        backs_row = current_card_back + backs_row

                        # card backs are prepended rather than appended to
                        # ensure correct layout when printing doublesided

                        if cards_on_page % cards_per_row is 0:
                            # a line has been filled- append the 3 card backs
                            # to the page in the right order
                            backs += backs_row

                            # reset to prepare for the next line
                            backs_row = ''

                    if cards_on_page == max_cards_per_page:
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
                cards_on_last_row = cards_on_page % cards_per_row

                if cards_on_last_row is not 0:
                    # less than MAX_CARDS_PER_ROW cards were added to the current line,
                    # so we have to add additional blank filler cards to ensure a correct layout

                    remaining_backs = cards_per_row - cards_on_last_row

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

        # store the card size that was just used, so we can determine
        # whether or not the size changes for the next datasource
        previous_card_size = card_size

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

        pages = fill_template_fields(
            field_name=TemplateFields.PAGES_TOTAL,
            field_value=str(pages_total),
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

    shutil.copyfile(os.path.join(cwd, 'templates/resources/cards.svg'),
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

    open_path(output_path)
