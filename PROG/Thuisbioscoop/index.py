from flask import Flask, render_template, url_for, flash, redirect, session
#from flask.ext.qrcode import QRcode
from forms import RegisterForm, LoginForm, CreateAccountForm, ValidateMovieCodeForm
from werkzeug.security import generate_password_hash
import csv
import requests
import xmltodict
import datetime
import os
import hashlib
import random
import string
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cecff03f1509d881852c2a9d84276214'
SESSION_TYPE = 'redis'
app.config.from_object(__name__)
#QRcode(app)


class StatusDenied(Exception):
    pass


def check_auth():
    if 'logged_in' not in session or bool(session['logged_in']) is False or 'user_id' not in session or bool(session['user_id']) is False:
        raise StatusDenied


# encrypt a string with sha256
def encrypt_string(hash_string):
    sha_signature = \
        hashlib.sha256(hash_string.encode()).hexdigest()
    return sha_signature


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html')  # TODO layout


@app.errorhandler(StatusDenied)
def redirect_on_status_denied(error):
    flash("you don't have premision to do that", "danger")
    return redirect("/login")


# URL routes
@app.route("/")
def home():
    return redirect('/login')


@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with open("db/users.csv", 'r') as myCSVFile:
            rows = csv.DictReader(myCSVFile, delimiter=';')
            for row in rows:
                if row['email'] == form.email.data and row['password'] == encrypt_string(form.password.data):
                    session['user_type_id'] = row['type_id']
                    session['user_id'] = row['id']
                    session['logged_in'] = True
                    flash('You have been logged in!', 'success')
                    if int(row['type_id']) == 1:
                        return redirect('accounts')
                    elif int(row['type_id']) == 2:
                        return redirect('movies')
            flash('No valid user and password!', 'danger')

    return render_template('login.html', form=form)


@app.route("/logout")
def logout():
    session.clear()
    return redirect('login')


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = check_user_exists(form.email.data)
        if user is False:
            create_user(form.username.data, form.email.data, form.password.data, form.type_id.data)
            flash('Account added!', 'success')
            return redirect(url_for('login'))
        else:
            flash('This mail address is already in use', 'danger')
    return render_template('register.html', form=form)


# TODO NICE TEMPLATE
@app.route('/accounts')
def accounts():
    check_auth()
    user_accounts = get_user_accounts()
    return render_template('accounts.html', accounts=user_accounts, account_count=len(user_accounts))


@app.route('/account/<account_id>')
def account_login(account_id):
    session['account_id'] = account_id
    return redirect('movies')


# TODO NICE TEMPLATE
@app.route('/account/create', methods=['GET', 'POST'])
def create_account():
    check_auth()
    form = CreateAccountForm()
    if form.validate_on_submit():
        create_user_account(form.name.data, session['user_id'])
        flash('New account sucsefuly created!', 'success')
        return redirect(url_for('accounts'))
    return render_template('create_account.html', form=form)


# TODO WEERGAVE
@app.route('/movies')
def movies():
    check_auth()
    if int(get_active_user()['type_id']) == 1:
        return render_template('user_movies.html', movies=get_user_movies(), tickets=get_user_tickets())
    elif int(get_active_user()['type_id']) == 2:
        return render_template('movies.html', movies=get_provided_movies())
    else:
        raise 404


@app.route('/movies/<movie_imdb_id>')
def add_movie(movie_imdb_id):
    check_auth()
    if int(get_active_user()['type_id']) == 1:
        reserve_movie(movie_imdb_id)
        return render_template('tickets.html')
    elif int(get_active_user()['type_id']) == 2:
        create_provided_movie(movie_imdb_id)  # TODO Check if realy instat aanbieden
        return redirect('/provided')
    else:
        raise 404


@app.route('/reservations', methods=['GET', 'POST'])
def validate_movie():
    check_auth()  # TODO ONLY USER_TYPE_1
    form = ValidateMovieCodeForm()
    if form.validate_on_submit():
        reserved = get_by_reservation_code(form.code.data)
        if reserved:
            flash('Reservation found', 'success')
            return 'found'  # TODO return something a page or anything like that
        else:
            flash('Reservation not found', 'danger')
            return redirect(url_for('validate_movie'))
    return render_template('reservations.html', form=form, reservations=get_reservations())


