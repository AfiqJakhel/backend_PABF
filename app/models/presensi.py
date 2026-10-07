from datetime import datetime, date
from app.core.extensions import db

class Presensi(db.Model):
    __tablename__ = 'presensi'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'tanggal', 'sesi', name='uq_user_tanggal_sesi'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    nim = db.Column(db.String(20), nullable=False, index=True)
    tanggal = db.Column(db.Date, nullable=False, default=date.today, index=True)
    waktu = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sesi = db.Column(db.String(20), nullable=False) # 'subuh', 'malam', 'kegiatan'
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    # Akurasi GPS dalam meter (nullable untuk kompatibilitas data lama)
    accuracy = db.Column(db.Float, nullable=True)
    # FK ke area absensi yang digunakan (nullable untuk presensi manual dan data lama)
    area_absensi_id = db.Column(
        db.Integer,
        db.ForeignKey('area_absensi.id', ondelete='SET NULL'),
        nullable=True
    )
    gedung_id = db.Column(
        db.Integer,
        db.ForeignKey('gedung.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    status = db.Column(db.String(20), nullable=False, default='hadir') # 'hadir', 'terlambat', 'alfa', 'izin'
    foto_wajah = db.Column(db.String(255), nullable=True)
    keterangan = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relasi
    area = db.relationship('AreaAbsensi', backref=db.backref('presensi_list', lazy='dynamic'))
    gedung = db.relationship('Gedung', backref=db.backref('presensi_records', lazy='dynamic'))

    def __init__(self, user_id: int = None, nim: str = "", tanggal: date = None, waktu: datetime = None,
                 sesi: str = "subuh", latitude: float = None, longitude: float = None,
                 accuracy: float = None, area_absensi_id: int = None, gedung_id: int = None,
                 status: str = "hadir", foto_wajah: str = None, keterangan: str = None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.nim = nim
        self.tanggal = tanggal or date.today()
        self.waktu = waktu or datetime.utcnow()
        self.sesi = sesi
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy = accuracy
        self.area_absensi_id = area_absensi_id
        self.gedung_id = gedung_id
        self.status = status
        self.foto_wajah = foto_wajah
        self.keterangan = keterangan

    def to_dict(self) -> dict:
        kamar_nama = None
        gedung_nama = None
        if self.gedung:
            gedung_nama = self.gedung.nama_gedung
        elif self.user and self.user.kamar_ref and self.user.kamar_ref.gedung:
            gedung_nama = self.user.kamar_ref.gedung.nama_gedung

        if self.user and self.user.kamar_ref:
            kamar_nama = str(self.user.kamar_ref.nomor_kamar)

        area_nama = self.area.nama if self.area else ("Di Luar Area" if self.latitude is not None else None)

        return {
            'id': self.id,
            'user_id': self.user_id,
            'nim': self.nim,
            'nama_mahasiswa': self.user.nama if self.user else None,
            'gedung_id': self.gedung_id or (self.user.kamar_ref.gedung_id if (self.user and self.user.kamar_ref) else None),
            'gedung': gedung_nama or "Asrama UNAND",
            'kamar': kamar_nama or "-",
            'tanggal': self.tanggal.isoformat() if self.tanggal else None,
            'waktu': self.waktu.isoformat() if self.waktu else None,
            'sesi': self.sesi,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accuracy': self.accuracy,
            'area_absensi_id': self.area_absensi_id,
            'area_nama': area_nama,
            'location_valid': bool(self.area_absensi_id),
            'status': self.status,
            'foto_wajah': self.foto_wajah,
            'keterangan': self.keterangan,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Presensi {self.nim} - {self.tanggal} ({self.sesi}): {self.status}>"
