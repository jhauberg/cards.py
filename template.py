# coding=utf-8

import csv
import os
import re

from typing import List

from util import most_common, warn
from meta import Metadata


class TemplateField(object):
    """ Represents a data field in a template. """

    def __init__(self, name: str, start_index: int, end_index: int):
        self.name = name  # the inner value of the template field; i.e. the name
        self.start_index = start_index  # the index of the first '{' wrapping character
        self.end_index = end_index  # the index of the last '}' wrapping character


def image_tag_from_path(image_path: str, images: dict=None, sizes: dict=None) -> (str, str):
    """ Constructs an HTML compliant image tag using the specified image path. """

    actual_image_path = ''

    # determine whether a size has been explicitly specified; e.g. "images/name-of-image.svg:16x16"
    size_index = image_path.rfind(':')

    # determine whether the : actually represents a protocol specification; i.e. http:// or similar
    if image_path[size_index + 1:size_index + 1 + 2] == '//':
        # in case it is, then ignore anything beyond the protocol specification
        size_index = -1

    copy_only = image_path.endswith('@copy-only')

    if copy_only:
        actual_image_path = image_path.replace('@copy-only', '')

        # ignore any size specification since an <img> tag will not be created for this image
        size_index = -1

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
        if copy_only:
            # the image should only be copied - so the "tag" is simply the image path
            image_tag = actual_image_path
        elif (explicit_width is not None and
              explicit_height is not None):
                image_tag = '<img src="{0}" width="{1}" height="{2}">'.format(
                    actual_image_path, explicit_width, explicit_height)
        else:
            image_tag = '<img src="{0}">'.format(actual_image_path)
    else:
        image_tag = ''

    return image_tag, actual_image_path


def get_template_fields(template: str) -> List[TemplateField]:
    """ Returns a list of all template fields (e.g. {{a_field}}) in a given template. """

    return [TemplateField(name=field.group(1).strip(),
                          start_index=field.start(), end_index=field.end())
            for field in list(re.finditer('{{(.*?)}}', template, re.DOTALL))]


def fill_image_fields(content: str, images: dict=None, sizes: dict=None) -> (str, list):
    """ Recursively finds all {{image:size}} fields and returns a string
        replaced with HTML compliant <img> tags.
    """

    image_paths = []

    for field in get_template_fields(content):
        # at this point we don't know that it's actually an image field - we only know that it's
        # a template field, so we just attempt to create an <img> tag from the field.
        # if it turns out to not be an image, we just ignore the field entirely and proceed
        image_tag, image_path = image_tag_from_path(field.name, images, sizes)

        if len(image_path) > 0:
            # we at least discovered that the field was pointing to an image,
            # so in the end it needs to be copied
            image_paths.append(image_path)

        if len(image_tag) > 0:
            # the field was transformed to either an <img> tag, or just the path (for copying only)
            content = fill_template_field(field, image_tag, content)

            # so since the content we're finding matches on has just changed, we can no longer
            # rely on the match indices, so we have to recursively "start over" again
            content, filled_image_paths = fill_image_fields(
                content, images, sizes)

            if len(filled_image_paths) > 0:
                image_paths.extend(filled_image_paths)

            break

    return content, image_paths


def fill_template_field(field: TemplateField, field_value: str, in_template: str) -> str:
    """ Fills a single template field with a value. """

    return in_template[:field.start_index] + field_value + in_template[field.end_index:]


