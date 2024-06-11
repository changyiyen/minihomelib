#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# minihomelib - a simple Flask app for tracking books in a home library

### Import required libs ###

# Prerequisites: flask, flask_login, passlib, bcrypt (pip3 install Flask flask-login passlib)
# (NB.: bcrypt is not directly imported here, but is suggested as a dependency of passlib.hash.bcrypt)
# NB.: Also note that a TOML library is needed further down for creation of new accounts
# (pip install toml) 
import flask
import flask_login
import passlib.hash

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
import urllib.request
import uuid

### Load config, translations, and users passwd file ###
with open('config.toml', 'rb') as configfile:
    conf = tomllib.load(configfile)
with open('ui_translations.toml', 'rb') as translations:
    ui_translations = tomllib.load(translations)
with open('passwd.toml', 'rb') as passwd:
    passwd = tomllib.load(passwd)

### Load initial data ###
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

### Set up Flask app ###
app = flask.Flask(__name__)

# The app will select the appropriate UI language from this list based on the
# HTTP request, but of course the language needs to be *fully supported*
# (at the moment) in ui_translations.toml, otherwise there will be errors due
# to missing values.
# [TODO] Add mechanism for language fallback in case of incomplete translations
supported_languages = ["en", "zh-TW"]

### Set up Flask-Login ###
#!!! Remember to generate a new secret key when deploying anew! !!!#
app.secret_key = 'e86f6a6c4ac73092b059b54194f1239c'
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.login_message = 'Ilogin'

class User(flask_login.UserMixin):
    pass

@login_manager.user_loader
def user_loader(username):
    if username not in passwd:
        return
    
    user = User()
    user.id = username
    return user

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    if username not in passwd:
        return
    
    user = User()
    user.id = username
    return user

# [TODO] Finish 401 handler later
#@login_manager.unauthorized_handler
#def unauthorized_handler():
#    return "Unauthorized", 401

### Add Flask views ###

@app.route('/', methods=['GET','POST'])
@flask_login.login_required
def main():
    global lib
    if flask.request.method == 'GET':
        return flask.render_template('main.htm',
            ui_translations=ui_translations,
            ui_lang=flask.request.accept_languages.best_match(supported_languages),
            lib=lib,
            pagedate=datetime.datetime.today().isoformat('T', 'seconds'),
            shelves=conf["shelves"],
            past_due=int(conf['past_due']),
            new_arrival=int(conf['new_arrival']),
            current_login=flask_login.current_user.id,
            cover_size=conf['openlibrary_cover_size'])
    if flask.request.method == 'POST':
        # Do nothing on empty ISBN or empty library
        if flask.request.form.get('isbn') == '' or len(lib) == 0:
            return flask.redirect('/')
        # Process checkout/checkin if ISBN exists in library
        elif flask.request.form.get('isbn') in lib:
            if ISBNlib_imported:
                if isbnlib.notisbn(flask.request.form.get('isbn')):
                    flask.flash("EinvalidISBN")
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
                    flask.request.form.get('current_user')
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
                flask.flash(ui_translations['Icheckout'][flask.request.accept_languages.best_match(supported_languages)].format(lib[flask.request.form.get('isbn')]['BOOKNAME']))
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
                    flask.request.form.get('current_user')
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

                flask.flash(ui_translations['Icheckin'][flask.request.accept_languages.best_match(supported_languages)].format(lib[flask.request.form.get('isbn')]['BOOKNAME']))
                return flask.redirect('/')
        else:
            flask.flash("EmissingISBN")
            return flask.redirect('/')

