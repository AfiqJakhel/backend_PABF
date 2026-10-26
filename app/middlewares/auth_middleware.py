from functools import wraps

from flask import jsonify, g
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from app.models.user import User


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


def role_required(*allowed_roles, verify_db: bool = False):
    """
    Protect an endpoint and enforce role claims.
    Jika verify_db=True, verifikasi role langsung terhadap database untuk aksi sensitif.
    """
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

            claims = get_jwt()
            role_claim = claims.get("role")

            if role_claim not in allowed_roles:
                return jsonify({
                    "success": False,
                    "message": "Akses ditolak untuk role pengguna ini.",
                    "data": None,
                }), 403

            if verify_db:
                user_id = get_jwt_identity()
                user = User.query.get(user_id)
                if not user:
                    return jsonify({
                        "success": False,
                        "message": "Pengguna tidak ditemukan atau sesi tidak valid. Silakan login kembali.",
                        "data": None,
                    }), 401

                if user.role not in allowed_roles:
                    return jsonify({
                        "success": False,
                        "message": "Akses ditolak untuk role pengguna ini.",
                        "data": None,
                    }), 403

                # Simpan user objek di request context g untuk dipakai controller
                g.current_user = user

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    """Protect an endpoint for administrator accounts only."""
    return role_required("admin")(fn)