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
import errno
import re
import shutil
import subprocess
import itertools

__version_info__ = ('0', '4', '2')
__version__ = '.'.join(__version_info__)


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


def dict_from_string(string: 'a string of key-value pairs') -> dict:
    """ Returns a dictionary object parsed from a string containing comma-separated key-value pairs.

        For example: "a_key=a_value, another_key=another_value"
    """
    if string is None or len(string) == 0:
        return None

    return dict(kvp.strip().split('=') for kvp in string.split(','))


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


def warn(message: str, in_context: str=None, as_error: 'apply error color'=False) -> None:
    """ Display a command-line warning. """

    apply_red_color = '\033[31m'
    apply_yellow_color = '\033[33m'
    apply_normal_color = '\033[0m'

    apply_color = apply_yellow_color if not as_error else apply_red_color

    message_content = '[{0}]'.format('!' if as_error else '-')

    if in_context is not None:
        message_content = '{0} [{1}]'.format(message_content, str(in_context))

    message_content = message_content + ' ' + message

    print(apply_color + message_content + apply_normal_color)


def is_special_column(column: str) -> bool:
    """ Determines whether a column is to be treated as a special column. """

    return column.startswith('@') if column is not None else False


def lower_first_row(rows):
    """ Returns rows where the first row is all lower-case. """

    return itertools.chain([next(rows).lower()], rows)


def create_missing_directories_if_necessary(path: str) -> None:
    """ Mimics the command 'mkdir -p'. """

    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


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
                shutil.copyfile(
                    relative_source_path, relative_destination_path)
            else:
                warn('One or more cards contain an image reference that does not exist: '
                     '\033[4;31m\'{0}\'\033[0m'.format(relative_source_path),
                     as_error=True)


def image_tag_from_path(image_path: str, images: dict=None, sizes: dict=None) -> (str, str):
    """ Constructs an HTML compliant image tag using the specified image path. """

    actual_image_path = image_path

    # determine whether a size has been explicitly specified; e.g. "images/name-of-image.svg:16x16"
    size_index = image_path.rfind(':')

    explicit_width = None
    explicit_height = None

    if size_index is not -1:
        # get the size specification; i.e. whatever is on the right hand size of the ':' splitter
        size = image_path[size_index + 1:].strip()

        # then, determine whether the value is a size specified in the metadata;
        # if it is, use that size specification.
        if sizes is not None and size in sizes:
            size = sizes.get(size)

        # get each size specification separately (removing blanks)
        size = list(filter(None, size.split('x')))

        if len(size) > 0:
            explicit_width = int(size[0])

            if explicit_width < 0:
                explicit_width = None

        if len(size) > 1:
            explicit_height = int(size[1])

            if explicit_height < 0:
                explicit_height = None
        else:
            # default to a squared size using the width specification
            explicit_height = explicit_width

        # get rid of the size specification to have a clean image path
        actual_image_path = image_path[:size_index]

        if images is not None and actual_image_path in images:
            actual_image_path = images.get(actual_image_path)

    if (explicit_width is not None and
       explicit_height is not None):
            image_tag = '<img src="{0}" width="{1}" height="{2}">'.format(
                actual_image_path, explicit_width, explicit_height)
    else:
        image_tag = '<img src="{0}">'.format(actual_image_path)

    return image_tag, actual_image_path


def fill_template_image_fields(template: str, images: dict=None, sizes: dict=None) -> (str, list):
    """ Recursively finds all {{image:size}} fields and returns a string
        replaced with HTML compliant <img> tags.
    """

    image_paths = []

    for match in re.finditer('{{(.*?)}}', template, re.DOTALL):
        image_path = match.group(1)

        if len(image_path) > 0:
            image_tag, image_path = image_tag_from_path(image_path, images, sizes)

            image_paths.append(image_path)

            # since the string we're finding matches on has just been changed,
            # we have to recursively look for more fields if there are any
            template, filled_image_paths = fill_template_image_fields(
                template[:match.start()] + image_tag + template[match.end():], images, sizes)

            image_paths.extend(filled_image_paths)

            break

    return template, image_paths


def fill_template_field(field_name: str, field_value: str, in_template: str) -> (str, int):
    """ Fills in the provided value in the provided template for all occurences
        of a given template field.
    """

    field_value = field_value if field_value is not None else ''

    # template fields are always represented by wrapping {{ }}'s'
    template_field = re.escape('{{' + str(field_name) + '}}')

    # find any occurences of the field, using a case-insensitive
    # comparison, to ensure that e.g. {{name}} is populated with the
    # value from column "Name", even though the casing might differ
    search = re.compile(template_field, re.IGNORECASE)

    # finally replace any found occurences of the template field with its value
    return search.subn(field_value, in_template)


