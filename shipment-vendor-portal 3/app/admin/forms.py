"""Admin forms — user creation/editing."""
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SelectField, BooleanField,
                     SubmitField)
from wtforms.validators import DataRequired, Email, Length, Optional


class UserForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=190)])
    role = SelectField("Role", choices=[("admin", "Admin"),
                                        ("staff", "Staff"),
                                        ("vendor", "Vendor")])
    password = PasswordField("Password (leave blank to auto-generate / keep)",
                             validators=[Optional(), Length(min=8, max=128)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save")
