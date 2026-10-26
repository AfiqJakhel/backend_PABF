from datetime import datetime
from app.core.extensions import db


class IzinDokumen(db.Model):
    """
    Dokumen pendukung pengajuan izin.

    `stored_name` adalah nama file acak (uuid4 hex + ekstensi) yang dibuat server;
    path absolut TIDAK pernah disimpan maupun dikirim ke klien. `original_name`
    hanya untuk tampilan dan sudah disanitasi.
    """
    __tablename__ = 'izin_dokumen'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    izin_id = db.Column(
        db.Integer, db.ForeignKey('izin.id', ondelete='CASCADE'), nullable=False, index=True
    )
    stored_name = db.Column(db.String(64), nullable=False, unique=True)
    original_name = db.Column(db.String(255), nullable=True)
    mime_type = db.Column(db.String(50), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, izin_id: int = None, stored_name: str = "", original_name: str = None,
                 mime_type: str = "", size_bytes: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.izin_id = izin_id
        self.stored_name = stored_name
        self.original_name = original_name
        self.mime_type = mime_type
        self.size_bytes = size_bytes

    def to_dict(self) -> dict:
        # stored_name sengaja tidak diekspos.
        return {
            'id': self.id,
            'original_name': self.original_name,
            'mime_type': self.mime_type,
            'size_bytes': self.size_bytes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<IzinDokumen {self.id} izin={self.izin_id}>"
