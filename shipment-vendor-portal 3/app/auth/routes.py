"""Authentication routes — login, logout, password reset, change password."""
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app)
from flask_login import (login_user, logout_user, login_required,
                         current_user)
from urllib.parse import urlparse

from ..extensions import db
from ..models import User
from ..utils.audit import log_activity
from ..utils.tokens import (generate_password_reset_token,
                            verify_password_reset_token)
from ..utils.email import send_password_reset
from .forms import LoginForm, ForgotForm, ResetForm, ChangePasswordForm

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


def _safe_next(target):
    """Avoid open-redirect: only allow relative paths back into our app."""
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.netloc:
        return None
    return target


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember.data)
            user.last_login_at = datetime.utcnow()
            log_activity("login", "user", user.id)
            db.session.commit()
            flash(f"Welcome back, {user.name}!", "success")
            nxt = _safe_next(request.args.get("next"))
            if nxt:
                return redirect(nxt)
            if user.is_vendor:
                return redirect(url_for("rfq.vendor_inbox"))
            return redirect(url_for("dashboard.index"))
        flash("Invalid credentials or inactive account.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    log_activity("logout", "user", current_user.id)
    db.session.commit()
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    form = ForgotForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = generate_password_reset_token(user.email)
            link = url_for("auth.reset", token=token, _external=True)
            send_password_reset(user, link)
            db.session.commit()
        # Don't disclose whether the email exists
        flash("If the email is registered, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot.html", form=form)


@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    email = verify_password_reset_token(token)
    if not email:
        flash("Reset link is invalid or expired.", "danger")
        return redirect(url_for("auth.forgot"))

    user = User.query.filter_by(email=email).first_or_404()
    form = ResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        log_activity("password_reset", "user", user.id)
        db.session.commit()
        flash("Password updated. You can now log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset.html", form=form)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current.data):
            flash("Current password is wrong.", "danger")
        else:
            current_user.set_password(form.new.data)
            log_activity("password_changed", "user", current_user.id)
            db.session.commit()
            flash("Password changed.", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("auth/change_password.html", form=form)