@app.route('/provided')
def movie_provided():
    return render_template('provided.html', movies=get_current_provider_movies())


@app.route('/user_tickets')
def user_tickets():
    return render_template('tickets.html', tickets=get_user_tickets())


@app.route('/user_tickets/<ticket_code>')
def user_ticket():
    return render_template('tickets.html', tickets=get_user_ticket())


def get_by_reservation_code(code):
    with open("db/reserved.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['ticket_code'] == code:
                return row
        return False


def get_user_movies():
    movies = []
    reserved = []

    with open("db/reserved.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            reserved.append(row['user_id'] + row['movie_id'])

        with open("db/provider_list.csv", 'r') as myCSVFile:
            rows = csv.DictReader(myCSVFile, delimiter=';')
            for row in rows:
                if row['date'] == datetime.datetime.today().strftime('%d-%m-%Y') and session['user_id'] + row['id'] not in reserved:
                    movies.append(row)
            return movies


def get_active_user():
    with open("db/users.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['id'] == session['user_id']:
                return row
    return False


def get_user(user_id):
    with open("db/users.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['id'] == user_id:
                return row
    return False


def get_account(account_id):
    with open("db/user_accounts.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['id'] == account_id:
                return row
    return False


def check_user_exists(email):
    with open("db/users.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        print(rows)
        for row in rows:
            if row['email'] == email:
                return row
    return False


def create_user(username, email, password, type_id):
    with open('db/users.csv', 'a', newline='') as myCSVFile:
        fieldnames = ['id', 'username', 'email', 'password', 'type_id']
        writer = csv.DictWriter(myCSVFile, fieldnames=fieldnames, delimiter=';')
        user_id = find_next_id('users')
        writer.writerow({
            'id': user_id,
            'username': username,
            'email': email,
            'password': encrypt_string(password),
            'type_id': type_id
        })
        create_user_account(username, user_id)
    return True


def get_user_accounts():
    accounts = []
    with open("db/user_accounts.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['user_id'] == session['user_id']:
                accounts.append(row)
    return accounts


def create_user_account(name, user_id):
    with open('db/user_accounts.csv', 'a', newline='') as myCSVFile:
        fieldnames = ['id', 'name', 'user_id', 'date_of_birth']
        writer = csv.DictWriter(myCSVFile, fieldnames=fieldnames, delimiter=';')
        writer.writerow({
            'id': find_next_id('user_accounts'),
            'name': name,
            'user_id': user_id,
            'date_of_birth': ''
        })
        return True


def find_next_id(filename):
    with open("db/" + str(filename) + ".csv") as myCSVFile:
        lines = myCSVFile.readlines()
        if len(lines) <= 1:
            return 1
        last_line = lines[len(lines) - 1]
        return int(last_line.split(';')[0]) + 1


def get_movies():
    api_url = 'http://api.filmtotaal.nl/filmsoptv.xml?apikey=5r8gfozevu90kas5jb9r0vqksqweujrx&dag=' + datetime.datetime.today().strftime('%d-%m-%Y') + '&sorteer=0'
    response = requests.get(api_url)
    return xmltodict.parse(response.text)


def get_movie(movie_imdb_id):
    movies = get_movies()
    for movie in movies['filmsoptv']['film']:
        if movie['imdb_id'] == movie_imdb_id:
            return movie


def create_provided_movie(movie_imdb_id):
    movie = get_movie(movie_imdb_id)
    with open('db/provider_list.csv', 'a', newline='') as myCSVFile:
        fieldnames = ['id', 'user_id', 'ft_link', 'titel', 'jaar', 'regisseur', 'cast', 'genre', 'land', 'cover',
                      'tagline', 'duur', 'synopsis', 'ft_rating', 'ft_votes', 'imdb_id', 'imdb_rating',
                      'imdb_votes', 'starttijd', 'eindtijd', 'zender', 'filmtip', 'date']
        writer = csv.DictWriter(myCSVFile, fieldnames=fieldnames, delimiter=';')

        writer.writerow({
            'id': find_next_id('provider_list'),
            'user_id': session['user_id'],
            'ft_link': movie['ft_link'],
            'titel': movie['titel'],
            'jaar': movie['jaar'],
            'regisseur': movie['regisseur'],
            'cast': movie['cast'],
            'genre': movie['genre'],
            'land': movie['land'],
            'cover': movie['cover'],
            'tagline': movie['tagline'],
            'duur': movie['duur'],
            'synopsis': movie['synopsis'],
            'ft_rating': movie['ft_rating'],
            'ft_votes': movie['ft_votes'],
            'imdb_id': movie['imdb_id'],
            'imdb_rating': movie['imdb_rating'],
            'imdb_votes': movie['imdb_votes'],
            'starttijd': convert_epoch(int(movie['starttijd'])),
            'eindtijd': convert_epoch(int(movie['eindtijd'])),
            'zender': movie['zender'],
            'filmtip': movie['filmtip'],
            'date': datetime.datetime.today().strftime('%d-%m-%Y')
        })
    return True


def get_provided_movies():
    movies = get_movies()
    imdb_ids = []
    provided_movies = []
    with open("db/provider_list.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            imdb_ids.append(row['imdb_id'])
    for movie in movies['filmsoptv']['film']:
        if movie['imdb_id'] not in imdb_ids:
            movie['starttijd'] = convert_epoch(int(movie['starttijd']))
            movie['eindtijd'] = convert_epoch(int(movie['eindtijd']))
            print(movie['starttijd'])
            provided_movies.append(movie)
    return provided_movies


def get_provided_movie(imdb_id):
    with open("db/provider_list.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['imdb_id'] == imdb_id:
                return row
    return False


def reserve_movie(imdb_id):
    movie = get_provided_movie(imdb_id)
    reserved = []

    with open('db/reserved''.csv', 'r', newline='') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')

        for row in rows:
            reserved.append(row['user_id'] + row['movie_id'])

        if session['user_id'] + movie['id'] not in reserved:

            with open('db/reserved''.csv', 'a', newline='') as myCSVFile:
                fieldnames = ['id', 'movie_id', 'provider_id', 'user_id', 'account_id', 'ticket_code', 'date', 'starttijd', 'eindtijd', 'titel']
                writer = csv.DictWriter(myCSVFile, fieldnames=fieldnames, delimiter=';')

                writer.writerow({
                    'id': find_next_id('reserved'),
                    'movie_id':     movie['id'],
                    'provider_id':  movie['user_id'],
                    'user_id':   session['user_id'],
                    'account_id':   session['account_id'],
                    'ticket_code':  generate_code(),
                    'date':         datetime.datetime.today().strftime('%d-%m-%Y'),
                    'starttijd':    convert_epoch(int(movie['starttijd'])),
                    'eindtijd':     convert_epoch(int(movie['eindtijd'])),
                    'titel':        movie['titel']
                })
        else:
            print("Staat er al in")

    return True

def generate_code():
    return ''.join(random.sample(string.ascii_uppercase+string.digits, 8))

def get_reservations():
    reservations = []
    with open("db/reserved.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['provider_id'] == session['user_id'] and row['date'] == datetime.datetime.today().strftime('%d-%m-%Y'):
                reservations.append(row)
    return reservations


def get_current_provider_movies():
    provided_movies = []
    with open("db/provider_list.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            print(row['user_id'] + session['user_id'])
            if row['user_id'] == session['user_id'] and row['date'] == datetime.datetime.today().strftime('%d-%m-%Y'):
                provided_movies.append(row)
    return provided_movies


def get_provider_history():
    movie_history = []
    with open("db/provider_list.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['id'] == session['user_id'] and row['date'] != datetime.datetime.today().strftime('%d-%m-%Y'):
                movie_history.append(row)
    return provided_movies


def get_user_tickets():
    tickets = []

    with open("db/reserved.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if session['user_id'] == row['user_id'] and row['date'] == datetime.datetime.today().strftime('%d-%m-%Y'):
                print(row)
                tickets.append(row)
        return tickets


def convert_epoch(date):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(date))


def get_user_ticket():
    print('asd')