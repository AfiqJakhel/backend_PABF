"""
Routes untuk endpoint Administrator — Area Absensi.
Semua route diproteksi admin_required (role = admin).

Prefix Blueprint: /api/admin
"""

from flask import Blueprint
from app.middlewares.auth_middleware import admin_required

from app.controllers.area_absensi_controller import (
    get_semua_area,
    buat_area,
    get_detail_area,
    update_area,
    hapus_area,
    toggle_active_area,
)

admin_bp = Blueprint("admin", __name__)

# GET  /api/admin/area-absensi            → Daftar semua area
admin_bp.add_url_rule(
    "/area-absensi",
    view_func=admin_required(get_semua_area),
    methods=["GET"],
    endpoint="get_semua_area",
)

# POST /api/admin/area-absensi            → Buat area baru
admin_bp.add_url_rule(
    "/area-absensi",
    view_func=admin_required(buat_area),
    methods=["POST"],
    endpoint="buat_area",
)

# GET  /api/admin/area-absensi/<id>       → Detail area
admin_bp.add_url_rule(
    "/area-absensi/<int:area_id>",
    view_func=admin_required(get_detail_area),
    methods=["GET"],
    endpoint="get_detail_area",
)

# PUT  /api/admin/area-absensi/<id>       → Update area
admin_bp.add_url_rule(
    "/area-absensi/<int:area_id>",
    view_func=admin_required(update_area),
    methods=["PUT"],
    endpoint="update_area",
)

# DELETE /api/admin/area-absensi/<id>     → Hapus area
admin_bp.add_url_rule(
    "/area-absensi/<int:area_id>",
    view_func=admin_required(hapus_area),
    methods=["DELETE"],
    endpoint="hapus_area",
)

# PATCH /api/admin/area-absensi/<id>/toggle → Toggle aktif/nonaktif
admin_bp.add_url_rule(
    "/area-absensi/<int:area_id>/toggle",
    view_func=admin_required(toggle_active_area),
    methods=["PATCH"],
    endpoint="toggle_active_area",
)
