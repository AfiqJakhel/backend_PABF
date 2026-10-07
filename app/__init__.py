from flask import Flask, send_from_directory
from config import DevelopmentConfig
from .core.extensions import db, jwt, cors, migrate
from .models import User, Gedung, Kamar, Presensi, Izin, SesiAbsensi, AreaAbsensi
from .routes import auth_bp, fasil_bp, mahasiswa_bp, admin_bp


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}, r"/uploads/*": {"origins": "*"}})
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(fasil_bp, url_prefix='/api/fasil')
    app.register_blueprint(mahasiswa_bp, url_prefix='/api/mahasiswa')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    # Serve static uploaded files (e.g. foto absensi)
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Root route for API health check
    @app.route('/')
    def index():
        return {"status": "success", "message": "Hello!"}

    return app
