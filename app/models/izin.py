from datetime import datetime, date
from app.core.extensions import db

class Izin(db.Model):
    __tablename__ = 'izin'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    tanggal_mulai = db.Column(db.Date, nullable=False, default=date.today)
    tanggal_selesai = db.Column(db.Date, nullable=False, default=date.today)
    alasan = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending') # 'pending', 'disetujui', 'ditolak'
    file_bukti = db.Column(db.String(255), nullable=True) # Path file bukti dokumen/foto surat
    disetujui_oleh = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True) # ID Fasilitator
    catatan_fasil = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, user_id: int = None, tanggal_mulai: date = None, tanggal_selesai: date = None,
                 alasan: str = "", status: str = "pending", file_bukti: str = None,
                 disetujui_oleh: int = None, catatan_fasil: str = None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.tanggal_mulai = tanggal_mulai or date.today()
        self.tanggal_selesai = tanggal_selesai or date.today()
        self.alasan = alasan
        self.status = status
        self.file_bukti = file_bukti
        self.disetujui_oleh = disetujui_oleh
        self.catatan_fasil = catatan_fasil

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'nama_pemohon': self.pemohon.nama if self.pemohon else None,
            'nim_pemohon': self.pemohon.nim if self.pemohon else None,
            'tanggal_mulai': self.tanggal_mulai.isoformat() if self.tanggal_mulai else None,
            'tanggal_selesai': self.tanggal_selesai.isoformat() if self.tanggal_selesai else None,
            'alasan': self.alasan,
            'status': self.status,
            'file_bukti': self.file_bukti,
            'disetujui_oleh': self.disetujui_oleh,
            'nama_fasil': self.validator.nama if self.validator else None,
            'catatan_fasil': self.catatan_fasil,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Izin ID:{self.id} User:{self.user_id} Status:{self.status}>"
