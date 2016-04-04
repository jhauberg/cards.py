# coding=utf-8

import csv
import os
import re

from util import most_common, warn
from meta import Metadata


def is_image(image_path: str) -> bool:
    return image_path.strip().lower().endswith(('.svg', '.png', '.jpg', '.jpeg'))


def image_tag_from_path(image_path: str, images: dict=None, sizes: dict=None) -> (str, str):
    """ Constructs an HTML compliant image tag using the specified image path. """

    actual_image_path = image_path

    # determine whether a size has been explicitly specified; e.g. "images/name-of-image.svg:16x16"
    size_index = image_path.rfind(':')

    explicit_width = None
    explicit_height = None

    if size_index is not -1:
        # get rid of the size specification to have a clean image path
        actual_image_path = image_path[:size_index]

        if images is not None and actual_image_path in images:
            actual_image_path = images.get(actual_image_path)

        # get the size specification; i.e. whatever is on the right hand size of the ':' splitter
        size = image_path[size_index + 1:].strip()

        # then, determine whether the value is a size specified in the metadata;
        # if it is, use that size specification.
        if sizes is not None and size in sizes:
            size = sizes.get(size)

        # get each size specification separately (removing blanks)
        size = list(filter(None, size.split('x')))

        if len(size) > 0:
            width_specification = size[0]

            try:
                explicit_width = int(width_specification)
            except ValueError:
                warn('The size specification \'{0}\' has not been defined. '
                     'Image might not display as expected.'.format(width_specification),
                     in_context=actual_image_path)
                explicit_width = None
            else:
                if explicit_width < 0:
                    explicit_width = None

        if len(size) > 1:
            explicit_height = int(size[1]) if size[1].isdigit() else None

            if explicit_height is not None and explicit_height < 0:
                explicit_height = None
        else:
            # default to a squared size using the width specification
            explicit_height = explicit_width

    if is_image(actual_image_path):
        if (explicit_width is not None and
           explicit_height is not None):
                image_tag = '<img src="{0}" width="{1}" height="{2}">'.format(
                    actual_image_path, explicit_width, explicit_height)
        else:
            image_tag = '<img src="{0}">'.format(actual_image_path)
    else:
        image_tag = ''

    return image_tag, actual_image_path


def get_template_fields(template: str) -> list:
    """ Returns a list of all template fields (e.g. {{a_field}}) in a given template """
    return list(re.finditer('{{(.*?)}}', template, re.DOTALL))


def fill_image_fields(content: str, images: dict=None, sizes: dict=None) -> (str, list):
    """ Recursively finds all {{image:size}} fields and returns a string
        replaced with HTML compliant <img> tags.
    """

    image_paths = []

    for match in get_template_fields(content):
        image_path = match.group(1)

        if len(image_path) > 0:
            image_tag, image_path = image_tag_from_path(image_path, images, sizes)

            image_paths.append(image_path)

            # since the string we're finding matches on has just been changed,
            # we have to recursively look for more fields if there are any
            content, filled_image_paths = fill_image_fields(
                content[:match.start()] + image_tag + content[match.end():], images, sizes)

            image_paths.extend(filled_image_paths)

            break

    return content, image_paths


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
    missing_fields_in_template = []

    # go through each data field for this card (row)
    for column in row:
        # ignore special columns
        if not is_special_column(column):
            # fetch the content for the field (may also be templated)
            field_content = str(row[column])

            if is_image(field_content):
                image_paths.append(field_content)
            else:
                # replace any image fields with HTML compliant <img> tags
                field_content, filled_image_paths = fill_image_fields(
                    field_content, metadata.image_definitions, metadata.size_definitions)

                image_paths.extend(filled_image_paths)

            # fill content into the provided template
            template, occurences = fill_template_field(
                field_name=str(column),
                field_value=str(field_content),
                in_template=template)

            if occurences is 0:
                # this field was not found anywhere in the specified template
                missing_fields_in_template.append(column)

    missing_fields_in_data = []

    # find any remaining template fields so we can warn that they were not filled
    remaining_fields = get_template_fields(template)

    # note that leftover fields may include special fields like '{{cards_total}}' that will actually
    # not be filled until all pages have been generated

    if len(remaining_fields) > 0:
        # leftover fields were found
        for remaining_field in remaining_fields:
            # get the actual field name
            field_name = remaining_field.group(1)

            if len(field_name) > 0:
                if is_image(field_name):
                    # the field is probably pointing to an image, so make sure that the image
                    # will be copied to the output directory
                    image_paths.append(field_name)

                    # finally "fill" this image field by simply getting rid of the curly brackets
                    template = template.replace(remaining_field.group(0), field_name)
                else:
                    # the field was not found in the card data, so make a warning about it
                    missing_fields_in_data.append(field_name)

    return template, image_paths, (missing_fields_in_template, missing_fields_in_data)


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


def fill_card(
        template: str,
        template_path: str,
        row: dict,
        row_index: int,
        card_index: int,
        metadata: Metadata) -> (str, list, list):
    """ Returns the contents of a card using the specified template. """

    # fill all row index fields (usually used for error templates)
    template, occurences = fill_template_field(
        field_name='card_row',
        field_value=str(row_index),
        in_template=template)

    # fill all template path fields (usually used for error templates)
    template, occurences = fill_template_field(
        field_name='card_template_path',
        field_value=template_path,
        in_template=template)

    # fill all card index fields
    template, occurences = fill_template_field(
        field_name='card_index',
        field_value=str(card_index),
        in_template=template)

    # fill all version fields
    template, occurences = fill_template_field(
        field_name='version',
        field_value=metadata.version,
        in_template=template)

    # attempt to fill all fields discovered in the template using the data for this card
    template, discovered_image_paths, missing_fields = fill_template(
        template, row, metadata)

    return template, discovered_image_paths, missing_fields


def get_sized_card(card: str, size: str, content: str) -> str:
    card = card.replace('{{size}}', size)
    card = card.replace('{{content}}', content)

    return card


def is_special_column(column: str) -> bool:
    """ Determines whether a column is to be treated as a special column. """

    return column.startswith('@') if column is not None else False


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