def fill_template(template: str, row: dict, metadata: Metadata) -> (str, list, list):
    """ Returns the contents of the template with all template fields replaced
        by any matching fields in the provided data.
    """

    image_paths = []
    missing_fields = []

    for column in row:
        # ignore special columns
        if not is_special_column(column):
            # fetch the content for the field (may also be templated)
            template_content = str(row[column])

            # replace any image fields with HTML compliant <img> tags
            template_content, filled_image_paths = fill_template_image_fields(
                template_content, metadata.image_definitions, metadata.size_definitions)

            image_paths.extend(filled_image_paths)

            # fill content into the provided template
            template, occurences = fill_template_field(
                field_name=str(column),
                field_value=str(template_content),
                in_template=template)

            if occurences is 0:
                missing_fields.append(column)

    return template, image_paths, missing_fields


def template_from_path(template_path: str, relative_to_path: str=None) -> (str, bool, str):
    """ Attempts returning the template contents of the given path.
        If specified, path is made relative to another path.
    """

    template = None
    template_not_found = False

    if template_path is not None and len(template_path) > 0:
        if not os.path.isabs(template_path):
            # the path is not an absolute path; assume that it's located relative to the data
            if relative_to_path is not None:
                template_path = os.path.join(
                    os.path.dirname(relative_to_path),
                    template_path)

        try:
            with open(template_path) as t:
                template = t.read().strip()
        except IOError:
            template_not_found = True
    else:
        template_not_found = True

    return template, template_not_found, template_path


def most_common(objects: list) -> object:
    """ Returns the object that occurs most frequently in a list of objects. """

    return max(set(objects), key=objects.count)


def is_probably_number(value: str) -> bool:
    """ Determine whether value is probably a numerical element. """

    # value is simply a numerical value
    probably_number = value.isdigit()

    if not probably_number:
        s = value.split(' ')

        if len(s) is 2:
            # value is made up of 2 components;
            # consider it a number if either of the components is a numerical value
            probably_number = True if s[0].isdigit() else s[1].isdigit()

    return probably_number


def is_probably_text(value: str) -> bool:
    """ Determine whether value is probably a text element. """

    # value has more than 3 components; assume it's a text
    return len(value.split(' ')) > 3


def is_probably_title(value: str) -> bool:
    """ Determine whether value is probably a title element. """

    # value has less than 3 components; assume it's a title
    return len(value.split(' ')) <= 3


def field_type_from_value(value: str) -> str:
    field_type = None

    if value is not None and len(value) > 0:
        # let's not waste efforts on troubleshooting whitespace...
        value = value.strip()

        if is_probably_number(value):
            field_type = 'number'
        elif is_probably_text(value):
            field_type = 'text'
        elif is_probably_title(value):
            field_type = 'title'

    return field_type


def template_from_data(data: csv.DictReader) -> str:
    """ Returns a template that is fit for the provided data. """

    analysis = {}

    for row in data:
        for column in data.fieldnames:
            if not is_special_column(column):
                field_type = field_type_from_value(row[column])

                if field_type is not None:
                    l = analysis.get(column, [])
                    l.append(field_type)

                    analysis[column] = l

    for field_name, field_types in analysis.items():
        field_type = most_common(field_types)

        analysis[field_name] = field_type

    sort_fields_by_type = True

    if not sort_fields_by_type:
        fields = analysis.items()
    else:
        fields = sorted(analysis.items(), key=lambda item: (
            0 if item[1] is 'number' else (
                1 if item[1] is 'title' else (
                    2 if item[1] is 'text' else -1))))

    template = '' if len(analysis) > 0 else None

    for field_name, field_type in fields:
        field = '{{' + str(field_name) + '}}'
        field_tag = '<div class=\"auto-template-field auto-template-{0}\">{1}</div>'

        template += field_tag.format(field_type, field)

    return template


