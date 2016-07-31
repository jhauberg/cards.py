# coding=utf-8

import os
import re

from typing import List

from cards.util import WarningContext, warn, dequote

from cards.constants import ColumnDescriptors, TemplateFields, TemplateFieldDescriptors


class TemplateField(object):
    """ Represents a field in a template. """

    def __init__(self, name: str, start_index: int, end_index: int):
        self.name = name  # the inner value of the template field; i.e. the field name
        self.start_index = start_index  # the index of the first '{' wrapping character
        self.end_index = end_index  # the index of the last '}' wrapping character


def warn_ambiguous_reference(reference, result) -> None:
    truncated_result = (result if len(result) < 18 else result[:18] + '…')

    warn('A reference named \'{0}\' could refer to both a column or a definition. '
         'The column data \'{1}\' was used.'
         .format(reference, truncated_result))


def warn_unknown_size_specification(context: WarningContext, size_specification: str) -> None:
    warn('The size specification \'{0}\' has not been defined. '
         'Image might not display as expected.'
         .format(size_specification),
         in_context=context)


def warn_included_file_not_found(context: WarningContext, included_file_path: str) -> None:
    warn('An included file was not found: \033[4;31m\'{0}\'\033[0m'
         .format(included_file_path),
         in_context=context,
         as_error=True)


def image_tag_from_path(image_path: str, definitions: dict=None) -> (str, str):
    """ Return a HTML-compliant image tag using the specified image path. """

    actual_image_path = image_path

    # determine whether a size has been explicitly specified; e.g. "images/name-of-image.svg:16x16"
    size_index = image_path.rfind(':')

    # determine whether the : actually represents a protocol specification; i.e. http:// or similar
    if image_path[size_index + 1:size_index + 1 + 2] == '//':
        # in case it is, then ignore anything beyond the protocol specification
        size_index = -1

    copy_only = image_path.endswith(TemplateFieldDescriptors.COPY_ONLY)

    if copy_only:
        actual_image_path = image_path.replace(TemplateFieldDescriptors.COPY_ONLY, '')

        # ignore any size specification since an <img> tag will not be created for this image
        size_index = -1

    explicit_width = None
    explicit_height = None

    if size_index is not -1:
        # get rid of the size specification to have a clean image path
        actual_image_path = image_path[:size_index]

        # get the size specification; i.e. whatever is on the right hand size of the ':' splitter
        size = image_path[size_index + 1:].strip()

        # then, determine whether the value is a size specified in the metadata;
        # if it is, use that size specification.
        if definitions is not None and size in definitions:
            size = get_definition_content(definitions, definition=size)

        # get each size specification separately (removing blanks)
        size = list(filter(None, size.split('x')))

        if len(size) > 0:
            width_specification = size[0]

            try:
                explicit_width = int(width_specification)
            except ValueError:
                explicit_width = None

                warn_unknown_size_specification(
                    WarningContext(actual_image_path), width_specification)
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

    if definitions is not None and actual_image_path in definitions:
        # the path is actually a definition; e.g. "enemy" or similar, so get the actual path.
        actual_image_path = get_definition_content(definitions, definition=actual_image_path)

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
        actual_image_path = ''
        image_tag = ''

    return image_tag, actual_image_path


def get_template_field(field_name: str, in_template: str) -> TemplateField:
    """ Return the first matching template field in a template, if any. """

    field_search = '{{\s*' + field_name + '\s*}}'
    field_matches = list(re.finditer(field_search, in_template, re.DOTALL))

    for field_match in field_matches:
        return TemplateField(name=field_match.group(1).strip(),
                             start_index=field_match.start(), end_index=field_match.end())

    return None


def get_template_fields(in_template: str) -> List[TemplateField]:
    """ Return a list of all template fields (e.g. '{{ a_field }}') that occur in a template. """

    return [TemplateField(name=field.group(1).strip(),
                          start_index=field.start(), end_index=field.end())
            for field in list(re.finditer('{{(.*?)}}', in_template, re.DOTALL))]


def get_template_field_names(in_template: str) -> List[str]:
    """ Return a list of all template field names that occur in a template. """

    template_fields = get_template_fields(in_template)
    template_field_names = {field.name for field in template_fields}

    return list(template_field_names)


def fill_image_fields(content: str, definitions: dict=None) -> (str, list):
    """ Populate all image fields in the template.

        An image field provides a way of transforming an image path into a HTML-compliant image tag.

        An image field should look like this: '{{ my-image.png:16x16 }}'.
    """

    image_paths = []

    for field in get_template_fields(content):
        # at this point we don't know that it's actually an image field - we only know that it's
        # a template field, so we just attempt to create an <img> tag from the field.
        # if it turns out to not be an image, we just ignore the field entirely and proceed
        image_tag, image_path = image_tag_from_path(field.name, definitions)

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
                content, definitions)

            if len(filled_image_paths) > 0:
                image_paths.extend(filled_image_paths)

            break

    return content, image_paths


def fill_definitions(definitions: dict, in_template: str) -> str:
    """ Populate all definition fields in the template. """

    template_content = in_template

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
        template_content = fill_template_fields(
            field_name=field_name,
            field_value=resolved_value,
            in_template=template_content)

    return template_content


