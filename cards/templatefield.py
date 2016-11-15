# coding=utf-8

"""
This module provides functions and structures for template fields.
"""

import re

from typing import Iterator


class TemplateField:  # pylint: disable=too-few-public-methods
    """ Represents a field in a template. """

    def __init__(self,
                 name: str=None,
                 context: str=None,
                 inner_content: str=None,
                 indices: range=None):
        self.name = name  # the name of the field
        self.context = context  # the context passed to the field name
        self.inner_content = inner_content  # the inner content between the field braces
        self.indices = indices  # the indices ranging from the first wrapping '{' to the last '}'

        if self.inner_content is None:
            if self.name is not None:
                if self.context is not None:
                    self.inner_content = self.name + ' ' + self.context
                else:
                    self.inner_content = self.name

    def __str__(self):
        return '{{ ' + (self.inner_content or '') + ' }}'

    def has_row_reference(self) -> bool:
        """ Determine whether a field holds a row reference. """

        return (self.context.startswith('#')
                if self.context is not None
                else False)


def fields(in_template: str,
           with_name_like: str=None,
           with_context_like: str=None,
           strictly_matching: bool=True) -> Iterator[TemplateField]:
    """ Return an iterator for all template fields (e.g. '{{ a_field }}')
        that occur in a template.
    """

    pattern = r'{{\s?(([^}}\s]*)\s?(.*?))\s?}}'

    for field_match in re.finditer(pattern, in_template):
        inner_content = field_match.group(1).strip()
        name = field_match.group(2).strip()
        context = field_match.group(3).strip()

        inner_content = inner_content if len(inner_content) > 0 else None
        name = name if len(name) > 0 else None
        context = context if len(context) > 0 else None

        field = TemplateField(
            name, context, inner_content, indices=range(
                field_match.start(), field_match.end()))

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
            yield field

    return None


def first_field(in_template: str,
                with_name_like: str=None,
                with_context_like: str=None,
                strictly_matching: bool=True) -> TemplateField:
    """ Return the first template field found in a template. """

    return next(fields(in_template, with_name_like, with_context_like, strictly_matching), None)
