# coding=utf-8

import csv

from cards.column import is_special_column, is_excluded_column

from cards.util import most_common


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
    """ Return a template that is fit for the provided data. """

    analysis = {}

    for row in data:
        for column in data.fieldnames:
            if not is_excluded_column(column) and not is_special_column(column):
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
        field = '{{ ' + str(field_name) + ' }}'
        field_tag = '<div class=\"auto-template-field auto-template-{0}\">{1}</div>'

        template += field_tag.format(field_type, field)

    return template
