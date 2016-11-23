# coding=utf-8

"""
This module provides functions for working with templates and rendering them.
"""

import os
import re
import datetime


from typing import List

from cards.templatefield import TemplateField, fields

from cards.column import (
    Row, get_column_contentd, get_definition_content, get_definition_contentd
)

from cards.resource import get_resource_path, is_resource, is_image, supported_image_types

from cards.util import first, dequote, get_line_number, get_padded_string
from cards.warning import WarningDisplay, WarningContext

from cards.constants import TemplateFields, TemplateFieldDescriptors, DateField

from cards.version import __version__


class Template:  # pylint: disable=too-few-public-methods
    """ Represents a template. """

    def __init__(self, content: str, path: str=None):
        self.content = content
        self.path = path

    def __iter__(self):
        return fields(self.content)

    def __str__(self):
        truncated_content = (('\'' + self.content[:50] + '\'…')
                             if len(self.content) > 50
                             else self.content)

        truncated_path = (('…\'' + self.path[-25:] + '\'')
                          if self.path is not None and len(self.path) > 25
                          else self.path)

        return ('{0} ({1})'.format(truncated_content, truncated_path)
                if truncated_path is not None
                else truncated_content)

    @staticmethod
    def from_path(path: str, relative_to_path: str=None) -> ('Template', bool):
        content, not_found, absolute_path = template_from_path(
            path, relative_to_path)

        return Template(content, absolute_path), not_found


class TemplateRenderData:  # pylint: disable=too-few-public-methods
    """ Provides additional data about the rendering of a template. """

    def __init__(self,
                 image_paths: set=None,
                 unknown_fields: set=None,
                 unused_fields: set=None,
                 referenced_definitions: set=None):
        self.image_paths = image_paths
        self.unknown_fields = unknown_fields
        self.unused_fields = unused_fields
        self.referenced_definitions = referenced_definitions


def strip_styles(template: Template) -> str:
    """ Strip and return any embedded <style></style> content from a template. """

    pattern = r'<style.*?>(.+?)</style>'
    stripped_styles = ''

    search = re.compile(pattern, re.DOTALL)

    # find all style matches and extract embedded styles
    for style_match in re.finditer(pattern, template.content, re.DOTALL):
        # note that we strip the entire style- not the inner content
        style = style_match.group(0).strip()
        # separating each style block for good measure
        stripped_styles = stripped_styles + '\n' + style if len(stripped_styles) > 0 else style

    # finally remove all style matches
    # note that this removes the <style></style> tags too
    template.content = re.sub(search, '', template.content).strip()

    # make sure we keep it clean- no unnecessary newlines or excess whitespace
    stripped_styles = stripped_styles.strip()

    template_field_names = list((field.name for field in fields(stripped_styles)))

    if len(template_field_names) > 0:
        context = template.path

        # if there's any fields in the styles, display a warning about it
        WarningDisplay.fields_in_styles(
            WarningContext(context), template_field_names)

    return stripped_styles


def template_from_path(template_path: str,
                       relative_to_path: str=None) -> (str, bool, str):
    """ Return the template contents of the given path, if possible.

        If specified, path is made relative to another path.
    """

    template_content = None
    template_not_found = False

    if template_path is not None and len(template_path) > 0:
        if not os.path.isabs(template_path):
            # the path is not an absolute path; assume that it's located relative to the data
            if relative_to_path is not None:
                template_path = os.path.join(
                    os.path.dirname(relative_to_path),
                    template_path)

        try:
            with open(template_path) as template_file:
                template_content = template_file.read().strip()
        except IOError:
            template_not_found = True
    else:
        template_not_found = True

    return template_content, template_not_found, template_path


def image_size(image_path: str, from_context: str) -> (int, int):
    """ Return the size specified by the context of an image field. """

    explicit_width = None

    # get each size specification separately (removing blanks)
    size_components = list(filter(None, from_context.split('x')))

    if len(size_components) > 0:
        width_specification = size_components[0]

        try:
            explicit_width = int(width_specification)
        except ValueError:
            explicit_width = None

            WarningDisplay.unknown_size_specification(
                WarningContext(image_path), from_context)
        else:
            if explicit_width < 0:
                WarningDisplay.invalid_width_specification(
                    WarningContext(image_path), explicit_width)

                explicit_width = None

    if len(size_components) > 1:
        height_specification = size_components[1]

        try:
            explicit_height = int(height_specification)
        except ValueError:
            explicit_height = None

            WarningDisplay.unknown_size_specification(
                WarningContext(image_path), from_context)
        else:
            if explicit_height < 0:
                WarningDisplay.invalid_height_specification(
                    WarningContext(image_path), explicit_height)

                explicit_height = None
    else:
        # default to a squared size using the width specification
        explicit_height = explicit_width

    return explicit_width, explicit_height


