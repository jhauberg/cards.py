# coding=utf-8

import re

from typing import List


class TemplateField:  # pylint: disable=too-few-public-methods
    """ Represents a field in a template. """

    def __init__(self,
                 inner_content: str,
                 name: str,
                 context: str,
                 start_index: int,
                 end_index: int):
        self.inner_content = inner_content  # the inner content between the field braces
        self.name = name  # the name of the field
        self.context = context  # the context passed to the field name
        self.start_index = start_index  # the index of the first '{' wrapping brace
        self.end_index = end_index  # the index of the last '}' wrapping brace


def get_template_fields(in_template: str,
                        limit: int=None,
                        with_name_like: str=None,
                        with_context_like: str=None,
                        strictly_matching: bool=True) -> List[TemplateField]:
    """ Return a list of all template fields (e.g. '{{ a_field }}') that occur in a template. """

    pattern = r'{{\s?(([^}}\s]*)\s?(.*?))\s?}}'

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

        satisfies_name_filter = (with_name_like is None or
                                 (with_name_like is not None and field.name is not None
                                  and re.search(with_name_like, field.name) is not None))

        satisfies_context_filter = (with_context_like is None or
                                    (with_context_like is not None and field.context is not None
                                     and re.search(with_context_like, field.context) is not None))

        satisfies_filter = (satisfies_name_filter and satisfies_context_filter
                            if strictly_matching
                            else satisfies_name_filter or satisfies_context_filter)

        if satisfies_filter:
            fields.append(field)

        if limit is not None and len(fields) == limit:
            break

    return fields


def get_template_field_names(in_template: str) -> List[str]:
    """ Return a list of all template field names that occur in a template. """

    # get all the fields
    template_fields = get_template_fields(in_template)
    # adding each field name to a set ensures we only get unique fields
    template_field_names = {field.inner_content for field in template_fields}

    return list(template_field_names)
