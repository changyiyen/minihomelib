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

with open('config.yaml', 'r') as configfile:
    conf = yaml.safe_load(configfile)

with open('library.yaml', 'r') as library:
    lib = yaml.safe_load(library)

app = flask.Flask(__name__)
status = ""

@app.route('/', methods=['GET','POST'])
def main():
    global status
    if flask.request.method == 'GET':
        return flask.render_template('main.htm', lib=lib, pagedate=datetime.datetime.isoformat(datetime.datetime.today()), status=status, past_due=int(conf['past_due']))
    if flask.request.method == 'POST':
        # Do nothing on empty ISBN
        if flask.request.form.get('isbn') == '':
            return flask.render_template('main.htm', lib=lib, pagedate=datetime.datetime.isoformat(datetime.datetime.today()), status=status)
        elif flask.request.form.get('isbn') in lib:
            #if ISBNlib_imported:
            #    if isbnlib.notisbn(flask.request.form.get('isbn')):
            #        status = ""Error: not valid ISBN""
            #        return flask.render_template('main.htm', lib=lib, pagedate=datetime.datetime.isoformat(datetime.datetime.today()), status=status)
            # Checkout (start new transaction)
            if lib[flask.request.form.get('isbn')]['CHECKOUT_STATUS'] == 'checked_in':
                lib[flask.request.form.get('isbn')]['CHECKOUT_STATUS'] = 'checked_out'
                lib[flask.request.form.get('isbn')]['TRANSACTION_DATES'].append([datetime.datetime.today().strftime('%Y-%m-%d')])
                with open('library.yaml', 'w') as library:
                    yaml.safe_dump(lib, library)
                status = "Book '{}' checked out!".format(lib[flask.request.form.get('isbn')]['BOOKNAME'])
                return flask.render_template('main.htm', lib=lib, pagedate=datetime.datetime.isoformat(datetime.datetime.today()), status=status)
            # Checkin (close latest transaction)
            if lib[flask.request.form.get('isbn')]['CHECKOUT_STATUS'] == 'checked_out':
                lib[flask.request.form.get('isbn')]['CHECKOUT_STATUS'] = 'checked_in'
                lib[flask.request.form.get('isbn')]['TRANSACTION_DATES'][-1].append(datetime.datetime.today().strftime('%Y-%m-%d'))
                with open('library.yaml', 'w') as library:
                    yaml.safe_dump(lib, library)
                status = "Book '{}' checked in!".format(lib[flask.request.form.get('isbn')]['BOOKNAME'])
                return flask.render_template('main.htm', lib=lib, pagedate=datetime.datetime.isoformat(datetime.datetime.today()), status=status)
        else:
            status = "Error: ISBN not in library"
            return flask.render_template('main.htm', lib=lib, pagedate=datetime.datetime.isoformat(datetime.datetime.today()), status=status)

@app.route('/add', methods=['POST'])
def add():
    global status
    # Read stuff from web form
    isbn = flask.request.form.get('isbn_new')
    if isbn in lib:
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
    if conf['isbnlib_fetch_meta']:
        try:
            metadata = isbnlib.meta(isbn)
        except isbnlib.NotValidISBNError:
            status = "Error: not valid ISBN"
            lib.pop(isbn)
            return flask.redirect('/')
        lib[isbn]['BOOKNAME'] = metadata['Title']
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

if __name__ == '__main__':
    app.run(debug=True)
