# coding=utf-8

"""
This module provides functions for handling and dealing with the resources used in a project.
"""

import os
import stat

from typing import List

from cards.util import is_url, copy_file_if_necessary, create_directories_if_necessary
from cards.warning import WarningDisplay, WarningContext


def supported_image_types() -> tuple:
    """ Return all supported and recognized image types. """

    return '.svg', '.png', '.jpg', '.jpeg', '.bmp'


def is_image(image_path: str) -> bool:
    """ Determine whether a path points to an image. """

    return (image_path.strip().lower().endswith(supported_image_types())
            if image_path is not None
            else False)


def get_resources_path() -> str:
    """ Get path for copied resources. """

    return 'res'


def get_resource_path(resource_name: str) -> str:
    """ Get destination path for the resource. """

    return (os.path.join(get_resources_path(), resource_name)
            if resource_name is not None and len(resource_name) > 0
            else None)


def is_hidden(path: str) -> bool:
    """ Determine whether the file at a path is hidden. """

    if os.path.isfile(path):
        filename = os.path.basename(os.path.abspath(path))

        return filename.startswith('.') or has_hidden_attribute(path)

    return False


def has_hidden_attribute(path: str) -> bool:
    """ Determine whether the file at a path contains a hidden attribute. """

    try:
        return bool(os.stat(path).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
    except AttributeError:
        return False


def get_unused_resources(in_directory_path: str, copied_filenames: list) -> (list, list):
    """ Return a list of all files in path that are not one of the copied files. """

    existing_resource_filenames = []

    resources_path = os.path.join(in_directory_path, get_resources_path())

    try:
        existing_resource_filenames = list(filter(
            lambda resource_path: not is_hidden(os.path.join(resources_path, resource_path)),
            os.listdir(resources_path)))
    except IOError:
        pass

    unused_resource_names = list(set(existing_resource_filenames) - set(copied_filenames))
    unused_resource_paths = [os.path.join(resources_path, resource_name)
                             for resource_name in unused_resource_names]

    return unused_resource_names, unused_resource_paths


def transformed_image_paths(image_paths: List[str], relative_to_path: str) -> List[str]:
    return [os.path.join(os.path.dirname(relative_to_path), image_path)
            for image_path in image_paths]


def copy_images_to_output_directory(
        image_paths: list,
        root_path: str,
        output_path: str) -> None:
    """ Copy all images to the output directory. """

    context = os.path.basename(root_path) if root_path is not None else '???'

    for image_path in image_paths:
        # copy each relatively specified image
        if is_url(image_path):
            # unless it's a URL
            WarningDisplay.image_not_copied(
                WarningContext(context), image_path)

            continue

        # if the image path is not an absolute path,
        # assume that it's located relative to where the data is
        relative_source_path = os.path.normpath(image_path)

        # only copy if the file actually exists
        if not os.path.isfile(relative_source_path):
            WarningDisplay.missing_image_error(
                WarningContext(context), relative_source_path)

            continue

        resource_path = get_resource_path(os.path.basename(image_path))

        relative_destination_path = os.path.join(
            output_path, resource_path)

        # make sure any missing directories are created as needed
        create_directories_if_necessary(
            os.path.dirname(relative_destination_path))

        resource_was_copied, resource_already_existed = copy_file_if_necessary(
            relative_source_path, relative_destination_path)

        resource_was_overwritten = resource_already_existed and resource_was_copied
        resource_was_duplicate = resource_already_existed and not resource_was_copied

        if resource_was_duplicate:
            # do nothing for now- this is triggered several times and is neither
            # a problem nor something that the user is interested in knowing about
            pass
        elif resource_was_overwritten:
            # the resource was named identically to an existing resource, but had
            # different or changed file contents; this might be an error, so warn about
            WarningDisplay.resource_was_overwritten(
                WarningContext(context), resource_path, relative_source_path)
