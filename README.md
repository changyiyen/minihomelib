# minihomelib
Simple Flask app for home library management

## Overview
minihomelib is a very simple web app (in its current form, basically a better-looking frontend to a YAML flat-file database) that I wrote out of frustration, after failing to find any lightweight solutions to home library management (in mid-2022); it was also written partly as an exercise in using Flask.

My particular use-case is this: I have a large number of books on multiple bookshelves at home, but I'm too messy/lazy to put each book back on its shelf after pulling it down for perusal. Over time, I lose track of where each book has gone, as well as where each book belongs. This app is intended to help with book management at home, especially when paired with a barcode scanner. The user can track when each book was checked out, and what its proper shelf is. A nice side effect is enabling collection of statistics on reading habits (although there's no code for processing that just yet).

Currently, minihomelib uses a text file (YAML) for its library database; this is intentional, since text files are more easily edited than SQLite files, in case larger numbers of books need to have their "home" shelves changed. I also intentionally left out a "delete book" button, since deletion events should be few and far between, and it's better to have the user manually delete those entries than risk accidental record deletion.

This app is very much in beta, and while functionally it can do its intended job just fine at a minimium level, there may be some less obvious bugs that I've overlooked. Please feel free to file reports, but I can't guarantee when I'll be able to fix them.

## Dependencies

minihomelib is a [Flask](https://pypi.org/project/Flask/) app, and was developed on Python 3. Database handling uses YAML. [ISBNlib](https://pypi.org/project/isbnlib/) is recommended for ISBN validation and metadata retrieval, but is not strictly required.

```shell
pip3 install Flask pyyaml
# Optional
pip3 install isbnlib
```

## Usage

Currently minihomelib uses Flask's built-in development server. Do not use it in production. See Flask's documentation for advice on formal deployment.

1. Start the server
```shell
$ python3 minihomelib.py
```
2. Navigate to 127.0.0.1:5000 using a Web browser (be sure to set your firewall properly)

## License

minihomelib is placed under the coffeeware license, itself a lightly modified beerware license.
