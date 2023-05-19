#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Prerequisites: flask (pip3 install Flask)
import flask

# Suggested: isbnlib (pip3 install isbnlib)
try:
    import isbnlib
    ISBNlib_imported = True
except ImportError:
    ISBNlib_imported = False

# Built-ins
import datetime
import json
import sqlite3
import sys
import tomllib

with open('config.toml', 'rb') as configfile:
    conf = tomllib.load(configfile)

with open('ui_translations.toml', 'rb') as translations:
    ui_translations = tomllib.load(translations)

# Load initial data
lib = dict()
con = sqlite3.connect(conf["library_db"])
cur = con.cursor()
item_data = cur.execute("SELECT ISBN, book_name, authors, language, publisher, publication_year, genres, acquisition_date, acquisition_location, home_shelf FROM item_info;").fetchall()
transaction_data = cur.execute("SELECT ISBN, transaction_type, transaction_date, user_name FROM transactions;").fetchall()
book_status = cur.execute("SELECT ISBN, status, last_transaction FROM book_status").fetchall()
con.close()
for row in item_data:
    lib[row[0]] = {
        "BOOKNAME": row[1],
        "AUTHORS": row[2],
        "LANGUAGE": row[3],
        "PUBLISHER": row[4],
        "PUBLICATION_YEAR": row[5],
        "GENRES": row[6],
        "ACQUISITION_DATE": row[7],
        "ACQUISITION_LOCATION": row[8],
        "HOME_SHELF": row[9],
    }
for row in transaction_data:
    lib[row[0]]["TRANSACTIONS"] = list()
for row in transaction_data:
    lib[row[0]]["TRANSACTIONS"].append(
        {
        "TRANSACTION_TYPE": row[1],
        "TRANSACTION_DATE": row[2],
        "USERNAME": row[3]
        }
    )
for row in book_status:
    lib[row[0]]["BOOK_STATUS"] = row[1]
    lib[row[0]]["LAST_TRANSACTION"] = row[2]

app = flask.Flask(__name__)
status = ""
supported_languages = ["en", "zh-TW"]

@app.route('/', methods=['GET','POST'])
def main():
    global status, lib
    if flask.request.method == 'GET':
        return flask.render_template('main.htm',
            ui_translations=ui_translations,
            ui_lang=flask.request.accept_languages.best_match(supported_languages),
            lib=lib,
            pagedate=datetime.datetime.today().isoformat('T', 'seconds'),
            status=status,
            shelves=conf["shelves"],
            past_due=int(conf['past_due']))
    if flask.request.method == 'POST':
        # Do nothing on empty ISBN or empty library
        if flask.request.form.get('isbn') == '' or len(lib) == 0:
            return flask.redirect('/')
        # Process checkout/checkin if ISBN exists in library
        elif flask.request.form.get('isbn') in lib:
            if ISBNlib_imported:
                if isbnlib.notisbn(flask.request.form.get('isbn')):
                    status = "Error: not valid ISBN"
                    return flask.redirect('/')
            # Checkout
            if lib[flask.request.form.get('isbn')]['BOOK_STATUS'] == 'checked in':
                # First change internal representation (lib)
                lib[flask.request.form.get('isbn')]['BOOK_STATUS'] = 'checked out'
                # Then write to database
                con = sqlite3.connect(conf["library_db"])
                cur = con.cursor()
                t = datetime.datetime.today().isoformat('T', 'seconds')
                cur.execute("INSERT INTO transactions VALUES(?,?,?,?)",
                    (
                    flask.request.form.get('isbn'),
                    "check out",
                    t,
                    flask.request.form.get('username')
                    )
                )
                cur.execute("UPDATE book_status SET status = 'checked out', last_transaction = (?) WHERE ISBN = (?)",
                    (
                    t,
                    flask.request.form.get('isbn')
                    )
                )               
                con.commit()
                con.close()
                status = "Book '{}' checked out!".format(lib[flask.request.form.get('isbn')]['BOOKNAME'])
                return flask.redirect('/')
            # Checkin
            if lib[flask.request.form.get('isbn')]['BOOK_STATUS'] == 'checked out':
                # First change internal representation (lib)
                lib[flask.request.form.get('isbn')]['BOOK_STATUS'] = 'checked in'
                # Then write to database
                con = sqlite3.connect(conf["library_db"])
                cur = con.cursor()
                t = datetime.datetime.today().isoformat('T', 'seconds')
                cur.execute("INSERT INTO transactions VALUES(?,?,?,?)",
                    (
                    flask.request.form.get('isbn'),
                    "check in",
                    t,
                    flask.request.form.get('username')
                    )
                )
                cur.execute("UPDATE book_status SET status = 'checked in', last_transaction = (?) WHERE ISBN = (?)",
                    (
                    t,
                    flask.request.form.get('isbn')
                    )
                )
                con.commit()
                con.close()
                status = "Book '{}' checked in!".format(lib[flask.request.form.get('isbn')]['BOOKNAME'])
                return flask.redirect('/')
        else:
            status = "Error: ISBN not in library"
            return flask.redirect('/')

