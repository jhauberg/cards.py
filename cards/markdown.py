# coding=utf-8

"""
This module provides Markdown formatting.
"""

import re

# matches any variation of bounding *'s:
# e.g. "emphasize *this*", or "strong **this**"
STRONG_PATTERN = r'(?<!\\)\*\*(.+?)\*\*'
EMPHASIS_PATTERN = r'(?<!\\)\*(.+?)\*'

# matches any variation of bounding _'s:
# e.g. "emphasize _this_", or "strong __this__"
# note that _'s applies under slightly different rules than *'s; it only kicks in
# when preceded and superceded by a special character or whitespace;
# e.g. "this_does not work_", "but _this does_" and "this (_works too_)"
STRONG_PATTERN_ALT = r'(?:(?<=\s|[^a-zA-Z0-9\\])|^)__(.+?)__(?=$|\s|[^a-zA-Z0-9])'
EMPHASIS_PATTERN_ALT = r'(?:(?<=\s|[^a-zA-Z0-9\\])|^)_(.+?)_(?=$|\s|[^a-zA-Z0-9])'

# match preceding ^; e.g. "5 kg/m^3"
SUPER_PATTERN = r'\^(.+?)(?=\s|\n|$)'

# matches any variation of bounding ~~'s': e.g. "deleted ~~this~~"
DELETED_PATTERN = r'~~(.+?)~~'
# matches any variation of bounding ++'s': e.g. "inserted ++this++"
INSERTED_PATTERN = r'\+\+(.+?)\+\+'

# matches any variation of 2 whitespace:
# e.g. "break this  line", or "break this    line twice"
BREAK_LINE_PATTERN = r'\s{2}'
# matches exactly: "break this   line twice"
# 4 whitespaces should produce same result, but this is a shortcut since 2 breaks is common
# note that this requires non-whitespace before, and after; so multiples of 3 does not work
BREAK_LINE_PATTERN_ALT = r'(?<=\S)\s{3}(?=\S)'

# match any escapes and get rid of them
ESCAPE_PATTERN = r'\\(?=\*|_)'


def markdown(content: str) -> str:
    """ Transform any Markdown formatting into HTML.

        This implementation provides only a subset of the Markdown specification
        (e.g. there's no support for headers, tables or images).  Additionally, it
        adds some things that are not part of the specification (e.g. line breaks).

        Supports:
            *emphasis*, _emphasis_
            **strong**, __strong__, "they can _also be **combined**_"
            ~~deleted~~, ++inserted++
            superscript^5

            Line break using multiples of 2 whitespace:
                "break  one time", "break    two times", "break      three times"
            or break twice by using 3 whitespace:
                "break   two times"
            note that multiples of 3 is not possible; e.g. 6 spaces will become 3 breaks.
    """

    # apply patterns with most constraints first, e.g. ** should overrule *, and __ overrule _
    content = re.sub(STRONG_PATTERN, '<strong>\\1</strong>', content)
    content = re.sub(STRONG_PATTERN_ALT, '<strong>\\1</strong>', content)

    content = re.sub(EMPHASIS_PATTERN, '<em>\\1</em>', content)
    content = re.sub(EMPHASIS_PATTERN_ALT, '<em>\\1</em>', content)

    content = re.sub(SUPER_PATTERN, '<sup>\\1</sup>', content)

    content = re.sub(DELETED_PATTERN, '<del>\\1</del>', content)
    content = re.sub(INSERTED_PATTERN, '<ins>\\1</ins>', content)

    # most constraints first; resolve three spaces first
    content = re.sub(BREAK_LINE_PATTERN_ALT, '<br /><br />', content)
    # then any double spaces
    content = re.sub(BREAK_LINE_PATTERN, '<br />', content)

    content = re.sub(ESCAPE_PATTERN, '', content)

    return content
