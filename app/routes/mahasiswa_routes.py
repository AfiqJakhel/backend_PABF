from flask import Blueprint

from app.controllers.mahasiswa_presensi_controller import (
    get_riwayat_presensi,
    get_status_hari_ini,
    validasi_lokasi,
)
from app.middlewares.auth_middleware import auth_required, role_required


mahasiswa_bp = Blueprint("mahasiswa", __name__)
mahasiswa_bp.add_url_rule("/presensi/riwayat", view_func=role_required("mahasiswa")(get_riwayat_presensi), methods=["GET"])
mahasiswa_bp.add_url_rule("/presensi/hari-ini", view_func=role_required("mahasiswa")(get_status_hari_ini), methods=["GET"])
mahasiswa_bp.add_url_rule("/presensi/validasi-lokasi", view_func=auth_required(validasi_lokasi), methods=["POST"])