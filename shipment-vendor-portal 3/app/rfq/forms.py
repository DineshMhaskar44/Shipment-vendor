"""RFQ + Quotation forms."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, TextAreaField, IntegerField, DateTimeLocalField,
                     SelectMultipleField, DecimalField, SelectField, SubmitField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class RFQForm(FlaskForm):
    rfq_number = StringField("RFQ Number",
                             validators=[DataRequired(), Length(max=40)])
    title = StringField("Title", validators=[DataRequired(), Length(max=190)])
    product_details = TextAreaField("Product details",
                                    validators=[DataRequired()])
    quantity = IntegerField("Quantity",
                            validators=[DataRequired(), NumberRange(min=1)])
    delivery_timeline = StringField("Delivery timeline (e.g. 30 days)",
                                    validators=[Optional(), Length(max=120)])
    submission_deadline = DateTimeLocalField(
        "Submission deadline", validators=[Optional()],
        format="%Y-%m-%dT%H:%M",
    )
    vendor_ids = SelectMultipleField("Invite vendors", coerce=int,
                                     validators=[DataRequired()])
    notes = TextAreaField("Internal notes", validators=[Optional()])
    submit = SubmitField("Create RFQ & send invites")


class QuotationForm(FlaskForm):
    unit_price = DecimalField("Unit price",
                              validators=[Optional(), NumberRange(min=0)],
                              places=2)
    total_price = DecimalField("Total price",
                               validators=[Optional(), NumberRange(min=0)],
                               places=2)
    currency = SelectField("Currency",
                           choices=[("INR", "INR"), ("USD", "USD"),
                                    ("EUR", "EUR"), ("GBP", "GBP")],
                           default="INR")
    delivery_days = IntegerField("Delivery (days)",
                                 validators=[Optional(), NumberRange(min=0)])
    payment_terms = StringField("Payment terms",
                                validators=[Optional(), Length(max=190)])
    warranty = StringField("Warranty",
                           validators=[Optional(), Length(max=120)])
    remarks = TextAreaField("Remarks", validators=[Optional()])
    file = FileField("Attach quotation (PDF/Excel)",
                     validators=[FileAllowed(["pdf", "xlsx", "xls", "doc", "docx"],
                                             "Allowed: pdf, xlsx, xls, doc, docx")])
    submit = SubmitField("Submit quotation")