def image(field: TemplateField) -> (str, str):
    """ Transform an image field into an image tag, unless field specifies otherwise.  """

    image_path = field.name

    no_transform = False

    width = None
    height = None

    if field.context is not None:
        if field.context == TemplateFieldDescriptors.COPY_ONLY:
            no_transform = True
        else:
            width, height = image_size(image_path, field.context)

    if not is_image(image_path):
        # the file is not an image; or something has gone wrong
        if no_transform or (width is not None or height is not None):
            # if either of these attributes exist, then it likely was supposed to be an image
            # but we could not resolve it properly- so warn about it
            WarningDisplay.unresolved_image_reference_error(
                image_reference=image_path,
                closest_resolution_value=field.name)

        return None, None  # no image, no tag

    resource_path = image_path

    if is_resource(image_path):
        image_name = os.path.basename(image_path)
        # transform the path so that it is relative within the output directory,
        # this way we can keep every resource contained
        resource_path = get_resource_path(image_name)

    if no_transform:
        return image_path, resource_path  # image path in resources, no tag

    return image_path, get_image_tag(resource_path, width, height)


def get_image_tag(image_path: str,
                  width: int=None,
                  height: int=None) -> str:
    """ Return a HTML-compliant image tag using the specified image path. """

    if width is not None and height is not None:
        # make a tag with the image at the specified dimensions
        return '<img src="{0}" width="{1}" height="{2}">'.format(image_path, width, height)

    # make a tag with the image at its intrinsic size
    return '<img src="{0}">'.format(image_path)


def fill_image_fields(template: Template) -> List[str]:
    """ Populate all image fields in the template.

        An image field provides a way of transforming an image path into a HTML-compliant image tag.

        An image field should look like this: '{{ my-image.png 16x16 }}'.
    """

    image_paths = []

    supported_images_pattern = '\\' + '|\\'.join(supported_image_types())

    def next_image_field() -> TemplateField:
        """ Return the next probable image field. """

        return first(fields(template.content, with_name_like=supported_images_pattern))

    field = next_image_field()

    while field is not None:
        # at this point we don't know that it's actually an image field - we only know that it's
        # a template field, so we just attempt to create an <img> tag from the field.
        # if it turns out to not be an image, we just ignore the field entirely and proceed
        image_path, image_tag = image(field)

        if image_path is not None:
            # we at least discovered that the field was pointing to an image,
            # so in the end it needs to be copied
            image_paths.append(image_path)

        if image_tag is not None:
            # the field was transformed to either an <img> tag, or just the path (for copying only)
            fill(field, image_tag, template)

        field = next_image_field()

    return image_paths


def fill(field: TemplateField,
         field_value: str,
         template: Template,
         indenting: bool=False) -> None:
    """ Populate a single template field in the template. """

    start_index = field.indices.start
    end_index = field.indices.stop

    if ((start_index < 0 or start_index > len(template.content)) or
            (end_index < 0 or end_index > len(template.content))):
        raise ValueError('Template field \'{0}\' out of range ({1}-{2}).'
                         .format(field.inner_content, start_index, end_index))

    if indenting:
        field_value = get_padded_string(
            field_value, template.content, field.indices.start)

    template.content = template.content[:start_index] + field_value + template.content[end_index:]


def fill_each(field_inner_content: str,
              field_value: str,
              template: Template,
              indenting: bool=False) -> int:
    """ Populate all matching template fields in the template.

        Matches are determined by comparing the inner content of each field with
        the provided content.
    """

    # make sure that we have a sane value
    field_value = field_value if field_value is not None else ''

    # template fields are always represented by wrapping {{ }}'s,
    # however, both {{my_field}} and {{ my_field }} should be valid;
    # i.e. any leading or trailing whitespace should simply be ignored
    field_search = r'{{\s*' + field_inner_content + r'\s*}}'

    # find any occurences of the field, using a case-insensitive
    # comparison, to ensure that e.g. {{name}} is populated with the
    # value from column "Name", even though the casing might differ
    search = re.compile(field_search, re.IGNORECASE)

    if indenting:
        match = search.search(template.content)

        if match is not None:
            # we only need the start index
            start_index = match.span()[0]

            field_value = get_padded_string(field_value, template.content, start_index)

    # finally replace any found occurences of the template field with its value
    template.content, occurences = search.subn(field_value, template.content)

    return occurences


