# <img width="72" src="cards.svg" alt="Tabletops"> cards.py

A tool for generating print-ready sheets of cards. Particularly useful in the early stages of prototyping a card game.

Feed it with a [CSV file](example/my-data.csv) containing all your card data, and it will output a single HTML file with pages of your cards laid out for easy and efficient cutting.

Use your browsers print function to save the pages to a PDF, or to print immediately.

**Currently only A4 pages with Poker-sized cards (2.5x3.5 inches) is supported.**

# Usage

Run from command line:

    $ python cards.py -f example/my-data.csv

## Browser support

  * Safari
  * Chrome

## Why?

The gap is too large between having all the card data, to getting a prototype on the table.

It should be easier, and this tool tries to make it so.

There's already plenty of tools that try to solve this problem. Some are free ([nanDeck](http://www.nand.it/nandeck/), [Squib](https://github.com/andymeneely/squib)), some are expensive ([inDesign](www.adobe.com/InDesign)). However, common for all of them is that they are more complicated than I think they need to be (for this specific task).

Though they provide you with a wide range of options and possibilities, you first have to get past the (steep) learning curve before you can *really* use them.

The hope and intent of this tool is to provide a way to get a prototype built fast, with as little hassle and setup as possible, while still providing options for customizing your cards as much- or as little, as you want to.

## License

    Copyright 2015 Jacob Hauberg Hansen.

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
