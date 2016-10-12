# coding=utf-8

import re

# matches any variation of bounding *'s:
# e.g. "emphasize *this*", or "strong **this**"
strong_pattern = '\*\*(.*?)\*\*'
emphasis_pattern = '\*(.*?)\*'

# matches any variation of bounding _'s:
# e.g. "emphasize _this_", or "strong __this__"
# note that _'s applies under slightly different rules than *'s; it only kicks in
# when preceded and superceded by a special character or whitespace;
# e.g. "this_does not work_", "but _this does_" and "this (_works too_)"
strong_pattern_alt = '(?:(?<=\s|[^a-zA-Z0-9])|^)__(.*?)__(?=$|\s|[^a-zA-Z0-9])'
emphasis_pattern_alt = '(?:(?<=\s|[^a-zA-Z0-9])|^)_(.*?)_(?=$|\s|[^a-zA-Z0-9])'

# match preceding ^; e.g. "5 kg/m^3"
super_pattern = '\^(.+?)(?=\s|\n|$)'

# matches any variation of bounding ~~'s': e.g. "deleted ~~this~~"
deleted_pattern = '~~(.*?)~~'
# matches any variation of bounding ++'s': e.g. "inserted ++this++"
inserted_pattern = '\+\+(.*?)\+\+'

# matches any variation of 2 whitespace:
# e.g. "break this  line", or "break this    line twice"
break_line_pattern = '\s{2}'
# matches exactly: "break this   line twice"
# 4 whitespaces should produce same result, but this is a shortcut since 2 breaks is common
# note that this requires non-whitespace before, and after; so multiples of 3 does not work
break_line_pattern_alt = '(?<=\S)\s{3}(?=\S)'


def markdown(content: str) -> str:
    """ Transform any Markdown formatting into HTML.

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
    content = re.sub(strong_pattern, '<strong>\\1</strong>', content)
    content = re.sub(strong_pattern_alt, '<strong>\\1</strong>', content)

    content = re.sub(emphasis_pattern, '<em>\\1</em>', content)
    content = re.sub(emphasis_pattern_alt, '<em>\\1</em>', content)

    content = re.sub(super_pattern, '<sup>\\1</sup>', content)

    content = re.sub(deleted_pattern, '<del>\\1</del>', content)
    content = re.sub(inserted_pattern, '<ins>\\1</ins>', content)

    # most constraints first; resolve three spaces first
    content = re.sub(break_line_pattern_alt, '<br /><br />', content)
    # then any double spaces
    content = re.sub(break_line_pattern, '<br />', content)

    return content
