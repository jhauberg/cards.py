# coding=utf-8

import os
import re
import csv
import datetime
import itertools

from typing import List

from cards.resource import get_resource_path, is_resource

from cards.util import dequote, lower_first_row, get_line_number
from cards.warning import WarningDisplay, WarningContext

from cards.constants import ColumnDescriptors, TemplateFields, TemplateFieldDescriptors


class TemplateField:
    """ Represents a field in a template. """

    def __init__(self, inner_content: str, name: str, context: str, start_index: int, end_index: int):
        self.inner_content = inner_content  # the inner content between the field braces
        self.name = name  # the name of the field
        self.context = context  # the context passed to the field name
        self.start_index = start_index  # the index of the first '{' wrapping brace
        self.end_index = end_index  # the index of the last '}' wrapping brace


class TemplateRenderData:
    """ Provides additional data about the rendering of a template. """

    def __init__(self,
                 image_paths: set,
                 unknown_fields: set,
                 unused_fields: set,
                 referenced_definitions: set):
        self.image_paths = image_paths
        self.unknown_fields = unknown_fields
        self.unused_fields = unused_fields
        self.referenced_definitions = referenced_definitions


class ColumnResolutionData:
    """ Provides additional data about the resolution of a column. """

    def __init__(self,
                 column_references: set,
                 definition_references: set):
        self.column_references = column_references
        self.definition_references = definition_references


