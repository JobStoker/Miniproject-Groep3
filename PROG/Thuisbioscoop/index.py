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


@app.route("/register")
def register():
    return render_template('register.html')
