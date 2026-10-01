from datetime import datetime, date
from app.core.extensions import db


class SesiAbsensi(db.Model):
    """
    Model untuk menyimpan data sesi absensi yang dibuat oleh Fasilitator.
    Satu sesi bisa berupa sesi pagi (subuh), malam, atau kegiatan tertentu.
    """
    __tablename__ = 'sesi_absensi'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nama_sesi = db.Column(db.String(100), nullable=False)
    # Tipe sesi: 'subuh', 'malam', 'kegiatan'
    tipe_sesi = db.Column(db.String(20), nullable=False, default='malam')
    tanggal = db.Column(db.Date, nullable=False, default=date.today, index=True)
    waktu_mulai = db.Column(db.DateTime, nullable=False)
    waktu_selesai = db.Column(db.DateTime, nullable=False)
    # Status sesi: 'aktif', 'ditutup'
    status = db.Column(db.String(20), nullable=False, default='aktif')
    # ID fasilitator yang membuat sesi
    dibuat_oleh = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    keterangan = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relasi ke user (fasilitator pembuat sesi)
    fasilitator = db.relationship(
        'User',
        foreign_keys=[dibuat_oleh],
        backref=db.backref('sesi_dibuat', lazy='dynamic')
    )

    def __init__(
        self,
        nama_sesi: str = "",
        tipe_sesi: str = "malam",
        tanggal: date = None,
        waktu_mulai: datetime = None,
        waktu_selesai: datetime = None,
        status: str = "aktif",
        dibuat_oleh: int = None,
        keterangan: str = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.nama_sesi = nama_sesi
        self.tipe_sesi = tipe_sesi
        self.tanggal = tanggal or date.today()
        self.waktu_mulai = waktu_mulai
        self.waktu_selesai = waktu_selesai
        self.status = status
        self.dibuat_oleh = dibuat_oleh
        self.keterangan = keterangan

    @property
    def is_aktif(self) -> bool:
        """Cek apakah sesi masih dalam rentang waktu aktif dan belum ditutup."""
        now = datetime.utcnow()
        return (
            self.status == 'aktif'
            and self.waktu_mulai <= now <= self.waktu_selesai
        )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'nama_sesi': self.nama_sesi,
            'tipe_sesi': self.tipe_sesi,
            'tanggal': self.tanggal.isoformat() if self.tanggal else None,
            'waktu_mulai': self.waktu_mulai.isoformat() if self.waktu_mulai else None,
            'waktu_selesai': self.waktu_selesai.isoformat() if self.waktu_selesai else None,
            'status': self.status,
            'is_aktif': self.is_aktif,
            'dibuat_oleh': self.dibuat_oleh,
            'nama_fasilitator': self.fasilitator.nama if self.fasilitator else None,
            'keterangan': self.keterangan,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<SesiAbsensi {self.nama_sesi} - {self.tanggal} [{self.status}]>"
