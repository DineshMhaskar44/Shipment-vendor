"""Shipment routes — list, view, create, edit, delete, bulk import, exports."""
from datetime import datetime, date
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, send_file, abort)
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, func

from ..extensions import db
from ..models import Shipment, Vendor
from ..utils.decorators import staff_or_admin_required
from ..utils.calculations import recompute_shipment
from ..utils.audit import log_activity
from ..utils.email import send_shipment_delay_alert
from ..utils.excel import (shipments_to_xlsx, shipments_to_pdf,
                           parse_shipment_xlsx, SHIPMENT_COLUMNS)
from .forms import ShipmentForm, BulkUploadForm

shipments_bp = Blueprint("shipments", __name__,
                         template_folder="../templates/shipments")


# ----------------------------- helpers ----------------------------- #
def _populate_logistics_choices(form):
    vendors = Vendor.query.order_by(Vendor.company_name).all()
    form.logistics_partner_id.choices = [(0, "—")] + [
        (v.id, v.company_name) for v in vendors
    ]


def _apply_filters(query):
    """Apply common list-page filters from query string."""
    args = request.args
    search = args.get("q", "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(or_(
            Shipment.customer_po_number.ilike(like),
            Shipment.oem_po_number.ilike(like),
            Shipment.oem_name.ilike(like),
            Shipment.device_model.ilike(like),
            Shipment.bank_name.ilike(like),
            Shipment.boe_number.ilike(like),
        ))
    if oem := args.get("oem"):
        query = query.filter(Shipment.oem_name == oem)
    if vendor_id := args.get("vendor_id", type=int):
        query = query.filter(Shipment.logistics_partner_id == vendor_id)
    if status := args.get("status"):
        query = query.filter(Shipment.status == status)
    if pay := args.get("payment_status"):
        query = query.filter(Shipment.payment_status == pay)
    if delay := args.get("delay_status"):
        query = query.filter(Shipment.delay_status == delay)
    if start := args.get("start"):
        try:
            d = datetime.strptime(start, "%Y-%m-%d").date()
            query = query.filter(Shipment.customer_po_date >= d)
        except ValueError:
            pass
    if end := args.get("end"):
        try:
            d = datetime.strptime(end, "%Y-%m-%d").date()
            query = query.filter(Shipment.customer_po_date <= d)
        except ValueError:
            pass
    return query


def _form_to_shipment(form, shipment):
    """Copy form data onto the shipment instance."""
    for attr, _ in SHIPMENT_COLUMNS:
        # logistics_partner_name set below from id
        if attr in {"payment_days", "readiness_delay_days",
                    "readiness_to_warehouse_days", "sailing_delayed_days",
                    "cc_delayed_days", "total_clearance_days",
                    "delay_status", "logistics_partner_name"}:
            continue
        if hasattr(form, attr):
            setattr(shipment, attr, getattr(form, attr).data)

    lp_id = form.logistics_partner_id.data or None
    if lp_id and lp_id != 0:
        shipment.logistics_partner_id = lp_id
        v = Vendor.query.get(lp_id)
        shipment.logistics_partner_name = v.company_name if v else None
    else:
        shipment.logistics_partner_id = None
        shipment.logistics_partner_name = None


# ----------------------------- routes ----------------------------- #
@shipments_bp.route("/")
@login_required
@staff_or_admin_required
def index():
    page = request.args.get("page", 1, type=int)
    q = _apply_filters(Shipment.query).order_by(Shipment.created_at.desc())
    pagination = q.paginate(page=page,
                            per_page=current_app.config["ITEMS_PER_PAGE"])
    oems = [r[0] for r in db.session.query(Shipment.oem_name)
            .filter(Shipment.oem_name.isnot(None)).distinct().all()]
    vendors = Vendor.query.order_by(Vendor.company_name).all()
    return render_template("shipments/list.html",
                           pagination=pagination, oems=oems, vendors=vendors,
                           filters=request.args)


@shipments_bp.route("/<int:sid>")
@login_required
@staff_or_admin_required
def view(sid):
    s = Shipment.query.get_or_404(sid)
    return render_template("shipments/view.html", s=s)


