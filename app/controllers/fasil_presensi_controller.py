"""
Controller untuk fitur Fasilitator — Monitoring & Rekapitulasi Presensi.
Bertanggung jawab atas:
  - Real-time monitoring kehadiran per sesi
  - Update status presensi secara manual
  - Input presensi manual untuk mahasiswa yang belum absen
  - Download/tampilkan rekap berdasarkan rentang tanggal
"""

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.services.fasil_service import PresensiService
from app.schemas.fasil_schemas import validate_update_presensi_manual


def get_rekap_sesi():
    """
    GET /api/fasil/presensi/sesi
    Real-time: siapa sudah/belum absen untuk sesi tertentu hari ini.
    Query params:
        sesi    : str  'subuh' | 'malam' | 'kegiatan'  (wajib)
        tanggal : str  YYYY-MM-DD                       (wajib)
    """
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

    data, error = PresensiService.get_rekap_sesi(tipe_sesi, tanggal_str)
    if error:
        return jsonify({"success": False, "message": error, "data": None}), 400

    return jsonify({"success": True, "message": "Rekap sesi berhasil diambil.", "data": data}), 200


def update_presensi_manual(presensi_id: int):
    """
    PATCH /api/fasil/presensi/<presensi_id>/status
    Ubah status kehadiran mahasiswa yang sudah memiliki record presensi.
    Body JSON:
        status      : str  'hadir' | 'terlambat' | 'alfa' | 'izin' | 'sakit'  (wajib)
        keterangan  : str  (wajib jika status 'izin' atau 'sakit')
    """
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
    Body JSON:
        user_id     : int  (wajib)
        sesi        : str  'subuh' | 'malam' | 'kegiatan'  (wajib)
        status      : str  'hadir' | 'terlambat' | 'alfa' | 'izin' | 'sakit'  (wajib)
        keterangan  : str  (opsional)
        tanggal     : str  YYYY-MM-DD  (opsional, default: hari ini)
    """
    from datetime import date
    from app.schemas.fasil_schemas import STATUS_PRESENSI_VALID, TIPE_SESI_VALID

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

    result, error = PresensiService.input_presensi_manual(
        user_id=user_id, tipe_sesi=sesi, status=status,
        keterangan=keterangan, tanggal=tanggal
    )
    if error:
        status_code = 409 if "sudah memiliki record" in error else 404
        return jsonify({"success": False, "message": error, "data": None}), status_code

    return jsonify({
        "success": True, "message": "Presensi manual berhasil diinput.", "data": result
    }), 201


def get_rekap_rentang():
    """
    GET /api/fasil/presensi/rekap
    Rekap presensi berdasarkan rentang tanggal.
    Query params:
        tanggal_mulai   : str   YYYY-MM-DD  (wajib)
        tanggal_selesai : str   YYYY-MM-DD  (wajib)
        sesi            : str   'subuh' | 'malam' | 'kegiatan'  (opsional)
        user_id         : int   (opsional, untuk filter 1 mahasiswa)
        page            : int   (default: 1)
        per_page        : int   (default: 20, max: 100)
        summary         : bool  'true' untuk ringkasan per mahasiswa  (default: false)
    """
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

    data, error = PresensiService.get_rekap_rentang(
        tgl_mulai, tgl_selesai, tipe_sesi, user_id, page, per_page, summary
    )
    if error:
        return jsonify({"success": False, "message": error, "data": None}), 400

    return jsonify({"success": True, "message": "Rekap presensi berhasil diambil.", "data": data}), 200
