# coding=utf-8

import os
import sys
import subprocess
import filecmp
import shutil
import itertools
import errno

from urllib.parse import urlparse


class FileWrapper:
    """ Provides access to the last read line of a file.

        Useful in combination with parsers such as DictReader when
        you also need access to unparsed data.
    """

    def __init__(self, file):
        self.file = file
        self.raw_line = None

    def __iter__(self):
        return self

    def __next__(self):
        # iterate like usual, but keep the read line around until the next is read
        self.raw_line = next(self.file)

        return self.raw_line


class WarningContext(object):
    """ Represents the context of a warning. """

    def __init__(self, name: str, row_index: int=-1, card_index: int=-1):
        self.name = name
        self.row_index = row_index
        self.card_index = card_index


def warn(message: str, in_context: WarningContext=None, as_error=False) -> None:
    """ Display a command-line warning, optionally showing its context. """

    apply_red_color = '\033[31m'
    apply_yellow_color = '\033[33m'
    apply_normal_color = '\033[0m'

    apply_color = apply_yellow_color if not as_error else apply_red_color

    message_context = '[{0}]'.format('!' if as_error else '-')

    if in_context is not None:
        if in_context.row_index > -1:
            if in_context.card_index > -1 and in_context.card_index != in_context.row_index:
                message_context = '{0} [{1}:#{2}.{3}]'.format(
                    message_context, in_context.name, in_context.row_index, in_context.card_index)
            else:
                message_context = '{0} [{1}:#{2}]'.format(
                    message_context, in_context.name, in_context.row_index)
        else:
            message_context = '{0} [{1}]'.format(
                message_context, in_context.name)

    message_content = message_context + ' ' + message

    print(apply_color + message_content + apply_normal_color)


def most_common(objects: list) -> object:
    """ Return the object that occurs most frequently in a list of objects. """

    return max(set(objects), key=objects.count)


def lower_first_row(rows):
    """ Return rows where the first row is all lower-case. """

    return itertools.chain([next(rows).lower()], rows)


def dequote(s):
    """
    If a string has single or double quotes around it, remove them.
    Make sure the pair of quotes match.
    If a matching pair of quotes is not found, return the string unchanged.
    """
    if (s[0] == s[-1]) and s.startswith(('\'', '"')):
        return s[1:-1]

    return s


def is_url(string: str) -> bool:
    """ Determines whether a string is an url or not. """
    return urlparse(string).scheme != ""


def open_path(path: str) -> None:
    """ Opens a path in a cross-platform manner;
        showing e.g. Finder on MacOS or Explorer on Windows
    """

    if sys.platform.startswith('darwin'):
        subprocess.call(('open', path))
    elif os.name == 'nt':
        subprocess.call(('start', path), shell=True)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', path))


def find_file_path(name: str, paths: list) -> (bool, str):
    """ Look for a path with 'name' in the filename in the specified paths.

        If found, returns the first discovered path to a file containing the specified name,
        otherwise returns the first potential path to where it looked for one.
    """

    found_path = None
    first_potential_path = None

    if len(paths) > 0:
        # first look for a file simply named exactly the specified name- we'll just use
        # the first provided path and assume that this is the main directory
        path_directory = os.path.dirname(paths[0])

        potential_path = os.path.join(path_directory, name)

        if os.path.isfile(potential_path):
            # we found one
            found_path = potential_path

    if found_path is None:
        # then attempt looking for a file named like 'some_file.the-name.csv' for each
        # provided path until a file is found, if any
        for path in paths:
            path_components = os.path.splitext(path)

            potential_path = str(path_components[0]) + '.' + name

            if first_potential_path is None:
                first_potential_path = potential_path

            if os.path.isfile(potential_path):
                # we found one
                found_path = potential_path

                break

    return ((True, found_path) if found_path is not None else
            (False, first_potential_path))


def copy_file_if_necessary(source_path: str, destination_path: str) -> bool:
    """ Attempt copying a file to a destination path.

        If the file already exists at the destination path, the destination file is only
        overwritten if it is different from the source.
    """

    if not os.path.exists(destination_path) or not filecmp.cmp(source_path, destination_path):
        # the file doesn't already exist, or it does exist, but is different
        try:
            shutil.copyfile(source_path, destination_path)

            return True
        except IOError:
            return False

    return False


def create_missing_directories_if_necessary(path: str) -> bool:
    """ Attempt to create any missing directories in a path.

        Essentially mimics the command 'mkdir -p'.
    """

    try:
        os.makedirs(path)

        return True
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
