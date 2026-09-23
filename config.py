import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration.
    
    Nilai konfigurasi TIDAK boleh diisi di sini secara langsung.
    Semua nilai sensitif (password, kunci rahasia, host, dll.) harus
    didefinisikan di dalam file .env di root folder backend.
    Nilai di bawah ini hanyalah FALLBACK (cadangan) jika .env tidak ditemukan.
    """
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')

    # Database — nilai aktual diatur di .env
    _DB_USER     = os.getenv('DB_USERNAME', 'root')
    _DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
    _DB_HOST     = os.getenv('DB_HOST', 'localhost')
    _DB_PORT     = os.getenv('DB_PORT', '3306')
    _DB_NAME     = os.getenv('DB_NAME', 'nama_database')

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{_DB_USER}:{_DB_PASSWORD}"
        f"@{_DB_HOST}:{_DB_PORT}/{_DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT — nilai aktual diatur di .env
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-me-in-production')

    # Uploads
    UPLOAD_FOLDER = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        os.getenv('UPLOAD_FOLDER', 'uploads')
    )
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file size


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