def fill_date_fields(template: Template,
                     date: datetime=DateField.TODAY) -> None:
    """ Populate all date fields in the template.

        A 'date' field provides an easy way of putting the current date into a template.

        A date field uses built-in Python date formats, and should look like this:

            '{{ date }}'              - using default formatting
            '{{ date '%d, %b %Y' }}'  - using custom formatting

        See all supported format identifiers here http://strftime.org
    """

    def next_date_field():
        """ Return the next probable date field. """

        return first(fields(template.content, with_name_like='date'))

    field = next_date_field()

    while field is not None:
        # default date format: 07 Oct, 2016
        date_format = '%B %-d, %Y'

        if field.context is not None:
            # a date field can have a custom format
            custom_date_format = dequote(field.context).strip()

            if len(custom_date_format) > 0:
                # if found, we'll use that and let date.strftime handle it
                date_format = custom_date_format

        formatted_date = date.strftime(date_format)

        # populate the include field with the content; or blank if unresolved
        fill(field, formatted_date, template)

        field = next_date_field()


def fill_include_fields(template: Template) -> None:
    """ Populate all include fields in the template.

        An 'include' field provides a way of putting re-usable template content into a
        separate file, and including it in place of the field.

        An include field should look like this:

            '{{ include 'path/to/file.html' }}'
    """

    original_template_content = template.content

    def next_include_field():
        """ Return the next probable include/inline field. """

        return first(fields(template.content, with_name_like='include|inline'))

    field = next_include_field()

    while field is not None:
        is_include_command = field.name == TemplateFields.INCLUDE
        is_inline_command = field.name == TemplateFields.INLINE

        # default to blank
        include_content = ''
        include_path = None

        if field.context is not None:
            # the field should contain a path
            include_path = dequote(field.context).strip()

        if include_path is not None and len(include_path) > 0:
            if not os.path.isabs(include_path):
                # it's not an absolute path, so we should make it a relative path
                if template.path is not None:
                    # make the path relative to the path of the containing template
                    include_path = os.path.join(
                        os.path.dirname(template.path), include_path)

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
                    WarningContext(os.path.basename(template.path)), include_path)

                include_content = '<strong>&lt;included file not found&gt;</strong>'
        else:
            WarningDisplay.include_should_specify_file(
                WarningContext('{0}:{1}'.format(
                    os.path.basename(template.path),
                    # todo: the line number could potentially be incorrect, as we might not be going
                    # through the original template anymore- the lineno can only serve as a hint
                    get_line_number(field.indices.start, original_template_content))),
                is_inline=is_inline_command)

        # populate the include field with the content; or blank if unresolved
        fill(field, include_content, template, indenting=is_include_command)

        field = next_include_field()


def fill_partial_definition(definition: str,
                            value: str,
                            template: Template) -> int:
    """ Populate any partial definitions in a template.

        A partial definition is a definition that is included in another template field;
        e.g. {{ my_column my_partial_definition }}, or {{ my_partial_definition 16x16 }}.

        Populating a partial definition is essentially just replacing the definition key with
        its resolved value, but otherwise leaving the field as it was.

        For example, {{ my_column my_partial_definition }} would become {{ my_column some_value }}.
    """

    partial_definition_occurences = 0

    # only match as a partial definition if it is isolated by whitespace (or {{}}'s),
    # otherwise it might just be part of something else;
    # for example, the definition 'monster' should not match {{ path/to/monster.svg 16x16 }}
    # note that this pattern actually has a limitation that it won't match more than one hit
    # in a single field, so e.g. {{ partial partial }} would only match the first
    pattern = r'(?:^|\s|{{)(' + definition + r')(?:$|\s|}})'

    def next_partial_definition_field():
        """ Return the next field likely to contain a partial definition. """

        return first(fields(
            template.content,
            with_name_like=pattern,
            with_context_like=pattern,
            strictly_matching=False))  # match either name or context, or both

    partial_definition_field = next_partial_definition_field()

    while partial_definition_field is not None:
        name = partial_definition_field.name
        context = partial_definition_field.context

        if name is not None:
            name = re.sub(pattern, value, name)

        if context is not None:
            context = re.sub(pattern, value, context)

        # essentially replace the field with a new and transformed field where the
        # partial definition is resolved and populated
        fill(partial_definition_field, str(TemplateField(name, context)), template)

        partial_definition_occurences += 1

        # keep searching for more matches
        partial_definition_field = next_partial_definition_field()

    return partial_definition_occurences


