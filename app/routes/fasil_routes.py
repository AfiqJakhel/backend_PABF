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
    hapus_sesi,
)
from app.controllers.fasil_presensi_controller import (
    get_rekap_sesi,
    update_presensi_manual,
    input_presensi_manual,
    get_rekap_rentang,
    get_daftar_verifikasi,
    export_rekap,
)
from app.controllers.fasil_izin_controller import (
    get_daftar_izin,
    get_detail_izin,
    proses_izin,
)
from app.controllers.user_controller import import_users_file
from app.controllers.fasil_mahasiswa_controller import (
    get_gedung_saya,
    get_mahasiswa_fasil,
    tambah_mahasiswa_fasil,
    update_mahasiswa_fasil,
    hapus_mahasiswa_fasil,
    download_template_csv,
    import_mahasiswa_csv,
)
from app.controllers.fasil_polygon_controller import (
    get_polygon_fasil,
    buat_polygon_fasil,
    update_polygon_fasil,
    hapus_polygon_fasil,
    toggle_active_polygon_fasil,
)

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

# DELETE /api/fasil/sesi/<id>      → Hapus jadwal kegiatan / sesi
fasil_bp.add_url_rule(
    '/sesi/<int:sesi_id>',
    view_func=fasil_required(hapus_sesi),
    methods=['DELETE'],
    endpoint='hapus_sesi'
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

# GET  /api/fasil/presensi/verifikasi    → Daftar foto presensi untuk verifikasi fasilitator
fasil_bp.add_url_rule(
    '/presensi/verifikasi',
    view_func=fasil_required(get_daftar_verifikasi),
    methods=['GET'],
    endpoint='get_daftar_verifikasi'
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

# GET   /api/fasil/presensi/export         → Export rekap presensi CSV (Terkunci ke gedung binaan)
fasil_bp.add_url_rule(
    '/presensi/export',
    view_func=fasil_required(export_rekap),
    methods=['GET'],
    endpoint='export_rekap'
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


# ─── Gedung & Mahasiswa Asrama Routes (Building-Scoped) ─────────────────────

# GET    /api/fasil/gedung-saya            → Profil gedung binaan & daftar kamar
fasil_bp.add_url_rule(
    '/gedung-saya',
    view_func=fasil_required(get_gedung_saya),
    methods=['GET'],
    endpoint='get_gedung_saya'
)

# GET    /api/fasil/mahasiswa              → Daftar mahasiswa gedung binaan (filter search & kamar)
fasil_bp.add_url_rule(
    '/mahasiswa',
    view_func=fasil_required(get_mahasiswa_fasil),
    methods=['GET'],
    endpoint='get_mahasiswa_fasil'
)

# POST   /api/fasil/mahasiswa              → Tambah mahasiswa baru ke kamar gedung binaan
fasil_bp.add_url_rule(
    '/mahasiswa',
    view_func=fasil_required(tambah_mahasiswa_fasil),
    methods=['POST'],
    endpoint='tambah_mahasiswa_fasil'
)

# PUT    /api/fasil/mahasiswa/<id>         → Update data mahasiswa gedung binaan (Anti-IDOR)
fasil_bp.add_url_rule(
    '/mahasiswa/<int:student_id>',
    view_func=fasil_required(update_mahasiswa_fasil),
    methods=['PUT'],
    endpoint='update_mahasiswa_fasil'
)

# DELETE /api/fasil/mahasiswa/<id>         → Hapus mahasiswa gedung binaan (Anti-IDOR)
fasil_bp.add_url_rule(
    '/mahasiswa/<int:student_id>',
    view_func=fasil_required(hapus_mahasiswa_fasil),
    methods=['DELETE'],
    endpoint='hapus_mahasiswa_fasil'
)

# GET    /api/fasil/mahasiswa/template-csv → Unduh template CSV untuk import mahasiswa
fasil_bp.add_url_rule(
    '/mahasiswa/template-csv',
    view_func=fasil_required(download_template_csv),
    methods=['GET'],
    endpoint='download_template_csv'
)

# POST   /api/fasil/mahasiswa/import-csv   → Import CSV mahasiswa (Otomatis ke gedung binaan)
fasil_bp.add_url_rule(
    '/mahasiswa/import-csv',
    view_func=fasil_required(import_mahasiswa_csv),
    methods=['POST'],
    endpoint='import_mahasiswa_csv'
)


# ─── Polygon Area Absensi Routes (Building-Scoped) ──────────────────────────

# GET    /api/fasil/polygon                → Daftar polygon gedung binaan
fasil_bp.add_url_rule(
    '/polygon',
    view_func=fasil_required(get_polygon_fasil),
    methods=['GET'],
    endpoint='get_polygon_fasil'
)

# POST   /api/fasil/polygon                → Buat polygon baru khusus gedung binaan
fasil_bp.add_url_rule(
    '/polygon',
    view_func=fasil_required(buat_polygon_fasil),
    methods=['POST'],
    endpoint='buat_polygon_fasil'
)

# PUT    /api/fasil/polygon/<id>           → Update polygon gedung binaan (Anti-IDOR)
fasil_bp.add_url_rule(
    '/polygon/<int:area_id>',
    view_func=fasil_required(update_polygon_fasil),
    methods=['PUT'],
    endpoint='update_polygon_fasil'
)

# DELETE /api/fasil/polygon/<id>           → Hapus polygon gedung binaan (Anti-IDOR)
fasil_bp.add_url_rule(
    '/polygon/<int:area_id>',
    view_func=fasil_required(hapus_polygon_fasil),
    methods=['DELETE'],
    endpoint='hapus_polygon_fasil'
)

# PATCH  /api/fasil/polygon/<id>/toggle    → Toggle aktif polygon gedung binaan (Anti-IDOR)
fasil_bp.add_url_rule(
    '/polygon/<int:area_id>/toggle',
    view_func=fasil_required(toggle_active_polygon_fasil),
    methods=['PATCH'],
    endpoint='toggle_active_polygon_fasil'
)


