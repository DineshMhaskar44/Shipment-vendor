"""RFQ blueprint — admin RFQ list/create + vendor inbox + quotation submit + comparison."""
import os
from datetime import datetime, date
from werkzeug.utils import secure_filename
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, send_file, abort)
from flask_login import login_required, current_user
from sqlalchemy import or_

from ..extensions import db
from ..models import RFQ, RFQVendor, Quotation, Vendor
from ..utils.decorators import (staff_or_admin_required, admin_required,
                                vendor_required)
from ..utils.audit import log_activity
from ..utils.tokens import random_invite_token
from ..utils.email import (send_rfq_invite, send_quotation_received_alert)
from ..utils.excel import quotations_compare_xlsx, quotations_compare_pdf
from .forms import RFQForm, QuotationForm

rfq_bp = Blueprint("rfq", __name__, template_folder="../templates/rfq")


# --------------------------------------------------------------------------- #
#  ADMIN / STAFF
# --------------------------------------------------------------------------- #
@rfq_bp.route("/")
@login_required
@staff_or_admin_required
def index():
    page = request.args.get("page", 1, type=int)
    q = RFQ.query
    if status := request.args.get("status"):
        q = q.filter(RFQ.status == status)
    if search := request.args.get("q", "").strip():
        like = f"%{search}%"
        q = q.filter(or_(RFQ.rfq_number.ilike(like), RFQ.title.ilike(like)))
    pagination = q.order_by(RFQ.created_at.desc()).paginate(
        page=page, per_page=current_app.config["ITEMS_PER_PAGE"]
    )
    return render_template("rfq/list.html", pagination=pagination,
                           filters=request.args)


@rfq_bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def new():
    form = RFQForm()
    form.vendor_ids.choices = [(v.id, v.company_name) for v in
                               Vendor.query.filter_by(is_approved=True)
                               .order_by(Vendor.company_name).all()]
    if form.validate_on_submit():
        if RFQ.query.filter_by(rfq_number=form.rfq_number.data).first():
            flash("RFQ number already exists.", "danger")
            return render_template("rfq/form.html", form=form, title="New RFQ")
        rfq = RFQ(
            rfq_number=form.rfq_number.data.strip(),
            title=form.title.data.strip(),
            product_details=form.product_details.data,
            quantity=form.quantity.data,
            delivery_timeline=form.delivery_timeline.data,
            submission_deadline=form.submission_deadline.data,
            notes=form.notes.data,
            status="Open",
            created_by_id=current_user.id,
        )
        db.session.add(rfq)
        db.session.flush()

        # Invite vendors
        invited = 0
        for vid in form.vendor_ids.data:
            vendor = Vendor.query.get(vid)
            if not vendor:
                continue
            link_token = random_invite_token()
            rv = RFQVendor(rfq_id=rfq.id, vendor_id=vendor.id,
                           invite_token=link_token,
                           email_sent_at=datetime.utcnow())
            db.session.add(rv)
            link = url_for("rfq.vendor_invite", token=link_token, _external=True)
            send_rfq_invite(rfq, vendor, link, sender_name=current_user.name)
            invited += 1

        log_activity("rfq_created", "rfq", rfq.id,
                     detail=f"invited={invited}")
        db.session.commit()
        flash(f"RFQ {rfq.rfq_number} created and sent to {invited} vendors.",
              "success")
        return redirect(url_for("rfq.view", rid=rfq.id))
    return render_template("rfq/form.html", form=form, title="New RFQ")


@rfq_bp.route("/<int:rid>")
@login_required
@staff_or_admin_required
def view(rid):
    rfq = RFQ.query.get_or_404(rid)
    quotations = rfq.quotations.order_by(Quotation.unit_price.asc()).all()
    return render_template("rfq/view.html", rfq=rfq, quotations=quotations)


@rfq_bp.route("/<int:rid>/award/<int:qid>", methods=["POST"])
@login_required
@admin_required
def award(rid, qid):
    rfq = RFQ.query.get_or_404(rid)
    quotation = Quotation.query.get_or_404(qid)
    if quotation.rfq_id != rfq.id:
        abort(400)
    # Reset all selections, mark this one
    for q in rfq.quotations.all():
        q.is_selected = False
    quotation.is_selected = True
    rfq.status = "Awarded"
    rfq.awarded_vendor_id = quotation.vendor_id
    log_activity("rfq_awarded", "rfq", rfq.id,
                 detail=f"vendor_id={quotation.vendor_id}")
    db.session.commit()
    flash(f"Awarded to {quotation.vendor.company_name}.", "success")
    return redirect(url_for("rfq.view", rid=rfq.id))


@rfq_bp.route("/<int:rid>/close", methods=["POST"])
@login_required
@admin_required
def close(rid):
    rfq = RFQ.query.get_or_404(rid)
    rfq.status = "Closed"
    log_activity("rfq_closed", "rfq", rfq.id)
    db.session.commit()
    flash("RFQ closed.", "info")
    return redirect(url_for("rfq.view", rid=rfq.id))