@app.route('/add', methods=['POST'])
@flask_login.login_required
def add():
    '''
    Add a book
    '''
    global lib
    t = datetime.datetime.today().isoformat('T', 'seconds')
    
    # Read ISBN from web form
    isbn = flask.request.form.get('isbn_new')
    # Abort if ISBN already in library
    if isbn in lib:
        flask.flash("EduplicateISBN")
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
    lib[isbn]['TRANSACTIONS'] = list()
    lib[isbn]['TRANSACTIONS'].append(
        {
        'TRANSACTION_TYPE': 'check in',
        'TRANSACTION_DATE': t,
        'USERNAME': flask.request.form.get('current_adding_user')
        }
    )
    lib[isbn]['BOOK_STATUS'] = flask.request.form.get('checkout_status')
    lib[isbn]['LAST_TRANSACTION'] = t

    # Automatically fetch metadata? (Fetched metadata overrides manually entered data)
    if conf['isbnlib_fetch_meta'] and ISBNlib_imported:
        try:
            metadata = isbnlib.meta(isbn)
        except isbnlib.NotValidISBNError:
            flask.flash("EinvalidISBN")
            lib.pop(isbn)
            return flask.redirect('/')
        lib[isbn]['BOOKNAME'] = metadata['Title']
        bookname = lib[isbn]['BOOKNAME']
        lib[isbn]['AUTHORS'] = ', '.join(metadata['Authors'])
        lib[isbn]['LANGUAGE'] = metadata['Language']
        lib[isbn]['PUBLISHER'] = metadata['Publisher']
        lib[isbn]['PUBLICATION_YEAR'] = metadata['Year']
    
    # Automatically fetch book cover (from openlibrary.org)
    # [TODO] Add mechanism to re-fetch covers
    if conf['openlibrary_fetch_cover']:
        if conf['openlibrary_cover_size'] not in tuple(["L", "M", "S"]):
            raise ValueError("Book cover size argument incorrectly set")
        with urllib.request.urlopen('https://covers.openlibrary.org/b/isbn/{}-{}.jpg'.format(isbn, conf['openlibrary_cover_size'])) as response:
            cover = response.read()
        with open('static/covers/{}-{}.jpg'.format(isbn, conf['openlibrary_cover_size']), 'wb') as imagefile:
            imagefile.write(cover)
            imagefile.close()
    
    # Write to database
    con = sqlite3.connect(conf["library_db"])
    cur = con.cursor()
    cur.execute("INSERT INTO item_info VALUES(?,?,?,?,?,?,?,?,?,?,?)",
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
        lib[isbn]['HOME_SHELF'],
        str(uuid.uuid4())
        )
    )
    cur.execute("INSERT INTO transactions VALUES(?,?,?,?)",
        (
        flask.request.form.get('isbn_new'),
        "check in",
        t,
        flask.request.form.get('current_adding_user')
        )
    )
    cur.execute("INSERT OR REPLACE INTO book_status (ISBN, status, last_transaction) VALUES (?,?,?)",
        (
        flask.request.form.get('isbn_new'),
        'checked in',
        t
        )
    )    
    con.commit()    
    con.close()

    flask.flash(ui_translations['Iaddbook'][flask.request.accept_languages.best_match(supported_languages)].format(lib[flask.request.form.get('isbn')]['BOOKNAME']))
    return flask.redirect('/')

@app.route('/book/<isbn>')
@flask_login.login_required
def bookinfo(isbn=""):
    # TODO: finish templates for book info (maybe add mechanism for comments)
    global lib
    '''
    Render info page for each book.
    '''
    if flask.request.method == 'GET':
        return flask.render_template('bookinfo.htm',
            ui_translations=ui_translations,
            ui_lang=flask.request.accept_languages.best_match(supported_languages),
            pagedate=datetime.datetime.today().isoformat('T', 'seconds'),
            cover_size=conf['openlibrary_cover_size'])

@app.route('/stats', methods=['GET'])
def stats():
    '''
    Generates stats and charts from reader data.
    '''
    global lib
    
    # [TODO] migrate to reading from SQL

    con = sqlite3.connect(conf["library_db"])
    cur = con.cursor()
    all_users = cur.execute("SELECT DISTINCT user_name FROM transactions;").fetchall()
    all_books = cur.execute("SELECT DISTINCT ISBN, book_name FROM item_info;").fetchall()
    all_checkins = cur.execute("SELECT ISBN, book_name, transaction_date AS checkin_date FROM transactions NATURAL JOIN item_info WHERE transaction_type='check in' ORDER BY transaction_date ASC;").fetchall() 
    all_checkouts = cur.execute("SELECT ISBN, user_name, transaction_date FROM transactions NATURAL JOIN item_info WHERE transaction_type='check out' ORDER BY transaction_date ASC;").fetchall()
    books_by_transactions = cur.execute("SELECT book_name, COUNT(transaction_type) AS transaction_count FROM transactions NATURAL JOIN item_info GROUP BY ISBN ORDER BY COUNT(transaction_type) DESC;").fetchall()
    books_by_checkouts = cur.execute("SELECT book_name, COUNT(transaction_type) AS checkout_count FROM transactions NATURAL JOIN item_info WHERE transaction_type='check out' GROUP BY ISBN ORDER BY COUNT(transaction_type) DESC;").fetchall()
    users_by_transactions = cur.execute("SELECT user_name, COUNT(transaction_type) AS transactions FROM transactions GROUP BY user_name ORDER BY COUNT(transaction_type) DESC;").fetchall()
    users_by_checkouts = cur.execute("SELECT user_name, COUNT(transaction_type) AS checkouts FROM transactions WHERE transaction_type='check out' GROUP BY user_name ORDER BY COUNT(transaction_type) DESC;").fetchall()
    users_by_genre_transactions = cur.execute("SELECT user_name, genres, COUNT(transaction_type) AS checkouts FROM transactions NATURAL JOIN item_info GROUP BY user_name, genres ORDER BY COUNT(transaction_type) DESC;").fetchall()
    users_by_genre_checkouts = cur.execute("SELECT user_name, genres, COUNT(transaction_type) AS checkouts FROM transactions NATURAL JOIN item_info WHERE transaction_type = 'check out' GROUP BY user_name, genres ORDER BY COUNT(transaction_type) DESC;").fetchall()
    con.close()

    ## Checkout session length for each user
    session_lengths = dict()
    for (user,) in all_users:
        session_lengths[user] = list()
    ## Get book with longest known checkout time
    longest_checkout = list([datetime.timedelta(), ''])

    for (isbn, book_name) in all_books:
        if isbn in [x[0] for x in all_checkouts]:
            sessions = list(zip(
                [x[2] for x in all_checkouts if isbn == x[0]],
                # We remove the first checkin because it's the initial storage
                [x[2] for x in all_checkins if isbn == x[0]][1:],
                # User checking out book defined as borrower
                [x[1] for x in all_checkouts if isbn == x[0]]
            ))
            for session in sessions:
                delta = datetime.datetime.strptime(session[1], '%Y-%m-%dT%H:%M:%S') - datetime.datetime.strptime(session[0], '%Y-%m-%dT%H:%M:%S')
                session_lengths[session[2]].append(delta)
                if delta > longest_checkout[0]:
                    longest_checkout[0] = delta
                    # Unlikely that two real transactions would be exactly the same length, down to the second; otherwise the book with the lower ISBN wins
                    longest_checkout[1] = book_name

    ## barplot: book name / total transaction count
    books_by_transactions_plotdata = {
        'x': list([i[0] for i in books_by_transactions]),
        'y': list([i[1] for i in books_by_transactions]),
        'type': 'bar'
    }
    books_by_transactions_plotJSON = json.dumps(books_by_transactions_plotdata)
    
    ## barplot: book name / checkout count
    books_by_checkouts_plotdata = {
        'x': list([i[0] for i in books_by_checkouts]),
        'y': list([i[1] for i in books_by_checkouts]),
        'type': 'bar'
    }
    books_by_checkouts_plotJSON = json.dumps(books_by_checkouts_plotdata)
    
    ## barplot: username / total transaction count
    users_by_transactions_plotdata = {
        'x': list([i[0] for i in users_by_transactions]),
        'y': list([i[1] for i in users_by_transactions]),
        'type': 'bar'
    }
    users_by_transactions_plotJSON = json.dumps(users_by_transactions_plotdata)

    # Generate graphs

    ## barplot: book name / checkout intervals
    ## barplot: genre / total transaction count
    ## barplot: genre / transaction count for last month
    ## histogram: time (month) / number of books acquired for each month
    ## histogram: time / total cumulative book count
    return flask.render_template('stats.htm',
        ui_translations=ui_translations,
        ui_lang=flask.request.accept_languages.best_match(supported_languages),
        pagedate=datetime.datetime.today().isoformat('T', 'seconds'),
        books_by_transactions=books_by_transactions,
        books_by_checkouts=books_by_checkouts,
        longest_checkout=longest_checkout,
        books_by_transactions_plotJSON=books_by_transactions_plotJSON,
        books_by_checkouts_plotJSON=books_by_checkouts_plotJSON,
        users_by_transactions_plotJSON=users_by_transactions_plotJSON
        )

