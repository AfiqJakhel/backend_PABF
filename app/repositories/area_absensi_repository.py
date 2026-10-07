"""
Repository untuk AreaAbsensi.
Mengabstraksi semua query database termasuk MySQL Spatial Functions
untuk Point-in-Polygon validation.
"""

from sqlalchemy import text
from app.core.extensions import db
from app.models.area_absensi import AreaAbsensi


class AreaAbsensiRepository:
    """Data Access Object untuk tabel area_absensi."""

    @staticmethod
    def get_all(aktif_only: bool = False) -> list[AreaAbsensi]:
        """Ambil semua area absensi, opsional filter hanya yang aktif."""
        query = AreaAbsensi.query
        if aktif_only:
            query = query.filter(AreaAbsensi.is_active == True)
        return query.order_by(AreaAbsensi.created_at.desc()).all()

    @staticmethod
    def get_by_id(area_id: int) -> AreaAbsensi | None:
        """Ambil satu area berdasarkan ID."""
        return AreaAbsensi.query.get(area_id)

    @staticmethod
    def create(data: dict) -> AreaAbsensi:
        """Buat area baru dan simpan ke database."""
        area = AreaAbsensi(**data)
        db.session.add(area)
        db.session.commit()
        return area

    @staticmethod
    def update(area: AreaAbsensi, data: dict) -> AreaAbsensi:
        """Update atribut area dan simpan perubahan."""
        for key, value in data.items():
            if hasattr(area, key):
                setattr(area, key, value)
        db.session.commit()
        return area

    @staticmethod
    def delete(area: AreaAbsensi) -> None:
        """Hapus area dari database."""
        db.session.delete(area)
        db.session.commit()

    @staticmethod
    def toggle_active(area: AreaAbsensi) -> AreaAbsensi:
        """Toggle status is_active area."""
        area.is_active = not area.is_active
        db.session.commit()
        return area

    @staticmethod
    def get_by_gedung(gedung_id: int, aktif_only: bool = False) -> list[AreaAbsensi]:
        """Ambil semua area absensi milik gedung tertentu."""
        query = AreaAbsensi.query.filter(AreaAbsensi.gedung_id == gedung_id)
        if aktif_only:
            query = query.filter(AreaAbsensi.is_active == True)
        return query.order_by(AreaAbsensi.created_at.desc()).all()

    @staticmethod
    def find_area_containing_point(latitude: float, longitude: float, gedung_id: int = None) -> AreaAbsensi | None:
        """
        Cari area absensi aktif yang mengandung titik GPS user.
        Jika gedung_id diberikan, batasi pencarian hanya pada polygon milik gedung tersebut.
        Menggunakan MySQL Spatial Function ST_Contains dengan ST_GeomFromText.

        Urutan koordinat WKT: POINT(longitude latitude) — sesuai standar GeoJSON.
        """
        point_wkt = f"POINT({longitude} {latitude})"

        if gedung_id is not None:
            sql = text("""
                SELECT id FROM area_absensi
                WHERE is_active = 1
                  AND gedung_id = :gedung_id
                  AND ST_Contains(
                        ST_GeomFromText(polygon_wkt, 4326),
                        ST_GeomFromText(:point_wkt, 4326)
                      )
                LIMIT 1
            """)
            params = {"point_wkt": point_wkt, "gedung_id": gedung_id}
        else:
            sql = text("""
                SELECT id FROM area_absensi
                WHERE is_active = 1
                  AND ST_Contains(
                        ST_GeomFromText(polygon_wkt, 4326),
                        ST_GeomFromText(:point_wkt, 4326)
                      )
                LIMIT 1
            """)
            params = {"point_wkt": point_wkt}

        row = db.session.execute(sql, params).first()

        if row:
            return AreaAbsensi.query.get(row[0])
        return None
