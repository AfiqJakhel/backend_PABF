"""
Controller untuk fitur Fasilitator — Manajemen Pengajuan Izin (Legacy/Fasil Route).
Didelegasikan ke IzinService baru agar konsisten dengan scoping gedung dan status transisi atomic.
"""

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.models.user import User
from app.services.izin_service import IzinService
from app.schemas.izin_schemas import validate_review_izin


def _get_fasil_user() -> User:
    user_id = get_jwt_identity()
    return User.query.get(user_id)


def get_daftar_izin():
    """
    GET /api/fasil/izin
    Ambil semua pengajuan izin mahasiswa di gedung binaan fasilitator.
    Query params:
        status      : str   'pending' | 'approved' | 'rejected' | 'cancelled'
        page        : int   (default: 1)
        per_page    : int   (default: 15, max: 50)
    """
    user = _get_fasil_user()
    if not user:
        return jsonify({"success": False, "message": "Fasilitator tidak ditemukan.", "data": None}), 401

    raw_status = request.args.get("status")
    # Normalisasi query status lama (misal 'disetujui' -> 'approved')
    status_map = {"disetujui": "approved", "ditolak": "rejected"}
    status = status_map.get(raw_status, raw_status)

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 15, type=int), 50)

    data, err, status_code = IzinService.get_daftar_izin_review(user, status=status, page=page, per_page=per_page)
    if err:
        return jsonify({"success": False, "message": err, "data": None}), status_code

    return jsonify({
        "success": True,
        "message": "Daftar izin berhasil diambil.",
        "data": data
    }), 200


def get_detail_izin(izin_id: int):
    """
    GET /api/fasil/izin/<izin_id>
    Ambil detail satu pengajuan izin berdasarkan ID.
    Otorisasi gedung enforced (404 jika di luar gedung binaan).
    """
    user = _get_fasil_user()
    if not user:
        return jsonify({"success": False, "message": "Fasilitator tidak ditemukan.", "data": None}), 401

    data, err, status_code = IzinService.get_detail_izin(izin_id, user)
    if err:
        return jsonify({"success": False, "message": err, "data": None}), status_code

    return jsonify({
        "success": True,
        "message": "Detail izin berhasil diambil.",
        "data": data
    }), 200


def proses_izin(izin_id: int):
    """
    PATCH /api/fasil/izin/<izin_id>/proses
    Setujui atau tolak pengajuan izin mahasiswa.
    Body JSON:
        aksi / status   : str   'approve'/'disetujui' | 'reject'/'ditolak'
        catatan         : str   (wajib jika reject/ditolak)
    """
    user = _get_fasil_user()
    if not user:
        return jsonify({"success": False, "message": "Fasilitator tidak ditemukan.", "data": None}), 401

    data = request.get_json(silent=True)
    errors, parsed = validate_review_izin(data)
    if errors:
        return jsonify({
            "success": False,
            "message": "Validasi gagal.",
            "errors": errors,
            "data": None
        }), 422

    result, err, status_code = IzinService.review_izin(izin_id, user, parsed)
    if err:
        return jsonify({"success": False, "message": err, "data": None}), status_code

    action = "disetujui" if parsed["status"] == "approved" else "ditolak"
    return jsonify({
        "success": True,
        "message": f"Pengajuan izin berhasil {action}.",
        "data": result
    }), 200
