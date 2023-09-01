# minihomelib
Simple Flask app for home library management

## Overview
minihomelib is a very simple web app that I wrote out of frustration, after failing to find any lightweight solutions to home library management (in mid-2022); it was also written partly as an exercise in using Flask.

My particular use-case is this: I have a large number of books on multiple bookshelves at home, but I'm too messy/lazy to put each book back on its shelf after pulling it down for perusal. Over time, I lose track of where each book has gone, as well as where each book belongs. This app is intended to help with book management at home, especially when paired with a barcode scanner. The user can track when each book was checked out, and what its proper shelf is. A nice side effect is enabling collection of statistics on reading habits (although stat functionality is still rudimentary).

Previously, minihomelib used a text file (YAML) for its library database as well as for its configuration; the idea was that text files are easier to edit than SQLite files. However, the complexity of book metadata later convinced me to switch to SQLite. I also switched from YAML to TOML for the configuration file format, since a TOML parser is now included in the standard library.

Regarding the interface, I intentionally left out a "delete book" button, since book deletion events should be few and far between, and it's better to have the user manually delete those entries than risk accidental record deletion.

This app is very much in beta, and while functionally it can do its intended job just fine at a minimium level, there may be some less obvious bugs that I've overlooked. Please feel free to file reports, but I can't guarantee when I'll be able to fix them.

## Dependencies

minihomelib is a [Flask](https://palletsprojects.com/p/flask/) app, and was developed with [Python 3](https://www.python.org/). Currently, it uses SQLite and TOML for storage (both built-ins). [ISBNlib](https://pypi.org/project/isbnlib/) is recommended for ISBN validation and metadata retrieval, but is not strictly required.

```shell
pip3 install Flask
# Optional
pip3 install isbnlib
```

## Usage

Currently minihomelib uses Flask's built-in development server. *Do not use it in production.* See Flask's documentation for advice on formal deployment.

1. Start the server
```shell
$ python3 minihomelib.py
```
2. Navigate to 127.0.0.1:5000 using a Web browser (be sure to set your firewall properly)

## Screenshots

![Screenshot with example library](/screenshots/20230901_main_zh-TW.png)
![Screenshot of login page](/screenshots/20230901_login_zh-TW.png)
![Screenshot of user registration page](/screenshots/20230901_adduser_zh-TW.png)

## License

minihomelib is placed under the coffeeware license, itself a lightly modified beerware license.

## Current feature requests
- Add more stats (per user, etc)
- Interface aesthetics:
	- highlight terms matching search
- Dynamically generate data pages for each book
- Build as Docker image
