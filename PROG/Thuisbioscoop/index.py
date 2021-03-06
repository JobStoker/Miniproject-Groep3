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
import calendar
from flask_qrcode import QRcode

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cecff03f1509d881852c2a9d84276214'
SESSION_TYPE = 'redis'
app.config.from_object(__name__)
QRcode(app)


class StatusDenied(Exception):
    pass


def check_auth(need_type_id=False):
    """
        :param need_type_id: Boolean|int
        :return: None|StatusDenied
    """
    if 'logged_in' not in session or bool(session['logged_in']) is False or 'user_id' not in session or bool(session['user_id']) is False:
        raise StatusDenied
    if need_type_id is not False:
        user_type = get_active_user()['type_id']
        if int(user_type) != int(need_type_id):
            raise StatusDenied


# encrypt a string with sha256
def encrypt_string(hash_string):
    """
        :param hash_string: string
        :return: string
    """
    sha_signature = \
        hashlib.sha256(hash_string.encode()).hexdigest()
    return sha_signature


@app.errorhandler(404)
def page_not_found(e):
    """Renders template 404"""
    return render_template('404.html')


@app.errorhandler(StatusDenied)
def redirect_on_status_denied(error):
    """Redirects to URL"""
    flash("you don't have permision to do that", "danger")
    if 'logged_in' in session and bool(session['logged_in']) is True:
        return redirect('/movies')
    return redirect("/login")


# URL routes
@app.route("/")
def home():
    """Renders template on URL"""
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
    """Clears session and redirects"""
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


@app.route('/accounts')
def accounts():
    """Renders template and passes data"""
    check_auth(1)
    user_accounts = get_user_accounts()
    return render_template('accounts.html', accounts=user_accounts, account_count=len(user_accounts))


@app.route('/account/<account_id>')
def account_login(account_id):
    """Sets session and redirects"""
    session['account_id'] = account_id
    return redirect('movies')


@app.route('/account/create', methods=['GET', 'POST'])
def create_account():
    """Creates user and renders template"""
    check_auth(1)
    form = CreateAccountForm()
    if form.validate_on_submit():
        create_user_account(form.name.data, session['user_id'])
        flash('New account sucsefuly created!', 'success')
        return redirect(url_for('accounts'))
    return render_template('create_account.html', form=form)


@app.route('/movies')
def movies():
    """Renders template based on type_id"""
    check_auth()
    if int(get_active_user()['type_id']) == 1:
        return render_template('user_movies.html', movies=get_user_movies())
    elif int(get_active_user()['type_id']) == 2:
        return render_template('movies.html', movies=get_provided_movies())
    else:
        raise 404


@app.route('/movies/<movie_imdb_id>')
def add_movie(movie_imdb_id):
    """Adds movie to CSV based on type_id and redirects to URL"""
    if int(get_active_user()['type_id']) == 1:
        reserve_movie(movie_imdb_id)
        return redirect('/user_tickets')
    elif int(get_active_user()['type_id']) == 2:
        create_provided_movie(movie_imdb_id)  # TODO Check if realy instat aanbieden
        return redirect('/provided')
    else:
        raise 404


@app.route('/reservations', methods=['GET', 'POST'])
def validate_movie():
    check_auth()
    form = ValidateMovieCodeForm()
    if form.validate_on_submit():
        reserved = get_by_reservation_code(form.code.data)
        if reserved:
            flash('Reservation found', 'success')
        else:
            flash('Reservation not found', 'danger')
            return redirect(url_for('validate_movie'))
    return render_template('reservations.html', form=form, reservations=get_reservations())


@app.route('/provided')
def movie_provided():
    return render_template('provided.html', movies=get_current_provider_movies())


@app.route('/user_tickets')
def user_tickets():
    return render_template('tickets.html', tickets=get_account_tickets())


