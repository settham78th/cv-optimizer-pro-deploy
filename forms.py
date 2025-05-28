from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from wtforms.widgets import TextArea

class LoginForm(FlaskForm):
    username = StringField('Nazwa użytkownika lub email', validators=[DataRequired()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    remember_me = BooleanField('Zapamiętaj mnie')
    submit = SubmitField('Zaloguj się')

class RegistrationForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[
        DataRequired(), 
        Length(min=3, max=20, message='Nazwa użytkownika musi mieć 3-20 znaków')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('Imię', validators=[Optional(), Length(max=50)])
    last_name = StringField('Nazwisko', validators=[Optional(), Length(max=50)])
    password = PasswordField('Hasło', validators=[
        DataRequired(),
        Length(min=6, message='Hasło musi mieć co najmniej 6 znaków')
    ])
    password2 = PasswordField('Potwierdź hasło', validators=[
        DataRequired(), 
        EqualTo('password', message='Hasła muszą się zgadzać')
    ])
    submit = SubmitField('Zarejestruj się')

class UserProfileForm(FlaskForm):
    first_name = StringField('Imię', validators=[Optional(), Length(max=50)])
    last_name = StringField('Nazwisko', validators=[Optional(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Zapisz zmiany')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Obecne hasło', validators=[DataRequired()])
    new_password = PasswordField('Nowe hasło', validators=[
        DataRequired(),
        Length(min=6, message='Hasło musi mieć co najmniej 6 znaków')
    ])
    new_password2 = PasswordField('Potwierdź nowe hasło', validators=[
        DataRequired(), 
        EqualTo('new_password', message='Hasła muszą się zgadzać')
    ])
    submit = SubmitField('Zmień hasło')