def fill_template_field(field: TemplateField, field_value: str, in_template: str) -> str:
    """ Populate a single template field in the template. """

    if (field.start_index < 0 or field.start_index >= len(in_template) or
       field.end_index < 0 or field.end_index >= len(in_template)):
        raise ValueError('Template field \'{0}\' out of range.'.format(field.name))

    return in_template[:field.start_index] + field_value + in_template[field.end_index:]


def fill_template_fields(
        field_name: str,
        field_value: str,
        in_template: str,
        counting_occurences=False) -> (str, int):
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

    # finally replace any found occurences of the template field with its value
    content, occurences = search.subn(field_value, in_template)

    return (content, occurences) if counting_occurences else content


def fill_include_fields(from_template_path: str, in_template: str) -> str:
    """ Populate all include fields in the template.

        An 'include' field provides a way of putting re-usable template components/content into a
        separate file, and including it in place of the field.

        An include field should look like this: '{{ include 'path/to/file.html' }}'.
    """

    template_content = in_template

    # find all template fields and go through each, determining whether it's an include field or not
    for field in get_template_fields(template_content):
        # include fields should strictly separate the keyword and path by a single whitespace
        field_components = field.name.split(' ', 1)

        if len(field_components) > 0 and field_components[0] == TemplateFields.INCLUDE:
            # the field at least contains the include keyword
            if len(field_components) > 1:
                # the field might also contain a path
                include_path = dequote(field_components[1])
                # default to blank
                include_content = ''

                if not os.path.isabs(include_path):
                    # it's not an absolute path, so we should make it a relative path
                    if from_template_path is not None:
                        # make the path relative to the path of the containing template
                        include_path = os.path.join(
                            os.path.dirname(from_template_path), include_path)

                if os.path.isfile(include_path):
                    # we've ended up with a path that can be opened
                    with open(include_path) as f:
                        # so we open it and read in the entire content
                        include_content = f.read()
                else:
                    warn_included_file_not_found(
                        WarningContext(os.path.basename(from_template_path)), include_path)

                # populate the include field with the content; or blank if unresolved
                template_content = fill_template_field(
                    field, include_content, template_content)

                # since we're using fill_template_field, we have to recursively start over,
                # otherwise the next field objects would have invalid indices and would not be
                # resolved properly
                template_content = fill_include_fields(
                    from_template_path, in_template=template_content)

                break

    return template_content


def fill_template(template: str,
                  template_path: str,
                  row: dict,
                  definitions: dict) -> (str, set, set):
    """ Populate all template fields in the template.

        Populating a template is done in 4 steps:

        First, an attempt is made at filling any include fields, since they might provide
        additional fields that needs to be resolved.

        Secondly, for each column in the row, a pass is made in an attempt to fill any matching
        column fields; recursively resolving any contained column references or definitions.

        Thirdly, for each definition, a pass is made in an attempt to fill any matching definition
        fields; recursively resolving any contained definition references.

        Finally, once all fields and references have been resolved, any remaining fields will be
        attempted resolved as image fields.
    """

    # first of all, find any {{ include }} fields and populate those,
    # as they might contribute even more template fields to populate
    template = fill_include_fields(
        from_template_path=template_path,
        in_template=template)

    # any discovered image paths from image fields
    image_paths = []

    # any field that is in the data, but not found in the template; for example, if there's
    # a 'rank' column in the data, but no {{ rank }} field in the template
    missing_fields_in_template = []
    column_references_in_data = []

    # go through each data field for this card (row)
    for column in row:
        # fetch the content for the field
        field_content, referenced_columns = get_column_content(
            row, column, definitions, default_content='', tracking_references=True)

        if is_image(field_content):
            # this field contains only an image path, so we have to make sure that it gets copied
            # note: a field that only specifies an image should rather use
            # "{{ image.png@copy-only }}", but for convenience "image.png" gives the same result
            image_paths.append(field_content)

        # fill content into the provided template
        template, occurences = fill_template_fields(
            field_name=column,
            field_value=field_content,
            in_template=template,
            counting_occurences=True)

        if occurences is 0:
            # this field was not found anywhere in the specified template
            missing_fields_in_template.append(column)
        else:
            # this field was found and populated in the template, so save any column references
            # made in the column content, so we can later compare that to the list of missing fields
            column_references_in_data.extend(referenced_columns)

    # make sure we only have one of each reference
    column_references = set(column_references_in_data)

    # remove any "missing fields" that are actually referenced in column content-
    # they may not be in the template, but they are not unused/missing, so don't warn about it
    missing_fields_in_template = list(set(missing_fields_in_template) - column_references)

    # fill any definition fields- note that this should happen prior to filling image fields,
    # since that allows symbol definitions to include image references
    template = fill_definitions(definitions, in_template=template)

    # replace any image fields with HTML compliant <img> tags
    template, filled_image_paths = fill_image_fields(template, definitions)

    image_paths.extend(filled_image_paths)

    # any template field visible in the template, but not found in the data; for example, if
    # the template has a {{ rank }} field (or more), but no 'rank' column in the data
    missing_fields_in_data = []

    # find any remaining template fields so we can warn that they were not filled
    remaining_fields = get_template_fields(template)

    if len(remaining_fields) > 0:
        # leftover fields were found
        for field in remaining_fields:
            if len(field.name) > 0:
                if field.name == TemplateFields.CARDS_TOTAL:
                    # this is a special case: this field will not be filled until every card
                    # has been generated- so this field should not be treated as if missing;
                    # instead, simply ignore it at this point
                    pass
                else:
                    # the field was not found in the card data, so make a warning about it
                    missing_fields_in_data.append(field.name)

    return template, image_paths, (set(missing_fields_in_template), set(missing_fields_in_data))


