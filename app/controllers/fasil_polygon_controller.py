"""
Controller khusus Fasilitator untuk Manajemen Polygon Area Absensi.
Prinsip Inti:
  FACILITATOR -> 1 GEDUNG -> POLYGON PRESENSI

Fasilitator hanya berhak melihat, membuat, mengubah, dan menghapus polygon
yang diasosiasikan dengan gedung asrama binaannya.
IDOR Protection: Percobaan manipulasi polygon gedung lain akan ditolak dengan HTTP 403 Forbidden.
"""

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.repositories.area_absensi_repository import AreaAbsensiRepository
from app.schemas.area_absensi_schemas import validate_buat_area, validate_update_area
from app.services.fasil_scope_service import (
    resolve_fasil_building,
    validate_area_in_building,
)


def get_polygon_fasil():
    """
    GET /api/fasil/polygon
    Mengambil polygon area absensi khusus gedung binaan fasilitator yang sedang login.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    aktif_only = request.args.get("aktif", "").lower() == "true"
    areas = AreaAbsensiRepository.get_by_gedung(gedung.id, aktif_only=aktif_only)

    return jsonify({
        "success": True,
        "message": f"Daftar area polygon {gedung.nama_gedung} berhasil dimuat.",
        "data": {
            "gedung_id": gedung.id,
            "nama_gedung": gedung.nama_gedung,
            "areas": [a.to_dict() for a in areas]
        }
    }), 200


def buat_polygon_fasil():
    """
    POST /api/fasil/polygon
    Membuat polygon area absensi baru untuk gedung binaan fasilitator.
    Gedung ID dipaksakan dari gedung binaan fasilitator (anti-spoofing).
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Body JSON dibutuhkan.", "data": None}), 400

    errors, parsed = validate_buat_area(data)
    if errors:
        return jsonify({
            "success": False, "message": "Validasi gagal.",
            "errors": errors, "data": None
        }), 422

    fasil_id = int(get_jwt_identity())
    parsed["dibuat_oleh"] = fasil_id
    parsed["gedung_id"] = gedung.id

    area = AreaAbsensiRepository.create(parsed)

    return jsonify({
        "success": True,
        "message": f"Area polygon '{area.nama}' untuk {gedung.nama_gedung} berhasil dibuat.",
        "data": area.to_dict()
    }), 201


def update_polygon_fasil(area_id: int):
    """
    PUT /api/fasil/polygon/<area_id>
    Memperbarui polygon area absensi gedung binaan fasilitator.
    IDOR Protection: Menolak dengan 403 Forbidden jika area milik gedung lain.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    # IDOR Check
    area, err_msg, status_code = validate_area_in_building(area_id, gedung.id)
    if err_msg:
        return jsonify({"success": False, "message": err_msg, "data": None}), status_code

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Body JSON dibutuhkan.", "data": None}), 400

    errors, parsed = validate_update_area(data)
    if errors:
        return jsonify({
            "success": False, "message": "Validasi gagal.",
            "errors": errors, "data": None
        }), 422

    updated = AreaAbsensiRepository.update(area, parsed)

    return jsonify({
        "success": True,
        "message": f"Area polygon '{updated.nama}' berhasil diperbarui.",
        "data": updated.to_dict()
    }), 200


def hapus_polygon_fasil(area_id: int):
    """
    DELETE /api/fasil/polygon/<area_id>
    Menghapus polygon area absensi gedung binaan fasilitator.
    IDOR Protection: Menolak dengan 403 Forbidden jika area milik gedung lain.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    # IDOR Check
    area, err_msg, status_code = validate_area_in_building(area_id, gedung.id)
    if err_msg:
        return jsonify({"success": False, "message": err_msg, "data": None}), status_code

    nama_area = area.nama
    AreaAbsensiRepository.delete(area)

    return jsonify({
        "success": True,
        "message": f"Area polygon '{nama_area}' untuk {gedung.nama_gedung} berhasil dihapus.",
        "data": None
    }), 200


def toggle_active_polygon_fasil(area_id: int):
    """
    PATCH /api/fasil/polygon/<area_id>/toggle
    Toggle status aktif polygon area absensi gedung binaan fasilitator.
    IDOR Protection: Menolak dengan 403 Forbidden jika area milik gedung lain.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    # IDOR Check
    area, err_msg, status_code = validate_area_in_building(area_id, gedung.id)
    if err_msg:
        return jsonify({"success": False, "message": err_msg, "data": None}), status_code

    updated = AreaAbsensiRepository.toggle_active(area)

    return jsonify({
        "success": True,
        "message": f"Status area polygon '{updated.nama}' berhasil diubah menjadi {'Aktif' if updated.is_active else 'Nonaktif'}.",
        "data": updated.to_dict()
    }), 200
