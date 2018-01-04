# coding=utf-8

"""
This module provides utility functions for common file, path, data and string operations.
"""

import os
import sys
import math
import subprocess
import filecmp
import shutil
import itertools
import errno

from urllib.parse import urlparse


class FileWrapper:  # pylint: disable=too-few-public-methods
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


def pretty_size(size_in_bytes: int) -> str:
    """ Return a pretty representation of a file size. """

    if size_in_bytes <= 0:
        return 'No content'

    sizes = ('B', 'KB', 'MB')

    size_index = int(math.floor(math.log(size_in_bytes, 1024)))
    size = round(size_in_bytes / math.pow(1024, size_index), 2)

    if size_index > len(sizes) - 1:
        return '>1 TB'

    size_format = sizes[size_index]

    return '{0:.{precision}f} {1}'.format(
        size, size_format, precision=(2 if size_index > 1 else 0))


def directory_size(directory_path: str) -> int:
    """ Return the total size of a directory and all of its sub-directories (in bytes). """

    size_in_bytes = 0

    for file in os.scandir(directory_path):
        if file.is_file():
            size_in_bytes += os.path.getsize(file.path)
        elif file.is_dir():
            size_in_bytes += directory_size(file.path)

    return size_in_bytes


def first(iterable):
    """ Return the first object in an iterable, if any. """

    return next(iterable, None)


def most_common(objects: list) -> object:
    """ Return the object that occurs most frequently in a list of objects. """

    return max(set(objects), key=objects.count)


def lower_first_row(rows):
    """ Return rows where the first row is all lower-case. """

    return itertools.chain([next(rows).lower()], rows)


def dequote(string: str) -> str:
    """ Return string by removing surrounding double or single quotes. """

    if (string[0] == string[-1]) and string.startswith(('\'', '"')):
        return string[1:-1]

    return string


def is_url(string: str) -> bool:
    """ Determine whether a string is an url or not. """

    try:
        result = urlparse(string)

        return result.scheme and result.netloc and result.path
    except:
        return False


def terminal_supports_color() -> bool:
    """ Determine whether the current terminal supports colored output. """

    platform = sys.platform

    is_supported_platform = platform != 'win32' or 'ANSICON' in os.environ
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    if not is_supported_platform or not is_a_tty:
        return False

    return True


def get_line_number(from_index: int, in_string: str) -> int:
    """ Return the line number of which the character at an index in a string is located. """

    return in_string.count('\n', 0, from_index) + 1


def get_padded_string(string: str,
                      in_string: str,
                      from_char_index: int) -> str:
    """ Return a string that is appropriately padded/indented, given a starting position.

        For example, if a starting index of 4 is given for a string "    content\ngoes here",
        the resulting string becomes "    content\n    goes here".
    """

    pad_count = 0
    index = from_char_index

    while index >= 0:
        # keep going backwards in the string
        index -= 1

        if index < 0 or in_string[index] == '\n':
            # we found the previous line or beginning of string
            break

        pad_count += 1

    if pad_count > 0:
        # split content up into separate lines
        lines = string.splitlines(keepends=True)
        # then append padding between each line
        string = (' ' * pad_count).join(lines)
        # and get rid of any trailing newlines
        string = string.rstrip()

    return string


def open_path(path: str) -> None:
    """ Open a path in a cross-platform manner;
        i.e. open Finder on MacOS and Explorer on Windows.
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


def copy_file_if_necessary(source_path: str, destination_path: str) -> (bool, bool):
    """ Attempt copying a file to a destination path.

        If the file already exists at the destination path, the destination file is only
        overwritten if it is different from the source.
    """

    file_already_exists = os.path.exists(destination_path)

    if not file_already_exists or not filecmp.cmp(source_path, destination_path):
        # the file doesn't already exist, or it does exist, but is different
        try:
            shutil.copyfile(source_path, destination_path)

            return True, file_already_exists
        except IOError:
            pass

    return False, file_already_exists


def create_directories_if_necessary(path: str) -> bool:
    """ Attempt to create any missing directories in a path.

        Essentially mimics the command 'mkdir -p'.
    """

    try:
        os.makedirs(path)

        return True
    except OSError as error:
        if error.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
