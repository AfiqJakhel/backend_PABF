from datetime import datetime
from app.core.extensions import db
from app.utils.polygon import wkt_to_geojson_coords


class AreaAbsensi(db.Model):
    """
    Model untuk menyimpan area absensi dalam format polygon.
    Polygon disimpan sebagai WKT (Well-Known Text) agar kompatibel
    dengan MySQL Spatial Functions (ST_Contains, ST_GeomFromText).
    """
    __tablename__ = "area_absensi"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nama = db.Column(db.String(100), nullable=False)
    deskripsi = db.Column(db.Text, nullable=True)
    # WKT format: POLYGON((lon lat, lon lat, ...)) — longitude dulu, baru latitude
    polygon_wkt = db.Column(db.Text, nullable=False)
    gedung_id = db.Column(
        db.Integer,
        db.ForeignKey("gedung.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    dibuat_oleh = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    gedung = db.relationship(
        "Gedung",
        backref=db.backref("polygon_areas", cascade="all, delete-orphan", lazy="dynamic")
    )
    pembuat = db.relationship(
        "User",
        foreign_keys=[dibuat_oleh],
        backref=db.backref("area_dibuat", lazy="dynamic")
    )

    def __init__(self, nama: str = "", deskripsi: str = None,
                 polygon_wkt: str = "", gedung_id: int = None,
                 is_active: bool = True, dibuat_oleh: int = None, **kwargs):
        super().__init__(**kwargs)
        self.nama = nama
        self.deskripsi = deskripsi
        self.polygon_wkt = polygon_wkt
        self.gedung_id = gedung_id
        self.is_active = is_active
        self.dibuat_oleh = dibuat_oleh

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nama": self.nama,
            "deskripsi": self.deskripsi,
            "gedung_id": self.gedung_id,
            "nama_gedung": self.gedung.nama_gedung if self.gedung else None,
            "coordinates": wkt_to_geojson_coords(self.polygon_wkt) if self.polygon_wkt else None,
            "is_active": self.is_active,
            "dibuat_oleh": self.dibuat_oleh,
            "nama_pembuat": self.pembuat.nama if self.pembuat else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<AreaAbsensi {self.nama} ({'aktif' if self.is_active else 'nonaktif'})>"
