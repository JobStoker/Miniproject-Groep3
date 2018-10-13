import csv
from flask import Flask, render_template, url_for, flash, redirect
from forms import RegisterForm, LoginForm

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
                    return redirect(url_for('home'))
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
        writer = csv.DictWriter(myCSVFile, fieldnames=fieldnames)
        writer.writerow({'username': username, 'email': email, 'password': password})
        return True
