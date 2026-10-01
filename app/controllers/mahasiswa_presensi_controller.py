from datetime import date
from operator import ge, le

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.models.presensi import Presensi
from app.utils.geofence import is_within_radius
from config import Config


def get_riwayat_presensi():
    user_id = int(get_jwt_identity())
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    query = Presensi.query.filter_by(user_id=user_id)

    for parameter, comparator in (("tanggal_mulai", ge), ("tanggal_selesai", le)):
        value = request.args.get(parameter)
        if not value:
            continue
        try:
            parsed_date = date.fromisoformat(value)
        except ValueError:
            return jsonify({"success": False, "message": f"Format {parameter} tidak valid.", "data": None}), 400
        query = query.filter(comparator(Presensi.tanggal, parsed_date))

    pagination = query.order_by(Presensi.tanggal.desc(), Presensi.waktu.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        "success": True,
        "message": "Riwayat presensi berhasil diambil.",
        "data": {
            "items": [item.to_dict() for item in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
        },
    }), 200


def get_status_hari_ini():
    user_id = int(get_jwt_identity())
    items = Presensi.query.filter_by(user_id=user_id, tanggal=date.today()).order_by(Presensi.waktu.asc()).all()
    return jsonify({"success": True, "message": "Status presensi hari ini berhasil diambil.", "data": [item.to_dict() for item in items]}), 200


def validasi_lokasi():
    payload = request.get_json(silent=True) or {}
    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"success": False, "message": "Latitude dan longitude wajib berupa angka.", "data": None}), 422

    inside, distance = is_within_radius(
        latitude, longitude,
        Config.GEOFENCE_CENTER_LATITUDE,
        Config.GEOFENCE_CENTER_LONGITUDE,
        Config.GEOFENCE_RADIUS_METERS,
    )
    return jsonify({
        "success": True,
        "message": "Lokasi berada di area asrama." if inside else "Lokasi berada di luar area asrama.",
        "data": {
            "allowed": inside,
            "distance_meters": round(distance, 2),
            "radius_meters": Config.GEOFENCE_RADIUS_METERS,
        },
    }), 200