# ----- exports for the comparison table ----- #
@rfq_bp.route("/<int:rid>/compare.xlsx")
@login_required
@staff_or_admin_required
def compare_xlsx(rid):
    rfq = RFQ.query.get_or_404(rid)
    quotes = rfq.quotations.order_by(Quotation.unit_price.asc()).all()
    buf = quotations_compare_xlsx(rfq, quotes)
    return send_file(buf, as_attachment=True,
                     download_name=f"RFQ_{rfq.rfq_number}_compare.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@rfq_bp.route("/<int:rid>/compare.pdf")
@login_required
@staff_or_admin_required
def compare_pdf(rid):
    rfq = RFQ.query.get_or_404(rid)
    quotes = rfq.quotations.order_by(Quotation.unit_price.asc()).all()
    buf = quotations_compare_pdf(rfq, quotes)
    return send_file(buf, as_attachment=True,
                     download_name=f"RFQ_{rfq.rfq_number}_compare.pdf",
                     mimetype="application/pdf")


# --------------------------------------------------------------------------- #
#  VENDOR PORTAL
# --------------------------------------------------------------------------- #
@rfq_bp.route("/vendor")
@login_required
@vendor_required
def vendor_inbox():
    """List of RFQs that this vendor has been invited to."""
    vendor = current_user.vendor
    if not vendor:
        flash("Your account is not linked to a vendor profile yet.", "warning")
        return render_template("rfq/vendor_inbox.html", invites=[])
    invites = (RFQVendor.query.filter_by(vendor_id=vendor.id)
               .order_by(RFQVendor.email_sent_at.desc()).all())
    return render_template("rfq/vendor_inbox.html", invites=invites)


@rfq_bp.route("/invite/<token>", methods=["GET", "POST"])
def vendor_invite(token):
    """Public landing page from the email invite.

    Flow:
      - Vendor clicks the email link.
      - If not logged in, we show a friendly page asking them to log in or
        contact admin (we don't auto-create users).
      - Once logged in as the right vendor, they can submit the quotation.
    """
    rv = RFQVendor.query.filter_by(invite_token=token).first_or_404()
    rfq = rv.rfq
    if not current_user.is_authenticated or not current_user.is_vendor \
       or current_user.vendor is None or current_user.vendor.id != rv.vendor_id:
        return render_template("rfq/vendor_invite_landing.html",
                               rfq=rfq, vendor=rv.vendor)
    return redirect(url_for("rfq.vendor_quote", rid=rfq.id))


@rfq_bp.route("/vendor/<int:rid>/quote", methods=["GET", "POST"])
@login_required
@vendor_required
def vendor_quote(rid):
    rfq = RFQ.query.get_or_404(rid)
    vendor = current_user.vendor
    if not vendor:
        abort(403)
    invite = RFQVendor.query.filter_by(rfq_id=rid, vendor_id=vendor.id).first()
    if not invite:
        abort(403)

    quotation = Quotation.query.filter_by(rfq_id=rid, vendor_id=vendor.id).first()
    form = QuotationForm(obj=quotation)

    if form.validate_on_submit():
        if not quotation:
            quotation = Quotation(rfq_id=rid, vendor_id=vendor.id)
            db.session.add(quotation)
        quotation.unit_price = form.unit_price.data
        quotation.total_price = form.total_price.data or (
            (form.unit_price.data or 0) * (rfq.quantity or 0)
        )
        quotation.currency = form.currency.data
        quotation.delivery_days = form.delivery_days.data
        quotation.payment_terms = form.payment_terms.data
        quotation.warranty = form.warranty.data
        quotation.remarks = form.remarks.data

        if form.file.data:
            f = form.file.data
            fname = secure_filename(f"rfq{rid}_v{vendor.id}_{int(datetime.utcnow().timestamp())}_{f.filename}")
            target_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "quotations")
            os.makedirs(target_dir, exist_ok=True)
            path = os.path.join(target_dir, fname)
            f.save(path)
            quotation.file_path = os.path.relpath(path, current_app.root_path)

        invite.responded_at = datetime.utcnow()
        log_activity("quotation_submitted", "rfq", rid,
                     detail=f"vendor_id={vendor.id}")

        db.session.flush()
        send_quotation_received_alert(
            quotation, current_app.config["ADMIN_NOTIFY_EMAIL"]
        )
        db.session.commit()
        flash("Your quotation has been submitted. Thank you.", "success")
        return redirect(url_for("rfq.vendor_inbox"))

    return render_template("rfq/vendor_quote.html",
                           rfq=rfq, form=form, quotation=quotation)


@rfq_bp.route("/quotation/<int:qid>/file")
@login_required
@staff_or_admin_required
def download_quotation_file(qid):
    q = Quotation.query.get_or_404(qid)
    if not q.file_path:
        abort(404)
    full = os.path.join(current_app.root_path, q.file_path)
    if not os.path.isfile(full):
        abort(404)
    return send_file(full, as_attachment=True)
