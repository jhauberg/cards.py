import os
import sys
import argparse
import csv
import errno
import re
import shutil
import subprocess
import itertools

__version_info__ = ('0', '2', '2')
__version__ = '.'.join(__version_info__)


class Metadata(object):
    """
    Provides metadata properties for the generated pages.
    """
    def __init__(self, title, description, version, copyright):
        self.title = title
        self.description = description
        self.version = version
        self.copyright = copyright

    @staticmethod
    def from_data_paths(data_paths):
        """
        Return a Metadata instance which reads any discovered metadata from
        the provided data paths.
        """
        title = ''
        description = ''
        version = ''
        copyright = ''

        # for now, just read from the first metadata provider
        data_path = data_paths[0]
        data_path_components = os.path.splitext(data_path)

        metadata_path = data_path_components[0] + '.meta'

        if len(data_path_components) > 1:
            metadata_path += data_path_components[1]

        if not os.path.isfile(metadata_path):
            if is_verbose:
                warn('No metadata was found. '
                     'You can provide it at: \'{0}\''.format(metadata_path))
        else:
            with open(metadata_path) as mf:
                metadata = csv.DictReader(lower_first_row(mf))

                for metadata_row in metadata:
                    title = metadata_row.get('@title')
                    description = metadata_row.get('@description')
                    version = metadata_row.get('@version')
                    copyright = metadata_row.get('@copyright')

                    break

        return Metadata(title, description, version, copyright)


def warn(message, as_error=False):
    apply_red_color = '\x1B[31m'
    apply_yellow_color = '\x1B[33m'
    apply_normal_color = '\033[0m'

    apply_color = apply_yellow_color if not as_error else apply_red_color

    print(apply_color +
          '[!] ' + message +
          apply_normal_color)


def lower_first_row(rows):
    return itertools.chain([next(rows).lower()], rows)


