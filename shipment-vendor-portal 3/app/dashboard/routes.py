"""Dashboard — KPI cards, OEM/vendor summaries, charts, monthly report."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, extract

from ..extensions import db
from ..models import Shipment, RFQ, Quotation, Vendor

dashboard_bp = Blueprint("dashboard", __name__,
                         template_folder="../templates/dashboard")


@dashboard_bp.route("/")
def root():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.is_vendor:
        return redirect(url_for("rfq.vendor_inbox"))
    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/dashboard")
@login_required
def index():
    if current_user.is_vendor:
        return redirect(url_for("rfq.vendor_inbox"))

    total = Shipment.query.count()
    delivered = Shipment.query.filter_by(status="Delivered").count()
    pending = Shipment.query.filter(Shipment.status.in_(
        ["Pending", "In Transit", "Customs", "Warehouse"])).count()
    delayed = Shipment.query.filter_by(delay_status="Delayed").count()
    payment_pending = Shipment.query.filter(
        Shipment.payment_status.in_(["Pending", "Advance Paid"])
    ).count()

    # OEM-wise summary
    oem_rows = (db.session.query(Shipment.oem_name,
                                 func.count(Shipment.id).label("cnt"),
                                 func.sum(func.coalesce(Shipment.shipment_quantity, 0))
                                 .label("qty"))
                .filter(Shipment.oem_name.isnot(None))
                .group_by(Shipment.oem_name)
                .order_by(func.count(Shipment.id).desc())
                .limit(10).all())
    oem_summary = [{"name": r[0], "count": r[1], "qty": int(r[2] or 0)}
                   for r in oem_rows]

    # Vendor (logistics) summary
    v_rows = (db.session.query(Shipment.logistics_partner_name,
                               func.count(Shipment.id).label("cnt"))
              .filter(Shipment.logistics_partner_name.isnot(None))
              .group_by(Shipment.logistics_partner_name)
              .order_by(func.count(Shipment.id).desc())
              .limit(10).all())
    vendor_summary = [{"name": r[0], "count": r[1]} for r in v_rows]

    # Recent
    recent = Shipment.query.order_by(Shipment.created_at.desc()).limit(5).all()

    return render_template(
        "dashboard/index.html",
        cards=dict(total=total, delivered=delivered, pending=pending,
                   delayed=delayed, payment_pending=payment_pending),
        oem_summary=oem_summary,
        vendor_summary=vendor_summary,
        recent=recent,
    )


# ----- chart data endpoints (consumed by Chart.js) ----- #
@dashboard_bp.route("/dashboard/chart/status.json")
@login_required
def chart_status():
    rows = (db.session.query(Shipment.status, func.count(Shipment.id))
            .group_by(Shipment.status).all())
    return jsonify({
        "labels": [r[0] for r in rows],
        "values": [r[1] for r in rows],
    })


@dashboard_bp.route("/dashboard/chart/monthly.json")
@login_required
def chart_monthly():
    """Last 12 months of shipment volume by created_at."""
    today = datetime.utcnow().replace(day=1)
    start = (today - timedelta(days=365)).replace(day=1)
    rows = (db.session.query(
                extract("year", Shipment.created_at).label("y"),
                extract("month", Shipment.created_at).label("m"),
                func.count(Shipment.id))
            .filter(Shipment.created_at >= start)
            .group_by("y", "m")
            .order_by("y", "m").all())
    labels, values = [], []
    for y, m, c in rows:
        labels.append(f"{int(y)}-{int(m):02d}")
        values.append(int(c))
    return jsonify({"labels": labels, "values": values})


@dashboard_bp.route("/dashboard/chart/delay.json")
@login_required
def chart_delay():
    rows = (db.session.query(Shipment.delay_status, func.count(Shipment.id))
            .group_by(Shipment.delay_status).all())
    return jsonify({
        "labels": [r[0] for r in rows],
        "values": [r[1] for r in rows],
    })
