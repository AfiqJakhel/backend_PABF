from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def auth_required(fn):
    """Protect an endpoint for any authenticated user."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({
                "success": False,
                "message": "Token tidak valid atau sudah kadaluarsa. Silakan login kembali.",
                "data": None,
            }), 401
        return fn(*args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    """Protect an endpoint and enforce JWT role claims at the API boundary."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return jsonify({
                    "success": False,
                    "message": "Token tidak valid atau sudah kadaluarsa. Silakan login kembali.",
                    "data": None,
                }), 401
            if get_jwt().get("role") not in allowed_roles:
                return jsonify({
                    "success": False,
                    "message": "Akses ditolak untuk role pengguna ini.",
                    "data": None,
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    """Protect an endpoint for administrator accounts only."""
    return role_required("admin")(fn)