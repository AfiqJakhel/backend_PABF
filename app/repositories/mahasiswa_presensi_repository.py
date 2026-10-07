"""
Repository untuk operasi presensi mahasiswa (self-service).
Mengabstraksi query database agar service layer tidak bersentuhan langsung dengan ORM.
"""

from datetime import date
from app.core.extensions import db
from app.models.presensi import Presensi


class MahasiswaPresensiRepository:
    """Data Access Object untuk tabel presensi (operasi mahasiswa)."""

    @staticmethod
    def get_by_user_tanggal_sesi(
        user_id: int, tanggal: date, sesi: str
    ) -> Presensi | None:
        """
        Cek apakah mahasiswa sudah memiliki record presensi
        untuk kombinasi user + tanggal + sesi tertentu.
        Digunakan untuk mencegah duplikat absensi.
        """
        return Presensi.query.filter_by(
            user_id=user_id,
            tanggal=tanggal,
            sesi=sesi
        ).first()

    @staticmethod
    def create_from_selfie(data: dict) -> Presensi:
        """
        Buat record presensi baru dari hasil selfie mahasiswa.

        Expected keys in data:
            user_id, nim, tanggal, waktu, sesi,
            latitude, longitude, accuracy,
            status, foto_wajah, area_absensi_id, keterangan
        """
        presensi = Presensi(**data)
        db.session.add(presensi)
        db.session.commit()
        return presensi