def fill_definitions(definitions: dict,
                     template: Template) -> set:
    """ Populate all definition fields in the template. """

    referenced_definitions = []

    resolved_definitions = {}

    # first resolve definitions and populate any definite definition fields (e.g. not partials)
    for definition in definitions:
        # note that this is an un-optimized solution; it loops through each definition, even if
        # that particular definition is not even used- AND it loops again after this one

        # recursively resolve the content of the definition
        resolved_definition_value, resolution_data = get_definition_contentd(
            definition, in_definitions=definitions,
            content_resolver=resolve_column_content, field_resolver=resolve_column_field)

        # we can save this for the partial pass coming up, to avoid having to resolve again
        resolved_definitions[definition] = resolved_definition_value

        # fill any definite occurences of the definition (e.g. '{{ my_definition }}')
        definite_occurences = fill_each(definition, resolved_definition_value, template)

        if definite_occurences > 0:
            # the definition was used somewhere, so flag it as referenced
            referenced_definitions.append(definition)
            # and also flag any definitions referenced during the resolution of the definition
            referenced_definitions.extend(
                list(resolution_data.definition_references))

    # then populate any partial definitions using the previously resolved definitions
    for definition in definitions:
        # we need this second loop, because a later definition might resolve to contain a partial
        # definition that the loop already went through; this second loop solves that problem
        partial_occurences = fill_partial_definition(
            definition, resolved_definitions[definition], template)

        if partial_occurences > 0:
            # the definition was used somewhere, so flag it as referenced
            referenced_definitions.append(definition)

    return set(referenced_definitions)


def resolve_column_content(content, in_data_path) -> str:
    """ Return content where any include, empty and date fields have been resolved.

        This resolver function is run when starting the resolution of the content of a column.
    """

    template = Template(content, path=in_data_path)

    # fill any include fields before doing anything else
    fill_include_fields(template)
    # clear out any empty fields
    fill_empty_fields(template)
    # then fill any date fields
    fill_date_fields(template)

    return template.content


def resolve_column_field(field_name, field_value, in_content) -> (str, int):
    """ Return content where any occurence of the provided field has been resolved.

        This resolver function is run when the resolution of the content of a column
        discovers a field.
    """

    template = Template(in_content)

    occurences = fill_each(field_name, field_value, template)

    return template.content, occurences


def fill_index(index: str,
               style: str,
               pages: str,
               header: str,
               pages_total: int,
               cards_total: int,
               definitions: dict) -> (str, TemplateRenderData):
    """ Populate and return index template with all styles and pages. """

    template = Template(index)

    if len(style) == 0:
        style = '<style type="text/css">\n  /* no embedded styles */\n</style>'

    fill_each('_styles', style, template, indenting=True)

    if len(header) > 0:
        header_tag = '<div class="ui-header">\n  {{ _header }}\n</div>'

        fill_each('_header', header_tag, template, indenting=True)

    fill_each('_header', header, template, indenting=True)

    fill_each(TemplateFields.PAGES, pages, template, indenting=True)
    fill_each(TemplateFields.CARDS_TOTAL, str(cards_total), template)
    fill_each(TemplateFields.PAGES_TOTAL, str(pages_total), template)
    fill_each(TemplateFields.PROGRAM_VERSION, __version__, template)

    # note that most of these fields could potentially be filled already when first getting the
    # page template; however, we instead do it as the very last thing to allow cards
    # using these fields (even if that might only be on rare occasions)
    title = get_definition_content(
        definition=TemplateFields.TITLE, in_definitions=definitions,
        content_resolver=resolve_column_content, field_resolver=resolve_column_field)

    if title is None:
        title = ''

    index_title = title if len(title) > 0 else 'cards.py [Untitled]'

    description = get_definition_content(
        definition=TemplateFields.DESCRIPTION, in_definitions=definitions,
        content_resolver=resolve_column_content, field_resolver=resolve_column_field)

    description = description if description is not None else ''

    copyright_notice = get_definition_content(
        definition=TemplateFields.COPYRIGHT, in_definitions=definitions,
        content_resolver=resolve_column_content, field_resolver=resolve_column_field)

    copyright_notice = copyright_notice if copyright_notice is not None else ''

    author = get_definition_content(
        definition=TemplateFields.AUTHOR, in_definitions=definitions,
        content_resolver=resolve_column_content, field_resolver=resolve_column_field)

    author = author if author is not None else ''

    version_identifier = get_definition_content(
        definition=TemplateFields.VERSION, in_definitions=definitions,
        content_resolver=resolve_column_content, field_resolver=resolve_column_field)

    version_identifier = version_identifier if version_identifier is not None else ''

    fill_each('__title', index_title, template)
    fill_each(TemplateFields.TITLE, title, template)
    fill_each(TemplateFields.DESCRIPTION, description, template)
    fill_each(TemplateFields.COPYRIGHT, copyright_notice, template)
    fill_each(TemplateFields.AUTHOR, author, template)
    fill_each(TemplateFields.VERSION, version_identifier, template)

    fill_date_fields(template)

    referenced_definitions = fill_definitions(definitions, template)

    # fill any image fields that might have appeared by populating the metadata fields
    filled_image_paths = fill_image_fields(template)

    return template.content, TemplateRenderData(
        image_paths=set(filled_image_paths),
        referenced_definitions=referenced_definitions)


