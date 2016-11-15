# coding=utf-8

"""
This module provides functions for working with and resolving data from a CSV file.
"""

import os
import csv
import itertools

from cards.markdown import markdown

from cards.templatefield import TemplateField, fields

from cards.util import lower_first_row
from cards.warning import WarningDisplay, WarningContext
from cards.constants import Columns, ColumnDescriptors


class Column:
    """ Represents a column in a datasource. """

    def __init__(self, name: str, content: str=None):
        self.name = name
        self.content = content

    def is_excluded(self) -> bool:
        """ Determine whether a column should be excluded. """

        return (self.name.startswith('(') and self.name.endswith(')')
                if self.name is not None
                else False)

    def is_special(self) -> bool:
        """ Determine whether a column is to be treated as a special column. """

        return (self.name.startswith('@')
                if self.name is not None
                else False)

    def is_back_only(self) -> bool:
        """ Determine whether a column is only intended for the back of a card. """

        return (self.name.endswith(ColumnDescriptors.BACK_ONLY)
                if self.name is not None
                else False)


class Row:
    """ Represents a row in a datasource. """

    def __init__(self, data: dict, data_path: str=None, row_index: int=None):
        self.data = data
        self.data_path = data_path
        self.row_index = row_index

    def _usable_columns(self) -> tuple:
        return (column for column in
                (Column(name, content) for name, content in self.data.items())
                if not column.is_excluded()
                and not column.is_special())

    def _front_data(self) -> dict:
        """ Return a dict containing only items fit for the front of a card. """

        return {column.name: column.content for column in self._usable_columns()
                if not column.is_back_only()}

    def _back_data(self) -> dict:
        """ Return a dict containing only items fit for the back of a card. """

        return {column.name[:-len(ColumnDescriptors.BACK_ONLY)]: column.content for column
                in self._usable_columns() if column.is_back_only()}

    def front_row(self) -> 'Row':
        """ Return a Row containing only data fit for the front of a card. """

        return Row(data=self._front_data(),
                   data_path=self.data_path,
                   row_index=self.row_index)

    def back_row(self) -> 'Row':
        """ Return a Row containing only data fit for the back of a card. """

        return Row(data=self._back_data(),
                   data_path=self.data_path,
                   row_index=self.row_index)


class InvalidColumnError:  # pylint: disable=too-few-public-methods
    """ Provides additional information about invalid data columns. """

    def __init__(self, column_name: str, reason: str):
        self.column_name = column_name
        self.reason = reason

    def __str__(self):
        return '\'{0}\' {1}'.format(self.column_name, self.reason)

    def __repr__(self):
        return self.__str__()


class ColumnResolutionData:  # pylint: disable=too-few-public-methods
    """ Provides additional data about the resolution of a data column. """

    def __init__(self, column_references: set=(), definition_references: set=()):
        self.column_references = column_references
        self.definition_references = definition_references


def get_invalid_columns(column_names: list) -> list:
    """ Return a list of errors for each invalid column. """

    return [InvalidColumnError(column_name, reason='contains whitespace (should be an underscore)')
            for column_name in column_names
            if ' ' in column_name]


def size_identifier_from_columns(column_names: list) -> (str, list):
    """ Parse and determine card size identifier from a list of column names. """

    size_identifier = None

    parsed_column_names = column_names

    for column_index, column_name in enumerate(column_names):
        # look for the '@template' column
        if column_name.startswith(Columns.TEMPLATE):
            # and isn't just '@template-back'
            if column_name != Columns.TEMPLATE_BACK:
                # then determine preferred card size, if any.
                # it should look like e.g. '@template:standard'
                size_index = column_name.rfind(':')

                if size_index != -1:
                    # a size identifier was found- so isolate it from the rest of the column
                    size_identifier = column_name[size_index + 1:].strip()
                    # and remove it so we have a clean column name (important for any column
                    # references to resolve properly)
                    parsed_column_names[column_index] = column_name[:size_index].strip()

                break

    return size_identifier, parsed_column_names


