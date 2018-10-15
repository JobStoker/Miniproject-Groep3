import csv
from flask import Flask, render_template, url_for, flash, redirect
from forms import RegisterForm, LoginForm, CreateAccountForm
import requests
import xmltodict
import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = 'cecff03f1509d881852c2a9d84276214'


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
    accounts = get_user_accounts()   # TODO with id or mail?
    return render_template('accounts.html', accounts=accounts)


# TODO NICE TEMPLATE
@app.route('/account/create', methods=['GET', 'POST'])
def create_account():
    form = CreateAccountForm()
    if form.validate_on_submit():
        create_user_account(form.name.data)
        flash('New account sucsefuly created!', 'success')
        return redirect(url_for('accounts'))
    return render_template('create_account.html', form=form)

# TODO WEERGAVE
@app.route('/movies')
def movies():
    movies = get_movies()
    return render_template('movies.html', movies=movies)

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
        fieldnames = ['username', 'email', 'password']
        writer = csv.DictWriter(myCSVFile, fieldnames=fieldnames, delimiter=';')
        writer.writerow({'username': username, 'email': email, 'password': password})
        create_user_account(username)
        return True


def get_user_accounts():  # TODO with id or mail?
    accounts = []
    with open("db/user_accounts.csv", 'r') as myCSVFile:
        rows = csv.DictReader(myCSVFile, delimiter=';')
        for row in rows:
            # if row['email'] == email: # TODO with id or mail?
            accounts.append(row)
    return accounts


def create_user_account(name):  # TODO with id or mail?
    with open('db/user_accounts.csv', 'a', newline='') as myCSVFile:
        fieldnames = ['name', 'date_of_birth']
        writer = csv.DictWriter(myCSVFile, fieldnames=fieldnames, delimiter=';')
        writer.writerow({'name': name, 'date_of_birth': ''}) # TODO DATE OF BIRTH
        return True

def get_movies():
    api_url = 'http://api.filmtotaal.nl/filmsoptv.xml?apikey=5r8gfozevu90kas5jb9r0vqksqweujrx&dag=' + datetime.datetime.today().strftime('%d-%m-%Y') + '&sorteer=0'
    response = requests.get(api_url)
    xml = xmltodict.parse(response.text)

    return xml