@app.route('/login', methods=['GET', 'POST'])
def login():
    '''
    Log a user if by matching credentials against the passwd file. Here we're using salted bcrypt-hashed passwords, but technically this can be any other algorithm you choose.
    '''
    if flask.request.method == 'GET':
        return flask.render_template('login.htm',
            ui_translations=ui_translations,
            ui_lang=flask.request.accept_languages.best_match(supported_languages)
        )
    if flask.request.method == 'POST':
        username = flask.request.form['username']
        if username in passwd:
            try:
                if passlib.hash.bcrypt.verify(flask.request.form['password'], passwd[username]['password']):
                    user = User()
                    user.id = username
                    flask_login.login_user(user)
                    return flask.redirect('/')
                else:
                    flask.flash("Ebadlogin")
                    return flask.redirect('/login')
            except ValueError:
                # [TODO] Change to another, more informative message
                flask.flash("Ebadlogin")
                return flask.redirect('/login')
        else:
            flask.flash("Ebadlogin")
            return flask.redirect('/login')

@app.route('/adduser', methods=['GET', 'POST'])
def adduser():
    '''
    Add a user to the passwd file. Here we're generating salted bcrypt-hashed passwords, but technically this can be any other algorithm you choose.
    '''
    if flask.request.method == 'GET':
        return flask.render_template('adduser.htm',
            ui_translations=ui_translations,
            ui_lang=flask.request.accept_languages.best_match(supported_languages)
        )
    
    if flask.request.method == 'POST':
        username_new = flask.request.form['username']
        if username_new in passwd:
            flask.flash("Eduplicateusername")
            return flask.redirect('/adduser')
        else:
            passwd[username_new] = dict()
            passwd[username_new]['password'] = passlib.hash.bcrypt.hash(flask.request.form['password'])
            with open('passwd.toml', 'w') as passwdfile:
                # Annoyingly, the TOML library in the standard library doesn't support writing TOML files (yet), so we have to use an external library
                import toml
                toml.dump(passwd, passwdfile)
            flask.flash("Iregistersuccess")
            return flask.redirect('/login')

@app.route('/logout')
def logout():
    flask_login.logout_user()
    flask.flash("Iloggedout")
    return flask.redirect('/')

@app.errorhandler(404)
def page_not_found(error):
    return flask.render_template('404.htm',
        ui_translations=ui_translations,
        ui_lang=flask.request.accept_languages.best_match(supported_languages)
    ), 404

if __name__ == '__main__':
    app.run(debug=True)
