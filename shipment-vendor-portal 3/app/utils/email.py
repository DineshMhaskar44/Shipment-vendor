"""Outbound email helpers + EmailLog persistence.

Every send is wrapped in try/except so a flaky SMTP server never breaks a
business action — the failure is logged in EmailLog instead.
"""
from datetime import datetime
from flask import current_app, render_template, url_for
from flask_mail import Message
from ..extensions import mail, db
from ..models import EmailLog


def _log(to, subject, template, status, error=None,
         related_type=None, related_id=None):
    log = EmailLog(
        to_address=to, subject=subject, template=template, status=status,
        error=error, related_type=related_type, related_id=related_id,
    )
    db.session.add(log)
    # We don't commit here; caller commits with its own transaction.


def send_email(to, subject, template, context=None,
               related_type=None, related_id=None):
    """Render an email template (HTML + optional text) and send it.

    Templates live under app/templates/emails/. Provide '<template>.html' and
    optionally '<template>.txt'.
    """
    context = context or {}
    if isinstance(to, str):
        recipients = [to]
    else:
        recipients = list(to)

    try:
        html = render_template(f"emails/{template}.html", **context)
        try:
            body = render_template(f"emails/{template}.txt", **context)
        except Exception:
            body = None

        msg = Message(subject=subject, recipients=recipients,
                      html=html, body=body)
        mail.send(msg)
        for addr in recipients:
            _log(addr, subject, template, "sent",
                 related_type=related_type, related_id=related_id)
        return True
    except Exception as exc:
        current_app.logger.exception("Email send failed: %s", exc)
        for addr in recipients:
            _log(addr, subject, template, "failed", error=str(exc),
                 related_type=related_type, related_id=related_id)
        return False


# ---- High-level helpers used by routes ----
def send_rfq_invite(rfq, vendor, link, sender_name=None):
    return send_email(
        to=vendor.email,
        subject=f"[RFQ {rfq.rfq_number}] {rfq.title} — quotation request",
        template="rfq_invite",
        context={"rfq": rfq, "vendor": vendor, "link": link,
                 "sender_name": sender_name},
        related_type="rfq", related_id=rfq.id,
    )


def send_quotation_received_alert(quotation, admin_email):
    return send_email(
        to=admin_email,
        subject=f"[RFQ {quotation.rfq.rfq_number}] New quotation from {quotation.vendor.company_name}",
        template="quotation_received",
        context={"q": quotation, "rfq": quotation.rfq, "vendor": quotation.vendor},
        related_type="rfq", related_id=quotation.rfq_id,
    )


def send_shipment_delay_alert(shipment, admin_email):
    return send_email(
        to=admin_email,
        subject=f"[Shipment #{shipment.id}] Delay detected",
        template="shipment_delayed",
        context={"s": shipment},
        related_type="shipment", related_id=shipment.id,
    )


def send_password_reset(user, reset_link):
    return send_email(
        to=user.email,
        subject="Reset your password",
        template="password_reset",
        context={"user": user, "link": reset_link},
    )


def send_user_welcome(user, password):
    return send_email(
        to=user.email,
        subject="Your Shipment Portal account",
        template="user_welcome",
        context={"user": user, "password": password},
    )
