# coding=utf-8

import os
import itertools
import errno


class WarningContext(object):
    def __init__(self, name: str, row_index: int=-1, card_index: int=-1):
        self.name = name
        self.row_index = row_index
        self.card_index = card_index


def warn(message: str, in_context: WarningContext=None, as_error=False) -> None:
    """ Display a command-line warning. """

    apply_red_color = '\033[31m'
    apply_yellow_color = '\033[33m'
    apply_normal_color = '\033[0m'

    apply_color = apply_yellow_color if not as_error else apply_red_color

    message_content = '[{0}]'.format('!' if as_error else '-')

    if in_context is not None:
        if in_context.row_index > -1:
            if in_context.card_index > -1:
                message_content = '{0} [{1}:{2}#{3}]'.format(
                    message_content, in_context.name, in_context.row_index, in_context.card_index)
            else:
                message_content = '{0} [{1}:{2}]'.format(
                    message_content, in_context.name, in_context.row_index)
        else:
            message_content = '{0} [{1}]'.format(
                message_content, in_context.name)

    message_content = message_content + ' ' + message

    print(apply_color + message_content + apply_normal_color)


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
