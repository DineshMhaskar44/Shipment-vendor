"""SQLAlchemy models.

Tables (matches the spec):
  - User              users + role-based access (admin / staff / vendor)
  - Vendor            vendor profile, linked optionally to a User
  - Shipment          all 30+ shipment-tracking columns
  - ShipmentUpdate    audit-trail of changes to a shipment
  - RFQ               request-for-quotation header
  - RFQVendor         many-to-many between RFQ and Vendor (with email tracking)
  - Quotation         vendor quote (price/file/terms) for an RFQ
  - EmailLog          every outbound email is logged
  - ActivityLog       generic activity log for audit
"""
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Index
from .extensions import db


# --------------------------------------------------------------------------- #
#  USER
# --------------------------------------------------------------------------- #
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum("admin", "staff", "vendor", name="user_role"),
        nullable=False,
        default="staff",
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)

    vendor = db.relationship("Vendor", back_populates="user", uselist=False)

    # ---- helpers ----
    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_vendor(self):
        return self.role == "vendor"

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


# --------------------------------------------------------------------------- #
#  VENDOR
# --------------------------------------------------------------------------- #
class Vendor(db.Model):
    __tablename__ = "vendors"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(190), nullable=False, index=True)
    contact_person = db.Column(db.String(120))
    email = db.Column(db.String(190), nullable=False, index=True)
    phone = db.Column(db.String(40))
    address = db.Column(db.Text)
    gstin = db.Column(db.String(40))
    category = db.Column(db.String(80))           # e.g. logistics, oem, hardware
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    rating = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="vendor")
    quotations = db.relationship("Quotation", back_populates="vendor", lazy="dynamic")
    rfq_links = db.relationship("RFQVendor", back_populates="vendor", lazy="dynamic")

    def __repr__(self):
        return f"<Vendor {self.company_name}>"


