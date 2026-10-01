from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def fasil_required(fn):
    """
    Decorator/Middleware untuk memproteksi endpoint khusus Fasilitator.
    - Memverifikasi keberadaan token JWT yang valid.
    - Memverifikasi bahwa role user dalam token adalah 'fasil' atau 'admin'.

    Penggunaan:
        @fasil_required
        def some_endpoint():
            ...
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # 1. Verifikasi JWT — akan raise exception jika token tidak valid/tidak ada
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({
                "success": False,
                "message": "Token tidak valid atau sudah kadaluarsa. Silakan login kembali.",
                "data": None
            }), 401

        # 2. Ambil claims dari JWT dan cek role
        claims = get_jwt()
        role = claims.get("role", "")

        if role not in ("fasil", "admin"):
            return jsonify({
                "success": False,
                "message": "Akses ditolak. Endpoint ini hanya untuk Fasilitator atau Admin.",
                "data": None
            }), 403

        return fn(*args, **kwargs)

    return wrapper
