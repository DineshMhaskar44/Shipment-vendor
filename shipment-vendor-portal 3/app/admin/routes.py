"""Admin blueprint: user management, vendor approval, activity log, settings."""
import secrets
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app)
from flask_login import login_required, current_user
from sqlalchemy import desc

from ..extensions import db
from ..models import User, Vendor, ActivityLog, EmailLog
from ..utils.decorators import admin_required
from ..utils.audit import log_activity
from ..utils.email import send_user_welcome
from .forms import UserForm

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


# ------------------------------ USERS ------------------------------ #
@admin_bp.route("/users")
@login_required
@admin_required
def users():
    page = request.args.get("page", 1, type=int)
    q = User.query.order_by(User.created_at.desc())
    pagination = q.paginate(page=page,
                            per_page=current_app.config["ITEMS_PER_PAGE"])
    return render_template("admin/users.html", pagination=pagination)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@login_required
@admin_required
def user_new():
    form = UserForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower().strip()).first():
            flash("Email already in use.", "danger")
            return render_template("admin/user_form.html", form=form, title="New user")
        user = User(name=form.name.data.strip(),
                    email=form.email.data.strip().lower(),
                    role=form.role.data,
                    is_active=form.is_active.data)
        password = form.password.data or secrets.token_urlsafe(10)
        user.set_password(password)
        db.session.add(user)
        log_activity("user_created", "user", None,
                     detail=f"{user.email} role={user.role}")
        db.session.flush()
        send_user_welcome(user, password)
        db.session.commit()
        flash(f"User created. Temporary password: {password}", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, title="New user")


@admin_bp.route("/users/<int:uid>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def user_edit(uid):
    user = User.query.get_or_404(uid)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.name = form.name.data.strip()
        user.email = form.email.data.strip().lower()
        user.role = form.role.data
        user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        log_activity("user_updated", "user", user.id)
        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form,
                           title=f"Edit {user.email}")


@admin_bp.route("/users/<int:uid>/toggle", methods=["POST"])
@login_required
@admin_required
def user_toggle(uid):
    user = User.query.get_or_404(uid)
    if user.id == current_user.id:
        flash("You cannot disable yourself.", "warning")
        return redirect(url_for("admin.users"))
    user.is_active = not user.is_active
    log_activity("user_toggle", "user", user.id,
                 detail=f"active={user.is_active}")
    db.session.commit()
    flash("Access updated.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:uid>/delete", methods=["POST"])
@login_required
@admin_required
def user_delete(uid):
    user = User.query.get_or_404(uid)
    if user.id == current_user.id:
        flash("You cannot delete yourself.", "warning")
        return redirect(url_for("admin.users"))
    db.session.delete(user)
    log_activity("user_deleted", "user", uid)
    db.session.commit()
    flash("User deleted.", "info")
    return redirect(url_for("admin.users"))


# ------------------------------ VENDOR APPROVAL ------------------------------ #
@admin_bp.route("/vendor-approvals")
@login_required
@admin_required
def vendor_approvals():
    pending = Vendor.query.filter_by(is_approved=False).all()
    return render_template("admin/vendor_approvals.html", vendors=pending)


@admin_bp.route("/vendor-approvals/<int:vid>/approve", methods=["POST"])
@login_required
@admin_required
def vendor_approve(vid):
    vendor = Vendor.query.get_or_404(vid)
    vendor.is_approved = True
    log_activity("vendor_approved", "vendor", vendor.id)
    db.session.commit()
    flash(f"{vendor.company_name} approved.", "success")
    return redirect(url_for("admin.vendor_approvals"))


# ------------------------------ ACTIVITY LOG ------------------------------ #
@admin_bp.route("/activity")
@login_required
@admin_required
def activity():
    page = request.args.get("page", 1, type=int)
    q = ActivityLog.query.order_by(desc(ActivityLog.created_at))
    pagination = q.paginate(page=page,
                            per_page=current_app.config["ITEMS_PER_PAGE"])
    return render_template("admin/activity.html", pagination=pagination)


# ------------------------------ EMAIL LOG ------------------------------ #
@admin_bp.route("/emails")
@login_required
@admin_required
def emails():
    page = request.args.get("page", 1, type=int)
    q = EmailLog.query.order_by(desc(EmailLog.created_at))
    pagination = q.paginate(page=page,
                            per_page=current_app.config["ITEMS_PER_PAGE"])
    return render_template("admin/emails.html", pagination=pagination)


# ------------------------------ SETTINGS ------------------------------ #
@admin_bp.route("/settings")
@login_required
@admin_required
def settings():
    """Read-only view of effective settings.

    For simplicity we surface a curated subset of app.config. In a future
    revision we'd make these editable in DB and hot-reload.
    """
    keys = [
        "MAIL_SERVER", "MAIL_PORT", "MAIL_USE_TLS",
        "MAIL_DEFAULT_SENDER", "ADMIN_NOTIFY_EMAIL",
        "APP_BASE_URL", "ITEMS_PER_PAGE",
        "PAYMENT_GRACE_DAYS", "DELAY_THRESHOLD_DAYS",
    ]
    settings = {k: current_app.config.get(k) for k in keys}
    return render_template("admin/settings.html", settings=settings)
