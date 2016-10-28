# coding=utf-8

"""
Generate print-ready cards for your tabletop game

https://github.com/jhauberg/cards.py

Copyright 2015 Jacob Hauberg Hansen.
License: MIT (see LICENSE)
"""

import os
import csv
import math
import shutil
import datetime

from datetime import timedelta

from cards.template import (
    fill_index, fill_template_fields, fill_image_fields, fill_card_front, fill_card_back
)

from cards.template import template_from_path, strip_styles, get_sized_card
from cards.autotemplate import template_from_data

from cards.column import get_invalid_columns, size_identifier_from_columns

from cards.resource import copy_images_to_output_directory, get_unused_resources, get_resources_path

from cards.constants import Columns, TemplateFields, CardSizes
from cards.warning import WarningDisplay, WarningContext

from cards.util import (
    FileWrapper, find_file_path, open_path, lower_first_row, terminal_supports_color,
    copy_file_if_necessary, create_directories_if_necessary, directory_size, pretty_size
)


def get_definitions_from_file(path: str) -> dict:
    """ Return a dict with all definitions found in file. """

    definitions = {}

    if path is not None and len(path) > 0:
        if not os.path.isfile(path):
            WarningDisplay.bad_definitions_file_error(path)
        else:
            with open(path) as data_file_raw:
                data_file = FileWrapper(data_file_raw)

                # skip the first row (column headers)
                next(data_file)

                # map all rows into key-value pairs (assume no more than 2 columns are present)
                # and skipping ignored rows
                definitions = {k: v for k, v in csv.reader(data_file)
                               if not is_line_excluded(data_file.raw_line)}

    return definitions


def is_line_excluded(line: str) -> bool:
    """ Determine if a line in a file should be excluded. """

    return line.strip().startswith('#')


def get_page(page_number: int, cards: str, page_template: str, is_card_backs: bool=False) -> str:
    """ Populate a page with cards. """

    page_class = 'page page-backs' if is_card_backs else 'page'

    page = fill_template_fields(
        '_page_class', page_class, page_template)

    numbered_page = fill_template_fields(
        TemplateFields.PAGE_NUMBER, str(page_number), page)

    return fill_template_fields(
        TemplateFields.CARDS, cards, in_template=numbered_page, indenting=True)


def get_base_path() -> str:
    """ Return the path of the actual location of the current script; i.e. the path from
        which we can reach included project resources like base templates, icons and so on.
    """

    return os.path.dirname(os.path.realpath(__file__))


def make_empty_project(in_path: str,
                       name: str=None) -> bool:
    """ Build an empty project that can be used as a starting point. """

    name = name if name is not None else 'empty'

    if name is not None and len(name) > 0:
        # make sure any whitespace is replaced with dashes
        name_components = name.split(' ')
        name = '-'.join(name_components).lower()

    empty_project_path = os.path.join(get_base_path(), 'templates/project')
    destination_path = os.path.join(in_path, '{0}/src'.format(name))

    if os.path.isdir(destination_path):
        WarningDisplay.could_not_make_new_project_error(
            destination_path, already_exists=True)

        return False

    try:
        shutil.copytree(empty_project_path, destination_path)

        print('Made new project at: {0}\'{1}\'{2}'.format(
            WarningDisplay.apply_normal_color_underlined, destination_path,
            WarningDisplay.apply_normal_color))

        open_path(destination_path)

        return True
    except IOError as error:
        WarningDisplay.could_not_make_new_project_error(
            destination_path, reason=str(error))

    return False


def determine_ambiguous_references(columns: set, definitions: set) -> set:
    """ Return the set of reference names that exist as both a column and a definition. """

    # get the diffs between the two sets
    unambiguous_columns = columns - definitions
    unambiguous_definitions = definitions - columns

    # then, by removing all the unambiguous names, we'll be left with the ambiguous ones
    ambiguous_references = ((columns | definitions) - unambiguous_definitions) - unambiguous_columns

    return ambiguous_references


