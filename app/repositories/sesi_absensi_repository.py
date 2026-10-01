"""
Repository untuk SesiAbsensi.
Mengabstraksi semua query database terkait sesi absensi,
sehingga Service layer tidak perlu tahu detail ORM.
"""

from datetime import date, datetime
from app.core.extensions import db
from app.models.sesi_absensi import SesiAbsensi


class SesiAbsensiRepository:
    """Data Access Object untuk tabel sesi_absensi."""

    @staticmethod
    def get_all(page: int = 1, per_page: int = 15, status: str = None,
                tipe_sesi: str = None, tanggal: date = None):
        """
        Ambil semua sesi dengan filter opsional dan pagination.
        Diurutkan dari yang terbaru.
        """
        query = SesiAbsensi.query

        if status:
            query = query.filter(SesiAbsensi.status == status)
        if tipe_sesi:
            query = query.filter(SesiAbsensi.tipe_sesi == tipe_sesi)
        if tanggal:
            query = query.filter(SesiAbsensi.tanggal == tanggal)

        return query.order_by(SesiAbsensi.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

    @staticmethod
    def get_aktif():
        """
        Ambil semua sesi yang statusnya 'aktif' dan waktu sekarang masih dalam rentang.
        Berguna untuk real-time monitoring.
        """
        now = datetime.utcnow()
        return SesiAbsensi.query.filter(
            SesiAbsensi.status == 'aktif',
            SesiAbsensi.waktu_mulai <= now,
            SesiAbsensi.waktu_selesai >= now,
        ).order_by(SesiAbsensi.waktu_mulai.asc()).all()

    @staticmethod
    def get_by_id(sesi_id: int) -> SesiAbsensi | None:
        """Ambil sesi berdasarkan ID."""
        return SesiAbsensi.query.get(sesi_id)

    @staticmethod
    def create(data: dict) -> SesiAbsensi:
        """Buat sesi baru dan simpan ke database."""
        sesi = SesiAbsensi(**data)
        db.session.add(sesi)
        db.session.commit()
        return sesi

    @staticmethod
    def update(sesi: SesiAbsensi, data: dict) -> SesiAbsensi:
        """Update atribut sesi dan simpan perubahan."""
        for key, value in data.items():
            if hasattr(sesi, key):
                setattr(sesi, key, value)
        db.session.commit()
        return sesi

    @staticmethod
    def delete(sesi: SesiAbsensi) -> None:
        """Hapus sesi dari database (jarang digunakan; lebih baik tutup saja)."""
        db.session.delete(sesi)
        db.session.commit()
