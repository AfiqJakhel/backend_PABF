from datetime import datetime
from app.core.extensions import db


class FasilitatorGedung(db.Model):
    """
    Relasi tanggung jawab fasilitator terhadap gedung (many-to-many).

    Dipakai oleh fitur perizinan untuk menentukan izin mana yang boleh direview
    seorang fasilitator. Data awal di-backfill dari kolom lama `gedung.user_id`.
    """
    __tablename__ = 'fasilitator_gedung'
    __table_args__ = (
        db.UniqueConstraint('fasilitator_id', 'gedung_id', name='uq_fasilitator_gedung'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fasilitator_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True
    )
    gedung_id = db.Column(
        db.Integer, db.ForeignKey('gedung.id', ondelete='CASCADE'), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    fasilitator = db.relationship(
        'User', backref=db.backref('gedung_tanggungan', lazy='dynamic', cascade='all, delete-orphan')
    )
    gedung = db.relationship(
        'Gedung', backref=db.backref('fasilitator_links', lazy='dynamic', cascade='all, delete-orphan')
    )

    def __init__(self, fasilitator_id: int = None, gedung_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.fasilitator_id = fasilitator_id
        self.gedung_id = gedung_id

    def __repr__(self):
        return f"<FasilitatorGedung fasil={self.fasilitator_id} gedung={self.gedung_id}>"
