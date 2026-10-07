from datetime import date
from operator import ge, le

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.models.presensi import Presensi
from app.models.user import User
from app.utils.geofence import is_within_radius
from app.schemas.mahasiswa_schemas import validate_submit_absensi
from app.services.mahasiswa_presensi_service import MahasiswaPresensiService
from app.repositories.sesi_absensi_repository import SesiAbsensiRepository
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


from app.repositories.area_absensi_repository import AreaAbsensiRepository


def validasi_lokasi():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User tidak ditemukan.", "data": None}), 404

    payload = request.get_json(silent=True) or {}
    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"success": False, "message": "Latitude dan longitude wajib berupa angka.", "data": None}), 422

    accuracy = None
    if "accuracy" in payload and payload["accuracy"] is not None:
        try:
            accuracy = float(payload["accuracy"])
        except (ValueError, TypeError):
            pass

    student_gedung_id = None
    gedung_nama = None
    if user.kamar_ref and user.kamar_ref.gedung:
        student_gedung_id = user.kamar_ref.gedung_id
        gedung_nama = user.kamar_ref.gedung.nama_gedung

    # Cari polygon gedung mahasiswa yang mencakup titik koordinat
    area = AreaAbsensiRepository.find_area_containing_point(
        latitude, longitude, gedung_id=student_gedung_id
    )

    inside = area is not None
    area_nama = area.nama if area else None

    # Evaluasi status akurasi sinyal GPS
    max_accuracy = Config.MAX_GPS_ACCURACY_METERS
    accuracy_sufficient = accuracy is None or accuracy <= max_accuracy

    message = (
        f"Lokasi terverifikasi di dalam {area_nama}."
        if inside
        else "Lokasi berada di luar area polygon gedung Anda."
    )

    return jsonify({
        "success": True,
        "message": message,
        "data": {
            "allowed": inside,
            "inside_polygon": inside,
            "area_id": area.id if area else None,
            "area_nama": area_nama,
            "gedung_id": student_gedung_id,
            "gedung_nama": gedung_nama,
            "accuracy": accuracy,
            "max_allowed_accuracy": max_accuracy,
            "accuracy_sufficient": accuracy_sufficient,
        },
    }), 200


def submit_absensi():
    """
    POST /api/mahasiswa/presensi/absen
    Submit absensi mahasiswa dengan foto selfie dan data GPS.

    Request: multipart/form-data
        foto      : file image (wajib)
        latitude  : float (wajib)
        longitude : float (wajib)
        accuracy  : float (opsional)

    Validasi backend:
        - User sudah login & role mahasiswa (via middleware)
        - File foto valid (MIME + ukuran)
        - Koordinat GPS valid
        - Akurasi GPS <= MAX_GPS_ACCURACY_METERS
        - Ada sesi absensi aktif
        - Belum pernah absen sesi ini hari ini
        - Koordinat berada di dalam polygon area absensi aktif (ST_Contains)
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User tidak ditemukan.", "data": None}), 404

    errors, parsed = validate_submit_absensi(request.form, request.files)
    if errors:
        return jsonify({
            "success": False,
            "message": "Validasi gagal.",
            "errors": errors,
            "data": None
        }), 422

    result, error = MahasiswaPresensiService.submit_absensi(user_id, user.nim, parsed)

    if error:
        # error adalah dict dengan message, code, location_valid, dll.
        status_code = 409 if error.get("code") == "DUPLICATE_ATTENDANCE" else 422
        return jsonify({
            "success": False,
            "message": error["message"],
            "data": {k: v for k, v in error.items() if k != "message"},
        }), status_code

    success_msg = (
        "Absensi berhasil dicatat."
        if result.get("location_valid")
        else "Absensi berhasil dicatat (lokasi berada di luar area geofencing)."
    )
    return jsonify({
        "success": True,
        "message": success_msg,
        "data": result,
    }), 201


def get_sesi_hari_ini():
    """
    GET /api/mahasiswa/presensi/sesi
    Mengembalikan daftar sesi presensi hari ini (Subuh & Malam),
    lengkap dengan jam mulai, jam selesai, status aktif/tidak aktif,
    dan status apakah mahasiswa yang sedang login sudah melakukan presensi.
    """
    from datetime import datetime
    user_id = int(get_jwt_identity())
    tanggal_hari_ini = date.today()
    now = datetime.now()

    from app.services.sesi_manager import resolve_sesi_info
    from app.models.presensi import Presensi

    # Ambil seluruh record presensi mahasiswa untuk hari ini
    today_records = Presensi.query.filter_by(user_id=user_id, tanggal=tanggal_hari_ini).all()
    record_map = {r.sesi: r for r in today_records}

    sesi_keys = ["subuh", "malam"]
    result_list = []

    for key in sesi_keys:
        info = resolve_sesi_info(key, target_date=tanggal_hari_ini, current_time=now)
        presensi = record_map.get(key)
        sudah_absen = presensi is not None

        item = {
            "tipe_sesi": info["tipe_sesi"],
            "nama_sesi": info["nama_sesi"],
            "tanggal": info["tanggal"],
            "waktu_mulai": info["waktu_mulai"],
            "waktu_selesai": info["waktu_selesai"],
            "jam_mulai": info["jam_mulai"],
            "jam_selesai": info["jam_selesai"],
            "is_aktif": info["is_aktif"],
            "status_sesi": info["status_sesi"],
            "pesan_status": info["pesan_status"],
            "sudah_absen": sudah_absen,
            "presensi_info": {
                "id": presensi.id,
                "status": presensi.status,
                "waktu": presensi.waktu.isoformat() if presensi.waktu else None,
                "location_valid": bool(presensi.area_absensi_id),
                "area_nama": presensi.area.nama if presensi.area else ("Di Luar Area" if presensi.latitude is not None else None),
                "keterangan": presensi.keterangan,
            } if sudah_absen else None
        }
        result_list.append(item)

    return jsonify({
        "success": True,
        "message": "Daftar sesi presensi hari ini berhasil diambil.",
        "data": {
            "tanggal": tanggal_hari_ini.isoformat(),
            "server_time": now.isoformat(),
            "sesi_list": result_list,
        }
    }), 200


def get_sesi_aktif():
    """
    GET /api/mahasiswa/presensi/sesi-aktif
    Mendapatkan daftar sesi absensi yang sedang aktif untuk mahasiswa.
    """
    from datetime import datetime
    tanggal_hari_ini = date.today()
    now = datetime.now()
    from app.services.sesi_manager import resolve_sesi_info
    aktif_list = []
    for key in ["subuh", "malam"]:
        info = resolve_sesi_info(key, target_date=tanggal_hari_ini, current_time=now)
        if info["is_aktif"]:
            aktif_list.append(info)
    return jsonify({
        "success": True,
        "message": "Sesi aktif berhasil diambil.",
        "data": aktif_list
    }), 200
