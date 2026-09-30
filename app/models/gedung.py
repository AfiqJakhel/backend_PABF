from datetime import datetime
from app.core.extensions import db

class Gedung(db.Model):
    __tablename__ = 'gedung'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nama_gedung = db.Column(db.String(50), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL', use_alter=True, name='fk_gedung_user_id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relasi
    fasil = db.relationship('User', foreign_keys=[user_id], backref=db.backref('gedung_binaan', uselist=False))
    daftar_kamar = db.relationship('Kamar', backref='gedung', cascade='all, delete-orphan', lazy='dynamic')

    def __init__(self, nama_gedung: str = "", user_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.nama_gedung = nama_gedung
        self.user_id = user_id

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'nama_gedung': self.nama_gedung,
            'user_id': self.user_id,
            'fasil': {
                'id': self.fasil.id,
                'nim': self.fasil.nim,
                'nama': self.fasil.nama
            } if self.fasil else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Gedung {self.nama_gedung}>"