def template_from_path(template_path: str,
                       relative_to_path: str=None) -> (str, bool, str):
    """ Return the template contents of the given path, if possible.

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


def image_tag_from_path(image_path: str,
                        definitions: dict=None) -> (str, str, list):
    """ Return a HTML-compliant image tag using the specified image path. """

    actual_image_path = image_path

    definition_references = []

    size_index = -1
    no_transform = False

    if image_path is not None:
        # determine whether a size has been explicitly specified;
        # e.g. "images/name-of-image.svg:16x16"
        size_index = image_path.rfind(':')

        # determine whether the : actually represents a protocol specification;
        # i.e. http:// or similar
        if image_path[size_index + 1:size_index + 1 + 2] == '//':
            # in case it is, then ignore anything beyond the protocol specification
            size_index = -1

        no_transform = image_path.endswith(TemplateFieldDescriptors.COPY_ONLY)

        if no_transform:
            actual_image_path = image_path.replace(TemplateFieldDescriptors.COPY_ONLY, '')

            # ignore any size specification since an <img> tag will not be created for this image
            size_index = -1

    explicit_width = None
    explicit_height = None

    if size_index != -1:
        # get rid of the size specification to have a clean image path
        actual_image_path = image_path[:size_index]

        # get the size specification; i.e. whatever is on the right hand size of the ':' splitter
        size = image_path[size_index + 1:].strip()

        # then, determine whether the value is a size specified in the metadata;
        # if it is, use that size specification.
        if definitions is not None and size in definitions:
            definition_references.append(size)

            size = get_definition_content(definitions, definition=size)

        # get each size specification separately (removing blanks)
        size_components = list(filter(None, size.split('x')))

        if len(size_components) > 0:
            width_specification = size_components[0]

            try:
                explicit_width = int(width_specification)
            except ValueError:
                explicit_width = None

                WarningDisplay.unknown_size_specification(
                    WarningContext(actual_image_path), size)
            else:
                if explicit_width < 0:
                    WarningDisplay.invalid_width_specification(
                        WarningContext(actual_image_path), explicit_width)

                    explicit_width = None

        if len(size_components) > 1:
            height_specification = size_components[1]

            try:
                explicit_height = int(height_specification)
            except ValueError:
                explicit_height = None

                WarningDisplay.unknown_size_specification(
                    WarningContext(actual_image_path), size)
            else:
                if explicit_height < 0:
                    WarningDisplay.invalid_height_specification(
                        WarningContext(actual_image_path), explicit_height)

                    explicit_height = None
        else:
            # default to a squared size using the width specification
            explicit_height = explicit_width

    if definitions is not None and actual_image_path in definitions:
        definition_references.append(actual_image_path)

        # the path is actually a definition; e.g. "enemy" or similar, so get the actual path.
        actual_image_path = get_definition_content(definitions, definition=actual_image_path)

    if actual_image_path is not None and is_image(actual_image_path):
        # the path points to an image, so we proceed the transformation
        resource_path = actual_image_path

        if is_resource(actual_image_path):
            # the path is relative and goes back
            image_name = os.path.basename(actual_image_path)
            # transform this path so that it is relative within the output directory,
            # so that we can keep every resource contained
            resource_path = get_resource_path(image_name)

        if no_transform:
            # the image should only be copied - so the "tag" is simply the image path
            image_tag = resource_path
        elif (explicit_width is not None and
              explicit_height is not None):
                # make a tag with the image at the specified dimensions
                image_tag = '<img src="{0}" width="{1}" height="{2}">'.format(
                    resource_path, explicit_width, explicit_height)
        else:
            # make a tag with the image at its intrinsic size
            image_tag = '<img src="{0}">'.format(resource_path)
    else:
        # the file is not an image; or something has gone wrong
        if no_transform or size_index != -1:
            # if either of these attributes exist, then it likely was supposed to be an image
            # but we could not resolve it properly- so warn about it
            WarningDisplay.unresolved_image_reference_error(
                image_reference=image_path,
                closest_resolution_value=actual_image_path)

        # clear any paths or tags as they would just be invalid
        actual_image_path = ''
        image_tag = ''

    return image_tag, actual_image_path, list(set(definition_references))


def get_template_field(field_name: str,
                       in_template: str) -> TemplateField:
    """ Return the first matching template field in a template, if any. """

    pattern = '.{0}'.format(field_name)

    template_fields = get_template_fields(in_template, like_pattern=pattern)

    if len(template_fields) > 0:
        return template_fields[0]

    return None


def get_template_fields(in_template: str,
                        like_pattern: str='[^}}\s]*') -> List[TemplateField]:
    """ Return a list of all template fields (e.g. '{{ a_field }}') that occur in a template. """

    pattern = '{{\s?((' + like_pattern + ')\s?(.*?))\s?}}'

    fields = []

    for field_match in list(re.finditer(pattern, in_template)):
        inner_content = field_match.group(1).strip()
        name = field_match.group(2).strip()
        context = field_match.group(3).strip()

        inner_content = inner_content if len(inner_content) > 0 else None
        name = name if len(name) > 0 else None
        context = context if len(context) > 0 else None

        field = TemplateField(
            inner_content, name, context,
            start_index=field_match.start(),
            end_index=field_match.end())

        fields.append(field)

    return fields


def get_template_field_names(in_template: str) -> List[str]:
    """ Return a list of all template field names that occur in a template. """

    # get all the fields
    template_fields = get_template_fields(in_template)
    # adding each field name to a set ensures we only get unique fields
    template_field_names = {field.inner_content for field in template_fields}

    return list(template_field_names)


def fill_image_fields(in_template: str,
                      definitions: dict=None,
                      tracking_references: bool=False) -> (str, list):
    """ Populate all image fields in the template.

        An image field provides a way of transforming an image path into a HTML-compliant image tag.

        An image field should look like this: '{{ my-image.png:16x16 }}'.
    """

    image_paths = []

    found_definition_references = []

    template_fields = get_template_fields(in_template)

    content = in_template

    for field in template_fields:
        # at this point we don't know that it's actually an image field - we only know that it's
        # a template field, so we just attempt to create an <img> tag from the field.
        # if it turns out to not be an image, we just ignore the field entirely and proceed
        image_tag, image_path, referenced_definitions = image_tag_from_path(
            field.inner_content, definitions)

        if len(referenced_definitions) > 0:
            found_definition_references.extend(referenced_definitions)

        if len(image_path) > 0:
            # we at least discovered that the field was pointing to an image,
            # so in the end it needs to be copied
            image_paths.append(image_path)

        if len(image_tag) > 0:
            # the field was transformed to either an <img> tag, or just the path (for copying only)
            content = fill_template_field(field, image_tag, content)

            if len(template_fields) > 1:
                # so since the content we're finding matches on has just changed, we can no longer
                # rely on the match indices, so we have to recursively "start over" again
                content, filled_image_paths, referenced_definitions = fill_image_fields(
                    content, definitions, tracking_references=True)

                if len(filled_image_paths) > 0:
                    image_paths.extend(filled_image_paths)

                if len(referenced_definitions) > 0:
                    found_definition_references.extend(referenced_definitions)

                break

    return ((content, image_paths, list(set(found_definition_references))) if tracking_references
            else (content, image_paths))


def get_padded_content(content: str, from_start_index: int, in_template: str) -> str:
    """ Return content that is appropriately padded/indented, given a starting position.

        For example, if a starting index of 4 is given for a template "    content\ngoes here",
        the resulting content becomes "    content\n    goes here".
    """

    pad_count = 0
    index = from_start_index

    while index >= 0:
        # keep going backwards in the string
        index -= 1

        if index < 0 or in_template[index] == '\n':
            # we found the previous line or beginning of string
            break

        pad_count += 1

    if pad_count > 0:
        # split content up into separate lines
        lines = content.splitlines(keepends=True)
        # then append padding between each line
        content = (' ' * pad_count).join(lines)

    return content


def fill_template_field(field: TemplateField,
                        field_value: str,
                        in_template: str,
                        indenting: bool=False) -> str:
    """ Populate a single template field in the template. """

    if (field.start_index < 0 or field.start_index > len(in_template) or
       field.end_index < 0 or field.end_index > len(in_template)):
        raise ValueError('Template field \'{0}\' out of range ({1}-{2}).'
                         .format(field.inner_content, field.start_index, field.end_index))

    if indenting:
        field_value = get_padded_content(
            field_value, field.start_index, in_template)

    return in_template[:field.start_index] + field_value + in_template[field.end_index:]


def fill_template_fields(
        field_name: str,
        field_value: str,
        in_template: str,
        counting_occurences: bool=False,
        indenting: bool=False) -> (str, int):
    """ Populate all template fields with a given name in the template. """

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

    if indenting:
        match = search.search(in_template)

        if match is not None:
            start_index, end_index = match.span()

            field_value = get_padded_content(field_value, start_index, in_template)

    # finally replace any found occurences of the template field with its value
    content, occurences = search.subn(field_value, in_template)

    return (content, occurences) if counting_occurences else content


def fill_date_fields(date: datetime, in_template: str) -> str:
    """ Populate all date fields in the template.

        A 'date' field provides an easy way of putting the current date into a template.

        A date field uses built-in Python date formats, and should look like this:

            '{{ date }}'              - using default formatting
            '{{ date '%d, %b %Y' }}'  - using custom formatting

        See all supported format identifiers here http://strftime.org
    """

    template_content = in_template

    for field in get_template_fields(template_content, like_pattern='date'):
        # default date format: 07, Oct 2016
        date_format = '%B %-d, %Y'

        if field.context is not None:
            # a date field can have a custom format
            custom_date_format = dequote(field.context).strip()

            if len(custom_date_format) > 0:
                # if found, we'll use that and let date.strftime handle it
                date_format = custom_date_format

        formatted_date = date.strftime(date_format)

        # populate the include field with the content; or blank if unresolved
        template_content = fill_template_field(
            field, formatted_date,
            in_template=template_content)

        # since we're using fill_template_field, we have to recursively start over,
        # otherwise the next field objects would have invalid indices and would not be
        # resolved properly
        template_content = fill_date_fields(
            date, in_template=template_content)

        break

    return template_content


def fill_include_fields(from_base_path: str,
                        in_template: str) -> str:
    """ Populate all include fields in the template.

        An 'include' field provides a way of putting re-usable template content into a
        separate file, and including it in place of the field.

        An include field should look like this:

            '{{ include 'path/to/file.html' }}'
    """

    template_content = in_template

    # find all template fields and go through each, determining whether it's an include field or not
    for field in get_template_fields(template_content, like_pattern='include|inline'):
        if field.name is not None:
            is_include_command = field.name == TemplateFields.INCLUDE
            is_inline_command = field.name == TemplateFields.INLINE

            if not is_include_command and not is_inline_command:
                # we're in a situation where we've, somehow, found neither of the type of fields
                # we're looking for; so just move on
                continue

            # default to blank
            include_content = ''
            include_path = None

            if field.context is not None:
                # the field should contain a path
                include_path = dequote(field.context).strip()

            if include_path is not None and len(include_path) > 0:
                if not os.path.isabs(include_path):
                    # it's not an absolute path, so we should make it a relative path
                    if from_base_path is not None:
                        # make the path relative to the path of the containing template
                        include_path = os.path.join(
                            os.path.dirname(from_base_path), include_path)

                if os.path.isfile(include_path):
                    # we've ended up with a path that can be opened
                    with open(include_path) as include_file:
                        if is_include_command:
                            # open it and read in the entire contents as is
                            include_content = include_file.read().strip()
                        elif is_inline_command:
                            # read each line
                            for line in include_file.readlines():
                                # stripping excess whitespace and newline in the process
                                include_content += line.strip()
                else:
                    WarningDisplay.included_file_not_found_error(
                        WarningContext(os.path.basename(from_base_path)), include_path)
            else:
                WarningDisplay.include_should_specify_file(
                    WarningContext('{0}:{1}'.format(
                        os.path.basename(from_base_path),
                        get_line_number(field.start_index, in_template))),
                    is_inline=is_inline_command)

            # populate the include field with the content; or blank if unresolved
            template_content = fill_template_field(
                field, include_content, template_content, indenting=is_include_command)

            # since we're using fill_template_field, we have to recursively start over,
            # otherwise the next field objects would have invalid indices and would not be
            # resolved properly
            template_content = fill_include_fields(
                from_base_path, in_template=template_content)

            break

    return template_content


def fill_definitions(definitions: dict,
                     in_template: str) -> (str, set):
    """ Populate all definition fields in the template.

        Note that this does not currently include definitions used in image fields.
    """

    template_content = in_template

    definitions_in_template = []

    # find all the visible template fields, but because we're going to be populating all occurences
    # of a field in one fell swoop, we only need a list of unique field names-
    # we don't need to go through each field instance
    field_names = get_template_field_names(in_template)

    for field_name in field_names:
        if field_name not in definitions:
            # this field is not a definition- so skip it
            continue

        # recursively resolve the content of the definition
        resolved_value = get_definition_content(definitions, definition=field_name)

        # fill any occurences of the definition
        template_content, occurences = fill_template_fields(
            field_name=field_name,
            field_value=resolved_value,
            in_template=template_content,
            counting_occurences=True)

        if occurences > 0:
            definitions_in_template.append(field_name)

    return template_content, set(definitions_in_template)


def fill_template(template: str,
                  template_path: str,
                  row: dict,
                  in_data_path: str,
                  definitions: dict) -> (str, TemplateRenderData):
    """ Populate all template fields in the template.

        Populating a template is done in 4 steps:

        First, an attempt is made at filling any include fields, since they might provide
        additional fields that needs to be resolved.

        Secondly, for each column in the row, a pass is made in an attempt to fill any matching
        column fields; recursively resolving any column references or definitions.

        Thirdly, for each definition, a pass is made in an attempt to fill any matching definition
        fields; recursively resolving any definition references.

        Finally, once all fields and references have been resolved, any remaining fields will be
        attempted resolved as image fields.
    """

    # first of all, find any include fields and populate those,
    # as they might contribute even more template fields to populate
    template = fill_include_fields(
        from_base_path=template_path,
        in_template=template)

    # any field that is in the data, but not found in the template; for example, if there's
    # a 'rank' column in the data, but no '{{ rank }}' field in the template
    unused_columns = []

    column_references_in_data = []
    discovered_definition_references = []

    # fill any definition fields- note that this should happen prior to filling image fields,
    # since that allows a definition to include image references
    template, referenced_definitions = fill_definitions(definitions, in_template=template)

    discovered_definition_references.extend(referenced_definitions)

    # go through each data field for this card (row)
    for column in row:
        # fetch the content for the field
        field_content, resolution_data = get_column_content(
            row, column, in_data_path, definitions,
            default_content='', tracking_references=True)

        # fill content into the provided template
        template, occurences = fill_template_fields(
            field_name=column,
            field_value=field_content,
            in_template=template,
            counting_occurences=True)

        if occurences is 0:
            # this field was not found anywhere in the specified template
            unused_columns.append(column)
        else:
            # this field was found and populated in the template, so save any column references
            # made in the column content, so we can later compare that to the list of missing fields
            column_references_in_data.extend(list(resolution_data.column_references))
            discovered_definition_references.extend(list(resolution_data.definition_references))

    # in case data might contain a column that clashes with the date field; i.e. named 'date'
    # just do this last so that the column always overrules
    template = fill_date_fields(
        datetime.date.today(), in_template=template)

    # replace any image fields with HTML compliant <img> tags
    template, filled_image_paths, referenced_definitions = fill_image_fields(
        template, definitions, tracking_references=True)

    discovered_definition_references.extend(referenced_definitions)

    # any template field visible in the template, but not found in the data; for example, if
    # the template has a {{ rank }} field (or more), but no 'rank' column in the data
    unknown_fields = []

    template = fill_empty_fields(in_template=template)

    # find any remaining template fields so we can warn that they were not filled
    remaining_fields = get_template_fields(in_template=template)

    for field in remaining_fields:
        if field.inner_content == TemplateFields.CARDS_TOTAL:
            # this is a special case: this field will not be filled until every card
            # has been generated- so this field should not be treated as if missing;
            # instead, simply ignore it at this point
            pass
        else:
            # try to resolve any row references
            column_reference, reference_row = get_column_reference(
                field.inner_content, in_reference_row=row, in_data_path=in_data_path)

            field_content = get_column_content(
                reference_row, column_reference, in_data_path, definitions)

            if field_content is not None:
                template = fill_template_fields(
                    field_name=field.inner_content,
                    field_value=field_content,
                    in_template=template)
            else:
                # the field was not found in the card data, so make a warning about it
                unknown_fields.append(field.inner_content)

    # make sure we only have one of each reference
    column_references = set(column_references_in_data)

    # remove any "missing fields" that are actually referenced in column content-
    # they may not be in the template, but they are not unused/missing, so don't warn about it
    unused_columns = list(set(unused_columns) - column_references)

    return template, TemplateRenderData(
        image_paths=set(filled_image_paths),
        unknown_fields=set(unknown_fields),
        unused_fields=set(unused_columns),
        referenced_definitions=set(discovered_definition_references))


def fill_empty_fields(in_template: str) -> str:
    return fill_template_fields(field_name='', field_value='', in_template=in_template)


def fill_card(
        template: str,
        template_path: str,
        row: dict,
        row_index: int,
        in_data_path: str,
        card_index: int,
        card_copy_index: int,
        definitions: dict) -> (str, TemplateRenderData):
    """ Return the contents of a card using the specified template. """

    # attempt to fill all fields discovered in the template using the data for this card
    template, render_data = fill_template(
        template, template_path, row, in_data_path, definitions)

    # fill all row index fields (usually used for error templates)
    template = fill_template_fields(
        field_name=TemplateFields.CARD_ROW_INDEX,
        field_value=str(row_index),
        in_template=template)

    # fill all template path fields (usually used for error templates)
    template = fill_template_fields(
        field_name=TemplateFields.CARD_TEMPLATE_PATH,
        field_value=template_path,
        in_template=template)

    # fill all card index fields
    template = fill_template_fields(
        field_name=TemplateFields.CARD_INDEX,
        field_value=str(card_index),
        in_template=template)

    template = fill_template_fields(
        field_name=TemplateFields.CARD_COPY_INDEX,
        field_value=str(card_copy_index),
        in_template=template)

    # card data might contain the following fields, but they would not have been rendered
    # during fill_template(), so make sure to remove them from the missing list if necessary
    except_fields = {TemplateFields.CARD_INDEX,
                     TemplateFields.CARD_ROW_INDEX,
                     TemplateFields.CARD_COPY_INDEX,
                     TemplateFields.CARD_TEMPLATE_PATH}

    # update the set of unknown fields to not include the exceptions listed above
    render_data.unknown_fields = render_data.unknown_fields - except_fields

    return template, render_data


def fill_card_front(
        template: str,
        template_path: str,
        row: dict,
        row_index: int,
        in_data_path: str,
        card_index: int,
        card_copy_index: int,
        definitions: dict) -> (str, TemplateRenderData):
    """ Return the contents of the front of a card using the specified template. """

    return fill_card(template, template_path, get_front_data(row), row_index, in_data_path,
                     card_index, card_copy_index, definitions)


def fill_card_back(
        template: str,
        template_path: str,
        row: dict,
        row_index: int,
        in_data_path: str,
        card_index: int,
        card_copy_index: int,
        definitions: dict) -> (str, TemplateRenderData):
    """ Return the contents of the back of a card using the specified template. """

    return fill_card(template, template_path, get_back_data(row), row_index, in_data_path,
                     card_index, card_copy_index, definitions)


def get_front_data(row: dict) -> dict:
    """ Return a dict containing only fields fit for the front of a card. """

    return {column: value for column, value in row.items()
            if not is_special_column(column) and not is_back_column(column)}


def get_back_data(row: dict) -> dict:
    """ Return a dict containing only fields fit for the back of a card. """

    return {column[:-len(ColumnDescriptors.BACK_ONLY)]: value for column, value in row.items()
            if not is_special_column(column) and is_back_column(column)}


def get_column_reference(field_name: str,
                         in_reference_row: dict,
                         in_data_path: str) -> (str, dict):
    """ Return the field name and the row of data that it references.

        If a field name like 'title #6' is passed, then 'title' and row number 6 is returned.
        If it is not considered a reference, just the field name and current row is returned.
    """

    # set default field name and row to whatever is passed
    reference_column = field_name
    reference_row = in_reference_row

    if in_data_path is not None and len(in_data_path) > 0:
        # a data path has been supplied, so we can attempt determining whether this
        # field is a reference to a column in another row
        field_components = field_name.split(' ', 1)

        if len(field_components) > 0:
            # it might be, because there's multiple components in the field name
            if len(field_components) > 1 and field_components[1].startswith('#'):
                # we've determined that this is probably a reference to another row
                # so get the row number
                row_number = field_components[1][1:]

                try:
                    row_number = int(row_number)
                except ValueError:
                    row_number = None

                if row_number is not None:
                    # when looking at rows in a CSV they are not zero-based, and the first row
                    # is always the headers, which makes the first row of actual data (that
                    # you see) appear visually at row #2, like for example:
                    #   #1 'rank,title'
                    #   #2 '2,My Card'
                    #   #2 '4,My Other Card'
                    # however, of course, when reading from the file, the first row is
                    # actually at index 0, so we have to take this into account
                    row_number -= 2

                    # the above logic essentially makes '#0' and '#1' invalid row numbers
                    if row_number >= 0:
                        # open a new instance of the current data file
                        with open(in_data_path) as data_file:
                            # actual field name is only the first part
                            reference_column = field_components[0]
                            # read data appropriately
                            data = csv.DictReader(lower_first_row(data_file))
                            # then read rows until reaching the target row_number
                            reference_row = next(itertools.islice(data, row_number, None))

    return reference_column, reference_row


def get_column_content(row: dict,
                       column: str,
                       in_data_path: str,
                       definitions: dict,
                       default_content: str=None,
                       tracking_references: bool=False) -> str:
    """ Return the content of a column, recursively resolving any column/definition references. """

    # get the raw content of the column, optionally assigning a default value
    column_content = row.get(column, default_content)

    column_references = []
    definition_references = []

    if column_content is not None:
        # strip excess whitespace
        column_content = column_content.strip()
        # fill any include fields before doing anything else
        column_content = fill_include_fields(in_data_path, in_template=column_content)

        # there's at least some kind of content, so begin filling column reference fields (if any)
        reference_field_names = get_template_field_names(column_content)

        for reference_field_name in reference_field_names:
            if len(reference_field_name) == 0:
                # there's at least one empty field (e.g. {{ }}) in the content, so get rid of it
                column_content = fill_template_fields(
                    field_name=reference_field_name,
                    field_value='',
                    in_template=column_content)
                # and just proceed
                continue

            column_reference, reference_row = get_column_reference(
                reference_field_name, in_reference_row=row, in_data_path=in_data_path)

            # determine if the field occurs as a definition
            is_definition = column_reference in definitions
            # determine if the field occurs as a column in the current row- note that if
            # the current row is actually the definitions, then it actually *is* a column,
            # but it should not be treated as such
            is_column = column_reference in reference_row and reference_row is not definitions

            if not is_column and not is_definition:
                # the field is not a reference that can be resolved right now, so skip it
                # (it might be an image reference)
                continue

            # recursively get the content of the referenced column to ensure any further
            # references are determined and filled prior to filling the originating reference

            if is_column:
                # prioritize the column reference by resolving it first,
                # even if it could also be a definition instead (but warn about it later)
                column_reference_content, resolution_data = get_column_content(
                    reference_row, column_reference, in_data_path, definitions, default_content,
                    tracking_references=True)
            elif is_definition:
                # resolve the definition reference, keeping track of any discovered references
                column_reference_content, resolution_data = get_definition_content(
                    definitions, definition=column_reference,
                    tracking_references=True)

            column_references.extend(list(resolution_data.column_references))
            definition_references.extend(list(resolution_data.definition_references))

            # and ultimately fill any occurences
            column_content, occurences = fill_template_fields(
                field_name=reference_field_name,
                field_value=column_reference_content,
                in_template=column_content,
                counting_occurences=True)

            if occurences > 0 and tracking_references:
                if is_column:
                    column_references.append(column_reference)
                elif is_definition:
                    definition_references.append(column_reference)

            if occurences > 0 and (is_definition and is_column and
                                   reference_row is not definitions):
                # the reference appears multiple places
                context = os.path.basename(in_data_path)
                # so warn about it
                WarningDisplay.ambiguous_reference(
                    WarningContext(context), column_reference, column_reference_content)

        # in case data might contain a column that clashes with the date field; i.e. named 'date'
        # just do this last so that the column always overrules
        column_content = fill_date_fields(datetime.date.today(), in_template=column_content)

        # transform content to html using any applied markdown formatting
        column_content = markdown(column_content)

    resolution_data = ColumnResolutionData(
        set(column_references), set(definition_references))

    return ((column_content, resolution_data) if tracking_references
            else column_content)


def get_definition_content(definitions: dict,
                           definition: str,
                           tracking_references: bool=False) -> str:
    """ Return the content of a definition, recursively resolving any references. """

    definition_content, resolution_data = get_column_content(
        row=definitions, column=definition, in_data_path='', definitions=definitions,
        default_content='', tracking_references=True)

    return ((definition_content, resolution_data) if tracking_references
            else definition_content)


def get_sized_card(card: str,
                   size_class: str,
                   content: str) -> str:
    """ Populate and return a card in a given size with the specified content. """

    card = fill_template_fields(TemplateFields.CARD_SIZE, size_class, in_template=card)
    card = fill_template_fields(TemplateFields.CARD_CONTENT, content, in_template=card, indenting=True)

    return card


def is_image(image_path: str) -> bool:
    """ Determine whether a path points to an image. """

    return image_path.strip().lower().endswith(('.svg', '.png', '.jpg', '.jpeg'))


def is_special_column(column: str) -> bool:
    """ Determine whether a column is to be treated as a special column. """

    return column.startswith('@') if column is not None else False


def is_back_column(column: str) -> bool:
    """ Determine whether a column is only intended for the back of a card. """

    return column.endswith(ColumnDescriptors.BACK_ONLY) if column is not None else False


def markdown(content: str) -> str:
    """ Transform any Markdown formatting into HTML.

        Supports:
            *emphasis*, _emphasis_
            **strong**, __strong__, "they can _also be **combined**_"
            ~~deleted~~, ++inserted++
            superscript^5

            Line break using multiples of 2 whitespace:
                "break  once", "break    twice", "break      thrice"
            or break twice by using 3 whitespace:
                "break   twice"
            note that multiples of 3 is not possible; e.g. 6 whitespace will be treated as 3 breaks.
    """

    # match any variation of bounding *'s:
    # e.g. "emphasize *this*", or "strong **this**"
    content = re.sub('(\*\*)(.+?)(\*\*)', '<strong>\\2</strong>', content)
    content = re.sub('(\*)(.+?)(\*)', '<em>\\2</em>', content)

    # match any variation of bounding _'s:
    # e.g. "emphasize _this_", or "strong __this__"
    # note that _'s applies under slightly different rules than *'s; it only kicks in
    # when preceded and superceded by a special character or whitespace;
    # e.g. "this_does not work_", "but _this does_" and "this (_works too_)"
    content = re.sub('(?<=(\s|[^a-zA-Z0-9]))(__)(.+?)(__)(?=(\s|[^a-zA-Z0-9]))', '<em>\\3</em>', content)
    content = re.sub('(?<=(\s|[^a-zA-Z0-9]))(_)(.+?)(_)(?=(\s|[^a-zA-Z0-9]))', '<em>\\3</em>', content)

    # match any variation of bounding ^'s:
    # e.g. "5 kg/m^3^"
    # content = re.sub('\^(.+)\^', '<sup>\\1</sup>', content)

    # match preceding ^; e.g. "5 kg/m^3"
    # note that this is preferred over using bounding ^'s, as both do not work together without
    # applying extended rules (like with the _'s)
    content = re.sub('\^(.+?)(?=(\s|\n|$))', '<sup>\\1</sup>', content)

    # matches any variation of bounding ~~'s': e.g. "deleted ~~this~~"
    content = re.sub('~~(.+)~~', '<del>\\1</del>', content)
    # matches any variation of bounding ++'s': e.g. "inserted ++this++"
    content = re.sub('\+\+(.+)\+\+', '<ins>\\1</ins>', content)

    # matches exactly: "break this   line twice"
    # 4 whitespaces should produce same result, but this is a shortcut since 2 breaks is common
    content = re.sub('(?<=\S)((\s{3})(?=\S))', '<br /><br />', content)
    # matches any variation of 2 whitespace:
    # e.g. "break this  line", or "break this    line twice"
    content = re.sub('\s\s', '<br />', content)

    return content
