from datetime import datetime
from app.core.extensions import db


class SesiPresensi(db.Model):
    """
    Master sesi presensi harian (mis. Pagi, Malam).

    Berbeda dari `SesiAbsensi` (instance sesi per tanggal yang dibuat fasilitator),
    tabel ini adalah daftar sesi tetap yang bisa dipilih untuk izin setengah hari.
    Kolom `kode` sengaja disamakan dengan nilai `presensi.sesi` ('subuh', 'malam')
    agar modul rekap dapat mencocokkan izin dengan record presensi.
    """
    __tablename__ = 'sesi_presensi'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kode = db.Column(db.String(20), nullable=False, unique=True)
    nama = db.Column(db.String(50), nullable=False)
    jam_mulai = db.Column(db.Time, nullable=True)
    jam_selesai = db.Column(db.Time, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, kode: str = "", nama: str = "", jam_mulai=None, jam_selesai=None,
                 is_active: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.kode = kode
        self.nama = nama
        self.jam_mulai = jam_mulai
        self.jam_selesai = jam_selesai
        self.is_active = is_active

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'kode': self.kode,
            'nama': self.nama,
            'jam_mulai': self.jam_mulai.strftime('%H:%M') if self.jam_mulai else None,
            'jam_selesai': self.jam_selesai.strftime('%H:%M') if self.jam_selesai else None,
            'is_active': bool(self.is_active),
        }

    def __repr__(self):
        return f"<SesiPresensi {self.kode} ({self.nama})>"