def create_missing_directories_if_necessary(path):
    """
    Mimics the command 'mkdir -p'.
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def copy_images_to_output_directory(image_paths, root_path, output_path,
                                    verbosely=False):
    """
    Copies all provided images to the specified output path, keeping the
    directory structure intact for each image.
    """
    for image_path in image_paths:
        # copy each relatively specified image (if an image is specified
        # using an absolute path, assume that it should not be copied)
        if not os.path.isabs(image_path):
            # if the image path is not an absolute path, assume
            # that it's located relative to where the data is
            relative_source_path = os.path.join(
                os.path.dirname(root_path), image_path)

            relative_destination_path = os.path.join(
                output_path, image_path)

            # make sure any missing directories are created as needed
            create_missing_directories_if_necessary(
                os.path.dirname(relative_destination_path))

            if os.path.isfile(relative_source_path):
                # only copy if the file actually exists
                shutil.copyfile(
                    relative_source_path, relative_destination_path)
            else:
                warn('One or more cards contain an image reference that does '
                     'not exist: \'{0}\''.format(relative_source_path),
                     as_error=True)


def fill_template_image_fields(template):
    """
    Recursively finds all {{image:size}} fields and returns a string replaced
    with HTML compliant <img> tags.
    """
    image_paths = []

    for match in re.finditer('{{(.*?)}}', template, re.DOTALL):
        image_path = match.group(1)

        if len(image_path) > 0:
            # determine whether a size has been explicitly specified; e.g.
            # images/name-of-image.svg:16x16
            size_index = image_path.rfind(':')

            explicit_width = None
            explicit_height = None

            if size_index is not -1:
                # get the size specifications (removing any whitespace)
                size = image_path[size_index + 1:].strip()
                # get each size specification separately (removing blanks)
                size = filter(None, size.split('x'))

                if len(size) > 0:
                    explicit_width = int(size[0])

                    if explicit_width < 0:
                        explicit_width = None

                if len(size) > 1:
                    explicit_height = int(size[1])

                    if explicit_height < 0:
                        explicit_height = None
                else:
                    # default to a square image using the width specification
                    explicit_height = explicit_width

                # get rid of the size specification to have a clean image path
                image_path = image_path[:size_index]

            if (explicit_width is not None and
               explicit_height is not None):
                    image_tag = '<img src="{0}" width="{1}" height="{2}">'
                    image_tag = image_tag.format(image_path,
                                                 explicit_width,
                                                 explicit_height)
            else:
                image_tag = '<img src="{0}">'.format(image_path)

            image_paths.append(image_path)

            # since the string we're finding matches on has just been changed,
            # we have to recursively look for more fields if there are any
            content = fill_template_image_fields(
                template[:match.start()] + image_tag + template[match.end():])

            template = content[0]

            image_paths.extend(content[1])

            break

    return (template, image_paths)


def fill_template_field(field_name, field_value, in_template):
    """
    Fills in the provided value in the provided template for all occurences
    of a given template field.
    """
    # template fields are always represented by wrapping {{ }}'s'
    template_field = re.escape('{{%s}}' % str(field_name))

    # find any occurences of the field, using a case-insensitive
    # comparison, to ensure that e.g. {{name}} is populated with the
    # value from column "Name", even though the casing might differ
    search = re.compile(template_field, re.IGNORECASE)

    # finally replace any found occurences of the template field with its value
    return search.sub(field_value, in_template)


def fill_template(template, data):
    """
    Returns the contents of the template with all template fields replaced by
    any matching fields in the provided data.
    """
    image_paths = []

    for field in data:
        # ignore special variable columns
        if not field.startswith('@'):
            # fetch the content for the field (may also be templated)
            template_content = str(data[field])

            # replace any image fields with HTML compliant <img> tags
            content = fill_template_image_fields(template_content)

            template_content = content[0]

            image_paths.extend(content[1])

            # fill content into the provided template
            template = fill_template_field(
                field_name=str(field),
                field_value=template_content,
                in_template=template)

    return (template, image_paths)


def setup_arguments(parser):
    parser.add_argument('-f', '--input-filename', dest='input_paths', type=str,
                        required=True, nargs='*',
                        help='A path to a CSV file containing card data')

    parser.add_argument('-o', '--output-folder', dest='output_path', type=str,
                        required=False,
                        help='A path to a directory in which the pages will '
                             'be generated')

    parser.add_argument('-t', '--template', dest='template', type=str,
                        required=False,
                        help='A path to a card template')

    parser.add_argument('--disable-cut-guides', dest='disable_cut_guides',
                        required=False, default=False, action='store_true',
                        help='Disable cut guides on the margins of the '
                             'generated pages')

    parser.add_argument('--verbose', dest='verbose',
                        required=False, default=False, action='store_true',
                        help='Show more information')

    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__,
                        help='Show the program\'s version, then exit')


def main(argv):
    parser = argparse.ArgumentParser(
        description='Generates printable sheets of cards.')

    setup_arguments(parser)

    args = vars(parser.parse_args())

    # required arguments
    data_paths = args['input_paths']

    # optional arguments
    output_path = args['output_path']
    default_template_path = args['template']
    disable_cut_guides = bool(args['disable_cut_guides'])
    is_verbose = bool(args['verbose'])

    if default_template_path is not None and len(default_template_path) > 0:
        with open(default_template_path) as t:
            default_template = t.read().strip()

        if is_verbose and len(default_template) == 0:
            warn('The provided template appears to be empty. '
                 'Blank cards may occur.')
    else:
        default_template = None

        if is_verbose:
            warn('A default template was not provided. '
                 'Blank cards may occur.')

    with open('template/page.html') as p:
        page = p.read()

        if disable_cut_guides:
            cut_guides_display = 'style="display: none"'
        else:
            cut_guides_display = 'style="display: block"'

        page = page.replace('{{cut_guides_style}}', cut_guides_display)

    with open('template/card.html') as c:
        card = c.read()

    with open('template/index.html') as i:
        index = i.read()

    metadata = Metadata.from_data_paths(data_paths)

    cards = ''
    pages = ''

    cards_on_page = 0
    cards_on_all_pages = 0

    max_cards_per_page = 9

    pages_total = 0

    image_paths = []

    # error format/template string for the output on cards specifying a
    # template that was not found, or could not be opened
    template_not_opened = """
                          <b>Error (at card #{{card_index}})</b>:
                          the template that was provided for this
                          card could not be opened:<br /><br />
                          <b>%s</b>
                          """

    # error format/template string for the output on cards when a default
    # template has not been specified, and the card hasn't specified one either
    template_not_provided = """
                            <b>Error (at card #{{card_index}})</b>:
                            a template was not provided for this card.
                            <br /><br />

                            Provide one using the <b>--template</b>
                            argument, or through a <b>@template</b>
                            column.
                            """

    for data_path in data_paths:
        with open(data_path) as f:
            data = csv.DictReader(lower_first_row(f))

            for row in data:
                # determine how many instances of this card to generate
                # (defaults to a single instance if not specified)
                count = int(row.get('@count', 1))

                if count < 0:
                    # if a negative count is specified, treat it as none
                    count = 0

                for i in range(count):
                    # determine which template to use for this card (defaults
                    # to the template specified from the --template option)
                    template_path = row.get('@template', default_template_path)
                    template = None

                    card_index = cards_on_all_pages + 1

                    if (template_path is not default_template_path and
                       len(template_path) > 0):
                        if not os.path.isabs(template_path):
                            # if the template path is not an absolute path,
                            # assume that it's located relative to the data
                            template_path = os.path.join(
                                os.path.dirname(data_path),
                                template_path)

                        try:
                            with open(template_path) as t:
                                template = t.read().strip()
                        except IOError:
                            template = template_not_opened % template_path

                            warn('The card at #{0} provided a template that '
                                 'could not be opened: \'{1}\''
                                 .format(card_index, template_path),
                                 as_error=True)
                    else:
                        # if the template path points to the same template as
                        # provided through --template, we already have it
                        template = default_template

                    if template is None:
                        template = template_not_provided

                    content = fill_template(template, data=row)

                    card_content = content[0]

                    image_paths.extend(content[1])

                    card_content = fill_template_field(
                        field_name='card_index',
                        field_value=str(card_index),
                        in_template=card_content)

                    card_content = fill_template_field(
                        field_name='version',
                        field_value=metadata.version,
                        in_template=card_content)

                    cards += card.replace(
                        '{{content}}', card_content)

                    cards_on_page += 1
                    cards_on_all_pages += 1

                    if cards_on_page == max_cards_per_page:
                        # add another page full of cards
                        pages += page.replace('{{cards}}', cards)

                        pages_total += 1

                        cards_on_page = 0
                        cards = ''

    if cards_on_page > 0:
        # in case there's still cards remaining, fill those into a new page
        pages += page.replace('{{cards}}', cards)

        pages_total += 1

    if output_path is None:
        # output to current working directory unless otherwise specified
        output_path = ''

    output_path = os.path.join(output_path, 'generated')

    create_missing_directories_if_necessary(output_path)

    pages_or_page = 'pages' if pages_total > 1 else 'page'
    cards_or_card = 'cards' if cards_on_all_pages > 1 else 'card'

    with open(os.path.join(output_path, 'index.html'), 'w') as result:
        title = metadata.title

        if not title or len(title) == 0:
            title = 'cards.py: {0} {1} on {2} {3}'.format(
                cards_on_all_pages, cards_or_card,
                pages_total, pages_or_page)

        pages = fill_template_field(
            field_name='cards_total',
            field_value=str(cards_on_all_pages),
            in_template=pages)

        index = index.replace('{{pages}}', pages)
        index = index.replace('{{title}}', title)
        index = index.replace('{{description}}', metadata.description)
        index = index.replace('{{copyright}}', metadata.copyright)

        result.write(index)

    # ensure there are no duplicate image paths, since that would just
    # cause unnecessary copy operations
    image_paths = list(set(image_paths))

    copy_images_to_output_directory(image_paths, data_path, output_path,
                                    verbosely=True)

    shutil.copyfile(
        'template/index.css',
        os.path.join(output_path, 'index.css'))

    print('Generated {0} {1} on {2} {3}. See \'{4}/index.html\'.'
          .format(cards_on_all_pages, cards_or_card,
                  pages_total, pages_or_page,
                  output_path))

    if sys.platform.startswith('darwin'):
        subprocess.call(('open', output_path))
    elif os.name == 'nt':
        subprocess.call(('start', output_path), shell=True)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', output_path))

if __name__ == "__main__":
    main(sys.argv)
