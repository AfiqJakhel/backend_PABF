"""
Routes untuk endpoint perizinan utama (/api/izin).
Semua endpoint dilindungi role_required dengan verify_db=True
untuk memverifikasi integritas role dari database pada setiap aksi.
"""

from flask import Blueprint
from app.middlewares.auth_middleware import role_required
from app.controllers.izin_controller import (
    submit_izin,
    get_izin_saya,
    batal_izin,
    get_izin_review,
    get_detail_izin,
    review_izin,
    get_dokumen_izin
)

izin_bp = Blueprint('izin', __name__)

# Mahasiswa endpoints
izin_bp.add_url_rule(
    '',
    view_func=role_required('mahasiswa', verify_db=True)(submit_izin),
    methods=['POST'],
    endpoint='submit_izin'
)

izin_bp.add_url_rule(
    '/saya',
    view_func=role_required('mahasiswa', verify_db=True)(get_izin_saya),
    methods=['GET'],
    endpoint='get_izin_saya'
)

izin_bp.add_url_rule(
    '/<int:izin_id>/batal',
    view_func=role_required('mahasiswa', verify_db=True)(batal_izin),
    methods=['PATCH'],
    endpoint='batal_izin'
)

# Fasilitator & Admin endpoints
izin_bp.add_url_rule(
    '/review',
    view_func=role_required('fasil', 'admin', verify_db=True)(get_izin_review),
    methods=['GET'],
    endpoint='get_izin_review'
)

# Shared detail & document endpoints (terproteksi object-level authorization)
izin_bp.add_url_rule(
    '/<int:izin_id>',
    view_func=role_required('mahasiswa', 'fasil', 'admin', verify_db=True)(get_detail_izin),
    methods=['GET'],
    endpoint='get_detail_izin'
)

izin_bp.add_url_rule(
    '/<int:izin_id>/review',
    view_func=role_required('fasil', verify_db=True)(review_izin),
    methods=['PATCH'],
    endpoint='review_izin'
)

izin_bp.add_url_rule(
    '/<int:izin_id>/dokumen',
    view_func=role_required('mahasiswa', 'fasil', 'admin', verify_db=True)(get_dokumen_izin),
    methods=['GET'],
    endpoint='get_dokumen_izin'
)
