"""
Controller untuk fitur Fasilitator — Monitoring & Rekapitulasi Presensi.
Bertanggung jawab atas:
  - Real-time monitoring kehadiran per sesi (Gedung-Scoped)
  - Update status presensi secara manual (Anti-IDOR)
  - Input presensi manual untuk mahasiswa yang belum absen (Anti-IDOR)
  - Download/tampilkan rekap berdasarkan rentang tanggal (Gedung-Scoped)
  - Verifikasi foto presensi (Gedung-Scoped)
  - Export data presensi CSV (Gedung-Scoped, anti-spoofing)
"""

import io
import csv
from datetime import date, datetime, time
from flask import request, jsonify, Response
from flask_jwt_extended import get_jwt_identity
from app.core.extensions import db
from app.models.presensi import Presensi
from app.models.user import User
from app.models.kamar import Kamar
from app.services.fasil_service import PresensiService
from app.schemas.fasil_schemas import validate_update_presensi_manual, STATUS_PRESENSI_VALID, TIPE_SESI_VALID
from app.services.fasil_scope_service import (
    resolve_fasil_building,
    validate_presensi_in_building,
    validate_student_in_building,
)


def get_rekap_sesi():
    """
    GET /api/fasil/presensi/sesi
    Real-time: siapa sudah/belum absen untuk sesi tertentu hari ini.
    Query params:
        sesi    : str  'subuh' | 'malam' | 'kegiatan'  (wajib)
        tanggal : str  YYYY-MM-DD                       (wajib)
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    tipe_sesi = request.args.get("sesi", "").strip()
    tanggal_str = request.args.get("tanggal", "").strip()

    if not tipe_sesi:
        return jsonify({
            "success": False, "message": "'sesi' wajib diisi sebagai query parameter.", "data": None
        }), 400
    if not tanggal_str:
        return jsonify({
            "success": False, "message": "'tanggal' wajib diisi sebagai query parameter.", "data": None
        }), 400

    data, error = PresensiService.get_rekap_sesi(tipe_sesi, tanggal_str, gedung_id=gedung.id)
    if error:
        return jsonify({"success": False, "message": error, "data": None}), 400

    data["gedung_id"] = gedung.id
    data["nama_gedung"] = gedung.nama_gedung

    return jsonify({"success": True, "message": f"Rekap sesi berhasil diambil untuk {gedung.nama_gedung}.", "data": data}), 200


def update_presensi_manual(presensi_id: int):
    """
    PATCH /api/fasil/presensi/<presensi_id>/status
    Ubah status kehadiran mahasiswa yang sudah memiliki record presensi.
    IDOR Protection: Menolak jika record presensi milik gedung lain.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    # IDOR Check
    presensi, err_msg, status_code = validate_presensi_in_building(presensi_id, gedung.id)
    if err_msg:
        return jsonify({"success": False, "message": err_msg, "data": None}), status_code

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Body JSON dibutuhkan.", "data": None}), 400

    errors, parsed = validate_update_presensi_manual(data)
    if errors:
        return jsonify({
            "success": False, "message": "Validasi gagal.", "errors": errors, "data": None
        }), 422

    result, error = PresensiService.update_status_manual(presensi_id, parsed)
    if error:
        return jsonify({"success": False, "message": error, "data": None}), 404

    return jsonify({
        "success": True, "message": "Status presensi berhasil diperbarui.", "data": result
    }), 200


