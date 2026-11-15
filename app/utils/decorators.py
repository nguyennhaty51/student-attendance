from functools import wraps
from flask import abort
from flask_login import current_user, login_required


def role_required(*roles):
    """Chỉ cho phép người dùng thuộc các vai trò chỉ định truy cập."""
    allowed = {r.value.upper() if hasattr(r, "value") else str(r).upper() for r in roles}

    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            user_role = current_user.role.value.upper() if hasattr(current_user.role, "value") else str(current_user.role).upper()
            if user_role not in allowed:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator