"""
Controller untuk fitur Fasilitator — Manajemen Pengajuan Izin.
Bertanggung jawab atas:
  - Melihat daftar pengajuan izin (dengan filter status)
  - Melihat detail satu pengajuan izin
  - Menyetujui atau menolak pengajuan izin
"""

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.services.fasil_service import IzinService
from app.schemas.fasil_schemas import validate_approval_izin


def get_daftar_izin():
    """
    GET /api/fasil/izin
    Ambil semua pengajuan izin mahasiswa.
    Query params:
        status      : str   'pending' | 'disetujui' | 'ditolak'  (opsional)
        page        : int   (default: 1)
        per_page    : int   (default: 15, max: 50)
    """
    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 15, type=int), 50)

    data = IzinService.get_daftar_izin(status=status, page=page, per_page=per_page)
    return jsonify({
        "success": True,
        "message": "Daftar izin berhasil diambil.",
        "data": data
    }), 200


def get_detail_izin(izin_id: int):
    """
    GET /api/fasil/izin/<izin_id>
    Ambil detail satu pengajuan izin berdasarkan ID.
    """
    data = IzinService.get_detail_izin(izin_id)
    if not data:
        return jsonify({
            "success": False,
            "message": "Pengajuan izin tidak ditemukan.",
            "data": None
        }), 404

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
        status          : str   'disetujui' | 'ditolak'  (wajib)
        catatan_fasil   : str   (wajib jika status 'ditolak')
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False, "message": "Body JSON dibutuhkan.", "data": None
        }), 400

    errors, parsed = validate_approval_izin(data)
    if errors:
        return jsonify({
            "success": False,
            "message": "Validasi gagal.",
            "errors": errors,
            "data": None
        }), 422

    fasil_id = int(get_jwt_identity())
    result, error = IzinService.proses_izin(izin_id, fasil_id, parsed)

    if error:
        # 404 jika tidak ditemukan, 409 jika sudah diproses sebelumnya
        status_code = 404 if "tidak ditemukan" in error else 409
        return jsonify({"success": False, "message": error, "data": None}), status_code

    action = "disetujui" if parsed["status"] == "disetujui" else "ditolak"
    return jsonify({
        "success": True,
        "message": f"Pengajuan izin berhasil {action}.",
        "data": result
    }), 200
