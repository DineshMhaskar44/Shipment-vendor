"""Single-use, signed tokens for password reset & vendor RFQ invites."""
import secrets
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app


def _serializer(salt):
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=salt)


def generate_password_reset_token(email):
    return _serializer("password-reset").dumps(email)


def verify_password_reset_token(token, max_age_seconds=3600):
    try:
        return _serializer("password-reset").loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None


def random_invite_token() -> str:
    """Random opaque token for vendor RFQ invites."""
    return secrets.token_urlsafe(32)
