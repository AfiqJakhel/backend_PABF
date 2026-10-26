from app.routes.auth_routes import auth_bp
from app.routes.fasil_routes import fasil_bp
from app.routes.mahasiswa_routes import mahasiswa_bp
from app.routes.admin_routes import admin_bp
from app.routes.izin_routes import izin_bp
from app.routes.sesi_routes import sesi_bp

__all__ = ['auth_bp', 'fasil_bp', 'mahasiswa_bp', 'admin_bp', 'izin_bp', 'sesi_bp']