@shipments_bp.route("/new", methods=["GET", "POST"])
@login_required
@staff_or_admin_required
def new():
    form = ShipmentForm()
    _populate_logistics_choices(form)
    if form.validate_on_submit():
        s = Shipment(created_by_id=current_user.id)
        _form_to_shipment(form, s)
        recompute_shipment(s, current_app.config["DELAY_THRESHOLD_DAYS"])
        db.session.add(s)
        db.session.flush()
        log_activity("shipment_created", "shipment", s.id)
        if s.delay_status == "Delayed":
            send_shipment_delay_alert(s, current_app.config["ADMIN_NOTIFY_EMAIL"])
        db.session.commit()
        flash("Shipment created.", "success")
        return redirect(url_for("shipments.view", sid=s.id))
    return render_template("shipments/form.html", form=form, title="New shipment")


@shipments_bp.route("/<int:sid>/edit", methods=["GET", "POST"])
@login_required
@staff_or_admin_required
def edit(sid):
    s = Shipment.query.get_or_404(sid)
    form = ShipmentForm(obj=s)
    _populate_logistics_choices(form)
    if request.method == "GET":
        form.logistics_partner_id.data = s.logistics_partner_id or 0

    if form.validate_on_submit():
        was_delayed = s.delay_status == "Delayed"
        _form_to_shipment(form, s)
        recompute_shipment(s, current_app.config["DELAY_THRESHOLD_DAYS"])
        log_activity("shipment_updated", "shipment", s.id)
        if not was_delayed and s.delay_status == "Delayed":
            send_shipment_delay_alert(s, current_app.config["ADMIN_NOTIFY_EMAIL"])
        db.session.commit()
        flash("Shipment updated.", "success")
        return redirect(url_for("shipments.view", sid=s.id))
    return render_template("shipments/form.html", form=form,
                           title=f"Edit shipment #{s.id}")


@shipments_bp.route("/<int:sid>/delete", methods=["POST"])
@login_required
@staff_or_admin_required
def delete(sid):
    s = Shipment.query.get_or_404(sid)
    db.session.delete(s)
    log_activity("shipment_deleted", "shipment", sid)
    db.session.commit()
    flash("Shipment deleted.", "info")
    return redirect(url_for("shipments.index"))


# ----------------------------- import / export ----------------------------- #
@shipments_bp.route("/export.xlsx")
@login_required
@staff_or_admin_required
def export_xlsx():
    rows = _apply_filters(Shipment.query).order_by(Shipment.id.asc()).all()
    buf = shipments_to_xlsx(rows)
    fname = f"shipments_{date.today().isoformat()}.xlsx"
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@shipments_bp.route("/export.pdf")
@login_required
@staff_or_admin_required
def export_pdf():
    rows = _apply_filters(Shipment.query).order_by(Shipment.id.asc()).all()
    buf = shipments_to_pdf(rows, title="Shipment Report")
    fname = f"shipments_{date.today().isoformat()}.pdf"
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype="application/pdf")


@shipments_bp.route("/import", methods=["GET", "POST"])
@login_required
@staff_or_admin_required
def bulk_import():
    form = BulkUploadForm()
    if form.validate_on_submit() and form.file.data:
        created = 0
        errors = []
        for idx, record in enumerate(parse_shipment_xlsx(form.file.data), start=2):
            try:
                s = Shipment(created_by_id=current_user.id, **record)
                recompute_shipment(s, current_app.config["DELAY_THRESHOLD_DAYS"])
                db.session.add(s)
                created += 1
            except Exception as exc:
                errors.append(f"Row {idx}: {exc}")
        log_activity("shipments_bulk_import", "shipment", None,
                     detail=f"created={created} errors={len(errors)}")
        db.session.commit()
        if created:
            flash(f"Imported {created} shipments.", "success")
        if errors:
            flash("Some rows had problems: " + "; ".join(errors[:5]), "warning")
        return redirect(url_for("shipments.index"))
    return render_template("shipments/import.html", form=form,
                           columns=[label for _, label in SHIPMENT_COLUMNS])


# ----------------------------- distinct OEM list (helper) ----------------------------- #
@shipments_bp.route("/oem-list.json")
@login_required
@staff_or_admin_required
def oem_list():
    oems = [r[0] for r in db.session.query(Shipment.oem_name)
            .filter(Shipment.oem_name.isnot(None)).distinct().all()]
    return {"oems": oems}
