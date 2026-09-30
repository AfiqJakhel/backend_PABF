from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.core.extensions import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nim = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nama = db.Column(db.String(100), nullable=False)
    asal = db.Column(db.String(100), nullable=True)
    jekel = db.Column(db.String(10), nullable=True) # 'L' atau 'P'
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='mahasiswa') # 'mahasiswa', 'fasil', 'admin'
    kamar_id = db.Column(db.Integer, db.ForeignKey('kamar.id', ondelete='SET NULL'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relasi
    daftar_presensi = db.relationship('Presensi', backref='user', cascade='all, delete-orphan', lazy='dynamic')
    daftar_izin = db.relationship('Izin', foreign_keys='Izin.user_id', backref='pemohon', cascade='all, delete-orphan', lazy='dynamic')
    daftar_izin_divalidasi = db.relationship('Izin', foreign_keys='Izin.disetujui_oleh', backref='validator', lazy='dynamic')

    def __init__(self, nim: str = "", nama: str = "", role: str = "mahasiswa", kamar_id: int = None,
                 asal: str = None, jekel: str = None, email: str = None, **kwargs):
        super().__init__(**kwargs)
        self.nim = nim
        self.nama = nama
        self.role = role
        self.kamar_id = kamar_id
        self.asal = asal
        self.jekel = jekel
        self.email = email

    def set_password(self, password: str) -> None:
        """Hash and store password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Serialize user object without sensitive data."""
        # Menjaga kompatibilitas dengan frontend yang membaca field 'kamar' sebagai string
        kamar_str = None
        kamar_detail = None
        if self.kamar_ref:
            gedung_nama = self.kamar_ref.gedung.nama_gedung if self.kamar_ref.gedung else ""
            kamar_str = f"{gedung_nama} - Kamar {self.kamar_ref.nomor_kamar}".strip(" -")
            kamar_detail = {
                'id': self.kamar_ref.id,
                'nomor_kamar': self.kamar_ref.nomor_kamar,
                'lantai': self.kamar_ref.lantai,
                'nama_gedung': gedung_nama
            }

        return {
            'id': self.id,
            'nim': self.nim,
            'nama': self.nama,
            'asal': self.asal,
            'jekel': self.jekel,
            'email': self.email,
            'role': self.role,
            'kamar_id': self.kamar_id,
            'kamar': kamar_str, # String untuk display langsung di frontend
            'kamar_detail': kamar_detail,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<User {self.nim} - {self.nama} ({self.role})>"
