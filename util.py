# coding=utf-8

import os
import itertools
import errno


def warn(message: str, in_context: str=None, as_error: 'apply error color'=False) -> None:
    """ Display a command-line warning. """

    apply_red_color = '\033[31m'
    apply_yellow_color = '\033[33m'
    apply_normal_color = '\033[0m'

    apply_color = apply_yellow_color if not as_error else apply_red_color

    message_content = '[{0}]'.format('!' if as_error else '-')

    if in_context is not None:
        message_content = '{0} [{1}]'.format(message_content, str(in_context))

    message_content = message_content + ' ' + message

    print(apply_color + message_content + apply_normal_color)


def dict_from_string(string: 'a string of key-value pairs') -> dict:
    """ Returns a dictionary object parsed from a string containing comma-separated key-value pairs.

        For example: "a_key=a_value, another_key=another_value"
    """
    if string is None or len(string) == 0:
        return None

    return dict(kvp.strip().split('=') for kvp in string.split(','))


def most_common(objects: list) -> object:
    """ Returns the object that occurs most frequently in a list of objects. """

    return max(set(objects), key=objects.count)


def lower_first_row(rows):
    """ Returns rows where the first row is all lower-case. """

    return itertools.chain([next(rows).lower()], rows)


def create_missing_directories_if_necessary(path: str) -> None:
    """ Mimics the command 'mkdir -p'. """

    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
