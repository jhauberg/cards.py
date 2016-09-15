<img width="90" src="https://rawgit.com/jhauberg/cards.py/master/cards/templates/resources/cards.svg" alt="cards.py" align="left">

# cards.py

A tool for generating print-ready sheets of cards.

Feed it with a [CSV file](example/love-letter/cards.csv) containing all your card data and it will output an HTML file with pages of your cards laid out for easy and efficient cutting. It's like a static site generator, but for cards!

Use the print function of your browser to save the pages to a PDF or to print them immediately.

# Installation

Install straight from the source:

    $ python3 setup.py install

# Usage

When installed, you can run `cards.py` on the command line:

    $ cards cards.csv

<details>
  <summary>**Running without installing**</summary>

You can also run `cards.py` without installing it. However, in that case, you must execute the `cards` module as a script.

Assuming working directory is the root of the project, you go like this:

    $ python3 -m cards cards.csv
</details>

<details>
  <summary>**Uninstalling**</summary>

If you wish to uninstall `cards.py` and make sure that you get rid of everything, you can run the installation again using the additional **--record** argument to save a list of all installed files:

    $ python3 setup.py install --record installed_files.txt

You can then go through all listed files and manually delete each one.

This is actually a general tip that can be used for any python package installed using `setup_tools`.
</details>

## Requirements

  * Python 3.5

## Browser support

  * Safari
  * Chrome

## Examples

See [Trickbook](https://github.com/jhauberg/trickbook), or [Dungeon Deck](https://github.com/jhauberg/dungeon-deck) for examples of real projects.

# Why make this?

I'm making this because it should be easier getting your ideas to the table.

There's already plenty of tools that solve this problem. Some are free ([nanDeck](http://www.nand.it/nandeck/), [Squib](https://github.com/andymeneely/squib)), some are expensive ([inDesign](http://www.adobe.com/InDesign)). Some seem really good (*but are not available yet*, [Paperize](http://paperize.io/beta)).

However, common for most of them is that they are more complicated than I think they need to be.

Though these tools provide you with a wide range of options and possibilities, you first have to get past the (steep) learning curve before you can *really* use them proficiently.

The hope and intent of this tool is to provide a way to get a prototype built quickly and with as little hassle and setup as possible, while still providing options for customizing your cards as much- or as little, as you want to.

It's also just a fun project to work on; so there's that.

# Contributing

If you find any problems using this software, please [open an issue](https://github.com/jhauberg/cards.py/issues/new) or submit a fix as a pull request.

Please refer to [CONTRIBUTING](CONTRIBUTING.md) for further information.

## License

    Copyright 2016 Jacob Hauberg Hansen.

    Permission is hereby granted, free of charge, to any person obtaining a copy of
    this software and associated documentation files (the "Software"), to deal in
    the Software without restriction, including without limitation the rights to
    use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is furnished to do
    so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

    http://en.wikipedia.org/wiki/MIT_License
