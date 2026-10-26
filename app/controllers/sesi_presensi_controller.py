from flask import jsonify
from app.repositories.izin_repository import SesiPresensiRepository


def get_daftar_sesi_presensi():
    """
    GET /api/sesi
    Mengambil daftar master sesi presensi harian (Pagi, Malam, dsb).
    Dapat diakses oleh semua pengguna yang terautentikasi.
    """
    sesi_list = SesiPresensiRepository.get_all_active()
    return jsonify({
        "success": True,
        "message": "Daftar master sesi presensi berhasil diambil.",
        "data": [s.to_dict() for s in sesi_list]
    }), 200
