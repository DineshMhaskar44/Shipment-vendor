"""Demo data seeder.

Run with:  flask seed-demo

Creates:
  - 1 admin (admin@example.com / admin123)
  - 1 staff  (staff@mosambee.local / staff123)
  - 3 vendor accounts + linked Vendor profiles
  - 3 RFQs
  - 6 shipments (mix of delivered / in-transit / delayed)
"""
from datetime import date, datetime, timedelta
from app.extensions import db
from app.models import (User, Vendor, Shipment, RFQ, RFQVendor, Quotation)
from app.utils.calculations import recompute_shipment
from app.utils.tokens import random_invite_token


def _ensure_user(email, name, role, password, vendor=None):
    u = User.query.filter_by(email=email).first()
    if not u:
        u = User(email=email, name=name, role=role, is_active=True)
        u.set_password(password)
        db.session.add(u)
        db.session.flush()
    if vendor:
        vendor.user_id = u.id
    return u


def _ensure_vendor(company, email, category="Logistics", approved=True):
    v = Vendor.query.filter_by(email=email).first()
    if not v:
        v = Vendor(company_name=company, email=email,
                   contact_person=company.split()[0] + " Manager",
                   phone="+91 9000000000", category=category,
                   is_approved=approved, rating=4.2)
        db.session.add(v)
        db.session.flush()
    return v


