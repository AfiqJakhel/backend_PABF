import os
from datetime import timedelta
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
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_MINUTES', '480'))
    )

    # Uploads
    UPLOAD_FOLDER = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        os.getenv('UPLOAD_FOLDER', 'uploads')
    )
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file size

    GEOFENCE_CENTER_LATITUDE = float(os.getenv('GEOFENCE_CENTER_LATITUDE', '-0.9147'))
    GEOFENCE_CENTER_LONGITUDE = float(os.getenv('GEOFENCE_CENTER_LONGITUDE', '100.4583'))
    GEOFENCE_RADIUS_METERS = float(os.getenv('GEOFENCE_RADIUS_METERS', '250'))

    # Batas maksimal akurasi GPS (meter).
    # Jika accuracy > nilai ini, absensi ditolak.
    MAX_GPS_ACCURACY_METERS = float(os.getenv('MAX_GPS_ACCURACY_METERS', '50'))

    # ─── Perizinan ──────────────────────────────────────────────────────────
    # Dokumen izin disimpan di folder PRIVAT (bukan di bawah UPLOAD_FOLDER yang
    # disajikan publik lewat /uploads). Hanya bisa diakses via endpoint ber-JWT.
    IZIN_UPLOAD_FOLDER = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        os.getenv('IZIN_UPLOAD_FOLDER', os.path.join('private_uploads', 'izin'))
    )
    IZIN_MAX_FILE_BYTES = int(os.getenv('IZIN_MAX_FILE_BYTES', str(5 * 1024 * 1024)))
    IZIN_MAX_DURASI_HARI = int(os.getenv('IZIN_MAX_DURASI_HARI', '14'))
    IZIN_MAKS_MUNDUR_HARI = int(os.getenv('IZIN_MAKS_MUNDUR_HARI', '3'))
    IZIN_MAKS_MAJU_HARI = int(os.getenv('IZIN_MAKS_MAJU_HARI', '60'))

    # Rate limit login: maksimal percobaan gagal per jendela waktu (per IP+NIM)
    LOGIN_RATE_LIMIT_ATTEMPTS = int(os.getenv('LOGIN_RATE_LIMIT_ATTEMPTS', '5'))
    LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv('LOGIN_RATE_LIMIT_WINDOW_SECONDS', '900'))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    """Konfigurasi pytest: SQLite in-memory, tidak menyentuh MySQL dev."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    JWT_SECRET_KEY = 'test-only-secret-key-not-for-production-use-32b'
    SECRET_KEY = 'test-only-secret'