@app.route('/add', methods=['POST'])
def add():
    global status, lib
    t = datetime.datetime.today().isoformat('T', 'seconds')
    
    # Read ISBN from web form
    isbn = flask.request.form.get('isbn_new')
    # Abort if ISBN already in library
    if isbn in lib:
        status = "Error: duplicate ISBN {}".format(isbn)
        return flask.redirect('/')

    # Create library entry in internal representation
    lib[isbn] = dict()
    lib[isbn]['BOOKNAME'] = flask.request.form.get('bookname')
    lib[isbn]['AUTHORS'] = flask.request.form.get('author')
    lib[isbn]['LANGUAGE'] = ''
    lib[isbn]['PUBLISHER'] = ''
    lib[isbn]['PUBLICATION_YEAR'] = ''
    lib[isbn]['GENRES'] = flask.request.form.get('genre')
    lib[isbn]['ACQUISITION_DATE'] = flask.request.form.get('acquisition_date')
    lib[isbn]['ACQUISITION_LOCATION'] = flask.request.form.get('acquisition_location')
    lib[isbn]['HOME_SHELF'] = flask.request.form.get('location')
    lib[isbn]['TRANSACTIONS'].append(
        {
        'TRANSACTION_TYPE': 'check in',
        'TRANSACTION_DATE': t,
        'USERNAME': flask.request.form.get('username')
        }
    )
    lib[isbn]['BOOK_STATUS'] = flask.request.form.get('checkout_status')
    lib[isbn]['LAST_TRANSACTION'] = t

    # Automatically fetch metadata? (Fetched metadata overrides manually entered data)
    if conf['isbnlib_fetch_meta'] and ISBNlib_imported:
        try:
            metadata = isbnlib.meta(isbn)
        except isbnlib.NotValidISBNError:
            status = "Error: not valid ISBN"
            lib.pop(isbn)
            return flask.redirect('/')
        lib[isbn]['BOOKNAME'] = metadata['Title']
        lib[isbn]['AUTHORS'] = ', '.join(metadata['Authors'])
        lib[isbn]['LANGUAGE'] = metadata['Language']
        lib[isbn]['PUBLISHER'] = metadata['Publisher']
        lib[isbn]['PUBLICATION_YEAR'] = metadata['Year']

    # Write to database
    con = sqlite3.connect(conf["library_db"])
    cur = con.cursor()
    cur.execute("INSERT INTO item_info VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
        isbn,
        lib[isbn]['BOOKNAME'],
        lib[isbn]['AUTHORS'],
        lib[isbn]['LANGUAGE'],
        lib[isbn]['PUBLISHER'],
        lib[isbn]['PUBLICATION_YEAR'],
        lib[isbn]['GENRES'],
        lib[isbn]['ACQUISITION_DATE'],
        lib[isbn]['ACQUISITION_LOCATION'],
        lib[isbn]['HOME_SHELF']
        )
    )
    cur.execute("INSERT INTO transactions VALUES(?,?,?,?)",
        (
        flask.request.form.get('isbn'),
        "check in",
        t,
        flask.request.form.get('username')
        )
    )
    cur.execute("UPDATE book_status SET status = 'checked in', last_transaction = (?) WHERE ISBN = (?)",
        (
        t,
        isbn
        )
    )    
    con.commit()    
    con.close()

    status = "Book '{}' added!".format(bookname)
    return flask.redirect('/')

@app.route('/stats', methods=['GET'])
def stats():
    global status, lib
    # This function is supposed to *only* read data to calculate stats, so
    # we're reading from the internal representation;
    # *take care not to modify the internal representation!*

    ## Get books with highest number of transactions (checkin + checkout)
    transaction_counts = list([0,list()])
    
    for isbn in lib:
        transactions = len(lib[isbn]['TRANSACTIONS'])
        if transactions > transaction_counts[0]:
            transaction_counts[0] = transactions
            transaction_counts[1] = [lib[isbn]['BOOKNAME']]
        elif transactions == transaction_counts[0]:
            transaction_counts[1].append(lib[isbn]['BOOKNAME'])
        
    ## Get book with longest known checkout time
    longest_checkout = list([datetime.timedelta(), ''])
    for isbn in lib:
        sessions = list(zip(
            [transaction['TRANSACTION_DATE'] for transaction in lib[isbn]['TRANSACTIONS'] if transaction['TRANSACTION_TYPE'] == 'check in'],
            [transaction['TRANSACTION_DATE'] for transaction in lib[isbn]['TRANSACTIONS'] if transaction['TRANSACTION_TYPE'] == 'check out']
        ))
        for session in sessions:
            delta = datetime.datetime.strptime(session[1], '%Y-%m-%dT%H:%M:%S') - datetime.datetime.strptime(session[0], '%Y-%m-%dT%H:%M:%S')
            if delta > longest_checkout[0]:
                longest_checkout[0] = delta
                # Unlikely that two real transactions would be exactly the same length, down to the second
                longest_checkout[1] = lib[isbn]['BOOKNAME']

    ## Build data for bar plot of bookname/transaction counts
    transaction_counts_plotdata = [
        {
            'data': [
              {
                'x': list([lib[isbn]['BOOKNAME'] for isbn in lib]),
                'y': list([len(lib[isbn]['TRANSACTIONS']) for isbn in lib]),
                'type': 'bar'}
            ]
        }
    ]

    transaction_counts_plotJSON = json.dumps(transaction_counts_plotdata)

    # Generate graphs
    ## barplot: book name / total transaction count
    ## barplot: book name / checkout intervals
    ## barplot: genre / total transaction count
    ## barplot: genre / transaction count for last month
    ## histogram: time (month) / number of books acquired for each month
    ## histogram: time / total cumulative book count
    return flask.render_template('stats.htm',
        ui_translations=ui_translations,
        ui_lang=flask.request.accept_languages.best_match(supported_languages),
        pagedate=datetime.datetime.today().isoformat('T', 'seconds'),
        status=status,
        transaction_counts=transaction_counts,
        longest_checkout=longest_checkout,
        transaction_counts_plotJSON=transaction_counts_plotJSON)

if __name__ == '__main__':
    app.run(debug=True)
