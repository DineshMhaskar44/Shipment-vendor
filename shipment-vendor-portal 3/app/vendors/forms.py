"""Vendor form."""
from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, BooleanField, FloatField,
                     SelectField, SubmitField)
from wtforms.validators import DataRequired, Email, Optional, Length, NumberRange


class VendorForm(FlaskForm):
    company_name = StringField("Company name",
                               validators=[DataRequired(), Length(max=190)])
    contact_person = StringField("Contact person",
                                 validators=[Optional(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=190)])
    phone = StringField("Phone", validators=[Optional(), Length(max=40)])
    address = TextAreaField("Address", validators=[Optional()])
    gstin = StringField("GSTIN", validators=[Optional(), Length(max=40)])
    category = SelectField("Category", choices=[
        ("Logistics", "Logistics"),
        ("OEM", "OEM"),
        ("Hardware", "Hardware"),
        ("Software", "Software"),
        ("Services", "Services"),
        ("Other", "Other"),
    ], default="Logistics")
    rating = FloatField("Rating (0-5)",
                        validators=[Optional(), NumberRange(min=0, max=5)],
                        default=0.0)
    is_approved = BooleanField("Approved", default=True)
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save vendor")