def input_presensi_manual():
    """
    POST /api/fasil/presensi/manual
    Buat record presensi baru secara manual (untuk mahasiswa yang belum absen sama sekali).
    IDOR Protection: Menolak jika user_id bukan mahasiswa di gedung binaan fasilitator.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Body JSON dibutuhkan.", "data": None}), 400

    errors = []
    user_id = data.get("user_id")
    sesi = data.get("sesi", "").strip()
    status = data.get("status", "").strip().lower()
    keterangan = data.get("keterangan", "").strip() or None
    tanggal_str = data.get("tanggal")

    if not user_id or not isinstance(user_id, int):
        errors.append("'user_id' wajib diisi dan harus berupa integer.")
    if not sesi or sesi not in TIPE_SESI_VALID:
        errors.append(f"'sesi' wajib diisi dan harus salah satu dari: {', '.join(sorted(TIPE_SESI_VALID))}.")
    if not status or status not in STATUS_PRESENSI_VALID:
        errors.append(f"'status' wajib diisi dan harus salah satu dari: {', '.join(sorted(STATUS_PRESENSI_VALID))}.")

    tanggal = None
    if tanggal_str:
        try:
            tanggal = date.fromisoformat(tanggal_str)
        except ValueError:
            errors.append("Format 'tanggal' tidak valid. Gunakan YYYY-MM-DD.")

    if errors:
        return jsonify({
            "success": False, "message": "Validasi gagal.", "errors": errors, "data": None
        }), 422

    # IDOR Check: Ensure student is in facilitator's building
    student, err_msg, status_code = validate_student_in_building(user_id, gedung.id)
    if err_msg:
        return jsonify({"success": False, "message": err_msg, "data": None}), status_code

    tanggal = tanggal or date.today()

    # Cek apakah sudah ada record untuk hari ini dan sesi ini
    existing = Presensi.query.filter_by(
        user_id=user_id, tanggal=tanggal, sesi=sesi
    ).first()
    if existing:
        return jsonify({
            "success": False,
            "message": f"Mahasiswa sudah memiliki record presensi untuk sesi '{sesi}' pada tanggal {tanggal.isoformat()}.",
            "data": None
        }), 409

    from app.repositories.fasil_repository import PresensiRepository
    presensi = PresensiRepository.create_manual({
        "user_id": user_id,
        "nim": student.nim,
        "tanggal": tanggal,
        "waktu": datetime.utcnow(),
        "sesi": sesi,
        "status": status,
        "keterangan": keterangan,
        "gedung_id": gedung.id
    })

    return jsonify({
        "success": True, "message": "Presensi manual berhasil diinput.", "data": presensi.to_dict()
    }), 201


def get_rekap_rentang():
    """
    GET /api/fasil/presensi/rekap
    Rekap presensi berdasarkan rentang tanggal (Scoped to Facilitator's Building).
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    tgl_mulai = request.args.get("tanggal_mulai", "").strip()
    tgl_selesai = request.args.get("tanggal_selesai", "").strip()
    tipe_sesi = request.args.get("sesi") or None
    user_id = request.args.get("user_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    summary = request.args.get("summary", "false").lower() == "true"

    if not tgl_mulai or not tgl_selesai:
        return jsonify({
            "success": False,
            "message": "'tanggal_mulai' dan 'tanggal_selesai' wajib diisi.",
            "data": None
        }), 400

    # IDOR Check if filtering by specific user_id
    if user_id:
        student, err_msg, status_code = validate_student_in_building(user_id, gedung.id)
        if err_msg:
            return jsonify({"success": False, "message": err_msg, "data": None}), status_code

    data, error = PresensiService.get_rekap_rentang(
        tgl_mulai, tgl_selesai, tipe_sesi, user_id, page, per_page, summary, gedung_id=gedung.id
    )
    if error:
        return jsonify({"success": False, "message": error, "data": None}), 400

    data["gedung_id"] = gedung.id
    data["nama_gedung"] = gedung.nama_gedung

    return jsonify({"success": True, "message": "Rekap presensi berhasil diambil.", "data": data}), 200


def resolve_sesi_time_window(tipe_sesi: str, target_date: date):
    """
    Menentukan rentang waktu sesi (waktu_mulai, waktu_selesai) dan status waktu aktif/berakhir
    berdasarkan tabel SesiAbsensi atau default jam sesi operasional asrama.
    """
    from app.services.sesi_manager import resolve_sesi_info
    info = resolve_sesi_info(tipe_sesi, target_date=target_date)
    return info["waktu_mulai_dt"], info["waktu_selesai_dt"], info["is_aktif"], info["is_ended"]


def get_daftar_verifikasi():
    """
    GET /api/fasil/presensi/verifikasi
    Daftar verifikasi presensi seluruh mahasiswa di gedung binaan fasilitator.
    Dibatasi ketat hanya untuk mahasiswa pada gedung binaan fasilitator!
    Seluruh mahasiswa di gedung binaan akan ditampilkan, terlepas dari apakah sudah absen atau belum.
    Status dihitung secara dinamis berdasarkan waktu server dan ketersediaan record presensi:
      - Sudah absen: status dari record presensi (hadir, terlambat, izin, sakit, alfa)
      - Belum absen & waktu belum berakhir: belum_absen
      - Belum absen & waktu berakhir: alfa
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    tanggal_aktif = date.today()
    now = datetime.now()
    tipe_sesi = (request.args.get("sesi", "").strip().lower() or "subuh")
    if tipe_sesi not in TIPE_SESI_VALID:
        return jsonify({
            "success": False,
            "message": f"'sesi' harus salah satu dari: {', '.join(sorted(TIPE_SESI_VALID))}.",
            "data": None
        }), 400

    status_filter = request.args.get("status", "").strip().lower()
    search = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)

    # 1. Resolusi rentang waktu sesi & status aktif / berakhir
    waktu_mulai, waktu_selesai, is_active, is_ended = resolve_sesi_time_window(tipe_sesi, tanggal_aktif)

    # 2. Query seluruh mahasiswa binaan di gedung fasilitator ini
    mahasiswa_query = (
        User.query
        .join(Kamar, User.kamar_id == Kamar.id)
        .filter(User.role == 'mahasiswa', Kamar.gedung_id == gedung.id)
    )

    if search:
        search_like = f"%{search}%"
        mahasiswa_query = mahasiswa_query.filter(
            db.or_(User.nama.ilike(search_like), User.nim.ilike(search_like))
        )

    mahasiswa_list = mahasiswa_query.order_by(Kamar.nomor_kamar.asc(), User.nama.asc()).all()

    # 3. Lookup data presensi untuk mahasiswa-mahasiswa tersebut pada tanggal dan sesi ini
    mhs_ids = [m.id for m in mahasiswa_list]
    presensi_map = {}
    if mhs_ids:
        records = Presensi.query.filter(
            Presensi.tanggal == tanggal_aktif,
            Presensi.sesi == tipe_sesi,
            Presensi.user_id.in_(mhs_ids)
        ).all()
        presensi_map = {p.user_id: p for p in records}

    # 4. Gabungkan seluruh mahasiswa dengan data presensi
    items = []
    counts = {
        "all": len(mahasiswa_list),
        "belum_absen": 0,
        "hadir": 0,
        "alfa": 0,
        "terlambat": 0,
        "izin": 0,
        "sakit": 0,
        "luar_zona": 0,
        "dalam_zona": 0,
    }

    for m in mahasiswa_list:
        p = presensi_map.get(m.id)
        kamar_nomor = m.kamar_ref.nomor_kamar if m.kamar_ref else "-"

        if p:
            item = p.to_dict()
            item['nama_mahasiswa'] = m.nama
            item['nim'] = m.nim
            item['gedung'] = gedung.nama_gedung
            item['kamar'] = kamar_nomor
            item['has_record'] = True

            # Validasi batas akhir waktu sesi:
            # Jika waktu presensi melewati batas akhir sesi (misal subuh berakhir 07:00 tapi absen jam 16:54),
            # maka presensi dianggap tidak sah dan status otomatis menjadi ALFA.
            is_lewat_batas_waktu = False
            if p.waktu and waktu_selesai and p.waktu > waktu_selesai:
                is_lewat_batas_waktu = True

            if is_lewat_batas_waktu and p.status.lower() not in ("izin", "sakit"):
                current_status = "alfa"
                item['status'] = "alfa"
                ket_lewat = "Presensi melewati batas waktu sesi (Alfa)"
                if not item.get('keterangan'):
                    item['keterangan'] = ket_lewat
                elif "melewati batas waktu" not in item['keterangan']:
                    item['keterangan'] = f"{item['keterangan']} | {ket_lewat}"

                # Sinkronkan ke database jika record sebelumnya berstatus hadir/terlambat
                if p.status != "alfa":
                    p.status = "alfa"
                    if not p.keterangan:
                        p.keterangan = ket_lewat
                    elif "melewati batas waktu" not in p.keterangan:
                        p.keterangan = f"{p.keterangan} | {ket_lewat}"
                    db.session.commit()
            else:
                current_status = p.status.lower()

            if not p.area_absensi_id and p.latitude is not None:
                counts["luar_zona"] += 1
            elif p.area_absensi_id:
                counts["dalam_zona"] += 1
        else:
            current_status = "alfa" if is_ended else "belum_absen"
            keterangan_default = "Tidak hadir presensi (Alfa otomatis)" if is_ended else "Belum melakukan presensi"
            item = {
                'id': None,
                'user_id': m.id,
                'nim': m.nim,
                'nama_mahasiswa': m.nama,
                'gedung_id': gedung.id,
                'gedung': gedung.nama_gedung,
                'kamar': kamar_nomor,
                'tanggal': tanggal_aktif.isoformat(),
                'waktu': None,
                'sesi': tipe_sesi,
                'latitude': None,
                'longitude': None,
                'accuracy': None,
                'area_absensi_id': None,
                'area_nama': None,
                'location_valid': False,
                'status': current_status,
                'foto_wajah': None,
                'foto_url': None,
                'keterangan': keterangan_default,
                'created_at': None,
                'has_record': False
            }

        if current_status in counts:
            counts[current_status] += 1

        items.append(item)

    # 5. Terapkan filter status jika ada
    if status_filter and status_filter != "all":
        if status_filter == "luar_zona":
            filtered_items = [it for it in items if it.get('has_record') and not it.get('location_valid')]
        elif status_filter == "dalam_zona":
            filtered_items = [it for it in items if it.get('has_record') and it.get('location_valid')]
        elif status_filter == "belum_absen":
            filtered_items = [it for it in items if it.get('status') == "belum_absen"]
        else:
            filtered_items = [it for it in items if it.get('status') == status_filter]
    else:
        filtered_items = items

    total = len(filtered_items)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_items = filtered_items[start_idx:end_idx]
    pages = (total + per_page - 1) // per_page if total > 0 else 1

    return jsonify({
        "success": True,
        "message": f"Daftar verifikasi presensi {gedung.nama_gedung} berhasil diambil.",
        "data": {
            "gedung_id": gedung.id,
            "nama_gedung": gedung.nama_gedung,
            "tanggal": tanggal_aktif.isoformat(),
            "sesi": tipe_sesi,
            "server_time": now.isoformat(),
            "waktu_mulai": waktu_mulai.isoformat() if waktu_mulai else None,
            "waktu_selesai": waktu_selesai.isoformat() if waktu_selesai else None,
            "is_active": is_active,
            "is_ended": is_ended,
            "counts": counts,
            "items": paginated_items,
            "total": total,
            "page": page,
            "pages": pages,
            "per_page": per_page,
        }
    }), 200


def export_rekap():
    """
    GET /api/fasil/presensi/export
    Ekspor data rekapitulasi presensi ke berkas CSV.
    ANTI-SPOOFING: Mengabaikan query param building_id/gedung_id!
    Selalu mengekspor data gedung binaan fasilitator yang sedang login.
    Query params:
        tanggal_mulai   : str YYYY-MM-DD (wajib)
        tanggal_selesai : str YYYY-MM-DD (wajib)
        sesi            : str (opsional)
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    tgl_mulai_str = request.args.get("tanggal_mulai", "").strip()
    tgl_selesai_str = request.args.get("tanggal_selesai", "").strip()
    tipe_sesi = request.args.get("sesi", "").strip() or None

    if not tgl_mulai_str or not tgl_selesai_str:
        return jsonify({
            "success": False,
            "message": "'tanggal_mulai' dan 'tanggal_selesai' wajib diisi.",
            "data": None
        }), 400

    try:
        tgl_mulai = date.fromisoformat(tgl_mulai_str)
        tgl_selesai = date.fromisoformat(tgl_selesai_str)
    except ValueError:
        return jsonify({"success": False, "message": "Format tanggal harus YYYY-MM-DD.", "data": None}), 400

    # Query all records for this building
    query = (
        Presensi.query
        .filter(
            Presensi.tanggal >= tgl_mulai,
            Presensi.tanggal <= tgl_selesai,
            db.or_(
                Presensi.gedung_id == gedung.id,
                Presensi.user.has(User.kamar_ref.has(Kamar.gedung_id == gedung.id))
            )
        )
    )
    if tipe_sesi and tipe_sesi != "all":
        query = query.filter(Presensi.sesi == tipe_sesi)

    records = query.order_by(Presensi.tanggal.desc(), Presensi.waktu.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "NIM",
        "Nama Mahasiswa",
        "Gedung",
        "Kamar",
        "Tanggal",
        "Waktu",
        "Sesi",
        "Status",
        "Keterangan",
        "Lokasi Valid",
        "Latitude",
        "Longitude",
        "Area Polygon"
    ])

    for r in records:
        mhs_nama = r.user.nama if r.user else "-"
        kamar_str = r.user.kamar_ref.nomor_kamar if r.user and r.user.kamar_ref else "-"
        waktu_str = r.waktu.strftime("%H:%M:%S") if r.waktu else "-"
        lokasi_valid = "Ya" if r.area_absensi_id else "Tidak (Luar Zona)"
        area_str = r.area.nama if r.area else "-"

        writer.writerow([
            r.nim,
            mhs_nama,
            gedung.nama_gedung,
            kamar_str,
            r.tanggal.isoformat() if r.tanggal else "-",
            waktu_str,
            r.sesi,
            r.status,
            r.keterangan or "-",
            lokasi_valid,
            str(r.latitude) if r.latitude else "-",
            str(r.longitude) if r.longitude else "-",
            area_str
        ])

    csv_data = output.getvalue()
    safe_gedung = gedung.nama_gedung.replace(" ", "_").lower()
    filename = f"rekap_presensi_{safe_gedung}_{tgl_mulai_str}_{tgl_selesai_str}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
