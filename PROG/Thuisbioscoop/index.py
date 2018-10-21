from flask import Flask, render_template, url_for, flash, redirect, session
from forms import RegisterForm, LoginForm, CreateAccountForm, ValidateMovieCodeForm
from werkzeug.security import generate_password_hash
import csv
import requests
import xmltodict
import datetime
import os
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cecff03f1509d881852c2a9d84276214'
SESSION_TYPE = 'redis'
app.config.from_object(__name__)


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


@app.errorhandler(StatusDenied)
def redirect_on_status_denied(error):
    flash("you don't have premision to do that", "danger")
    return redirect("login")


# URL routes
@app.route("/")
def home():
    return render_template('home.html')


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
        return render_template('user_movies.html', movies=get_user_movies())
    elif int(get_active_user()['type_id']) == 2:
        return render_template('movies.html', movies=get_provided_movies())
    else:
        print('error')
        # TODO 404 error


@app.route('/movies/<movie_imdb_id>')
def add_movie(movie_imdb_id):
    check_auth()
    if int(get_active_user()['type_id']) == 1:
        print('xxx')  # TODO MAKE RESERVATION!!!
        return 'TODO'
    elif int(get_active_user()['type_id']) == 2:
        create_provided_movie(movie_imdb_id)  # TODO Check if realy instat aanbieden
        return render_template('addmovie.html', movie=get_movie(movie_imdb_id))
    else:
        print('error')
        # TODO 404 error


@app.route('/validate/movie', methods=['GET', 'POST'])
def validate_movie():
    check_auth()  # TODO ONLY USER_TYPE_1
    form = ValidateMovieCodeForm()
    if form.validate_on_submit():
        print('x')
    return render_template('validate_movie.html', form=form)









def get_user_movies():
    accounts = []
    with open("db/provider_list.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            # if row['user_id'] == session['user_id']: # TODO RULES only movies today ect....
            accounts.append(row)
        return accounts


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
        })  # TODO DATE OF BIRTH if needed idk if we want to do this or anything like this
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
                      'imdb_votes', 'starttijd', 'eindtijd', 'zender', 'filmtip']
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
            'starttijd': movie['starttijd'],
            'eindtijd': movie['eindtijd'],
            'zender': movie['zender'],
            'filmtip': movie['filmtip']
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
            provided_movies.append(movie)
    return provided_movies