# --------------------------------------------------------------------------- #
#  SHIPMENT
# --------------------------------------------------------------------------- #
class Shipment(db.Model):
    __tablename__ = "shipments"

    id = db.Column(db.Integer, primary_key=True)

    # ---- Customer / OEM PO ----
    bank_name = db.Column(db.String(190), index=True)
    customer_po_date = db.Column(db.Date)
    customer_po_number = db.Column(db.String(80), index=True)
    oem_po_date = db.Column(db.Date)
    oem_po_number = db.Column(db.String(80), index=True)

    # ---- Payments ----
    advance_payment_date = db.Column(db.Date)
    balance_payment_date = db.Column(db.Date)
    payment_days = db.Column(db.Integer)            # auto-calculated
    payment_status = db.Column(
        db.Enum("Pending", "Advance Paid", "Balance Paid", "Fully Paid",
                name="payment_status"),
        default="Pending", nullable=False,
    )

    # ---- Quantities / OEM ----
    quantity = db.Column(db.Integer, default=0)
    oem_name = db.Column(db.String(190), index=True)
    device_model = db.Column(db.String(120))
    boe_number = db.Column(db.String(80))
    shipment_quantity = db.Column(db.Integer, default=0)
    branding_specification = db.Column(db.Text)

    # ---- Readiness ----
    oem_readiness_date = db.Column(db.Date)
    revised_oem_readiness_date = db.Column(db.Date)
    readiness_delay_days = db.Column(db.Integer)    # auto-calc
    warehouse_gatein_date = db.Column(db.Date)
    readiness_to_warehouse_days = db.Column(db.Integer)  # auto-calc

    # ---- Logistics ----
    logistics_partner_id = db.Column(db.Integer, db.ForeignKey("vendors.id"))
    logistics_partner_name = db.Column(db.String(190))     # denormalized snapshot
    committed_sailing_date = db.Column(db.Date)
    actual_sailing_date = db.Column(db.Date)
    sailing_delayed_days = db.Column(db.Integer)           # auto-calc
    shipment_mode_confirmation = db.Column(db.String(40))  # Confirmed / Pending
    mode = db.Column(db.Enum("Air", "Sea", "Road", "Rail", name="shipment_mode"),
                     default="Sea")
    india_port_landing_date = db.Column(db.Date)
    custom_clearance_date = db.Column(db.Date)
    cc_delayed_days = db.Column(db.Integer)                # auto-calc
    proposed_eta_warehouse = db.Column(db.Date)
    actual_delivery_date = db.Column(db.Date)
    total_clearance_days = db.Column(db.Integer)           # auto-calc
    dispatch_date = db.Column(db.Date)

    # ---- Final ----
    status = db.Column(
        db.Enum("Pending", "In Transit", "Customs", "Warehouse",
                "Delivered", "Cancelled", name="shipment_status"),
        default="Pending", nullable=False, index=True,
    )
    delay_status = db.Column(
        db.Enum("Non Delayed", "Delayed", name="delay_status"),
        default="Non Delayed", nullable=False, index=True,
    )
    handover_remarks = db.Column(db.Text)

    # ---- Audit ----
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)

    logistics_partner = db.relationship("Vendor", foreign_keys=[logistics_partner_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    updates = db.relationship("ShipmentUpdate", back_populates="shipment",
                              cascade="all, delete-orphan", lazy="dynamic")

    __table_args__ = (
        Index("ix_shipment_status_delay", "status", "delay_status"),
    )

    def __repr__(self):
        return f"<Shipment #{self.id} {self.customer_po_number}>"


class ShipmentUpdate(db.Model):
    __tablename__ = "shipment_updates"

    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id"), nullable=False)
    field_name = db.Column(db.String(80))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    note = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    shipment = db.relationship("Shipment", back_populates="updates")
    user = db.relationship("User")


# --------------------------------------------------------------------------- #
#  RFQ + QUOTATION
# --------------------------------------------------------------------------- #
class RFQ(db.Model):
    __tablename__ = "rfqs"

    id = db.Column(db.Integer, primary_key=True)
    rfq_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    title = db.Column(db.String(190), nullable=False)
    product_details = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Integer, default=0)
    delivery_timeline = db.Column(db.String(120))
    submission_deadline = db.Column(db.DateTime)
    status = db.Column(
        db.Enum("Draft", "Open", "Closed", "Awarded", "Cancelled", name="rfq_status"),
        default="Open", nullable=False,
    )
    awarded_vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"))
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)

    awarded_vendor = db.relationship("Vendor", foreign_keys=[awarded_vendor_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    rfq_vendors = db.relationship("RFQVendor", back_populates="rfq",
                                  cascade="all, delete-orphan", lazy="dynamic")
    quotations = db.relationship("Quotation", back_populates="rfq",
                                 cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
        return f"<RFQ {self.rfq_number}>"


class RFQVendor(db.Model):
    """Many-to-many bridge between RFQ and Vendor with email tracking."""
    __tablename__ = "rfq_vendors"

    id = db.Column(db.Integer, primary_key=True)
    rfq_id = db.Column(db.Integer, db.ForeignKey("rfqs.id"), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    invite_token = db.Column(db.String(64), unique=True, index=True)
    email_sent_at = db.Column(db.DateTime)
    responded_at = db.Column(db.DateTime)

    rfq = db.relationship("RFQ", back_populates="rfq_vendors")
    vendor = db.relationship("Vendor", back_populates="rfq_links")

    __table_args__ = (
        db.UniqueConstraint("rfq_id", "vendor_id", name="uq_rfq_vendor"),
    )


class Quotation(db.Model):
    __tablename__ = "quotations"

    id = db.Column(db.Integer, primary_key=True)
    rfq_id = db.Column(db.Integer, db.ForeignKey("rfqs.id"), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    unit_price = db.Column(db.Numeric(14, 2))
    total_price = db.Column(db.Numeric(14, 2))
    currency = db.Column(db.String(8), default="INR")
    delivery_days = db.Column(db.Integer)
    payment_terms = db.Column(db.String(190))
    warranty = db.Column(db.String(120))
    remarks = db.Column(db.Text)
    file_path = db.Column(db.String(255))         # uploaded PDF/Excel
    is_selected = db.Column(db.Boolean, default=False, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)

    rfq = db.relationship("RFQ", back_populates="quotations")
    vendor = db.relationship("Vendor", back_populates="quotations")

    __table_args__ = (
        db.UniqueConstraint("rfq_id", "vendor_id", name="uq_quotation_rfq_vendor"),
    )


# --------------------------------------------------------------------------- #
#  LOGS
# --------------------------------------------------------------------------- #
class EmailLog(db.Model):
    __tablename__ = "email_logs"

    id = db.Column(db.Integer, primary_key=True)
    to_address = db.Column(db.String(190), nullable=False)
    subject = db.Column(db.String(255))
    template = db.Column(db.String(80))
    status = db.Column(db.String(20), default="queued")  # queued/sent/failed
    error = db.Column(db.Text)
    related_type = db.Column(db.String(40))   # 'rfq', 'shipment', etc.
    related_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(80), nullable=False)
    target_type = db.Column(db.String(40))
    target_id = db.Column(db.Integer)
    detail = db.Column(db.Text)
    ip_address = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User")
