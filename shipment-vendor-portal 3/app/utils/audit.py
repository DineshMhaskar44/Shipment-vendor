"""Activity-log helper used everywhere mutations happen."""
from flask import request
from flask_login import current_user
from ..extensions import db
from ..models import ActivityLog


def log_activity(action, target_type=None, target_id=None, detail=None):
    user_id = current_user.id if current_user.is_authenticated else None
    ip = request.headers.get("X-Forwarded-For", request.remote_addr) if request else None
    db.session.add(ActivityLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip_address=ip,
    ))