def content_from_row(
        row: dict,
        row_index: int,
        card_index: int,
        template: str,
        template_path: str,
        metadata: Metadata) -> (str, list, list):
    """ Returns the contents of a card using the specified template. """

    # attempt to fill all fields discovered in the template using the data for this card
    content, discovered_image_paths, missing_fields = fill_template(
        template, row, metadata)

    # fill all row index fields (usually used for error templates)
    content, occurences = fill_template_field(
        field_name='card_row',
        field_value=str(row_index),
        in_template=content)

    # fill all template path fields (usually used for error templates)
    content, occurences = fill_template_field(
        field_name='card_template_path',
        field_value=template_path,
        in_template=content)

    # fill all card index fields
    content, occurences = fill_template_field(
        field_name='card_index',
        field_value=str(card_index),
        in_template=content)

    # fill all version fields
    content, occurences = fill_template_field(
        field_name='version',
        field_value=metadata.version,
        in_template=content)

    return content, discovered_image_paths, missing_fields


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

    with open(os.path.join(cwd, 'template/card.html')) as c:
        # load the container template for a card
        card = c.read()

    with open(os.path.join(cwd, 'template/page.html')) as p:
        # load the container template for a page
        page = p.read()

        if disable_cut_guides:
            # simply add a css rule to hide them
            cut_guides_display = 'style="display: none"'
        else:
            cut_guides_display = 'style="display: block"'

        page = page.replace('{{cut_guides_style}}', cut_guides_display)

    with open(os.path.join(cwd, 'template/index.html')) as i:
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
    with open(os.path.join(cwd, 'template/error/could_not_open.html')) as e:
        template_not_opened = e.read()

    # error template for the output on cards when a default template has not been specified,
    # and the card hasn't specified one either
    with open(os.path.join(cwd, 'template/error/not_provided.html')) as e:
        template_not_provided = e.read()

    # error template for the output on cards when a template back has not been specified,
    # and backs are not disabled
    with open(os.path.join(cwd, 'template/error/back_not_provided.html')) as e:
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

    # list of all the image paths discovered during card generation
    image_paths = []

    for data_path in data_paths:
        # define the context as the base filename of the current data- useful when troubleshooting
        context = os.path.basename(data_path)

        card_size = default_card_size

        # empty backs may be necessary to fill in empty spots on a page to ensure
        # that the layout remains correct
        empty_back = card.replace('{{size}}', card_size)
        empty_back = empty_back.replace('{{content}}', '')

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
                            warn('The template at \033[4;31m\'{0}\'\033[0m for the card at '
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

                    card_content, found_image_paths, missing_fields = content_from_row(
                        row, row_index, card_index, template, template_path, metadata)

                    if len(missing_fields) > 0 and (template is not template_not_provided and
                                                    template is not template_not_opened):
                        if is_verbose:
                            warn('The template for the card at #{0} (row {1}) did not contain '
                                 'the fields: {2}'.format(card_index, row_index, missing_fields),
                                 in_context=context)

                    image_paths.extend(found_image_paths)

                    current_card = card.replace('{{size}}', card_size)
                    current_card = current_card.replace('{{content}}', card_content)

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
                                warn('The back template at \033[4;31m\'{0}\'\033[0m for the card '
                                     'at #{1} (row {2}) appears to be empty. Blank cards may occur.'
                                     .format(template_path, card_index, row_index),
                                     in_context=context)

                        if template_back is None:
                            template_back = template_back_not_provided

                        back_content, found_image_paths, missing_fields = content_from_row(
                            row, row_index, card_index, template_back, template_path_back, metadata)

                        image_paths.extend(found_image_paths)

                        # prepend this card back to the current line of backs
                        backs_row = card.replace('{{content}}', back_content) + backs_row

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

        if cards_on_page > 0:
            # in case there's still cards remaining, fill those into a new page
            pages += page.replace('{{cards}}', cards)
            pages_total += 1

            if not disable_backs:
                if cards_on_page % MAX_CARDS_PER_ROW is not 0:
                    # less than MAX_CARDS_PER_ROW cards were added to the current line, so
                    # we have to add an additional blank filler card to ensure correct layout
                    backs_row = empty_back + backs_row

                backs += backs_row

                # fill another page with the backs
                pages += page.replace('{{cards}}', backs)
                pages_total += 1

            # reset to prepare for the next page
            cards_on_page = 0
            cards = ''

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
    shutil.copyfile(os.path.join(cwd, 'template/index.css'), os.path.join(output_path, 'index.css'))

    # ensure there are no duplicate image paths, since that would just
    # cause unnecessary copy operations
    image_paths = list(set(image_paths))

    # additionally, copy all referenced images to the output directory as well
    # (making sure to keep their original directory structure)
    copy_images_to_output_directory(image_paths, data_path, output_path, verbosely=True)

    print('Generated {0} {1} on {2} {3}. See \'{4}/index.html\'.'
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
