from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.user import User
from app.utils.rate_limiter import login_rate_limiter

auth_bp = Blueprint('auth', __name__)

# Dummy password hash untuk timing-attack mitigation ketika user tidak ditemukan
_DUMMY_HASH = generate_password_hash("dummy_constant_password_12345")


@auth_bp.route('/login', methods=['POST'])
def login():
    """Endpoint untuk autentikasi pengguna (Mahasiswa, Fasilitator, Admin)."""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()

    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False,
            "message": "Permintaan tidak valid, data JSON dibutuhkan.",
            "data": None
        }), 400

    nim = str(data.get('nim', '')).strip()
    password = str(data.get('password', ''))

    if not nim or not password:
        return jsonify({
            "success": False,
            "message": "NIM dan kata sandi wajib diisi.",
            "data": None
        }), 400

    # Rate limiting berdasarkan kombinasi IP + NIM
    rate_key = f"{client_ip}:{nim}"
    max_attempts = current_app.config.get('LOGIN_RATE_LIMIT_ATTEMPTS', 5)
    window_sec = current_app.config.get('LOGIN_RATE_LIMIT_WINDOW_SECONDS', 900)

    if login_rate_limiter.is_rate_limited(rate_key, max_attempts=max_attempts, window_seconds=window_sec):
        return jsonify({
            "success": False,
            "message": "Terlalu banyak percobaan login yang gagal. Silakan coba lagi nanti dalam beberapa menit.",
            "data": None
        }), 429

    # Cari user berdasarkan NIM
    user = User.query.filter_by(nim=nim).first()

    # Cegah timing attack: selalu jalankan hashing check
    is_valid_pw = False
    if user:
        is_valid_pw = user.check_password(password)
    else:
        # Dummy check agar waktu komputasi seimbang
        check_password_hash(_DUMMY_HASH, password)

    if not user or not is_valid_pw:
        login_rate_limiter.record_attempt(rate_key, window_seconds=window_sec)
        # Pesan error tidak membedakan "user tidak ditemukan" dan "password salah"
        return jsonify({
            "success": False,
            "message": "NIM atau kata sandi yang Anda masukkan salah.",
            "data": None
        }), 401

    # Login sukses -> bersihkan hitungan rate limit
    login_rate_limiter.clear(rate_key)

    # Generate JWT Token
    additional_claims = {
        "role": user.role,
        "nim": user.nim,
        "nama": user.nama
    }
    access_token = create_access_token(identity=str(user.id), additional_claims=additional_claims)

    return jsonify({
        "success": True,
        "message": "Login berhasil.",
        "data": {
            "access_token": access_token,
            "user": user.to_dict()
        }
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """Mendapatkan profil pengguna yang sedang login berdasarkan JWT Token."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            "success": False,
            "message": "Pengguna tidak ditemukan atau sesi tidak valid.",
            "data": None
        }), 404

    return jsonify({
        "success": True,
        "message": "Data profil berhasil diambil.",
        "data": user.to_dict()
    }), 200
