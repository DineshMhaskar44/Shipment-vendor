"""REST API (v1) — JWT auth, JSON only.

Designed for future mobile / integration consumers. Uses Flask-JWT-Extended.

Auth flow:
  POST /api/v1/auth/login {email, password}  -> {access_token}
  Send token as: Authorization: Bearer <token>
"""
from datetime import datetime, date
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (create_access_token, jwt_required,
                                get_jwt_identity)
from sqlalchemy import or_

from ..extensions import db
from ..models import User, Shipment, Vendor, RFQ, Quotation
from ..utils.calculations import recompute_shipment

api_bp = Blueprint("api", __name__)


def _shipment_to_dict(s):
    out = {}
    for col in s.__table__.columns:
        v = getattr(s, col.name)
        if isinstance(v, (datetime, date)):
            v = v.isoformat()
        out[col.name] = v
    return out


def _vendor_to_dict(v):
    return {
        "id": v.id, "company_name": v.company_name,
        "contact_person": v.contact_person, "email": v.email,
        "phone": v.phone, "category": v.category,
        "is_approved": v.is_approved, "rating": v.rating,
    }


def _rfq_to_dict(r):
    return {
        "id": r.id, "rfq_number": r.rfq_number, "title": r.title,
        "product_details": r.product_details, "quantity": r.quantity,
        "delivery_timeline": r.delivery_timeline,
        "submission_deadline": r.submission_deadline.isoformat()
            if r.submission_deadline else None,
        "status": r.status,
        "awarded_vendor_id": r.awarded_vendor_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# ----------------------------- AUTH ----------------------------- #
@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password) or not user.is_active:
        return jsonify({"error": "invalid_credentials"}), 401
    token = create_access_token(identity=str(user.id),
                                additional_claims={"role": user.role,
                                                   "name": user.name})
    return jsonify({"access_token": token, "role": user.role,
                    "name": user.name})


@api_bp.route("/me")
@jwt_required()
def api_me():
    uid = int(get_jwt_identity())
    u = db.session.get(User, uid)
    if not u:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"id": u.id, "name": u.name, "email": u.email,
                    "role": u.role})


# ----------------------------- SHIPMENTS ----------------------------- #
@api_bp.route("/shipments", methods=["GET"])
@jwt_required()
def api_shipments_list():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 25, type=int), 200)
    q = Shipment.query
    if status := request.args.get("status"):
        q = q.filter(Shipment.status == status)
    if delay := request.args.get("delay_status"):
        q = q.filter(Shipment.delay_status == delay)
    if search := request.args.get("q"):
        like = f"%{search}%"
        q = q.filter(or_(Shipment.customer_po_number.ilike(like),
                         Shipment.oem_name.ilike(like)))
    pagination = q.order_by(Shipment.created_at.desc()).paginate(
        page=page, per_page=per_page
    )
    return jsonify({
        "items": [_shipment_to_dict(s) for s in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
    })


@api_bp.route("/shipments/<int:sid>")
@jwt_required()
def api_shipment_get(sid):
    s = db.session.get(Shipment, sid)
    if not s:
        return jsonify({"error": "not_found"}), 404
    return jsonify(_shipment_to_dict(s))


@api_bp.route("/shipments", methods=["POST"])
@jwt_required()
def api_shipment_create():
    data = request.get_json() or {}
    s = Shipment()
    for col in s.__table__.columns:
        if col.name in data:
            value = data[col.name]
            if col.name.endswith("_date") and isinstance(value, str):
                try:
                    value = datetime.strptime(value[:10], "%Y-%m-%d").date()
                except ValueError:
                    value = None
            setattr(s, col.name, value)
    s.created_by_id = int(get_jwt_identity())
    recompute_shipment(s, current_app.config["DELAY_THRESHOLD_DAYS"])
    db.session.add(s)
    db.session.commit()
    return jsonify(_shipment_to_dict(s)), 201


@api_bp.route("/shipments/<int:sid>", methods=["PUT", "PATCH"])
@jwt_required()
def api_shipment_update(sid):
    s = db.session.get(Shipment, sid)
    if not s:
        return jsonify({"error": "not_found"}), 404
    data = request.get_json() or {}
    for col in s.__table__.columns:
        if col.name in data:
            value = data[col.name]
            if col.name.endswith("_date") and isinstance(value, str):
                try:
                    value = datetime.strptime(value[:10], "%Y-%m-%d").date()
                except ValueError:
                    value = None
            setattr(s, col.name, value)
    recompute_shipment(s, current_app.config["DELAY_THRESHOLD_DAYS"])
    db.session.commit()
    return jsonify(_shipment_to_dict(s))


@api_bp.route("/shipments/<int:sid>", methods=["DELETE"])
@jwt_required()
def api_shipment_delete(sid):
    s = db.session.get(Shipment, sid)
    if not s:
        return jsonify({"error": "not_found"}), 404
    db.session.delete(s)
    db.session.commit()
    return "", 204


# ----------------------------- VENDORS ----------------------------- #
@api_bp.route("/vendors")
@jwt_required()
def api_vendors_list():
    rows = Vendor.query.order_by(Vendor.company_name).all()
    return jsonify({"items": [_vendor_to_dict(v) for v in rows]})


# ----------------------------- RFQs ----------------------------- #
@api_bp.route("/rfqs")
@jwt_required()
def api_rfq_list():
    rows = RFQ.query.order_by(RFQ.created_at.desc()).all()
    return jsonify({"items": [_rfq_to_dict(r) for r in rows]})


@api_bp.route("/rfqs/<int:rid>/quotations")
@jwt_required()
def api_rfq_quotations(rid):
    rfq = db.session.get(RFQ, rid)
    if not rfq:
        return jsonify({"error": "not_found"}), 404
    out = []
    for q in rfq.quotations.all():
        out.append({
            "id": q.id, "vendor_id": q.vendor_id,
            "vendor": q.vendor.company_name,
            "unit_price": float(q.unit_price) if q.unit_price else None,
            "total_price": float(q.total_price) if q.total_price else None,
            "currency": q.currency,
            "delivery_days": q.delivery_days,
            "is_selected": q.is_selected,
            "submitted_at": q.submitted_at.isoformat() if q.submitted_at else None,
        })
    return jsonify({"rfq": _rfq_to_dict(rfq), "items": out})