def previous_or_current_path(current_path: str, previous_path: str) -> str:
    """ Return previous path only if the current path is used as a pointer
        to the contents of the previous path.
    """

    return (previous_path if (current_path is not None and current_path.strip() == '^')
            else current_path)


def determine_count(row: dict) -> (int, bool):
    """ Determine and return count value from the @count column in a row. """

    # determine how many instances of this card to generate
    # (defaults to a single instance if not specified)
    count = row.get(Columns.COUNT, '1')

    was_indeterminable = False

    if len(count.strip()) > 0:
        # the count column has content, so attempt to parse it
        try:
            count = int(count)
        except ValueError:
            # count could not be determined, so default to skip this card
            count = 0

            was_indeterminable = True
    else:
        # the count column did not have content, so default count to 1
        count = 1

    if count < 0:
        count = 0

        was_indeterminable = True

    return count, was_indeterminable


def make(data_paths: list,
         definitions_path: str=None,
         output_path: str=None,
         output_filename: str=None,
         force_page_breaks: bool=False,
         disable_backs: bool=False,
         default_card_size_identifier: str='standard',
         is_preview: bool=False,
         discover_datasources: bool=False):
    """ Build cards for all specified datasources. """

    time_started_make = datetime.datetime.now()

    if discover_datasources:
        # todo: discover any CSV files in current working directory and append those to data_paths
        # todo: then clear duplicates by doing data_paths = list(set(data_paths))
        pass

    data_path_names = [os.path.basename(data_path) for data_path in data_paths]

    datasource_count = len(data_paths)

    if datasource_count > 0:
        print('Generating cards from {0} {1}:\n {2}'.format(
            datasource_count, 'datasources' if datasource_count > 1 else 'datasource',
            data_path_names))
        print()
    else:
        print('No datasources.')

    if datasource_count == 0:
        print('Generated 0 cards.')

        return

    disable_auto_templating = False

    if definitions_path is None and discover_datasources:
        # no definitions file has been explicitly specified, so try looking for it automatically
        found, potential_definitions_path = find_file_path('definitions.csv', data_paths)

        if found and potential_definitions_path is not None:
            definitions_path = potential_definitions_path

            WarningDisplay.using_automatically_found_definitions_info(
                definitions_path)

    definitions = get_definitions_from_file(definitions_path)

    if is_preview:
        WarningDisplay.preview_enabled_info()

    # dict of all image paths discovered for each context during card generation
    context_image_paths = {}

    base_path = get_base_path()

    card_template_path = os.path.join(base_path, 'templates/base/card.html')

    with open(card_template_path) as card_template:
        # load the container template for a card
        card = card_template.read()

        # fill any image fields defined by the default card template
        card, filled_image_paths = fill_image_fields(card)

        if len(filled_image_paths) > 0:
            context_image_paths[card_template_path] = list(set(filled_image_paths))

    page_template_path = os.path.join(base_path, 'templates/base/page.html')

    with open(page_template_path) as page_template:
        # load the container template for a page
        page = page_template.read()

        # fill any image fields defined by the default page template
        page, filled_image_paths = fill_image_fields(page)

        if len(filled_image_paths) > 0:
            context_image_paths[page_template_path] = list(set(filled_image_paths))

    index_template_path = os.path.join(base_path, 'templates/base/index.html')

    with open(index_template_path) as index_template:
        # load the container template for the final html file
        index = index_template.read()

        # fill any image fields defined by the default index template
        index, filled_image_paths = fill_image_fields(index)

        if len(filled_image_paths) > 0:
            context_image_paths[index_template_path] = list(set(filled_image_paths))

    not_found_template_path = os.path.join(base_path, 'templates/base/error/could_not_open.html')

    with open(not_found_template_path) as error_template:
        template_not_opened = error_template.read()

    no_front_template_path = os.path.join(base_path, 'templates/base/error/not_provided.html')

    with open(no_front_template_path) as error_template:
        template_not_provided = error_template.read()

    no_back_template_path = os.path.join(base_path, 'templates/base/error/back_not_provided.html')

    with open(no_back_template_path) as error_template:
        template_back_not_provided = error_template.read()

    default_card_size = CardSizes.get_card_size(default_card_size_identifier)

    if default_card_size is None:
        default_card_size = CardSizes.get_default_card_size()

        WarningDisplay.bad_card_size(
            WarningContext(), size_identifier=default_card_size_identifier)

    # buffer that will contain at most MAX_CARDS_PER_PAGE amount of cards
    cards = ''
    # buffer that will contain at most MAX_CARDS_PER_PAGE amount of card backs
    backs = ''
    # buffer of a row of backs that is filled in reverse to support double-sided printing
    backs_row = ''
    # buffer for all generated pages
    pages = ''

    embedded_styles = {}

    # incremented each time a card is generated, but reset to 0 for each page
    cards_on_page = 0
    # incremented each time a card is generated
    cards_total = 0
    # incremented each time a page is generated
    pages_total = 0

    cards_total_unique = 0

    previous_card_size = None

    page_size = CardSizes.get_page_size()

    # some definitions are always guaranteed to be referenced,
    # if not by cards, then by the final page output
    all_referenced_definitions = {TemplateFields.TITLE,
                                  TemplateFields.DESCRIPTION,
                                  TemplateFields.COPYRIGHT,
                                  TemplateFields.VERSION}

    for data_path in data_paths:
        # define the context as the base filename of the current data- useful when troubleshooting
        context = os.path.basename(data_path)

        card_size = default_card_size

        image_paths = []

        # determine whether this path leads to anything
        if not os.path.isfile(data_path):
            # if it doesn't, warn that the path to the datasource is not right
            WarningDisplay.bad_data_path_error(WarningContext(context), data_path)
            # and skip this datasource
            continue

        with open(data_path) as data_file_raw:
            # wrap the file stream to retain access to unparsed lines
            data_file = FileWrapper(data_file_raw)
            # read the csv as a dict, so that we can access each column by name
            data = csv.DictReader(lower_first_row(data_file))

            # make a list of all column names as they are (but stripped of excess whitespace)
            column_names = [column_name.strip() for column_name in data.fieldnames]

            # then determine the size identifier (if any; e.g. '@template:jumbo')
            size_identifier, stripped_column_names = size_identifier_from_columns(column_names)

            # determine whether this datasource contains invalid columns
            invalid_column_names = get_invalid_columns(stripped_column_names)

            if len(invalid_column_names) > 0:
                # warn that this datasource will be skipped
                WarningDisplay.invalid_columns_error(
                    WarningContext(context), invalid_column_names)

                continue

            # replace the column keys with stripped/parsed representations
            # (e.g. '@template:jumbo' becomes just '@template')
            data.fieldnames = stripped_column_names

            if size_identifier is not None:
                new_card_size = CardSizes.get_card_size(size_identifier)

                if new_card_size is not None:
                    card_size = new_card_size
                else:
                    WarningDisplay.bad_card_size(
                        WarningContext(context), size_identifier)

            if card_size != previous_card_size and cards_on_page > 0:
                # card sizing is different for this datasource, so any remaining cards
                # must be added to a new page at this point
                pages += get_page(pages_total + 1, cards, page)
                pages_total += 1

                if not disable_backs:
                    # using the last value of cards_per_row
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
                    pages += get_page(pages_total + 1, backs, page, is_card_backs=True)
                    pages_total += 1

                    backs = ''

                # reset to prepare for the next page
                cards_on_page = 0
                cards = ''

            card_width, card_height = card_size.size_in_inches
            page_width, page_height = page_size.size_in_inches

            cards_per_column = math.floor(page_width / card_width)
            cards_per_row = math.floor(page_height / card_height)

            max_cards_per_page = cards_per_column * cards_per_row

            if disable_auto_templating:
                default_template = None
            else:
                # get a fitting template by analyzing the content of the data
                default_template = template_from_data(data)

                # reset the iterator
                # (note how this is done directly on the file stream; i.e. not on the wrapper)
                data_file_raw.seek(0)

                # and start over
                data = csv.DictReader(
                    lower_first_row(data_file),
                    fieldnames=stripped_column_names)

                # setting fieldnames explicitly causes the first row
                # to be treated as data, so skip it
                next(data)

            if default_template is None and Columns.TEMPLATE not in data.fieldnames:
                WarningDisplay.missing_default_template(
                    WarningContext(context))

            if not disable_backs and Columns.TEMPLATE_BACK in data.fieldnames:
                WarningDisplay.assume_backs_info(
                    WarningContext(context))
            else:
                if not disable_backs:
                    WarningDisplay.no_backs_info(
                        WarningContext(context))

                disable_backs = True

            if not disable_backs:
                # empty backs may be necessary to fill in empty spots on a page to ensure
                # that the layout remains correct
                empty_back = get_sized_card(
                    card, size_class=card_size.style, content='')

            ambiguous_references = determine_ambiguous_references(
                set(stripped_column_names),
                set(definitions.keys()))

            if len(ambiguous_references) > 0:
                WarningDisplay.potential_ambiguous_references(
                    WarningContext(context), list(ambiguous_references))

            previous_template_path = None
            previous_template_path_back = None

            row_index = 1

            for row in data:
                # since the column names counts as a row, and most editors
                # do not use a zero-based row index, the first row == 2
                row_index += 1

                if is_line_excluded(data_file.raw_line):
                    WarningDisplay.card_was_skipped_intentionally_info(
                        WarningContext(context, row_index))

                    # this row should be ignored - so skip and continue
                    continue

                count, indeterminable_count = determine_count(row)

                if indeterminable_count:
                    WarningDisplay.indeterminable_count(
                        WarningContext(context, row_index))

                if count > 100:
                    # the count was unusually high; ask whether it's an error or not
                    if WarningDisplay.abort_unusually_high_count(
                            WarningContext(context, row_index), count):
                        # it was an error, so break out and continue with the next card
                        continue

                if count > 0 and is_preview:
                    # only render 1 card unless it should be skipped
                    count = 1

                # determine which template to use for this card, if any
                template_path = row.get(Columns.TEMPLATE, None)
                template_path = previous_or_current_path(
                    template_path, previous_template_path)

                previous_template_path = template_path

                if not disable_backs:
                    template_path_back = row.get(Columns.TEMPLATE_BACK, None)
                    template_path_back = previous_or_current_path(
                        template_path_back, previous_template_path_back)

                    previous_template_path_back = template_path_back

                if count == 0:
                    # might as well move on to the next card-
                    # this card should not count towards number of unique cards either
                    # note, however, that we *do* want to register the template paths
                    continue

                resolved_template_path = None

                if template_path is not None and len(template_path) > 0:
                    template, not_found, resolved_template_path = template_from_path(
                        template_path, relative_to_path=data_path)

                    if not_found:
                        template = template_not_opened

                        WarningDisplay.bad_template_path_error(
                            WarningContext(context, row_index),
                            resolved_template_path, cards_affected=count)
                    elif len(template) == 0:
                        template = default_template

                        WarningDisplay.empty_template(
                            WarningContext(context, row_index),
                            resolved_template_path, cards_affected=count)
                else:
                    template = default_template

                    if template is not None:
                        WarningDisplay.using_auto_template(
                            WarningContext(context, row_index), cards_affected=count)

                if template is None:
                    template = template_not_provided

                    WarningDisplay.missing_template_error(
                        WarningContext(context, row_index), cards_affected=count)

                styles, template = strip_styles(from_template=template,
                                                at_template_path=template_path)

                embedded_styles[template_path] = styles

                resolved_template_path_back = None

                if not disable_backs:
                    template_back = None

                    if template_path_back is not None and len(template_path_back) > 0:
                        template_back, not_found, resolved_template_path_back = template_from_path(
                            template_path_back, relative_to_path=data_path)

                        if not_found:
                            template_back = template_not_opened

                            WarningDisplay.bad_template_path_error(
                                WarningContext(context, row_index),
                                resolved_template_path, is_back=True,
                                cards_affected=count)
                        elif len(template_back) == 0:
                            WarningDisplay.empty_template(
                                WarningContext(context, row_index),
                                resolved_template_path, is_back_template=True,
                                cards_affected=count)

                    if template_back is None:
                        template_back = template_back_not_provided

                    back_styles, template_back = strip_styles(from_template=template_back,
                                                              at_template_path=template_path_back)

                    embedded_styles[template_path_back] = back_styles

                # this is also the shared index for any instance of this card
                cards_total_unique += 1

                for i in range(count):
                    card_index = cards_total + 1

                    card_content, render_data = fill_card_front(
                        template, resolved_template_path,
                        row, row_index, data_path,
                        card_index, cards_total_unique,
                        definitions)

                    if (template is not template_not_provided
                            and template is not template_not_opened):
                        if len(render_data.unused_fields) > 0:
                            WarningDisplay.missing_fields_in_template(
                                WarningContext(context, row_index),
                                list(render_data.unused_fields),
                                cards_affected=count)

                        if len(render_data.unknown_fields) > 0:
                            WarningDisplay.unknown_fields_in_template(
                                WarningContext(context, row_index),
                                list(render_data.unknown_fields),
                                cards_affected=count)

                    all_referenced_definitions |= render_data.referenced_definitions

                    image_paths.extend(render_data.image_paths)

                    current_card = get_sized_card(
                        card, size_class=card_size.style, content=card_content)

                    cards += current_card

                    cards_on_page += 1
                    cards_total += 1

                    if not disable_backs:
                        back_content, render_data = fill_card_back(
                            template_back, resolved_template_path_back,
                            row, row_index, data_path,
                            card_index, cards_total_unique,
                            definitions)

                        if (template_back is not template_back_not_provided
                                and template_back is not template_not_opened):
                            if len(render_data.unused_fields) > 0:
                                WarningDisplay.missing_fields_in_template(
                                    WarningContext(context, row_index),
                                    list(render_data.unused_fields), is_back_template=True,
                                    cards_affected=count)

                            if len(render_data.unknown_fields) > 0:
                                WarningDisplay.unknown_fields_in_template(
                                    WarningContext(context, row_index),
                                    list(render_data.unknown_fields), is_back_template=True,
                                    cards_affected=count)

                        all_referenced_definitions |= render_data.referenced_definitions

                        image_paths.extend(render_data.image_paths)

                        current_card_back = get_sized_card(
                            card, size_class=card_size.style, content=back_content)

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
                            pages += get_page(pages_total + 1, backs, page, is_card_backs=True)
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
                pages += get_page(pages_total + 1, backs, page, is_card_backs=True)
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

    # determine unused definitions, if any
    unused_definitions = list(set(definitions.keys()) - all_referenced_definitions)

    if len(unused_definitions) > 0:
        WarningDisplay.unused_definitions(unused_definitions)

    if output_path is None:
        # output to current working directory unless otherwise specified
        output_path = ''

    output_directory_name = 'generated'

    # construct the final output path
    output_path = os.path.join(output_path, output_directory_name)

    # ensure all directories exist or created if missing
    create_directories_if_necessary(output_path)

    output_filepath = os.path.join(output_path, output_filename)

    # begin writing pages to the output file (overwriting any existing file)
    with open(output_filepath, 'w') as result:
        index = fill_template_fields(
            '_toggle_card_backs_display', 'none' if disable_backs else 'block', index)

        styles = ''

        for template_path, style in embedded_styles.items():
            styles = styles + '\n' + style if len(styles) > 0 else style

        if len(styles) == 0:
            styles = '<style type="text/css">\n  /* no embedded styles */\n</style>'

        index, render_data = fill_index(
            index, styles, pages, pages_total, cards_total, definitions)

        if len(render_data.image_paths) > 0:
            # we assume that any leftover images would have been from a definition
            context_image_paths[definitions_path] = list(set(render_data.image_paths))

        result.write(index)

    css_path = os.path.join(output_path, 'css')
    js_path = os.path.join(output_path, 'js')

    resources_path = os.path.join(output_path, get_resources_path())

    create_directories_if_necessary(css_path)
    create_directories_if_necessary(js_path)
    create_directories_if_necessary(resources_path)

    copy_file_if_necessary(os.path.join(base_path, 'templates/base/css/cards.css'),
                           os.path.join(css_path, 'cards.css'))

    copy_file_if_necessary(os.path.join(base_path, 'templates/base/css/index.css'),
                           os.path.join(css_path, 'index.css'))

    copy_file_if_necessary(os.path.join(base_path, 'templates/base/js/index.js'),
                           os.path.join(js_path, 'index.js'))

    all_copied_image_filenames = []

    # additionally, copy all referenced images to the output directory
    for context in context_image_paths:
        image_paths = context_image_paths[context]
        image_filenames = [os.path.basename(image_path) for image_path in image_paths]

        copy_images_to_output_directory(
            image_paths, context, output_path)

        all_copied_image_filenames.extend(image_filenames)

    unused_resources = get_unused_resources(output_path, all_copied_image_filenames)

    if len(unused_resources) > 0:
        WarningDisplay.unused_resources(
            unused_resources, in_resource_dir=get_resources_path())

    output_location_message = (' → \033[4m\'{0}\'\033[0m'.format(output_filepath)
                               if terminal_supports_color() else
                               ' → \'{0}\''.format(output_filepath))

    # get the grammar right
    errors_or_error = 'error' if WarningDisplay.error_count == 1 else 'errors'
    warnings_or_warning = 'warning' if WarningDisplay.warning_count == 1 else 'warnings'

    warnings_and_errors_message = (' ({0} {1}, {2} {3}{4})'
                                   .format(WarningDisplay.error_count, errors_or_error,
                                           WarningDisplay.warning_count, warnings_or_warning,
                                           ('; set --verbose for more'
                                            if not WarningDisplay.is_verbose else ''))
                                   if WarningDisplay.has_encountered_errors()
                                   or WarningDisplay.has_encountered_warnings()
                                   else '')

    now = datetime.datetime.now()

    time_difference = now - time_started_make
    time_difference_in_seconds = time_difference / timedelta(seconds=1)

    print()
    print('[{0}] Finished in {1:.3f} seconds{2}'.format(
        '✔' if not WarningDisplay.has_encountered_errors() else '✖',
        time_difference_in_seconds, warnings_and_errors_message))
    print()

    # find the total size of the generated directory
    generated_directory_size = pretty_size(directory_size(output_path))

    if cards_total > 0:
        # get the grammar right
        pages_or_page = 'pages' if pages_total > 1 else 'page'
        cards_or_card = 'cards' if cards_total > 1 else 'card'

        if cards_total > cards_total_unique:
            print('Generated {0} ({1} unique) {2} on {3} {4} ({5})\n{6}'
                  .format(cards_total, cards_total_unique, cards_or_card,
                          pages_total, pages_or_page,
                          generated_directory_size, output_location_message))
        else:
            print('Generated {0} {1} on {2} {3} ({4})\n{5}'
                  .format(cards_total, cards_or_card,
                          pages_total, pages_or_page,
                          generated_directory_size, output_location_message))
    else:
        print('Generated 0 cards ({0})\n{1}'
              .format(generated_directory_size, output_location_message))

    print()

    open_path(output_path)