def get_by_reservation_code(code):
    """
        :param code: Boolean
        :return: List|Boolean
    """
    with open("db/reserved.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['ticket_code'] == code:
                return row
        return False


def get_user_movies():
    """
        get all movies of a user
        :return List
    """
    movies = []
    reserved = []

    with open("db/reserved.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            reserved.append(row['movie_id'])

        with open("db/provider_list.csv", 'r') as myCSVFile:
            rows = csv.DictReader(myCSVFile, delimiter=';')
            for row in rows:
                if row['date'] == datetime.datetime.today().strftime('%d-%m-%Y'):
                    movies.append(row)
            return movies


def get_active_user():
    """
        Get the current logged_in user
        :return: List|Bool
    """
    with open("db/users.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['id'] == session['user_id']:
                return row
    return False


def get_user(user_id):
    """
        Get user by user_id
        :return: List|Bool
    """
    with open("db/users.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['id'] == user_id:
                return row
    return False


def get_account(account_id):
    """
        Get account by account_id
        :return: List|Bool
    """
    with open("db/user_accounts.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['id'] == account_id:
                return row
    return False


def check_user_exists(email):
    """
        Check if the user exists by email
        :param email: string
        :return: Bool|List
    """
    with open("db/users.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['email'] == email:
                return row
    return False


def create_user(username, email, password, type_id):
    """
        Create a user by params
        :param username: string
        :param email: string
        :param password: string
        :param type_id: int
        :return: Boolean
    """
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
    """
        get accounts of the current user
        :return: List
    """
    accounts = []
    with open("db/user_accounts.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['user_id'] == session['user_id']:
                accounts.append(row)
    return accounts


def create_user_account(name, user_id):
    """
        Create a user account
        :param name: string
        :param user_id: int
        :return: Boolean
    """
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
    """
        Get the next id in line by file
        :param filename: string
        :return: int
    """
    with open("db/" + str(filename) + ".csv") as myCSVFile:
        lines = myCSVFile.readlines()
        if len(lines) <= 1:
            return 1
        last_line = lines[len(lines) - 1]
        return int(last_line.split(';')[0]) + 1


def get_movies():
    """
        Get the movies out of the api
        :return: List
    """
    api_url = 'http://api.filmtotaal.nl/filmsoptv.xml?apikey=5r8gfozevu90kas5jb9r0vqksqweujrx&dag=' + datetime.datetime.today().strftime('%d-%m-%Y') + '&sorteer=0'
    response = requests.get(api_url)
    return xmltodict.parse(response.text)


def get_movie(movie_imdb_id):
    """
        Get movie out of the api by imdb_id
        :param movie_imdb_id: int
        :return: list
    """
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
    """
        :return: List
    """
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
            provided_movies.append(movie)
    return provided_movies


def get_provided_movie(imdb_id):
    """
        Get the provided movie by imdb_id
        :param imdb_id: int
        :return: List|Boolean
    """
    with open("db/provider_list.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['imdb_id'] == imdb_id:
                return row
    return False


def reserve_movie(imdb_id):
    """
        Get the reserve movie by imdb_id
        :param imdb_id: int
        :return:
    """
    movie = get_provided_movie(imdb_id)
    with open('db/reserved''.csv', 'a', newline='') as myCSVFile:
        fieldnames = ['id', 'movie_id', 'provider_id', 'user_id', 'account_id', 'ticket_code', 'date',
                      'starttijd', 'eindtijd', 'titel']
        writer = csv.DictWriter(myCSVFile, fieldnames=fieldnames, delimiter=';')

        writer.writerow({
            'id': find_next_id('reserved'),
            'movie_id': movie['id'],
            'provider_id': movie['user_id'],
            'user_id': session['user_id'],
            'account_id': session['account_id'],
            'ticket_code': generate_code(),
            'date': datetime.datetime.today().strftime('%d-%m-%Y'),
            'starttijd': movie['starttijd'],
            'eindtijd': movie['eindtijd'],
            'titel': movie['titel']
        })
    return True

def generate_code():
    """
        Generate a random code
        :return: string
    """
    return ''.join(random.sample(string.ascii_uppercase+string.digits, 8))


def get_reservations():
    """
        Get reservations of the current logged in user
        :return: List
    """
    reservations = []
    with open("db/reserved.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            print(session['user_id'])
            print(row['provider_id'])
            if row['provider_id'] == session['user_id'] and row['date'] == datetime.datetime.today().strftime('%d-%m-%Y'):
                row['name'] = get_account(row['account_id'])['name']
                reservations.append(row)
    return reservations


def get_current_provider_movies():
    """
        Get the current movies of the provider of today
        :return: List
    """
    provided_movies = []
    with open("db/provider_list.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['user_id'] == session['user_id'] and row['date'] == datetime.datetime.today().strftime('%d-%m-%Y'):
                row['users_count'] = get_users_per_movie(row['id'])
                provided_movies.append(row)
    return provided_movies


def get_users_per_movie(provided_id):
    """
        Get user count by movie_id
        :param provided_id: int
        :return: int
    """
    count = 0
    with open("db/reserved.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['movie_id'] == int(provided_id):
                count += 1
        return count


def get_account_tickets():
    """
        Get Tickets of the current account
        :return: List
    """
    tickets = []
    with open("db/reserved.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if session['account_id'] == row['account_id'] and row['date'] == datetime.datetime.today().strftime('%d-%m-%Y'):
                row['provider_name'] = get_user(row['provider_id'])['username']
                tickets.append(row)
        return tickets


def convert_epoch(date):
    """
        Convert epoch timestamp to normal timestamp
        :param date: string
        :return: string
    """
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(date))
