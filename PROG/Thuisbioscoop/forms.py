from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo


class RegisterForm(FlaskForm):
    """Form validation for the register form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    type_id = SelectField('Account type', choices=[('1', 'Huurder'), ('2', 'Aanbieder')], validators=[DataRequired()])
    submit = SubmitField('Sign Up')


class LoginForm(FlaskForm):
    """Form validation for the login form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class CreateAccountForm(FlaskForm):
    """Form validation for the create account form"""
    name = StringField('name', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('Aanmaken')


class ValidateMovieCodeForm(FlaskForm):
    """Form validation for the Validate movie form"""
    code = StringField('Ticket Code validatie', validators=[DataRequired()])
    submit = SubmitField('Ticket Code checken')
