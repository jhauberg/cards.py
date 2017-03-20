<img width="90" src="https://cdn.rawgit.com/jhauberg/cards.py/master/logo.svg" alt="cards.py" align="left">

# cards.py

A tool for generating pages full of cards- ready to print.

Feed it with a [CSV file](example/love-letter/cards.csv) containing all your card data and it will output an HTML file with pages of your cards laid out for easy and efficient cutting. It's like a static site generator, but for cards!

Use the print function of your browser to save the pages to a PDF or to print them immediately.

# Installation

Install straight from the source:

```shell
$ python3 setup.py install
```

<details>
  <summary><strong>Uninstalling</strong></summary>

If you want to uninstall `cards.py` and make sure that you get rid of everything, you can run the installation again using the additional **--record** argument to save a list of all installed files:

```shell
$ python3 setup.py install --record installed_files.txt
```

You can then go through all listed files and manually delete each one.
</details>

# Usage

When installed, you can run `cards.py` on the command line:

```shell
$ cards make cards.csv
```

<details>
  <summary><strong>It doesn't work</strong></summary>

There's a few things that could go wrong during an install. If things didn't go as expected, check the following:

**Your PATH environment variable may be incorrect**

When you first installed Python, the installer probably added the `PATH` automatically to your `~/.profile` or `~/.bash_profile`. However, in case it didn't, it should look something like this:

```bash
PATH="/Library/Frameworks/Python.framework/Versions/3.6/bin:${PATH}"
export PATH
```

You may additionally need to add the `PYTHONPATH` variable and have it point to the `site-packages` directory of your Python version; for example, for a Python 3.6 installation, the variable could look like this:

```bash
export PYTHONPATH="${PYTHONPATH}/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/site-packages"
```
</details>

<details>
  <summary><strong>Running without installing</strong></summary>

You can also run `cards.py` without installing it. However, in that case, you must execute the `cards` module as a script.

Assuming working directory is the root of the project, you go like this:

```shell
$ python3 -m cards make cards.csv
```
</details>

## Requirements

This project strives to keep dependencies at an absolute minimum.

  * Python 3.5+
  * [docopt](https://github.com/docopt/docopt) - provides a nicer command-line interface

## Browser support

  * Safari
  * Chrome

## Examples

See [Trickbook](https://github.com/jhauberg/trickbook), or [Dungeon Deck](https://github.com/jhauberg/dungeon-deck) for examples of real projects.

## Full usage

```console
Generate print-ready cards for your tabletop game

Usage:
  cards make [<datasource>]... [--definitions=<defs>]
             [--output-path=<path>] [--output-file=<file>] [--include-header=<template>]
             [--card-size=<size>] [--force-page-breaks] [--disable-backs] [--disable-page-sections]
             [--discover] [--preview] [--verbose]
  cards new  [<name>] [--output-path=<path>] [--verbose]
  cards -h | --help
  cards --version

Examples:
  cards make cards.csv
    Builds the 'cards.csv' datasource and outputs to the current directory.

  cards make cards.csv tokens.csv -d defs.csv -o ~/Desktop
    Builds both 'cards.csv' and 'tokens.csv' datasources with the definitions 'defs.csv',
    and outputs to the specified path (the desktop in this case).

  cards new "Empty Game"
    Creates an empty project in the current directory.

Options:
  -h --help                         Show program help
  -o --output-path=<path>           Specify output directory
  -f --output-file=<file>           Specify output filename [default: index.html]
  -p --include-header=<template>    Specify a presentation template
  -d --definitions=<defs>           Specify definitions filename
  --card-size=<size>                Specify default card size [default: standard]
                                    Other options include: \'domino\', \'jumbo\' or \'token\'
  --force-page-breaks               Force a page break after each datasource
  --disable-backs                   Do not render card backs
  --disable-page-sections           Do not render page sections
  --discover                        Automatically find and use datasources in the current directory
  --preview                         Only render 1 of each card
  --verbose                         Show more information
  --version                         Show program version
```

# Why make this?

I'm making this because it should be easier getting your ideas to the table.

There's already plenty of tools that solve this problem. Some are free ([nanDeck](http://www.nand.it/nandeck/), [Squib](https://github.com/andymeneely/squib)), some are expensive ([inDesign](http://www.adobe.com/InDesign)). Some seem really good (*but are not available yet*, [Paperize](http://paperize.io/beta)).

However, common for most of them is that they are more complicated than I think they need to be.

Though these tools provide you with a wide range of options and possibilities, you first have to get past the (steep) learning curve before you can *really* use them proficiently.

The hope and intent of this tool is to provide a way to get a prototype built quickly and with as little hassle and setup as possible, while still providing options for customizing your cards as much- or as little, as you want to.

It's also just a fun project to work on; so there's that!

# Contributing

If you find any problems using this software, please [open an issue](https://github.com/jhauberg/cards.py/issues/new) or submit a fix as a pull request.

Please refer to [CONTRIBUTING](CONTRIBUTING.md) for further information.

## License

See [LICENSE](LICENSE)