def seed_all():
    today = date.today()

    # Vendors first so we can link users
    v_blue = _ensure_vendor("Blue Ocean Logistics", "ops@blueocean.example.com",
                            "Logistics")
    v_air = _ensure_vendor("AirSwift Couriers", "rfq@airswift.example.com",
                           "Logistics")
    v_oem = _ensure_vendor("Shenzhen TechWorks", "sales@stechworks.example.com",
                           "OEM")

    # Users
    _ensure_user("admin@example.com", "Admin User", "admin", "admin123")
    _ensure_user("staff@example.com", "Staff User", "staff", "staff123")
    _ensure_user("vendor.blue@example.com", "Blue Ocean", "vendor",
                 "vendor123", vendor=v_blue)
    _ensure_user("vendor.air@example.com", "AirSwift", "vendor",
                 "vendor123", vendor=v_air)
    _ensure_user("vendor.oem@example.com", "TechWorks", "vendor",
                 "vendor123", vendor=v_oem)

    db.session.commit()

    # RFQs
    if not RFQ.query.count():
        admin = User.query.filter_by(email="admin@example.com").first()
        rfqs_data = [
            ("RFQ-2026-001", "POS terminals — 500 units",
             "Android-based POS, 4G+WiFi, 2GB RAM, 16GB storage",
             500, "30 days"),
            ("RFQ-2026-002", "Air freight — Shenzhen to Mumbai",
             "Air freight, 2 pallets ~250kg, urgent shipment",
             250, "7 days"),
            ("RFQ-2026-003", "Branding stickers — 10000 units",
             "Vinyl branding stickers, 4-color CMYK, custom die-cut",
             10000, "21 days"),
        ]
        for num, title, det, qty, tl in rfqs_data:
            r = RFQ(rfq_number=num, title=title, product_details=det,
                    quantity=qty, delivery_timeline=tl,
                    submission_deadline=datetime.utcnow() + timedelta(days=14),
                    status="Open", created_by_id=admin.id)
            db.session.add(r)
            db.session.flush()
            for v in [v_blue, v_air, v_oem]:
                db.session.add(RFQVendor(rfq_id=r.id, vendor_id=v.id,
                                         invite_token=random_invite_token(),
                                         email_sent_at=datetime.utcnow()))
        # Sample quotations on the first RFQ
        rfq1 = RFQ.query.filter_by(rfq_number="RFQ-2026-001").first()
        for v, price in [(v_blue, 9800), (v_air, 10250), (v_oem, 9500)]:
            db.session.add(Quotation(
                rfq_id=rfq1.id, vendor_id=v.id,
                unit_price=price, total_price=price * rfq1.quantity,
                currency="INR", delivery_days=28,
                payment_terms="30% advance, 70% on delivery",
                warranty="12 months",
                remarks="Sample quotation",
            ))

    # Shipments
    if not Shipment.query.count():
        admin = User.query.filter_by(email="admin@example.com").first()
        shipments_data = [
            dict(bank_name="HDFC", customer_po_number="CPO-1001",
                 customer_po_date=today - timedelta(days=80),
                 oem_po_number="OPO-1001", oem_po_date=today - timedelta(days=78),
                 advance_payment_date=today - timedelta(days=75),
                 balance_payment_date=today - timedelta(days=10),
                 quantity=500, shipment_quantity=500,
                 oem_name="Shenzhen TechWorks", device_model="MosaPay X1",
                 boe_number="BOE-9981",
                 oem_readiness_date=today - timedelta(days=40),
                 revised_oem_readiness_date=today - timedelta(days=38),
                 warehouse_gatein_date=today - timedelta(days=20),
                 logistics_partner_id=v_blue.id,
                 logistics_partner_name=v_blue.company_name,
                 committed_sailing_date=today - timedelta(days=35),
                 actual_sailing_date=today - timedelta(days=33),
                 mode="Sea", shipment_mode_confirmation="Confirmed",
                 india_port_landing_date=today - timedelta(days=15),
                 custom_clearance_date=today - timedelta(days=12),
                 proposed_eta_warehouse=today - timedelta(days=10),
                 actual_delivery_date=today - timedelta(days=9),
                 dispatch_date=today - timedelta(days=7),
                 status="Delivered", payment_status="Fully Paid",
                 handover_remarks="On-time delivery."),
            dict(bank_name="ICICI", customer_po_number="CPO-1002",
                 customer_po_date=today - timedelta(days=60),
                 oem_po_number="OPO-1002", oem_po_date=today - timedelta(days=58),
                 advance_payment_date=today - timedelta(days=55),
                 quantity=300, shipment_quantity=300,
                 oem_name="Shenzhen TechWorks", device_model="MosaPay Lite",
                 oem_readiness_date=today - timedelta(days=20),
                 revised_oem_readiness_date=today - timedelta(days=10),
                 logistics_partner_id=v_air.id,
                 logistics_partner_name=v_air.company_name,
                 committed_sailing_date=today - timedelta(days=15),
                 actual_sailing_date=today - timedelta(days=8),
                 mode="Air", shipment_mode_confirmation="Confirmed",
                 india_port_landing_date=today - timedelta(days=6),
                 proposed_eta_warehouse=today - timedelta(days=2),
                 status="Customs", payment_status="Advance Paid",
                 handover_remarks="Awaiting clearance."),
            dict(bank_name="SBI", customer_po_number="CPO-1003",
                 customer_po_date=today - timedelta(days=45),
                 oem_po_number="OPO-1003", oem_po_date=today - timedelta(days=44),
                 quantity=200, shipment_quantity=200,
                 oem_name="OrionPay HK", device_model="OPay Pro",
                 oem_readiness_date=today - timedelta(days=10),
                 logistics_partner_id=v_blue.id,
                 logistics_partner_name=v_blue.company_name,
                 committed_sailing_date=today - timedelta(days=5),
                 mode="Sea", shipment_mode_confirmation="Pending",
                 proposed_eta_warehouse=today + timedelta(days=18),
                 status="Pending", payment_status="Pending",
                 handover_remarks="Awaiting OEM PO ack."),
            dict(bank_name="Axis", customer_po_number="CPO-1004",
                 customer_po_date=today - timedelta(days=120),
                 oem_po_number="OPO-1004", oem_po_date=today - timedelta(days=118),
                 advance_payment_date=today - timedelta(days=110),
                 balance_payment_date=today - timedelta(days=20),
                 quantity=1000, shipment_quantity=1000,
                 oem_name="Shenzhen TechWorks", device_model="MosaPay X1",
                 oem_readiness_date=today - timedelta(days=80),
                 revised_oem_readiness_date=today - timedelta(days=70),
                 warehouse_gatein_date=today - timedelta(days=55),
                 logistics_partner_id=v_blue.id,
                 logistics_partner_name=v_blue.company_name,
                 committed_sailing_date=today - timedelta(days=60),
                 actual_sailing_date=today - timedelta(days=50),
                 mode="Sea", shipment_mode_confirmation="Confirmed",
                 india_port_landing_date=today - timedelta(days=25),
                 custom_clearance_date=today - timedelta(days=18),
                 proposed_eta_warehouse=today - timedelta(days=15),
                 actual_delivery_date=today - timedelta(days=14),
                 dispatch_date=today - timedelta(days=12),
                 status="Delivered", payment_status="Fully Paid",
                 handover_remarks="Delayed sailing — vendor compensated."),
            dict(bank_name="Kotak", customer_po_number="CPO-1005",
                 customer_po_date=today - timedelta(days=30),
                 oem_po_number="OPO-1005", oem_po_date=today - timedelta(days=28),
                 advance_payment_date=today - timedelta(days=25),
                 quantity=400, shipment_quantity=400,
                 oem_name="OrionPay HK", device_model="OPay Pro",
                 oem_readiness_date=today + timedelta(days=2),
                 logistics_partner_id=v_air.id,
                 logistics_partner_name=v_air.company_name,
                 committed_sailing_date=today + timedelta(days=5),
                 mode="Air", shipment_mode_confirmation="Confirmed",
                 proposed_eta_warehouse=today + timedelta(days=12),
                 status="In Transit", payment_status="Advance Paid",
                 handover_remarks="On schedule."),
            dict(bank_name="YES Bank", customer_po_number="CPO-1006",
                 customer_po_date=today - timedelta(days=14),
                 quantity=150, shipment_quantity=150,
                 oem_name="Shenzhen TechWorks", device_model="MosaPay Lite",
                 status="Pending", payment_status="Pending"),
        ]
        for d in shipments_data:
            s = Shipment(created_by_id=admin.id, **d)
            recompute_shipment(s)
            db.session.add(s)

    db.session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    # Run standalone:  python -m seeds.seed_data
    from app import create_app
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_all()
