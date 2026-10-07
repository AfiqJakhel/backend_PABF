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
from app.models.kamar import Kamar
from app.models.gedung import Gedung


class PresensiRepository:
    """Data Access Object untuk tabel presensi (operasi fasilitator)."""

    @staticmethod
    def get_by_sesi(tipe_sesi: str, tanggal: date, gedung_id: int = None) -> list[Presensi]:
        """
        Ambil semua record presensi untuk tipe sesi dan tanggal tertentu.
        Jika gedung_id diberikan, batasi pada gedung tersebut.
        """
        query = Presensi.query.filter(Presensi.sesi == tipe_sesi, Presensi.tanggal == tanggal)
        if gedung_id is not None:
            query = query.filter(
                db.or_(
                    Presensi.gedung_id == gedung_id,
                    Presensi.user.has(User.kamar_ref.has(Kamar.gedung_id == gedung_id))
                )
            )
        return query.all()

    @staticmethod
    def get_mahasiswa_belum_absen(tipe_sesi: str, tanggal: date, gedung_id: int = None) -> list[User]:
        """
        Ambil daftar mahasiswa (role='mahasiswa') yang BELUM melakukan absensi
        pada tipe sesi dan tanggal tertentu.
        Jika gedung_id diberikan, hanya ambil mahasiswa yang kamarnya di gedung tersebut.
        """
        # Subquery: user_id yang sudah absen
        presensi_sub = db.session.query(Presensi.user_id).filter(
            Presensi.sesi == tipe_sesi,
            Presensi.tanggal == tanggal
        )
        if gedung_id is not None:
            presensi_sub = presensi_sub.filter(
                db.or_(
                    Presensi.gedung_id == gedung_id,
                    Presensi.user.has(User.kamar_ref.has(Kamar.gedung_id == gedung_id))
                )
            )
        sudah_absen_ids = presensi_sub.subquery()

        query = User.query.filter(
            User.role == 'mahasiswa',
            ~User.id.in_(sudah_absen_ids)
        )
        if gedung_id is not None:
            query = query.filter(User.kamar_ref.has(Kamar.gedung_id == gedung_id))

        return query.order_by(User.nama.asc()).all()

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
        per_page: int = 20,
        gedung_id: int = None
    ):
        """
        Ambil rekapitulasi presensi berdasarkan rentang tanggal.
        Mendukung filter per tipe sesi, per mahasiswa, dan per gedung.
        """
        query = Presensi.query.filter(
            Presensi.tanggal >= tanggal_mulai,
            Presensi.tanggal <= tanggal_selesai
        )
        if gedung_id is not None:
            query = query.filter(
                db.or_(
                    Presensi.gedung_id == gedung_id,
                    Presensi.user.has(User.kamar_ref.has(Kamar.gedung_id == gedung_id))
                )
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
        tipe_sesi: str = None,
        gedung_id: int = None
    ) -> list[dict]:
        """
        Hitung ringkasan kehadiran per mahasiswa dalam rentang tanggal.
        Mengembalikan list dict: {nim, nama, hadir, terlambat, alfa, izin, sakit, total}.
        """
        query = (
            db.session.query(
                User.nim,
                User.nama,
                Gedung.nama_gedung,
                Kamar.nomor_kamar,
                Presensi.status,
                func.count(Presensi.id).label('jumlah')
            )
            .join(Presensi, User.id == Presensi.user_id)
            .outerjoin(Kamar, User.kamar_id == Kamar.id)
            .outerjoin(Gedung, Kamar.gedung_id == Gedung.id)
            .filter(
                Presensi.tanggal >= tanggal_mulai,
                Presensi.tanggal <= tanggal_selesai,
                User.role == 'mahasiswa'
            )
        )
        if gedung_id is not None:
            query = query.filter(
                db.or_(
                    Presensi.gedung_id == gedung_id,
                    Kamar.gedung_id == gedung_id
                )
            )
        if tipe_sesi:
            query = query.filter(Presensi.sesi == tipe_sesi)

        rows = query.group_by(
            User.nim, User.nama, Gedung.nama_gedung, Kamar.nomor_kamar, Presensi.status
        ).all()

        # Pivot: struktur per mahasiswa
        summary: dict = {}
        for nim, nama, nama_gedung, nomor_kamar, status, jumlah in rows:
            if nim not in summary:
                summary[nim] = {
                    'nim': nim, 'nama': nama,
                    'gedung': nama_gedung,
                    'kamar': nomor_kamar,
                    'hadir': 0, 'terlambat': 0,
                    'alfa': 0, 'izin': 0, 'sakit': 0
                }
            if status in summary[nim]:
                summary[nim][status] = jumlah

        # Hitung total
        result = []
        for data in summary.values():
            data['total'] = sum(data[k] for k in ('hadir', 'terlambat', 'alfa', 'izin', 'sakit'))
            data['persentase'] = round(
                ((data['hadir'] + data['terlambat']) / data['total']) * 100, 2
            ) if data['total'] else 0
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
    def get_all(status: str = None, page: int = 1, per_page: int = 15, gedung_id: int = None):
        """Ambil semua pengajuan izin, dengan filter status dan gedung opsional."""
        query = Izin.query
        if gedung_id is not None:
            query = query.join(Izin.pemohon).filter(User.kamar_ref.has(Kamar.gedung_id == gedung_id))
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
