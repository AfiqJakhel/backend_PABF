"""
Controller untuk Fitur Perizinan Mahasiswa dan Fasilitator.
Mengimplementasikan semua endpoint perizinan dengan validasi, otorisasi objek, dan penanganan dokumen privat.
"""

from flask import request, jsonify, send_file, g
from app.models.user import User
from app.services.izin_service import IzinService
from app.services.izin_access_service import IzinAccessService
from app.schemas.izin_schemas import validate_pengajuan_izin, validate_review_izin
from app.utils.izin_file_storage import get_izin_document_abs_path


def _get_current_user() -> User:
    """Mengambil user terverifikasi dari request context g."""
    return getattr(g, "current_user", None)


def submit_izin():
    """
    POST /api/izin
    Multipart form-data pengajuan izin oleh mahasiswa.
    Fields:
      - jenis: 'full' | 'half'
      - tanggal_mulai: YYYY-MM-DD
      - tanggal_selesai: YYYY-MM-DD (opsional jika half)
      - sesi_id: ID sesi presensi (wajib jika half)
      - keterangan / alasan: string catatan pengajuan
      - dokumen: File dokumen pendukung (jpg/png/pdf)
    """
    user = _get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Identitas pengguna tidak ditemukan.", "data": None}), 401

    file_obj = request.files.get("dokumen") or request.files.get("file")
    has_file = bool(file_obj and file_obj.filename)

    errors, parsed = validate_pengajuan_izin(request.form, has_document=has_file)
    if errors:
        return jsonify({
            "success": False,
            "message": "Validasi pengajuan izin gagal.",
            "errors": errors,
            "data": None
        }), 422

    result, err, status_code = IzinService.ajukan_izin(user, parsed, file_obj)
    if err:
        return jsonify({
            "success": False,
            "message": err,
            "data": None
        }), status_code

    return jsonify({
        "success": True,
        "message": "Pengajuan izin berhasil dikirim dan menunggu verifikasi fasilitator.",
        "data": result
    }), 201


def get_izin_saya():
    """
    GET /api/izin/saya
    Melihat daftar riwayat izin milik mahasiswa sendiri.
    Query params:
      - status: 'pending' | 'approved' | 'rejected' | 'cancelled'
      - page: int
      - per_page: int
    """
    user = _get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Identitas pengguna tidak ditemukan.", "data": None}), 401

    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 15, type=int), 50)

    data = IzinService.get_daftar_izin_saya(mahasiswa_id=user.id, status=status, page=page, per_page=per_page)
    return jsonify({
        "success": True,
        "message": "Riwayat izin berhasil diambil.",
        "data": data
    }), 200


def batal_izin(izin_id: int):
    """
    PATCH /api/izin/<id>/batal
    Membatalkan pengajuan izin yang masih pending oleh mahasiswa pemohon.
    """
    user = _get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Identitas pengguna tidak ditemukan.", "data": None}), 401

    result, err, status_code = IzinService.batalkan_izin(izin_id, user)
    if err:
        return jsonify({
            "success": False,
            "message": err,
            "data": None
        }), status_code

    return jsonify({
        "success": True,
        "message": "Pengajuan izin berhasil dibatalkan.",
        "data": result
    }), 200


def get_izin_review():
    """
    GET /api/izin/review
    Melihat daftar izin masuk:
      - Fasilitator: HANYA mahasiswa di gedung binaannya
      - Admin: Read-only untuk seluruh gedung
    Query params:
      - status: 'pending' | 'approved' | 'rejected' | 'cancelled'
      - page: int
      - per_page: int
    """
    user = _get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Identitas pengguna tidak ditemukan.", "data": None}), 401

    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 15, type=int), 50)

    data, err, status_code = IzinService.get_daftar_izin_review(user, status=status, page=page, per_page=per_page)
    if err:
        return jsonify({
            "success": False,
            "message": err,
            "data": None
        }), status_code

    return jsonify({
        "success": True,
        "message": "Daftar izin untuk review berhasil diambil.",
        "data": data
    }), 200


def get_detail_izin(izin_id: int):
    """
    GET /api/izin/<id>
    Melihat detail satu pengajuan izin.
    Terproteksi object-level authorization (Pemilik, Fasil gedungnya, Admin).
    """
    user = _get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Identitas pengguna tidak ditemukan.", "data": None}), 401

    data, err, status_code = IzinService.get_detail_izin(izin_id, user)
    if err:
        return jsonify({
            "success": False,
            "message": err,
            "data": None
        }), status_code

    return jsonify({
        "success": True,
        "message": "Detail izin berhasil diambil.",
        "data": data
    }), 200


def review_izin(izin_id: int):
    """
    PATCH /api/izin/<id>/review
    Fasilitator mereview (approve atau reject) pengajuan izin di gedungnya.
    Body JSON:
      - aksi / status: 'approve' | 'reject'
      - catatan: string (wajib jika reject)
    """
    user = _get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Identitas pengguna tidak ditemukan.", "data": None}), 401

    data = request.get_json(silent=True)
    errors, parsed = validate_review_izin(data)
    if errors:
        return jsonify({
            "success": False,
            "message": "Validasi review izin gagal.",
            "errors": errors,
            "data": None
        }), 422

    result, err, status_code = IzinService.review_izin(izin_id, user, parsed)
    if err:
        return jsonify({
            "success": False,
            "message": err,
            "data": None
        }), status_code

    status_str = "disetujui" if parsed["status"] == "approved" else "ditolak"
    return jsonify({
        "success": True,
        "message": f"Pengajuan izin berhasil {status_str}.",
        "data": result
    }), 200


def get_dokumen_izin(izin_id: int):
    """
    GET /api/izin/<id>/dokumen
    Menyajikan file dokumen izin dari folder privat.
    Wajib autentikasi JWT dan pengecekan hak akses (Object-level authorization):
    - Mahasiswa pemilik
    - Fasilitator gedung mahasiswa
    - Admin
    Semua pihak lain mengembalikan 404 (bukan 403) agar tidak membocorkan keberadaan data.
    """
    user = _get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Identitas pengguna tidak ditemukan.", "data": None}), 401

    izin, err, status_code = IzinAccessService.authorize_and_get_izin(izin_id, user)
    if err:
        return jsonify({
            "success": False,
            "message": err,
            "data": None
        }), status_code

    if not izin.dokumen:
        return jsonify({
            "success": False,
            "message": "Pengajuan izin ini tidak memiliki lampiran dokumen.",
            "data": None
        }), 404

    dokumen = izin.dokumen[0]
    file_path = get_izin_document_abs_path(dokumen.stored_name)

    if not file_path:
        return jsonify({
            "success": False,
            "message": "Berkas fisik dokumen tidak ditemukan pada penyimpanan server.",
            "data": None
        }), 404

    # Sajikan file dengan header keamanan
    response = send_file(
        file_path,
        mimetype=dokumen.mime_type,
        as_attachment=False,
        download_name=dokumen.original_name or "dokumen_izin"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
    return response