def get_row_reference(field: TemplateField,
                      in_reference_row: Row) -> (str, Row):
    """ Return the column and row of data that a template field references.

        If a field like 'title #6' is passed, then return 'title' and row number 6.

        If it is not a reference, return the row passed.
    """

    # set default field name and row to whatever is passed
    reference_column = None
    reference_row = in_reference_row

    if reference_row.data_path is not None and len(reference_row.data_path) > 0:
        # a data path has been supplied, so we can attempt determining whether this
        # field is a reference to a column in another row

        if field.has_row_reference():
            # it might be, because there's multiple components in the field name
            # we've determined that this is probably a reference to another row
            # so get the row number
            row_number = field.context[1:]

            try:
                row_number = int(row_number)
            except ValueError:
                row_number = None

            if row_number is not None:
                if row_number == reference_row.row_index:
                    # the row number would lead to the same row that was passed, so we clean up
                    # the field by removing the number reference, but otherwise leave the row as is
                    return field.name, reference_row

                # when looking at rows in a CSV they are not zero-based, and the first row
                # is always the headers, which makes the first row of actual data (that
                # you see) appear visually at row #2, like for example:
                #   #1 'rank,title'
                #   #2 '2,My Card'
                #   #2 '4,My Other Card'
                # however, of course, when reading from the file, the first row is
                # actually at index 0, so we have to take this into account
                line_number = row_number - 2

                # the above logic essentially makes '#0' and '#1' invalid row numbers
                if line_number >= 0:
                    # open a new instance of the current data file
                    with open(reference_row.data_path) as data_file:
                        # actual field name is only the first part
                        reference_column = field.name
                        # read data appropriately
                        data = csv.DictReader(lower_first_row(data_file))
                        # then read rows until reaching the target row_number
                        row_data = next(itertools.islice(data, line_number, None))
                        # however, we don't want to provide every column found in this row;
                        # we *only* want the columns also available in the originating row
                        filtered_row_data = {column: column_content for column, column_content
                                             in row_data.items() if column in reference_row.data}
                        # create a new row with the data at the referenced row
                        reference_row = Row(filtered_row_data, reference_row.data_path, row_number)

    return reference_column, reference_row


