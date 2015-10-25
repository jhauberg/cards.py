import os
import sys
import argparse
import csv
import errno
import shutil

from datetime import datetime


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


def content_from_template(data, template):
    """
    Returns the contents of the template with all template fields replaced by
    any matching fields in the provided data.
    """
    content = template

    for field in data:
        content = content.replace('{{%s}}' % str(field), data[field])

    return content


def main(argv):
    parser = argparse.ArgumentParser(
        description='Generate printable sheets of cards')

    parser.add_argument('-f', '--filename',
                        dest='filename',
                        help='The path to a CSV file containing card data',
                        required=True)

    parser.add_argument('-t', '--template',
                        dest='template',
                        help='The path to a card template',
                        required=True)

    args = vars(parser.parse_args())

    data = args['filename']
    template = args['template']

    with open(data) as f:
        data = csv.DictReader(f)

        with open(template) as t:
            template = t.read()

        with open('template/page.html') as p:
            page = p.read()

        with open('template/card.html') as c:
            card = c.read()

        with open('template/index.html') as i:
            index = i.read()

        cards = ''
        pages = ''

        cards_on_page = 0
        cards_on_all_pages = 0
        max_cards_per_page = 9

        for row in data:
            cards += card.replace('{{content}}',
                                  content_from_template(row, template))

            cards_on_page += 1
            cards_on_all_pages += 1

            if cards_on_page == max_cards_per_page:
                pages += page.replace('{{cards}}', cards)

                cards_on_page = 0
                cards = ''

        if cards_on_page > 0:
            pages += page.replace('{{cards}}', cards)

        create_missing_directories_if_necessary('generated')

        with open('generated/index.html', 'w') as result:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            title = '{0} cards generated ({1})'.format(cards_on_all_pages, now)

            index = index.replace('{{title}}', title)
            index = index.replace('{{pages}}', pages)

            result.write(index)

        shutil.copyfile('template/index.css', 'generated/index.css')

if __name__ == "__main__":
    main(sys.argv)
