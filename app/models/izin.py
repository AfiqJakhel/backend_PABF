from datetime import datetime, date
from app.core.extensions import db


# ─── Konstanta domain izin ───────────────────────────────────────────────────
STATUS_PENDING = 'pending'
STATUS_APPROVED = 'approved'
STATUS_REJECTED = 'rejected'
STATUS_CANCELLED = 'cancelled'
STATUS_VALID = (STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_CANCELLED)
# Status yang dianggap "aktif" untuk pengecekan tumpang tindih
STATUS_AKTIF = (STATUS_PENDING, STATUS_APPROVED)

JENIS_FULL = 'full'
JENIS_HALF = 'half'
JENIS_VALID = (JENIS_FULL, JENIS_HALF)


class Izin(db.Model):
    __tablename__ = 'izin'
    __table_args__ = (
        db.Index('ix_izin_user_status', 'user_id', 'status'),
        db.Index('ix_izin_status_mulai', 'status', 'tanggal_mulai'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # user_id = mahasiswa_id (nama kolom lama dipertahankan agar non-destruktif)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    tanggal_mulai = db.Column(db.Date, nullable=False, default=date.today)
    tanggal_selesai = db.Column(db.Date, nullable=False, default=date.today)
    # alasan = keterangan/catatan dari mahasiswa
    alasan = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)  # pending|approved|rejected|cancelled
    file_bukti = db.Column(db.String(255), nullable=True)  # LEGACY: digantikan tabel izin_dokumen
    # disetujui_oleh = reviewer_id (fasilitator yang approve/reject)
    disetujui_oleh = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    # catatan_fasil = catatan reviewer (wajib saat reject)
    catatan_fasil = db.Column(db.Text, nullable=True)
    jenis = db.Column(db.String(10), nullable=False, default=JENIS_FULL, server_default=JENIS_FULL)  # full|half
    sesi_id = db.Column(db.Integer, db.ForeignKey('sesi_presensi.id', ondelete='RESTRICT'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sesi = db.relationship('SesiPresensi')
    dokumen = db.relationship(
        'IzinDokumen', backref='izin', cascade='all, delete-orphan',
        order_by='IzinDokumen.id', lazy='selectin'
    )

    def __init__(self, user_id: int = None, tanggal_mulai: date = None, tanggal_selesai: date = None,
                 alasan: str = "", status: str = STATUS_PENDING, file_bukti: str = None,
                 disetujui_oleh: int = None, catatan_fasil: str = None,
                 jenis: str = JENIS_FULL, sesi_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.tanggal_mulai = tanggal_mulai or date.today()
        self.tanggal_selesai = tanggal_selesai or date.today()
        self.alasan = alasan
        self.status = status
        self.file_bukti = file_bukti
        self.disetujui_oleh = disetujui_oleh
        self.catatan_fasil = catatan_fasil
        self.jenis = jenis
        self.sesi_id = sesi_id

    def to_dict(self) -> dict:
        pemohon = self.pemohon
        kamar = pemohon.kamar_ref if pemohon else None
        gedung = kamar.gedung if kamar else None
        return {
            'id': self.id,
            'user_id': self.user_id,
            'mahasiswa_id': self.user_id,
            'nama_pemohon': pemohon.nama if pemohon else None,
            'nim_pemohon': pemohon.nim if pemohon else None,
            'gedung_id': gedung.id if gedung else None,
            'nama_gedung': gedung.nama_gedung if gedung else None,
            'nomor_kamar': kamar.nomor_kamar if kamar else None,
            'jenis': self.jenis,
            'tanggal_mulai': self.tanggal_mulai.isoformat() if self.tanggal_mulai else None,
            'tanggal_selesai': self.tanggal_selesai.isoformat() if self.tanggal_selesai else None,
            'sesi': self.sesi.to_dict() if self.sesi else None,
            'alasan': self.alasan,
            'keterangan': self.alasan,
            'status': self.status,
            'dokumen': [d.to_dict() for d in self.dokumen],
            'has_dokumen': len(self.dokumen) > 0,
            'disetujui_oleh': self.disetujui_oleh,
            'nama_fasil': self.validator.nama if self.validator else None,
            'catatan_fasil': self.catatan_fasil,
            'catatan_reviewer': self.catatan_fasil,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Izin ID:{self.id} User:{self.user_id} Status:{self.status}>"
