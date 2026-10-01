"""
Routes untuk semua endpoint Fasilitator.
Semua route diproteksi oleh middleware `fasil_required` yang
memverifikasi JWT dan memastikan role user adalah 'fasil' atau 'admin'.

Prefix Blueprint: /api/fasil
"""

from flask import Blueprint
from app.middlewares.fasil_middleware import fasil_required
from app.middlewares.auth_middleware import admin_required

# Import controller functions
from app.controllers.fasil_sesi_controller import (
    buat_sesi,
    get_daftar_sesi,
    get_sesi_aktif,
    get_detail_sesi,
    update_sesi,
    tutup_sesi,
)
from app.controllers.fasil_presensi_controller import (
    get_rekap_sesi,
    update_presensi_manual,
    input_presensi_manual,
    get_rekap_rentang,
)
from app.controllers.fasil_izin_controller import (
    get_daftar_izin,
    get_detail_izin,
    proses_izin,
)
from app.controllers.user_controller import import_users_file

# ─── Blueprint Definition ────────────────────────────────────────────────────
fasil_bp = Blueprint('fasil', __name__)


# ─── Sesi Absensi Routes ─────────────────────────────────────────────────────

# GET  /api/fasil/sesi/aktif      → Daftar sesi yang sedang aktif sekarang
fasil_bp.add_url_rule(
    '/sesi/aktif',
    view_func=fasil_required(get_sesi_aktif),
    methods=['GET'],
    endpoint='get_sesi_aktif'
)

# GET  /api/fasil/sesi            → Daftar semua sesi (dengan filter & pagination)
fasil_bp.add_url_rule(
    '/sesi',
    view_func=fasil_required(get_daftar_sesi),
    methods=['GET'],
    endpoint='get_daftar_sesi'
)

# POST /api/fasil/sesi            → Buat sesi absensi baru
fasil_bp.add_url_rule(
    '/sesi',
    view_func=fasil_required(buat_sesi),
    methods=['POST'],
    endpoint='buat_sesi'
)

# GET  /api/fasil/sesi/<id>       → Detail satu sesi
fasil_bp.add_url_rule(
    '/sesi/<int:sesi_id>',
    view_func=fasil_required(get_detail_sesi),
    methods=['GET'],
    endpoint='get_detail_sesi'
)

# PUT  /api/fasil/sesi/<id>       → Update sesi (nama, waktu, status, keterangan)
fasil_bp.add_url_rule(
    '/sesi/<int:sesi_id>',
    view_func=fasil_required(update_sesi),
    methods=['PUT'],
    endpoint='update_sesi'
)

# PATCH /api/fasil/sesi/<id>/tutup → Tutup sesi secara manual
fasil_bp.add_url_rule(
    '/sesi/<int:sesi_id>/tutup',
    view_func=fasil_required(tutup_sesi),
    methods=['PATCH'],
    endpoint='tutup_sesi'
)


# ─── Presensi Routes ─────────────────────────────────────────────────────────

# GET  /api/fasil/presensi/sesi          → Real-time: siapa sudah/belum absen per sesi
fasil_bp.add_url_rule(
    '/presensi/sesi',
    view_func=fasil_required(get_rekap_sesi),
    methods=['GET'],
    endpoint='get_rekap_sesi'
)

# GET  /api/fasil/presensi/rekap         → Rekap presensi berdasarkan rentang tanggal
fasil_bp.add_url_rule(
    '/presensi/rekap',
    view_func=fasil_required(get_rekap_rentang),
    methods=['GET'],
    endpoint='get_rekap_rentang'
)

# POST /api/fasil/presensi/manual        → Input presensi manual (mahasiswa belum absen)
fasil_bp.add_url_rule(
    '/presensi/manual',
    view_func=fasil_required(input_presensi_manual),
    methods=['POST'],
    endpoint='input_presensi_manual'
)

# PATCH /api/fasil/presensi/<id>/status  → Update status presensi yang sudah ada
fasil_bp.add_url_rule(
    '/presensi/<int:presensi_id>/status',
    view_func=fasil_required(update_presensi_manual),
    methods=['PATCH'],
    endpoint='update_presensi_manual'
)

fasil_bp.add_url_rule(
    '/users/import',
    view_func=admin_required(import_users_file),
    methods=['POST'],
    endpoint='import_users_file'
)


# ─── Izin Routes ─────────────────────────────────────────────────────────────

# GET   /api/fasil/izin           → Daftar semua pengajuan izin
fasil_bp.add_url_rule(
    '/izin',
    view_func=fasil_required(get_daftar_izin),
    methods=['GET'],
    endpoint='get_daftar_izin'
)

# GET   /api/fasil/izin/<id>      → Detail satu pengajuan izin
fasil_bp.add_url_rule(
    '/izin/<int:izin_id>',
    view_func=fasil_required(get_detail_izin),
    methods=['GET'],
    endpoint='get_detail_izin'
)

# PATCH /api/fasil/izin/<id>/proses → Setujui atau tolak izin
fasil_bp.add_url_rule(
    '/izin/<int:izin_id>/proses',
    view_func=fasil_required(proses_izin),
    methods=['PATCH'],
    endpoint='proses_izin'
)
