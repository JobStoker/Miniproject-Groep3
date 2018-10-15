from flask import Flask, render_template, url_for, flash, redirect, session
from forms import RegisterForm, LoginForm, CreateAccountForm
import csv
import requests
import xmltodict
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cecff03f1509d881852c2a9d84276214'
SESSION_TYPE = 'redis'
app.config.from_object(__name__)


def check_auth():
    if 'logged_in' not in session or not session['logged_in']:
        flash("you don't have premision to do that")
        return redirect(url_for('home'))


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
                if row['email'] == form.email.data and row['password'] == form.password.data:
                    session['user_id'] = row['id']
                    session['logged_in'] = True
                    flash('You have been logged in!', 'success')
                    return redirect('accounts')
        flash('No valid user and password!', 'danger')

    return render_template('login.html', form=form)


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = check_user_exists(form.email.data)
        if user is False:
            create_user(form.username.data, form.email.data, form.password.data)
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
        create_user_account(form.name.data)
        flash('New account sucsefuly created!', 'success')
        return redirect(url_for('accounts'))
    return render_template('create_account.html', form=form)


# TODO WEERGAVE
@app.route('/movies')
def movies():
    check_auth()
    return render_template('movies.html', movies=get_movies())


@app.route('/movies/<movie_imdb_id>', methods=['GET', 'POST'])
def add_movie(movie_imdb_id):
    check_auth()
    create_provided_movie(movie_imdb_id)
    return render_template('addmovie.html', movie=get_movie(movie_imdb_id))
















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


def create_user(username, email, password):
    with open('db/users.csv', 'a', newline='') as myCSVFile:
        fieldnames = ['id', 'username', 'email', 'password']
        writer = csv.DictWriter(myCSVFile, fieldnames=fieldnames, delimiter=';')
        writer.writerow({'id': find_next_id('users'), 'username': username, 'email': email, 'password': password})
        create_user_account(username)
        return True


def get_user_accounts():
    accounts = []
    with open("db/user_accounts.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            if row['user_id'] == session['user_id']:
                accounts.append(row)
    return accounts


def create_user_account(name):
    with open('db/user_accounts.csv', 'a', newline='') as myCSVFile:
        fieldnames = ['id', 'name', 'user_id', 'date_of_birth']
        writer = csv.DictWriter(myCSVFile, fieldnames=fieldnames, delimiter=';')
        writer.writerow({
            'id': find_next_id('user_accounts'),
            'name': name,
            'user_id': session['user_id'],
            'date_of_birth': ''
        })  # TODO DATE OF BIRTH
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