"""Auth/RBAC decorators."""
from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*roles):
    """Restrict a view to one of the given roles."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def admin_required(view):
    return role_required("admin")(view)


def staff_or_admin_required(view):
    return role_required("admin", "staff")(view)


def vendor_required(view):
    return role_required("vendor")(view)
