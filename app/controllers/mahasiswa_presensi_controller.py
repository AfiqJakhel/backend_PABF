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

    user = User.query.get(user_id)
    student_gedung_id = None
    student_gedung_nama = None
    fasil_id = None
    if user and user.kamar_ref and user.kamar_ref.gedung:
        student_gedung_id = user.kamar_ref.gedung_id
        student_gedung_nama = user.kamar_ref.gedung.nama_gedung
        fasil_id = user.kamar_ref.gedung.user_id

    from app.models.sesi_absensi import SesiAbsensi
    sesi_keys = ["subuh", "malam", "kegiatan"]
    result_list = []

    for key in sesi_keys:
        if key == "kegiatan":
            # Cari sesi kegiatan yang dijadwalkan oleh Fasilitator gedung mahasiswa hari ini
            query = SesiAbsensi.query.filter(
                SesiAbsensi.tipe_sesi == 'kegiatan',
                SesiAbsensi.tanggal == tanggal_hari_ini
            )
            if fasil_id:
                query = query.filter(SesiAbsensi.dibuat_oleh == fasil_id)

            kegiatan_record = query.order_by(SesiAbsensi.created_at.desc()).first()

            if kegiatan_record:
                waktu_mulai = kegiatan_record.waktu_mulai
                waktu_selesai = kegiatan_record.waktu_selesai
                is_forced_closed = (kegiatan_record.status == 'ditutup')
                jam_mulai_str = waktu_mulai.strftime("%H:%M") if waktu_mulai else "08:00"
                jam_selesai_str = waktu_selesai.strftime("%H:%M") if waktu_selesai else "22:00"

                if is_forced_closed:
                    is_aktif = False
                    status_sesi = "tidak_aktif"
                    pesan_status = "Kegiatan telah ditutup oleh Fasilitator gedung."
                elif now < waktu_mulai:
                    is_aktif = False
                    status_sesi = "tidak_aktif"
                    pesan_status = f"Kegiatan belum dimulai. Dibuka pukul {jam_mulai_str} WIB."
                elif waktu_selesai and now > waktu_selesai:
                    is_aktif = False
                    status_sesi = "tidak_aktif"
                    pesan_status = f"Kegiatan telah berakhir pada pukul {jam_selesai_str} WIB."
                else:
                    is_aktif = True
                    status_sesi = "aktif"
                    pesan_status = f"Kegiatan sedang aktif berlangsung di {student_gedung_nama or 'gedung Anda'}."

                info = {
                    "tipe_sesi": "kegiatan",
                    "nama_sesi": kegiatan_record.nama_sesi,
                    "tanggal": tanggal_hari_ini.isoformat(),
                    "waktu_mulai": waktu_mulai.isoformat() if waktu_mulai else None,
                    "waktu_selesai": waktu_selesai.isoformat() if waktu_selesai else None,
                    "jam_mulai": jam_mulai_str,
                    "jam_selesai": jam_selesai_str,
                    "is_aktif": is_aktif,
                    "status_sesi": status_sesi,
                    "pesan_status": pesan_status,
                    "keterangan": kegiatan_record.keterangan,
                    "gedung_nama": student_gedung_nama,
                }
            else:
                info = {
                    "tipe_sesi": "kegiatan",
                    "nama_sesi": "Kegiatan Gedung",
                    "tanggal": tanggal_hari_ini.isoformat(),
                    "waktu_mulai": None,
                    "waktu_selesai": None,
                    "jam_mulai": "-",
                    "jam_selesai": "-",
                    "is_aktif": False,
                    "status_sesi": "tidak_aktif",
                    "pesan_status": f"Tidak ada kegiatan yang dijadwalkan oleh Fasilitator di {student_gedung_nama or 'gedung Anda'} hari ini.",
                    "keterangan": None,
                    "gedung_nama": student_gedung_nama,
                }
        else:
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
            "keterangan": info.get("keterangan"),
            "gedung_nama": info.get("gedung_nama"),
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
    user_id = int(get_jwt_identity())
    tanggal_hari_ini = date.today()
    now = datetime.now()
    from app.services.sesi_manager import resolve_sesi_info
    from app.models.sesi_absensi import SesiAbsensi

    user = User.query.get(user_id)
    fasil_id = None
    if user and user.kamar_ref and user.kamar_ref.gedung:
        fasil_id = user.kamar_ref.gedung.user_id

    aktif_list = []
    for key in ["subuh", "malam", "kegiatan"]:
        if key == "kegiatan":
            query = SesiAbsensi.query.filter(
                SesiAbsensi.tipe_sesi == 'kegiatan',
                SesiAbsensi.tanggal == tanggal_hari_ini
            )
            if fasil_id:
                query = query.filter(SesiAbsensi.dibuat_oleh == fasil_id)
            kegiatan_record = query.order_by(SesiAbsensi.created_at.desc()).first()
            if kegiatan_record and kegiatan_record.is_aktif:
                aktif_list.append(kegiatan_record.to_dict())
        else:
            info = resolve_sesi_info(key, target_date=tanggal_hari_ini, current_time=now)
            if info["is_aktif"]:
                aktif_list.append(info)

    return jsonify({
        "success": True,
        "message": "Sesi aktif berhasil diambil.",
        "data": aktif_list
    }), 200