def template_from_path(template_path: str, relative_to_path: str=None) -> (str, bool, str):
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


def fill_card(
        template: str,
        template_path: str,
        row: dict,
        row_index: int,
        card_index: int,
        card_copy_index: int,
        definitions: dict) -> (str, list, list):
    """ Return the contents of a card using the specified template. """

    # attempt to fill all fields discovered in the template using the data for this card
    template, discovered_image_paths, missing_fields = fill_template(
        template, template_path, row, definitions)

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

    # card data might contain these three fields, but they would not have been rendered
    # during fill_template(), so make sure to remove them from the missing list if necessary
    except_fields = {TemplateFields.CARD_INDEX,
                     TemplateFields.CARD_ROW_INDEX,
                     TemplateFields.CARD_COPY_INDEX,
                     TemplateFields.CARD_TEMPLATE_PATH}

    missing_fields = (missing_fields[0], missing_fields[1] - except_fields)

    return template, discovered_image_paths, missing_fields


def fill_card_front(
        template: str,
        template_path: str,
        row: dict,
        row_index: int,
        card_index: int,
        card_copy_index: int,
        definitions: dict) -> (str, list, list):
    """ Return the contents of the front of a card using the specified template. """

    return fill_card(template, template_path, get_front_data(row),
                     row_index, card_index, card_copy_index, definitions)


def fill_card_back(
        template: str,
        template_path: str,
        row: dict,
        row_index: int,
        card_index: int,
        card_copy_index: int,
        definitions: dict) -> (str, list, list):
    """ Return the contents of the back of a card using the specified template. """

    return fill_card(template, template_path, get_back_data(row),
                     row_index, card_index, card_copy_index, definitions)


def get_front_data(row: dict) -> dict:
    """ Return a dict containing only fields fit for the front of a card. """

    return {column: value for column, value in row.items()
            if not is_special_column(column) and not is_back_column(column)}


def get_back_data(row: dict) -> dict:
    """ Return a dict containing only fields fit for the back of a card. """

    return {column[:-len(ColumnDescriptors.BACK_ONLY)]: value for column, value in row.items()
            if not is_special_column(column) and is_back_column(column)}


def get_definition_content(definitions: dict, definition: str) -> str:
    """ Return the content of a definition, recursively resolving any references. """

    return get_column_content(definitions, definition, definitions, default_content='')


def get_column_content(row: dict,
                       column: str,
                       definitions: dict,
                       default_content: str=None,
                       tracking_references: bool=False) -> str:
    """ Return the content of a column, recursively resolving any column/definition references. """

    # get the raw content of the column, optionally assigning a default value
    column_content = row.get(column, default_content)

    references = []

    if column_content is not None:
        # there's at least some kind of content, so begin filling column reference fields (if any)
        reference_field_names = get_template_field_names(column_content)

        if len(reference_field_names) > 0:
            for reference_field_name in reference_field_names:
                other_column = reference_field_name

                is_definition = other_column in definitions
                is_column = other_column in row

                if not is_column and not is_definition:
                    # the field is not a reference that can be resolved right now, so skip it
                    # (it might be an image reference)
                    continue

                # recursively get the content of the referenced column to ensure any further
                # references are determined and filled prior to filling the originating reference

                if is_column:
                    # prioritize the column column reference by resolving it first,
                    # even if it could also be a definition instead (warn about it later)
                    other_column_content = get_column_content(
                        row, other_column, definitions, default_content)
                elif is_definition:
                    # resolve the definition reference
                    other_column_content = get_definition_content(
                        definitions, definition=other_column)

                # and ultimately fill any occurences
                column_content, occurences = fill_template_fields(
                    field_name=other_column,
                    field_value=other_column_content,
                    in_template=column_content,
                    counting_occurences=True)

                if occurences > 0 and tracking_references:
                    references.append(other_column)

                if occurences > 0 and (is_definition and is_column and row is not definitions):
                    # the reference appears multiple places
                    warn_ambiguous_reference(other_column, other_column_content)

    return (column_content, references) if tracking_references else column_content


def get_sized_card(card: str, size_class: str, content: str) -> str:
    """ Populate and return a card in a given size with the specified content. """

    card = fill_template_fields(TemplateFields.CARD_SIZE, size_class, in_template=card)
    card = fill_template_fields(TemplateFields.CARD_CONTENT, content, in_template=card)

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
