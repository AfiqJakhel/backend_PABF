"""
Controller untuk CRUD Area Absensi (Admin only).
Mengikuti pola controller existing di project.
"""

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.services.area_absensi_service import AreaAbsensiService
from app.schemas.area_absensi_schemas import validate_buat_area, validate_update_area


def get_semua_area():
    """
    GET /api/admin/area-absensi
    Daftar semua area absensi dengan filter opsional.
    Query params:
        aktif : "true" untuk hanya menampilkan area aktif
    """
    aktif_only = request.args.get("aktif", "").lower() == "true"
    data = AreaAbsensiService.get_semua_area(aktif_only=aktif_only)
    return jsonify({
        "success": True,
        "message": f"{len(data)} area absensi ditemukan.",
        "data": data
    }), 200


def buat_area():
    """
    POST /api/admin/area-absensi
    Buat area absensi baru.
    Body JSON:
        nama        : str (wajib)
        deskripsi   : str (opsional)
        coordinates : [[[lon, lat], ...]] (wajib — GeoJSON polygon)
        is_active   : bool (opsional, default true)
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Body JSON dibutuhkan.", "data": None}), 400

    errors, parsed = validate_buat_area(data)
    if errors:
        return jsonify({
            "success": False, "message": "Validasi gagal.",
            "errors": errors, "data": None
        }), 422

    admin_id = int(get_jwt_identity())
    result = AreaAbsensiService.buat_area(parsed, admin_id)
    return jsonify({
        "success": True,
        "message": f"Area absensi '{result['nama']}' berhasil dibuat.",
        "data": result
    }), 201


def get_detail_area(area_id: int):
    """
    GET /api/admin/area-absensi/<area_id>
    Detail satu area absensi.
    """
    result = AreaAbsensiService.get_area_by_id(area_id)
    if not result:
        return jsonify({"success": False, "message": "Area absensi tidak ditemukan.", "data": None}), 404
    return jsonify({"success": True, "message": "Detail area berhasil diambil.", "data": result}), 200


def update_area(area_id: int):
    """
    PUT /api/admin/area-absensi/<area_id>
    Update area absensi.
    Body JSON: nama, deskripsi, coordinates, is_active (semua opsional)
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Body JSON dibutuhkan.", "data": None}), 400

    errors, parsed = validate_update_area(data)
    if errors:
        return jsonify({
            "success": False, "message": "Validasi gagal.",
            "errors": errors, "data": None
        }), 422

    result, error = AreaAbsensiService.update_area(area_id, parsed)
    if error:
        return jsonify({"success": False, "message": error, "data": None}), 404

    return jsonify({
        "success": True,
        "message": f"Area absensi '{result['nama']}' berhasil diperbarui.",
        "data": result
    }), 200


def hapus_area(area_id: int):
    """
    DELETE /api/admin/area-absensi/<area_id>
    Hapus area absensi.
    """
    result, error = AreaAbsensiService.hapus_area(area_id)
    if error:
        return jsonify({"success": False, "message": error, "data": None}), 404

    return jsonify({
        "success": True,
        "message": "Area absensi berhasil dihapus.",
        "data": None
    }), 200


def toggle_active_area(area_id: int):
    """
    PATCH /api/admin/area-absensi/<area_id>/toggle
    Toggle status aktif/nonaktif area absensi.
    """
    result, error = AreaAbsensiService.toggle_active(area_id)
    if error:
        return jsonify({"success": False, "message": error, "data": None}), 404

    status_label = "diaktifkan" if result["is_active"] else "dinonaktifkan"
    return jsonify({
        "success": True,
        "message": f"Area absensi '{result['nama']}' berhasil {status_label}.",
        "data": result
    }), 200