def fill_template(template: Template,
                  row: Row,
                  definitions: dict) -> TemplateRenderData:
    """ Populate all template fields in a template.

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
    fill_include_fields(template)

    # clear out any empty fields
    fill_empty_fields(template)

    # any field that is in the data, but not found in the template; for example, if there's
    # a 'rank' column in the data, but no '{{ rank }}' field in the template
    unused_columns = []

    column_references_in_data = []
    discovered_definition_refs = []

    # go through each data field for this card (row)
    for column in row.data:
        # fetch the content for the field
        field_content, resolution_data = get_column_contentd(
            column, row, definitions,
            content_resolver=resolve_column_content,
            field_resolver=resolve_column_field)

        # fill content into the provided template
        occurences = fill_each(column, field_content, template)

        if occurences is 0:
            # this field was not found anywhere in the specified template
            unused_columns.append(column)
        else:
            # this field was found and populated in the template, so save any column references
            # made in the column content, so we can later compare that to the list of missing fields
            column_references_in_data.extend(list(resolution_data.column_references))
            discovered_definition_refs.extend(list(resolution_data.definition_references))

    # fill any definition fields
    discovered_definition_refs.extend(
        fill_definitions(definitions, template))

    fill_date_fields(template)

    # replace any image fields with HTML compliant <img> tags
    filled_image_paths = fill_image_fields(template)

    # any template field visible in the template, but not found in the data; for example, if
    # the template has a {{ rank }} field (or more), but no 'rank' column in the data
    unknown_fields = []

    # find any remaining template fields so we can warn that they were not filled
    for field in template:
        if (field.inner_content == TemplateFields.CARDS_TOTAL or
                field.inner_content == TemplateFields.CARDS_TOTAL_IN_CONTEXT):
            # this is a special case: these fields will not be filled until every card
            # has been generated- so each field should not be treated as if missing;
            # instead, simply ignore them at this point
            pass
        else:
            # the field was not found in the card data, so make a warning about it
            unknown_fields.append(field.inner_content)

    # make sure we only have one of each reference
    column_references = set(column_references_in_data)

    # remove any "missing fields" that are actually referenced in column content-
    # they may not be in the template, but they are not unused/missing, so don't warn about it
    unused_columns = list(set(unused_columns) - column_references)

    return TemplateRenderData(
        image_paths=set(filled_image_paths),
        unknown_fields=set(unknown_fields),
        unused_fields=set(unused_columns),
        referenced_definitions=set(discovered_definition_refs))


def fill_empty_fields(template: Template) -> None:
    """ Populate all empty fields in a template (with nothing). """

    fill_each('', '', template)


def fill_card(template: Template,
              row: Row,
              card_index: int,
              card_copy_index: int,
              definitions: dict) -> (str, TemplateRenderData):
    """ Return the contents of a card using the specified template. """

    # attempt to fill all fields discovered in the template using the data for this card
    render_data = fill_template(template, row, definitions)

    # fill all row index fields (usually used for error templates)
    fill_each(TemplateFields.CARD_ROW_INDEX, str(row.row_index), template)

    # fill all template path fields (usually used for error templates)
    fill_each(TemplateFields.CARD_TEMPLATE_PATH, template.path, template)

    # fill all card index fields
    fill_each(TemplateFields.CARD_INDEX, str(card_index), template)

    fill_each(TemplateFields.CARD_COPY_INDEX, str(card_copy_index), template)

    # card data might contain the following fields, but they would not have been rendered
    # during fill_template(), so make sure to remove them from the missing list if necessary
    except_fields = {TemplateFields.CARD_INDEX,
                     TemplateFields.CARD_ROW_INDEX,
                     TemplateFields.CARD_COPY_INDEX,
                     TemplateFields.CARD_TEMPLATE_PATH}

    # update the set of unknown fields to not include the exceptions listed above
    render_data.unknown_fields = render_data.unknown_fields - except_fields

    return template.content, render_data
