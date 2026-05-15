"""Vendor CRUD."""
from datetime import date
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, send_file)
from flask_login import login_required
from sqlalchemy import or_

from ..extensions import db
from ..models import Vendor, User
from ..utils.decorators import staff_or_admin_required, admin_required
from ..utils.audit import log_activity
from ..utils.excel import vendors_to_xlsx
from .forms import VendorForm

vendors_bp = Blueprint("vendors", __name__,
                       template_folder="../templates/vendors")


@vendors_bp.route("/")
@login_required
@staff_or_admin_required
def index():
    page = request.args.get("page", 1, type=int)
    q = Vendor.query
    if search := request.args.get("q", "").strip():
        like = f"%{search}%"
        q = q.filter(or_(Vendor.company_name.ilike(like),
                         Vendor.email.ilike(like),
                         Vendor.contact_person.ilike(like)))
    if category := request.args.get("category"):
        q = q.filter(Vendor.category == category)
    pagination = q.order_by(Vendor.company_name).paginate(
        page=page, per_page=current_app.config["ITEMS_PER_PAGE"]
    )
    return render_template("vendors/list.html", pagination=pagination,
                           filters=request.args)


@vendors_bp.route("/<int:vid>")
@login_required
@staff_or_admin_required
def view(vid):
    v = Vendor.query.get_or_404(vid)
    return render_template("vendors/view.html", v=v)


@vendors_bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def new():
    form = VendorForm()
    if form.validate_on_submit():
        v = Vendor(
            company_name=form.company_name.data.strip(),
            contact_person=form.contact_person.data,
            email=form.email.data.strip().lower(),
            phone=form.phone.data,
            address=form.address.data,
            gstin=form.gstin.data,
            category=form.category.data,
            rating=form.rating.data or 0,
            is_approved=form.is_approved.data,
            notes=form.notes.data,
        )
        db.session.add(v)
        db.session.flush()
        log_activity("vendor_created", "vendor", v.id)
        db.session.commit()
        flash("Vendor created.", "success")
        return redirect(url_for("vendors.view", vid=v.id))
    return render_template("vendors/form.html", form=form, title="New vendor")


@vendors_bp.route("/<int:vid>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit(vid):
    v = Vendor.query.get_or_404(vid)
    form = VendorForm(obj=v)
    if form.validate_on_submit():
        form.populate_obj(v)
        v.email = v.email.strip().lower()
        log_activity("vendor_updated", "vendor", v.id)
        db.session.commit()
        flash("Vendor updated.", "success")
        return redirect(url_for("vendors.view", vid=v.id))
    return render_template("vendors/form.html", form=form,
                           title=f"Edit {v.company_name}")


@vendors_bp.route("/<int:vid>/delete", methods=["POST"])
@login_required
@admin_required
def delete(vid):
    v = Vendor.query.get_or_404(vid)
    db.session.delete(v)
    log_activity("vendor_deleted", "vendor", vid)
    db.session.commit()
    flash("Vendor deleted.", "info")
    return redirect(url_for("vendors.index"))


@vendors_bp.route("/export.xlsx")
@login_required
@staff_or_admin_required
def export_xlsx():
    rows = Vendor.query.order_by(Vendor.company_name).all()
    buf = vendors_to_xlsx(rows)
    return send_file(buf, as_attachment=True,
                     download_name=f"vendors_{date.today().isoformat()}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