def resolve_column(column: Column,
                   in_row: Row,
                   definitions: dict,
                   content_resolver=None,
                   field_resolver=None) -> (str, ColumnResolutionData):
    """ Return the content of a column by recursively resolving any fields within. """

    column_references = []
    definition_references = []

    is_resolving_definition = in_row.data == definitions

    resolved_column_content = column.content

    for reference_field in fields(resolved_column_content):
        # determine whether this field is a row reference
        reference_column, reference_row = get_row_reference(
            reference_field, in_reference_row=in_row)

        if reference_column is None:
            # it was not a row reference
            reference_column = reference_field.inner_content

        # determine if the field occurs as a definition
        is_definition = reference_column in definitions
        # determine if the field occurs as a column in the current row- note that if
        # the current row is actually the definitions, then it actually *is* a column,
        # but it should not be treated as such
        is_column = reference_column in reference_row.data and not is_resolving_definition

        if not is_column and not is_definition:
            # the field is not a reference that can be resolved right now, so skip it
            # (it might be an image reference, an include field or similar)
            continue

        context = (os.path.basename(reference_row.data_path)
                   if reference_row.data_path is not None
                   else ('definitions' if is_resolving_definition else ''))

        # this field refers to the column in the same row that is already being resolved;
        # i.e. an infinite cycle (if it was another row it might not be infinite)
        is_infinite_column_ref = reference_column == column.name and reference_row is in_row
        # this definition field refers to itself; also leading to an infinite cycle
        is_infinite_definition_ref = (is_infinite_column_ref
                                      and is_definition
                                      and not is_column)

        if is_infinite_definition_ref:
            WarningDisplay.unresolved_infinite_definition_reference(
                WarningContext(context, row_index=reference_row.row_index, column=column.name),
                reference_field.inner_content)

            continue

        if is_infinite_column_ref:
            WarningDisplay.unresolved_infinite_column_reference(
                WarningContext(context, row_index=reference_row.row_index, column=column.name),
                reference_field.inner_content)

            continue

        # only resolve further if it would not lead to an infinite cycle
        use_column = is_column and not is_infinite_column_ref
        # however, the field might ambiguously refer to a definition too,
        # so if this could be resolved, use the definition value instead
        use_definition = (is_definition
                          and not use_column
                          and not is_infinite_definition_ref)

        if not use_column and not use_definition:
            # could not resolve this field at all
            WarningDisplay.unresolved_reference(
                WarningContext(context, row_index=reference_row.row_index, column=column.name),
                reference_field.inner_content)

            continue

        if use_column:
            # prioritize the column reference by resolving it first,
            # even if it could also be a definition instead (but warn about that later)
            column_reference_content, resolution_data = get_column_contentd(
                reference_column, reference_row, definitions,
                content_resolver, field_resolver)
        elif use_definition:
            # resolve the definition reference, keeping track of any discovered references
            column_reference_content, resolution_data = get_definition_contentd(
                definition=reference_column, in_definitions=definitions,
                content_resolver=content_resolver, field_resolver=field_resolver)

        column_references.extend(list(resolution_data.column_references))
        definition_references.extend(list(resolution_data.definition_references))

        occurences = 0

        if field_resolver is not None:
            resolved_column_content, occurences = field_resolver(
                reference_field.inner_content, column_reference_content, resolved_column_content)

        if occurences > 0:
            if use_column:
                column_references.append(reference_column)
            elif use_definition:
                definition_references.append(reference_column)

            if is_definition and is_column and not is_resolving_definition:
                # the reference could point to both a column and a definition
                if use_column:
                    # the column data was preferred over the definition data
                    WarningDisplay.ambiguous_reference_used_column(
                        WarningContext(context), reference_column, column_reference_content)
                elif use_definition:
                    # the definition data was preferred over the column data;
                    # this is likely because the column reference was an infinite reference
                    # don't inform about that detail, but do warn that the definition was used
                    WarningDisplay.ambiguous_reference_used_definition(
                        WarningContext(context), reference_column, column_reference_content)

    resolution_data = ColumnResolutionData(
        set(column_references), set(definition_references))

    return resolved_column_content, resolution_data


def get_column_contentd(column: str,
                        in_row: Row,
                        definitions: dict,
                        content_resolver=None,
                        field_resolver=None) -> (str, ColumnResolutionData):
    """ Return the content of a column, recursively resolving any column/definition references. """

    # get the raw content of the column, optionally assigning a default value
    column_content = in_row.data.get(column, None)

    if column_content is None:
        # return early with default content
        return column_content, ColumnResolutionData()

    # strip excess whitespace
    column_content = column_content.strip()

    if len(column_content) == 0:
        # return early with default content
        return column_content, ColumnResolutionData()

    if content_resolver is not None:
        # the content resolver typically fills any include, date or empty fields
        column_content = content_resolver(column_content, in_row.data_path)

    resolved_column_content, resolution_data = resolve_column(
        Column(column, column_content), in_row, definitions, content_resolver, field_resolver)

    # transform content to html using any applied markdown formatting
    resolved_column_content = markdown(resolved_column_content)

    return resolved_column_content, resolution_data


def get_column_content(column: str,
                       in_row: Row,
                       definitions: dict,
                       content_resolver=None,
                       field_resolver=None) -> str:
    """ Return the content of a column, recursively resolving any column/definition references. """

    return get_column_contentd(
        column, in_row, definitions, content_resolver, field_resolver)[0]


def get_definition_contentd(definition: str,
                            in_definitions: dict,
                            content_resolver=None,
                            field_resolver=None) -> (str, ColumnResolutionData):
    """ Return the content of a definition, recursively resolving any references. """

    definition_content, resolution_data = get_column_contentd(
        column=definition, in_row=Row(data=in_definitions), definitions=in_definitions,
        content_resolver=content_resolver, field_resolver=field_resolver)

    return definition_content, resolution_data


def get_definition_content(definition: str,
                           in_definitions: dict,
                           content_resolver=None,
                           field_resolver=None) -> str:
    """ Return the content of a definition, recursively resolving any references. """

    return get_definition_contentd(
        definition, in_definitions, content_resolver, field_resolver)[0]
