# coding=utf-8

import os

from cards.util import is_url, copy_file_if_necessary, create_missing_directories_if_necessary
from cards.warning import WarningDisplay, WarningContext


def should_retain_relative_resource_structure() -> bool:
    """ Determine whether resources should be copied retaining their relative directory structure.

        When this is True, a resource located at e.g. "images/my-image.png" will be copied as is.

        Otherwise, that same resource will be copied to "resources/copied/my-image.png".
        However, backwards-facing paths (like e.g. "../../my-image.png") or absolute paths, will
        always be copied to "resources/copied".
    """

    return False


def is_resource(file_path: str) -> bool:
    """ Determine whether file is a resource that should be copied. """

    # note that this function can be used to toggle whether all images should be copied to
    # /resources/copied, or if they should retain their directory structure as is
    # in either case, absolute or relative paths going back should always be copied
    return (file_path.startswith('..') or os.path.isabs(file_path)
            if should_retain_relative_resource_structure()
            else True)


def get_resource_path(resource_name: str) -> str:
    """ Get destination path for the resource. """

    return ('resources/copied/{0}'.format(resource_name)
            if resource_name is not None and len(resource_name) > 0
            else None)


def copy_images_to_output_directory(
        image_paths: list,
        root_path: str,
        output_path: str,
        verbosely: 'show warnings'=False) -> None:
    """ Copy all images to the output directory. """

    context = os.path.basename(root_path)

    for image_path in image_paths:
        # copy each relatively specified image
        if is_url(image_path):
            # unless it's a URL
            if verbosely:
                WarningDisplay.image_not_copied(WarningContext(context), image_path)
        else:
            # if the image path is not an absolute path, assume
            # that it's located relative to where the data is
            relative_source_path = os.path.join(
                os.path.dirname(root_path), image_path)

            # only copy if the file actually exists
            if os.path.isfile(relative_source_path):
                # retain relative directory structure
                resource_path = image_path

                if is_resource(image_path):
                    # unless it's a resource that should always be copied to the output directory
                    resource_path = get_resource_path(os.path.basename(image_path))

                relative_destination_path = os.path.join(
                    output_path, resource_path)

                # make sure any missing directories are created as needed
                create_missing_directories_if_necessary(
                    os.path.dirname(relative_destination_path))

                copy_file_if_necessary(relative_source_path, relative_destination_path)
            else:
                WarningDisplay.missing_image_error(
                    WarningContext(context), relative_source_path)