def fill_template_fields(field_name: str, field_value: str, in_template: str) -> (str, int):
    """ Fills all occurences of a named template field with a value. """

    # make sure that we have a sane value
    field_value = field_value if field_value is not None else ''

    # template fields are always represented by wrapping {{ }}'s,
    # however, both {{my_field}} and {{ my_field }} should be valid;
    # i.e. any leading or trailing whitespace should simply be ignored
    field_search = '{{\s*' + field_name + '\s*}}'

    # find any occurences of the field, using a case-insensitive
    # comparison, to ensure that e.g. {{name}} is populated with the
    # value from column "Name", even though the casing might differ
    search = re.compile(field_search, re.IGNORECASE)

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
        # fetch the content for the field (may also be templated)
        field_content = str(row[column])

        if is_image(field_content):
            # this field contains only an image path, so we have to make sure that it gets copied
            # note: a field that only specifies an image should rather use
            # "{{image.png@copy-only}}", but for convenience "image.png" gives the same result
            image_paths.append(field_content)

        # fill content into the provided template
        template, occurences = fill_template_fields(
            field_name=str(column),
            field_value=str(field_content),
            in_template=template)

        if occurences is 0:
            # this field was not found anywhere in the specified template
            missing_fields_in_template.append(column)

    # replace any image fields with HTML compliant <img> tags
    template, filled_image_paths = fill_image_fields(
        template, metadata.image_definitions, metadata.size_definitions)

    image_paths.extend(filled_image_paths)

    missing_fields_in_data = []

    # find any remaining template fields so we can warn that they were not filled
    remaining_fields = get_template_fields(template)

    if len(remaining_fields) > 0:
        # leftover fields were found
        for field in remaining_fields:
            if len(field.name) > 0:
                if field.name == 'cards_total':
                    # this is a special case: this field will not be filled until every card
                    # has been generated- so this field should not be treated as if missing;
                    # instead, simply ignore it at this point
                    pass
                else:
                    # the field was not found in the card data, so make a warning about it
                    missing_fields_in_data.append(field.name)

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
    template, occurences = fill_template_fields(
        field_name='card_row',
        field_value=str(row_index),
        in_template=template)

    # fill all template path fields (usually used for error templates)
    template, occurences = fill_template_fields(
        field_name='card_template_path',
        field_value=template_path,
        in_template=template)

    # fill all card index fields
    template, occurences = fill_template_fields(
        field_name='card_index',
        field_value=str(card_index),
        in_template=template)

    # fill all version fields
    template, occurences = fill_template_fields(
        field_name='version',
        field_value=metadata.version,
        in_template=template)

    # attempt to fill all fields discovered in the template using the data for this card
    template, discovered_image_paths, missing_fields = fill_template(
        template, row, metadata)

    return template, discovered_image_paths, missing_fields


def fill_card_front(
        template: str,
        template_path: str,
        row: dict,
        row_index: int,
        card_index: int,
        metadata: Metadata) -> (str, list, list):
    """ Returns the contents of the front of a card using the specified template. """

    return fill_card(template, template_path, get_front_data(row), row_index, card_index, metadata)


def fill_card_back(
        template: str,
        template_path: str,
        row: dict,
        row_index: int,
        card_index: int,
        metadata: Metadata) -> (str, list, list):
    """ Returns the contents of the back of a card using the specified template. """

    return fill_card(template, template_path, get_back_data(row), row_index, card_index, metadata)


def get_front_data(row: dict) -> dict:
    """ Returns a dict containing only fields fit for the front of a card. """

    return {column: value for column, value in row.items()
            if not is_special_column(column) and not is_back_column(column)}


def get_back_data(row: dict) -> dict:
    """ Returns a dict containing only fields fit for the back of a card. """

    return {column[:-len('@back')]: value for column, value in row.items()
            if not is_special_column(column) and is_back_column(column)}


def get_sized_card(card: str, size: str, content: str) -> str:
    card = card.replace('{{size}}', size)
    card = card.replace('{{content}}', content)

    return card


def is_image(image_path: str) -> bool:
    """ Determines whether a path points to an image. """

    return image_path.strip().lower().endswith(('.svg', '.png', '.jpg', '.jpeg'))


def is_special_column(column: str) -> bool:
    """ Determines whether a column is to be treated as a special column. """

    return column.startswith('@') if column is not None else False


def is_back_column(column: str) -> bool:
    """ Determines whether a column is only intended for the back of a card. """

    return column.endswith('@back') if column is not None else False


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
