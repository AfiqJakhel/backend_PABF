"""
Repository untuk Presensi dan Izin (operasi khusus Fasilitator).
Mengabstraksi semua query database terkait presensi mahasiswa dan izin.
"""

from datetime import date
from sqlalchemy import func
from app.core.extensions import db
from app.models.presensi import Presensi
from app.models.izin import Izin
from app.models.user import User


class PresensiRepository:
    """Data Access Object untuk tabel presensi (operasi fasilitator)."""

    @staticmethod
    def get_by_sesi(tipe_sesi: str, tanggal: date) -> list[Presensi]:
        """
        Ambil semua record presensi untuk tipe sesi dan tanggal tertentu.
        Berguna untuk monitoring real-time kehadiran pada satu sesi.
        """
        return (
            Presensi.query
            .filter(Presensi.sesi == tipe_sesi, Presensi.tanggal == tanggal)
            .all()
        )

    @staticmethod
    def get_mahasiswa_belum_absen(tipe_sesi: str, tanggal: date) -> list[User]:
        """
        Ambil daftar mahasiswa (role='mahasiswa') yang BELUM melakukan absensi
        pada tipe sesi dan tanggal tertentu.
        """
        # Subquery: user_id yang sudah absen
        sudah_absen_ids = db.session.query(Presensi.user_id).filter(
            Presensi.sesi == tipe_sesi,
            Presensi.tanggal == tanggal
        ).subquery()

        return (
            User.query
            .filter(
                User.role == 'mahasiswa',
                ~User.id.in_(sudah_absen_ids)
            )
            .order_by(User.nama.asc())
            .all()
        )

    @staticmethod
    def get_by_id(presensi_id: int) -> Presensi | None:
        """Ambil satu record presensi berdasarkan ID."""
        return Presensi.query.get(presensi_id)

    @staticmethod
    def get_rekap(
        tanggal_mulai: date,
        tanggal_selesai: date,
        tipe_sesi: str = None,
        user_id: int = None,
        page: int = 1,
        per_page: int = 20
    ):
        """
        Ambil rekapitulasi presensi berdasarkan rentang tanggal.
        Mendukung filter per tipe sesi dan per mahasiswa, dengan pagination.
        """
        query = Presensi.query.filter(
            Presensi.tanggal >= tanggal_mulai,
            Presensi.tanggal <= tanggal_selesai
        )
        if tipe_sesi:
            query = query.filter(Presensi.sesi == tipe_sesi)
        if user_id:
            query = query.filter(Presensi.user_id == user_id)

        return query.order_by(Presensi.tanggal.desc(), Presensi.waktu.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

    @staticmethod
    def get_rekap_summary(
        tanggal_mulai: date,
        tanggal_selesai: date,
        tipe_sesi: str = None
    ) -> list[dict]:
        """
        Hitung ringkasan kehadiran per mahasiswa dalam rentang tanggal.
        Mengembalikan list dict: {nim, nama, hadir, terlambat, alfa, izin, sakit, total}.
        """
        query = (
            db.session.query(
                User.nim,
                User.nama,
                Presensi.status,
                func.count(Presensi.id).label('jumlah')
            )
            .join(Presensi, User.id == Presensi.user_id)
            .filter(
                Presensi.tanggal >= tanggal_mulai,
                Presensi.tanggal <= tanggal_selesai,
                User.role == 'mahasiswa'
            )
        )
        if tipe_sesi:
            query = query.filter(Presensi.sesi == tipe_sesi)

        rows = query.group_by(User.nim, User.nama, Presensi.status).all()

        # Pivot: struktur per mahasiswa
        summary: dict = {}
        for nim, nama, status, jumlah in rows:
            if nim not in summary:
                summary[nim] = {
                    'nim': nim, 'nama': nama,
                    'hadir': 0, 'terlambat': 0,
                    'alfa': 0, 'izin': 0, 'sakit': 0
                }
            if status in summary[nim]:
                summary[nim][status] = jumlah

        # Hitung total
        result = []
        for data in summary.values():
            data['total'] = sum(data[k] for k in ('hadir', 'terlambat', 'alfa', 'izin', 'sakit'))
            result.append(data)

        return sorted(result, key=lambda x: x['nama'])

    @staticmethod
    def update_status(presensi: Presensi, status: str, keterangan: str = None) -> Presensi:
        """Update status dan keterangan presensi tertentu."""
        presensi.status = status
        if keterangan is not None:
            presensi.keterangan = keterangan
        db.session.commit()
        return presensi

    @staticmethod
    def create_manual(data: dict) -> Presensi:
        """
        Buat record presensi secara manual untuk mahasiswa yang belum absen.
        Digunakan fasilitator saat memasukkan status 'alfa' atau 'izin' secara manual.
        """
        presensi = Presensi(**data)
        db.session.add(presensi)
        db.session.commit()
        return presensi


class IzinRepository:
    """Data Access Object untuk tabel izin (operasi fasilitator)."""

    @staticmethod
    def get_all(status: str = None, page: int = 1, per_page: int = 15):
        """Ambil semua pengajuan izin, dengan filter status opsional."""
        query = Izin.query
        if status:
            query = query.filter(Izin.status == status)
        return query.order_by(Izin.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

    @staticmethod
    def get_by_id(izin_id: int) -> Izin | None:
        """Ambil satu pengajuan izin berdasarkan ID."""
        return Izin.query.get(izin_id)

    @staticmethod
    def update_status(
        izin: Izin,
        status: str,
        fasil_id: int,
        catatan: str = None
    ) -> Izin:
        """Setujui atau tolak pengajuan izin."""
        izin.status = status
        izin.disetujui_oleh = fasil_id
        izin.catatan_fasil = catatan
        db.session.commit()
        return izin
