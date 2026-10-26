from flask import Blueprint
from app.middlewares.auth_middleware import auth_required
from app.controllers.sesi_presensi_controller import get_daftar_sesi_presensi

sesi_bp = Blueprint('sesi', __name__)

sesi_bp.add_url_rule(
    '',
    view_func=auth_required(get_daftar_sesi_presensi),
    methods=['GET'],
    endpoint='get_daftar_sesi_presensi'
)
