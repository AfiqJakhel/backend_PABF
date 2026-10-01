"""
Controller untuk fitur Fasilitator — Manajemen Sesi Absensi.
Bertanggung jawab atas:
  - Membuat sesi absensi baru
  - Melihat daftar / detail sesi
  - Menutup atau memperbarui sesi
"""

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.services.fasil_service import SesiAbsensiService
from app.schemas.fasil_schemas import validate_buat_sesi, validate_update_sesi


def buat_sesi():
    """
    POST /api/fasil/sesi
    Body JSON:
        nama_sesi     : str  (wajib)
        tipe_sesi     : str  'subuh' | 'malam' | 'kegiatan'  (default: 'malam')
        waktu_mulai   : str  ISO-8601  (wajib)
        waktu_selesai : str  ISO-8601  (wajib)
        keterangan    : str  (opsional)
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Body JSON dibutuhkan.", "data": None}), 400

    errors, parsed = validate_buat_sesi(data)
    if errors:
        return jsonify({
            "success": False,
            "message": "Validasi gagal.",
            "errors": errors,
            "data": None
        }), 422

    fasil_id = int(get_jwt_identity())
    sesi_data = SesiAbsensiService.buat_sesi(parsed, fasil_id)
    return jsonify({
        "success": True,
        "message": "Sesi absensi berhasil dibuat.",
        "data": sesi_data
    }), 201


def get_daftar_sesi():
    """
    GET /api/fasil/sesi
    Query params:
        page        : int   (default: 1)
        per_page    : int   (default: 15)
        status      : str   'aktif' | 'ditutup'     (opsional)
        tipe_sesi   : str   'subuh' | 'malam' | 'kegiatan'  (opsional)
        tanggal     : str   YYYY-MM-DD               (opsional)
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 15, type=int), 50)
    status = request.args.get("status")
    tipe_sesi = request.args.get("tipe_sesi")
    tanggal = request.args.get("tanggal")

    result = SesiAbsensiService.get_daftar_sesi(page, per_page, status, tipe_sesi, tanggal)

    if "error" in result:
        return jsonify({"success": False, "message": result["error"], "data": None}), 400

    return jsonify({"success": True, "message": "Daftar sesi berhasil diambil.", "data": result}), 200


def get_sesi_aktif():
    """
    GET /api/fasil/sesi/aktif
    Ambil semua sesi yang sedang aktif saat ini.
    """
    data = SesiAbsensiService.get_sesi_aktif()
    return jsonify({
        "success": True,
        "message": f"Ditemukan {len(data)} sesi aktif.",
        "data": data
    }), 200


def get_detail_sesi(sesi_id: int):
    """
    GET /api/fasil/sesi/<sesi_id>
    Ambil detail satu sesi berdasarkan ID.
    """
    data = SesiAbsensiService.get_sesi_by_id(sesi_id)
    if not data:
        return jsonify({"success": False, "message": "Sesi tidak ditemukan.", "data": None}), 404
    return jsonify({"success": True, "message": "Detail sesi berhasil diambil.", "data": data}), 200


def update_sesi(sesi_id: int):
    """
    PUT /api/fasil/sesi/<sesi_id>
    Body JSON (semua opsional, minimal satu):
        nama_sesi     : str
        status        : str  'aktif' | 'ditutup'
        waktu_selesai : str  ISO-8601
        keterangan    : str
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Body JSON dibutuhkan.", "data": None}), 400

    errors, parsed = validate_update_sesi(data)
    if errors:
        return jsonify({
            "success": False,
            "message": "Validasi gagal.",
            "errors": errors,
            "data": None
        }), 422

    result, error = SesiAbsensiService.update_sesi(sesi_id, parsed)
    if error:
        return jsonify({"success": False, "message": error, "data": None}), 404

    return jsonify({"success": True, "message": "Sesi berhasil diperbarui.", "data": result}), 200


def tutup_sesi(sesi_id: int):
    """
    PATCH /api/fasil/sesi/<sesi_id>/tutup
    Menutup sesi absensi secara manual. Tidak memerlukan body.
    """
    result, error = SesiAbsensiService.tutup_sesi(sesi_id)
    if error:
        status_code = 404 if "tidak ditemukan" in error else 409
        return jsonify({"success": False, "message": error, "data": None}), status_code

    return jsonify({"success": True, "message": "Sesi berhasil ditutup.", "data": result}), 200
