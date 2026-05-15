"""Shipment form — every column maps to a field. Date fields are HTML5 date inputs."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, DateField, IntegerField, SelectField,
                     TextAreaField, SubmitField)
from wtforms.validators import Optional, Length, NumberRange


class ShipmentForm(FlaskForm):
    # ---- Customer / OEM ----
    bank_name = StringField("Bank Name", validators=[Optional(), Length(max=190)])
    customer_po_date = DateField("Customer PO Date", validators=[Optional()])
    customer_po_number = StringField("Customer PO Number",
                                     validators=[Optional(), Length(max=80)])
    oem_po_date = DateField("OEM PO Date", validators=[Optional()])
    oem_po_number = StringField("OEM PO Number",
                                validators=[Optional(), Length(max=80)])

    # ---- Payments ----
    advance_payment_date = DateField("Advance Payment Date", validators=[Optional()])
    balance_payment_date = DateField("Balance Payment Date", validators=[Optional()])
    payment_status = SelectField(
        "Payment Status",
        choices=[("Pending", "Pending"), ("Advance Paid", "Advance Paid"),
                 ("Balance Paid", "Balance Paid"), ("Fully Paid", "Fully Paid")],
        default="Pending",
    )

    # ---- Quantities / OEM ----
    quantity = IntegerField("Quantity", validators=[Optional(), NumberRange(min=0)])
    oem_name = StringField("OEM Name", validators=[Optional(), Length(max=190)])
    device_model = StringField("Device Model", validators=[Optional(), Length(max=120)])
    boe_number = StringField("BOE Number", validators=[Optional(), Length(max=80)])
    shipment_quantity = IntegerField("Shipment Quantity",
                                     validators=[Optional(), NumberRange(min=0)])
    branding_specification = TextAreaField("Branding Specification",
                                           validators=[Optional()])

    # ---- Readiness ----
    oem_readiness_date = DateField("OEM Readiness Date", validators=[Optional()])
    revised_oem_readiness_date = DateField("Revised OEM Readiness Date",
                                           validators=[Optional()])
    warehouse_gatein_date = DateField("Warehouse Gate-in Date",
                                      validators=[Optional()])

    # ---- Logistics ----
    logistics_partner_id = SelectField("Logistics Partner",
                                       coerce=int, choices=[], validators=[Optional()])
    committed_sailing_date = DateField("Committed Sailing Date",
                                       validators=[Optional()])
    actual_sailing_date = DateField("Actual Sailing Date", validators=[Optional()])
    shipment_mode_confirmation = SelectField(
        "Mode Confirmation",
        choices=[("", "—"), ("Confirmed", "Confirmed"), ("Pending", "Pending")],
        validators=[Optional()],
    )
    mode = SelectField("Mode",
                       choices=[("Sea", "Sea"), ("Air", "Air"),
                                ("Road", "Road"), ("Rail", "Rail")],
                       default="Sea")
    india_port_landing_date = DateField("India Port Landing Date",
                                        validators=[Optional()])
    custom_clearance_date = DateField("Custom Clearance Date", validators=[Optional()])
    proposed_eta_warehouse = DateField("Proposed ETA at Warehouse",
                                       validators=[Optional()])
    actual_delivery_date = DateField("Actual Delivery Date", validators=[Optional()])
    dispatch_date = DateField("Dispatch Date", validators=[Optional()])

    # ---- Final ----
    status = SelectField(
        "Status",
        choices=[("Pending", "Pending"), ("In Transit", "In Transit"),
                 ("Customs", "Customs"), ("Warehouse", "Warehouse"),
                 ("Delivered", "Delivered"), ("Cancelled", "Cancelled")],
        default="Pending",
    )
    handover_remarks = TextAreaField("Handover Remarks & Comments",
                                     validators=[Optional()])

    submit = SubmitField("Save shipment")


class BulkUploadForm(FlaskForm):
    file = FileField("Excel file (.xlsx)",
                     validators=[FileAllowed(["xlsx", "xls"], "Excel only")])
    submit = SubmitField("Upload")
