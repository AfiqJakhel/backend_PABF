"""
Repository untuk entitas Izin, IzinDokumen, FasilitatorGedung, dan SesiPresensi.
Semua query menggunakan SQLAlchemy ORM murni tanpa raw SQL concatenation.
"""

from typing import List, Optional, Tuple
from sqlalchemy import or_, and_
from app.core.extensions import db
from app.models.izin import Izin, STATUS_AKTIF, STATUS_PENDING
from app.models.izin_dokumen import IzinDokumen
from app.models.fasilitator_gedung import FasilitatorGedung
from app.models.sesi_presensi import SesiPresensi
from app.models.user import User
from app.models.kamar import Kamar
from app.models.gedung import Gedung


class IzinRepository:
    @staticmethod
    def get_by_id(izin_id: int) -> Optional[Izin]:
        """Mengambil izin berdasarkan ID."""
        return Izin.query.get(izin_id)

    @staticmethod
    def lock_user_for_update(user_id: int) -> Optional[User]:
        """Mengunci record user untuk mencegah race condition / double-submit pengajuan."""
        try:
            return User.query.filter_by(id=user_id).with_for_update().first()
        except Exception:
            # Fallback untuk backend database yang tidak mendukung with_for_update (misal SQLite in-memory test)
            return User.query.get(user_id)

    @staticmethod
    def find_overlapping_izin(mahasiswa_id: int, tgl_mulai, tgl_selesai, jenis: str, sesi_id: Optional[int]) -> List[Izin]:
        """
        Mencari izin aktif (pending / approved) milik mahasiswa yang tumpang tindih.

        Logika tumpang tindih:
        1. Rentang tanggal bersinggungan jika:
           existing.tanggal_mulai <= baru.tanggal_selesai AND existing.tanggal_selesai >= baru.tanggal_mulai
        2. Jika salah satu atau keduanya adalah 'full', maka otomatis overlap jika tanggal bersinggungan.
        3. Jika keduanya adalah 'half', overlap terjadi HANYA jika tanggal sama DAN sesi_id sama.
        """
        base_query = Izin.query.filter(
            Izin.user_id == mahasiswa_id,
            Izin.status.in_(STATUS_AKTIF),
            Izin.tanggal_mulai <= tgl_selesai,
            Izin.tanggal_selesai >= tgl_mulai
        )

        candidates = base_query.all()
        overlapping = []

        for cand in candidates:
            # Jika salah satu bertipe 'full', jelas terjadi tumpang tindih
            if cand.jenis == 'full' or jenis == 'full':
                overlapping.append(cand)
            else:
                # Keduanya 'half': tumpang tindih hanya jika tanggal sama dan sesi_id sama
                if cand.tanggal_mulai == tgl_mulai and cand.sesi_id == sesi_id:
                    overlapping.append(cand)

        return overlapping

    @staticmethod
    def get_mahasiswa_izin_list(mahasiswa_id: int, status: Optional[str] = None, page: int = 1, per_page: int = 15):
        """Daftar riwayat izin milik mahasiswa sendiri."""
        q = Izin.query.filter_by(user_id=mahasiswa_id)
        if status:
            q = q.filter_by(status=status)
        return q.order_by(Izin.created_at.desc(), Izin.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_review_list_by_gedung_ids(gedung_ids: Optional[List[int]], status: Optional[str] = None, page: int = 1, per_page: int = 15):
        """
        Daftar izin untuk direview fasilitator (dibatasi gedung) atau admin (semua gedung jika gedung_ids is None).
        """
        q = Izin.query.join(User, Izin.user_id == User.id).join(Kamar, User.kamar_id == Kamar.id)

        if gedung_ids is not None:
            q = q.filter(Kamar.gedung_id.in_(gedung_ids))

        if status:
            q = q.filter(Izin.status == status)

        return q.order_by(Izin.created_at.desc(), Izin.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def atomic_cancel(izin_id: int, mahasiswa_id: int, cancelled_at) -> bool:
        """
        Transisi status atomic ke 'cancelled' hanya jika status saat ini 'pending' dan user_id cocok.
        Mengembalikan True jika 1 baris berhasil diupdate, False jika status sudah bukan pending.
        """
        rows = Izin.query.filter(
            Izin.id == izin_id,
            Izin.user_id == mahasiswa_id,
            Izin.status == STATUS_PENDING
        ).update({
            Izin.status: 'cancelled',
            Izin.cancelled_at: cancelled_at
        }, synchronize_session=False)

        db.session.commit()
        return rows == 1

    @staticmethod
    def atomic_review(izin_id: int, target_status: str, reviewer_id: int, catatan: Optional[str], reviewed_at) -> bool:
        """
        Transisi status atomic ke 'approved' atau 'rejected' hanya jika status saat ini 'pending'.
        Mengembalikan True jika 1 baris berhasil diupdate.
        """
        rows = Izin.query.filter(
            Izin.id == izin_id,
            Izin.status == STATUS_PENDING
        ).update({
            Izin.status: target_status,
            Izin.disetujui_oleh: reviewer_id,
            Izin.catatan_fasil: catatan,
            Izin.reviewed_at: reviewed_at
        }, synchronize_session=False)

        db.session.commit()
        return rows == 1


class FasilitatorGedungRepository:
    @staticmethod
    def get_gedung_ids_by_fasilitator(fasil_id: int) -> List[int]:
        """
        Mendapatkan ID semua gedung yang menjadi tanggung jawab fasilitator.
        Mencakup dari tabel `fasilitator_gedung` dan fallback dari `gedung.user_id`.
        """
        ids = set()

        # Dari tabel fasilitator_gedung
        rows = FasilitatorGedung.query.filter_by(fasilitator_id=fasil_id).all()
        for r in rows:
            ids.add(r.gedung_id)

        # Fallback kompatibilitas jika gedung.user_id belum termigrasi sempurna
        gedung_lama = Gedung.query.filter_by(user_id=fasil_id).all()
        for g in gedung_lama:
            ids.add(g.id)

        return list(ids)

    @staticmethod
    def is_fasilitator_of_building(fasil_id: int, gedung_id: int) -> bool:
        """Memeriksa apakah fasilitator berwenang atas gedung tertentu."""
        if not gedung_id:
            return False
        assigned = FasilitatorGedungRepository.get_gedung_ids_by_fasilitator(fasil_id)
        return gedung_id in assigned


class SesiPresensiRepository:
    @staticmethod
    def get_all_active() -> List[SesiPresensi]:
        return SesiPresensi.query.filter_by(is_active=True).order_by(SesiPresensi.id.asc()).all()

    @staticmethod
    def get_by_id(sesi_id: int) -> Optional[SesiPresensi]:
        return SesiPresensi.query.get(sesi_id)

    @staticmethod
    def get_by_kode(kode: str) -> Optional[SesiPresensi]:
        return SesiPresensi.query.filter_by(kode=kode).first()
