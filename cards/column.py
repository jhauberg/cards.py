# coding=utf-8

"""
This module provides functions for working with and resolving data from a CSV file.
"""

import os
import csv
import itertools

from cards.markdown import markdown

from cards.templatefield import TemplateField, get_template_fields

from cards.util import lower_first_row
from cards.warning import WarningDisplay, WarningContext
from cards.constants import Columns, ColumnDescriptors


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

    def __init__(self,
                 column_references: set,
                 definition_references: set):
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


def is_row_reference(field: TemplateField) -> bool:
    """ Determine whether a field contains a row reference. """

    return (field.context is not None and field.context.startswith('#')
            if field is not None
            else False)


def get_row_reference(field: TemplateField,
                      in_reference_row: dict,
                      in_data_path: str) -> (str, dict):
    """ Return the column and row of data that a template field references.

        If a field like 'title #6' is passed, then return 'title' and row number 6.

        If it is not a reference, return the row passed.
    """

    # set default field name and row to whatever is passed
    reference_column = None
    reference_row = in_reference_row

    if in_data_path is not None and len(in_data_path) > 0:
        # a data path has been supplied, so we can attempt determining whether this
        # field is a reference to a column in another row

        if is_row_reference(field):
            # it might be, because there's multiple components in the field name
            # we've determined that this is probably a reference to another row
            # so get the row number
            row_number = field.context[1:]

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
                        reference_column = field.name
                        # read data appropriately
                        data = csv.DictReader(lower_first_row(data_file))
                        # then read rows until reaching the target row_number
                        reference_row = next(itertools.islice(data, row_number, None))

    return reference_column, reference_row


def get_column_content(column: str,
                       in_row: dict,
                       definitions: dict,
                       in_data_path: str=None,
                       default_content: str=None,
                       content_resolver=None,
                       field_resolver=None,
                       tracking_references: bool=False) -> str:
    """ Return the content of a column, recursively resolving any column/definition references. """

    # get the raw content of the column, optionally assigning a default value
    column_content = in_row.get(column, default_content)

    column_references = []
    definition_references = []

    if column_content is not None and len(column_content) > 0:
        # strip excess whitespace
        column_content = column_content.strip()

        if content_resolver is not None:
            column_content = content_resolver(column_content, in_data_path)
        else:
            print('No resolver has been specified (column={0})'.format(column))

        is_resolving_definition = in_row == definitions

        reference_fields = get_template_fields(column_content)

        for reference_field in reference_fields:
            # determine whether this field is a row reference
            reference_column, reference_row = get_row_reference(
                reference_field, in_reference_row=in_row, in_data_path=in_data_path)

            if reference_column is None:
                # it was not a row reference
                reference_column = reference_field.inner_content

            # determine if the field occurs as a definition
            is_definition = reference_column in definitions
            # determine if the field occurs as a column in the current row- note that if
            # the current row is actually the definitions, then it actually *is* a column,
            # but it should not be treated as such
            is_column = reference_column in reference_row and not is_resolving_definition

            if not is_column and not is_definition:
                # the field is not a reference that can be resolved right now, so skip it
                # (it might be an image reference)
                continue

            # recursively get the content of the referenced column to ensure any further
            # references are determined and filled prior to filling the originating reference

            # this field refers to the column in the same row that is already being resolved;
            # i.e. an infinite cycle (if it was another row it might not be infinite)
            is_infinite_column_ref = reference_column == column and reference_row is in_row
            # this definition field refers to itself; also leading to an infinite cycle
            is_infinite_definition_ref = (is_infinite_column_ref
                                          and is_definition
                                          and not is_column)

            # only resolve further if it would not lead to an infinite cycle
            use_column = is_column and not is_infinite_column_ref
            # however, the field might ambiguously refer to a definition too,
            # so if this could be resolved, use the definition value instead
            use_definition = (is_definition
                              and not use_column
                              and not is_infinite_definition_ref)

            if not use_column and not use_definition:
                # could not resolve this field at all
                print('could not resolve: ' + reference_column)
                continue

            if use_column:
                # prioritize the column reference by resolving it first,
                # even if it could also be a definition instead (but warn about that later)
                column_reference_content, resolution_data = get_column_content(
                    reference_column, reference_row, definitions, in_data_path, default_content,
                    content_resolver, field_resolver,
                    tracking_references=True)
            elif use_definition:
                # resolve the definition reference, keeping track of any discovered references
                column_reference_content, resolution_data = get_definition_content(
                    definition=reference_column, in_definitions=definitions,
                    content_resolver=content_resolver, field_resolver=field_resolver,
                    tracking_references=True)

            column_references.extend(list(resolution_data.column_references))
            definition_references.extend(list(resolution_data.definition_references))

            occurences = 0

            if field_resolver is not None:
                column_content, occurences = field_resolver(
                    reference_field.inner_content, column_reference_content, column_content)
            else:
                print('No field resolver has been specified (column={0})'.format(column))

            if occurences > 0:
                if tracking_references:
                    if use_column:
                        column_references.append(reference_column)
                    elif use_definition:
                        definition_references.append(reference_column)

                if is_definition and is_column and not is_resolving_definition:
                    # the reference appears multiple places
                    context = os.path.basename(in_data_path)

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

        # transform content to html using any applied markdown formatting
        column_content = markdown(column_content)

    resolution_data = ColumnResolutionData(
        set(column_references), set(definition_references))

    return ((column_content, resolution_data) if tracking_references
            else column_content)


def get_definition_content(definition: str,
                           in_definitions: dict,
                           content_resolver=None,
                           field_resolver=None,
                           tracking_references: bool=False) -> str:
    """ Return the content of a definition, recursively resolving any references. """

    definition_content, resolution_data = get_column_content(
        column=definition, in_row=in_definitions, definitions=in_definitions,
        content_resolver=content_resolver, field_resolver=field_resolver,
        tracking_references=True)

    return ((definition_content, resolution_data) if tracking_references
            else definition_content)


def get_front_data(row: dict) -> dict:
    """ Return a dict containing only items fit for the front of a card. """

    return {column: value for column, value in row.items()
            if not is_excluded_column(column)
            and not is_special_column(column)
            and not is_back_column(column)}


def get_back_data(row: dict) -> dict:
    """ Return a dict containing only items fit for the back of a card. """

    return {column[:-len(ColumnDescriptors.BACK_ONLY)]: value for column, value in row.items()
            if not is_excluded_column(column)
            and not is_special_column(column)
            and is_back_column(column)}


def is_excluded_column(column: str) -> bool:
    """ Determine whether a column should be excluded. """

    return column.startswith('(') and column.endswith(')') if column is not None else False


def is_special_column(column: str) -> bool:
    """ Determine whether a column is to be treated as a special column. """

    return column.startswith('@') if column is not None else False


def is_back_column(column: str) -> bool:
    """ Determine whether a column is only intended for the back of a card. """

    return column.endswith(ColumnDescriptors.BACK_ONLY) if column is not None else False
