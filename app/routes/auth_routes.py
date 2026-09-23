from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Endpoint untuk autentikasi user (Mahasiswa / Admin)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False,
            "message": "Permintaan tidak valid, data JSON dibutuhkan.",
            "data": None
        }), 400

    nim = data.get('nim', '').strip()
    password = data.get('password', '')

    if not nim:
        return jsonify({
            "success": False,
            "message": "Nomor Induk Mahasiswa (NIM) wajib diisi.",
            "data": None
        }), 400

    if not password:
        return jsonify({
            "success": False,
            "message": "Kata sandi wajib diisi.",
            "data": None
        }), 400

    # Cari user berdasarkan NIM
    user = User.query.filter_by(nim=nim).first()

    if not user or not user.check_password(password):
        return jsonify({
            "success": False,
            "message": "NIM atau kata sandi yang Anda masukkan salah.",
            "data": None
        }), 401

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
            "message": "Pengguna tidak ditemukan.",
            "data": None
        }), 404

    return jsonify({
        "success": True,
        "message": "Data profil berhasil diambil.",
        "data": user.to_dict()
    }), 200