def get_kegiatan_terjadwal():
    """
    GET /api/mahasiswa/presensi/kegiatan
    Mengambil daftar kegiatan asrama yang dijadwalkan oleh Fasilitator untuk gedung mahasiswa.
    """
    from datetime import datetime
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User tidak ditemukan.", "data": None}), 404

    student_gedung_nama = None
    fasil_id = None
    if user.kamar_ref and user.kamar_ref.gedung:
        student_gedung_nama = user.kamar_ref.gedung.nama_gedung
        fasil_id = user.kamar_ref.gedung.user_id

    from app.models.sesi_absensi import SesiAbsensi
    from app.models.presensi import Presensi

    # Ambil kegiatan asrama yang dibuat oleh fasilitator gedung (atau semua kegiatan jika belum ditugaskan gedung)
    query = SesiAbsensi.query.filter(SesiAbsensi.tipe_sesi == 'kegiatan')
    if fasil_id:
        query = query.filter(SesiAbsensi.dibuat_oleh == fasil_id)

    # Ambil kegiatan (urutkan tanggal terbaru / mendatang)
    kegiatan_records = query.order_by(SesiAbsensi.tanggal.desc(), SesiAbsensi.waktu_mulai.desc()).limit(20).all()

    # Ambil catatan presensi kegiatan yang sudah dilakukan mahasiswa
    presensi_kegiatan = Presensi.query.filter_by(user_id=user_id, sesi='kegiatan').all()
    presensi_date_map = {p.tanggal: p for p in presensi_kegiatan}

    now = datetime.now()
    items = []
    for k in kegiatan_records:
        k_waktu_mulai = k.waktu_mulai
        k_waktu_selesai = k.waktu_selesai

        jam_mulai_str = k_waktu_mulai.strftime("%H:%M") if k_waktu_mulai else "-"
        jam_selesai_str = k_waktu_selesai.strftime("%H:%M") if k_waktu_selesai else None
        jam_formatted = f"{jam_mulai_str} - {jam_selesai_str} WIB" if jam_selesai_str else f"{jam_mulai_str} WIB"

        presensi_item = presensi_date_map.get(k.tanggal)
        sudah_absen = presensi_item is not None

        # Tentukan keaktifan sesi berdasarkan status & waktu lokal
        is_currently_active = False
        if k.status == 'aktif' and k_waktu_mulai:
            if k_waktu_selesai:
                is_currently_active = (k_waktu_mulai <= now <= k_waktu_selesai)
            else:
                is_currently_active = (k_waktu_mulai <= now)

        if sudah_absen:
            status = "sudah_absen"
            status_label = "SUDAH ABSEN"
        elif k.status == 'ditutup':
            status = "selesai"
            status_label = "DITUTUP"
        elif k_waktu_selesai and now > k_waktu_selesai:
            status = "selesai"
            status_label = "SELESAI"
        elif is_currently_active:
            status = "aktif"
            status_label = "SEDANG AKTIF"
        elif k_waktu_mulai and now < k_waktu_mulai:
            status = "akan_datang"
            status_label = "AKAN DATANG"
        else:
            status = "selesai"
            status_label = "SELESAI"

        items.append({
            "id": k.id,
            "nama_kegiatan": k.nama_sesi,
            "tanggal": k.tanggal.isoformat() if k.tanggal else None,
            "waktu_mulai": k_waktu_mulai.isoformat() if k_waktu_mulai else None,
            "waktu_selesai": k_waktu_selesai.isoformat() if k_waktu_selesai else None,
            "jam_formatted": jam_formatted,
            "jam_mulai": jam_mulai_str,
            "jam_selesai": jam_selesai_str,
            "lokasi": student_gedung_nama or "Asrama UNAND",
            "keterangan": k.keterangan or "-",
            "nama_fasilitator": k.fasilitator.nama if k.fasilitator else "Fasilitator Asrama",
            "status": status,
            "status_label": status_label,
            "is_aktif": is_currently_active,
            "sudah_absen": sudah_absen,
            "can_absen": bool(is_currently_active and not sudah_absen and k.status != 'ditutup')
        })

    return jsonify({
        "success": True,
        "message": "Daftar kegiatan asrama terjadwal berhasil diambil.",
        "data": {
            "gedung_nama": student_gedung_nama,
            "total": len(items),
            "items": items
        }
    }), 200
