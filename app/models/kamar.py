from datetime import datetime
from app.core.extensions import db

class Kamar(db.Model):
    __tablename__ = 'kamar'
    __table_args__ = (
        db.UniqueConstraint('gedung_id', 'nomor_kamar', name='uq_gedung_nomor_kamar'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gedung_id = db.Column(db.Integer, db.ForeignKey('gedung.id', ondelete='CASCADE'), nullable=False, index=True)
    nomor_kamar = db.Column(db.String(20), nullable=False)
    lantai = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relasi
    penghuni = db.relationship('User', backref='kamar_ref', lazy='dynamic')

    def __init__(self, gedung_id: int = None, nomor_kamar: str = "", lantai: int = 1, **kwargs):
        super().__init__(**kwargs)
        self.gedung_id = gedung_id
        self.nomor_kamar = nomor_kamar
        self.lantai = lantai

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'gedung_id': self.gedung_id,
            'nama_gedung': self.gedung.nama_gedung if self.gedung else None,
            'nomor_kamar': self.nomor_kamar,
            'lantai': self.lantai,
            'jumlah_penghuni': self.penghuni.count() if hasattr(self.penghuni, 'count') else len(self.penghuni),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Kamar {self.nomor_kamar} - Lantai {self.lantai}>"
