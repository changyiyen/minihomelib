#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Prerequisites: flask, pyyaml (pip3 install Flask pyyaml)
import flask
import yaml

# Suggested: isbnlib (pip3 install isbnlib)
try:
    import isbnlib
    ISBNlib_imported = True
except ImportError:
    ISBNlib_imported = False

# Built-ins
import datetime
#import sqlite3
import sys

# Change to .ini file?
with open('config.yaml', 'r') as configfile:
    conf = yaml.safe_load(configfile)

# Change to SQLite?
with open('library.yaml', 'r') as library:
    lib = yaml.safe_load(library)

app = flask.Flask(__name__)
status = ""

@app.route('/', methods=['GET','POST'])
def main():
    global status
    if flask.request.method == 'GET':
        return flask.render_template('main.htm', lib=lib, pagedate=datetime.datetime.isoformat(datetime.datetime.today()), status=status, shelves=conf["shelves"], past_due=int(conf['past_due']))
    if flask.request.method == 'POST':
        # Do nothing on empty ISBN
        if flask.request.form.get('isbn') == '' or lib == None:
            #return flask.redirect('/')
            return flask.render_template('main.htm', lib=lib, pagedate=datetime.datetime.isoformat(datetime.datetime.today()), status=status, shelves=conf["shelves"])
        elif flask.request.form.get('isbn') in lib:
            if ISBNlib_imported:
                if isbnlib.notisbn(flask.request.form.get('isbn')):
                    status = "Error: not valid ISBN"
                    #return flask.redirect('/')
                    return flask.render_template('main.htm', lib=lib, pagedate=datetime.datetime.isoformat(datetime.datetime.today()), status=status)
            # Checkout (start new transaction)
            if lib[flask.request.form.get('isbn')]['CHECKOUT_STATUS'] == 'checked_in':
                lib[flask.request.form.get('isbn')]['CHECKOUT_STATUS'] = 'checked_out'
                lib[flask.request.form.get('isbn')]['TRANSACTION_DATES'].append([datetime.datetime.today().strftime('%Y-%m-%d')])
                with open('library.yaml', 'w') as library:
                    yaml.safe_dump(lib, library)
                status = "Book '{}' checked out!".format(lib[flask.request.form.get('isbn')]['BOOKNAME'])
                #return flask.redirect('/')
                return flask.render_template('main.htm', lib=lib, pagedate=datetime.datetime.isoformat(datetime.datetime.today()), status=status, shelves=conf["shelves"])
            # Checkin (close latest transaction)
            if lib[flask.request.form.get('isbn')]['CHECKOUT_STATUS'] == 'checked_out':
                lib[flask.request.form.get('isbn')]['CHECKOUT_STATUS'] = 'checked_in'
                lib[flask.request.form.get('isbn')]['TRANSACTION_DATES'][-1].append(datetime.datetime.today().strftime('%Y-%m-%d'))
                with open('library.yaml', 'w') as library:
                    yaml.safe_dump(lib, library)
                status = "Book '{}' checked in!".format(lib[flask.request.form.get('isbn')]['BOOKNAME'])
                #return flask.redirect('/')
                return flask.render_template('main.htm', lib=lib, pagedate=datetime.datetime.isoformat(datetime.datetime.today()), status=status, shelves=conf["shelves"])
        else:
            status = "Error: ISBN not in library"
            #return flask.redirect('/')
            return flask.render_template('main.htm', lib=lib, pagedate=datetime.datetime.isoformat(datetime.datetime.today()), status=status, shelves=conf["shelves"])

@app.route('/add', methods=['POST'])
def add():
    global status, lib
    # Read stuff from web form
    isbn = flask.request.form.get('isbn_new')
    if (lib != None) and (isbn in lib):
        status = "Error: duplicate ISBN {}".format(isbn)
        return flask.redirect('/')
    bookname = flask.request.form.get('bookname')
    author = flask.request.form.get('author')
    purchase_date = flask.request.form.get('purchase_date')
    purchase_location = flask.request.form.get('purchase_location')
    genre = flask.request.form.get('genre')
    location = flask.request.form.get('location')
    checkout_status = flask.request.form.get('checkout_status')
    transaction_dates =[[datetime.datetime.today().strftime('%Y-%m-%d')]]

    # Initialize library entry
    if lib == None:
        lib = dict()
    lib[isbn] = dict()
    lib[isbn]['BOOKNAME'] = ''
    lib[isbn]['AUTHOR'] = ''
    lib[isbn]['PURCHASE_DATE'] = ''
    lib[isbn]['PURCHASE_LOCATION'] = ''
    lib[isbn]['GENRE'] = ''
    lib[isbn]['LOCATION'] = ''
    lib[isbn]['CHECKOUT_STATUS'] = '-'
    lib[isbn]['TRANSACTION_DATES'] = transaction_dates
    
    # Automatically fetch metadata?
    if conf['isbnlib_fetch_meta'] and ISBNlib_imported:
        try:
            metadata = isbnlib.meta(isbn)
        except isbnlib.NotValidISBNError:
            status = "Error: not valid ISBN"
            lib.pop(isbn)
            return flask.redirect('/')
        lib[isbn]['BOOKNAME'] = metadata['Title']
        bookname = metadata['Title']
        lib[isbn]['AUTHOR'] = ', '.join(metadata['Authors'])
    else:
        lib[isbn]['BOOKNAME'] = bookname
        lib[isbn]['AUTHOR'] = author

    lib[isbn]['PURCHASE_DATE'] = purchase_date
    lib[isbn]['PURCHASE_LOCATION'] = purchase_location
    lib[isbn]['GENRE'] = genre
    lib[isbn]['LOCATION'] = location
    lib[isbn]['CHECKOUT_STATUS'] = checkout_status
    lib[isbn]['TRANSACTION_DATES'] = transaction_dates
    
    with open('library.yaml', 'w') as library:
        yaml.safe_dump(lib, library)
    status = "Book '{}' added!".format(bookname)
    return flask.redirect('/')

@app.route('/stats', methods=['GET'])
def stats():
    global status, lib
    # Load library and calculate stats
    # Pass stats to template
    # Generate graphs
    ## barplot: book name / total transaction count
    ## barplot: book name / checkout intervals
    ## barplot: genre / total transaction count
    ## barplot: genre / transaction count for last month
    ## histogram: time (month) / number of books acquired for each month
    ## histogram: time / total cumulative book count
    pass

if __name__ == '__main__':
    app.run(debug=True)
