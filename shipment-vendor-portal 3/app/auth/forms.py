"""WTForms used by the auth blueprint."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=190)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=4, max=128)])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign in")


class ForgotForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send reset link")


class ResetForm(FlaskForm):
    password = PasswordField("New password",
                             validators=[DataRequired(), Length(min=8, max=128)])
    confirm = PasswordField("Confirm",
                            validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Update password")


class ChangePasswordForm(FlaskForm):
    current = PasswordField("Current password", validators=[DataRequired()])
    new = PasswordField("New password",
                        validators=[DataRequired(), Length(min=8, max=128)])
    confirm = PasswordField("Confirm",
                            validators=[DataRequired(), EqualTo("new")])
    submit = SubmitField("Change password")
