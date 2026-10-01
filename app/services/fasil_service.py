"""
Service Layer untuk Fasilitator.
Berisi semua business logic terkait:
  - Manajemen Sesi Absensi
  - Monitoring & Rekapitulasi Presensi
  - Persetujuan / Penolakan Izin
"""

from datetime import date, datetime
from app.repositories.sesi_absensi_repository import SesiAbsensiRepository
from app.repositories.fasil_repository import PresensiRepository, IzinRepository
from app.models.user import User


# ─── Sesi Absensi Service ────────────────────────────────────────────────────

class SesiAbsensiService:
    """Business logic untuk pengelolaan sesi absensi oleh Fasilitator."""

    @staticmethod
    def buat_sesi(parsed_data: dict, fasil_id: int) -> dict:
        """
        Buat sesi absensi baru.
        - Menambahkan fasil_id sebagai pembuat.
        - Menurunkan tanggal dari waktu_mulai jika tidak disertakan.
        """
        parsed_data['dibuat_oleh'] = fasil_id
        # Ambil tanggal dari waktu_mulai
        if 'waktu_mulai' in parsed_data and 'tanggal' not in parsed_data:
            parsed_data['tanggal'] = parsed_data['waktu_mulai'].date()

        sesi = SesiAbsensiRepository.create(parsed_data)
        return sesi.to_dict()

    @staticmethod
    def get_daftar_sesi(page: int, per_page: int, status: str = None,
                        tipe_sesi: str = None, tanggal_str: str = None) -> dict:
        """Ambil daftar sesi dengan pagination dan filter opsional."""
        tanggal = None
        if tanggal_str:
            try:
                tanggal = date.fromisoformat(tanggal_str)
            except ValueError:
                return {"error": "Format 'tanggal' tidak valid. Gunakan YYYY-MM-DD."}

        pagination = SesiAbsensiRepository.get_all(
            page=page, per_page=per_page,
            status=status, tipe_sesi=tipe_sesi, tanggal=tanggal
        )
        return {
            "items": [s.to_dict() for s in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
        }

    @staticmethod
    def get_sesi_aktif() -> list:
        """Ambil semua sesi yang sedang aktif saat ini."""
        sesi_list = SesiAbsensiRepository.get_aktif()
        return [s.to_dict() for s in sesi_list]

    @staticmethod
    def get_sesi_by_id(sesi_id: int) -> dict | None:
        """Ambil detail satu sesi. Return None jika tidak ditemukan."""
        sesi = SesiAbsensiRepository.get_by_id(sesi_id)
        return sesi.to_dict() if sesi else None

    @staticmethod
    def update_sesi(sesi_id: int, parsed_data: dict) -> tuple:
        """
        Update sesi absensi. Kembalikan (data_dict, error_str).
        - error_str None jika sukses.
        - error_str berisi pesan jika sesi tidak ditemukan.
        """
        sesi = SesiAbsensiRepository.get_by_id(sesi_id)
        if not sesi:
            return None, "Sesi absensi tidak ditemukan."

        updated = SesiAbsensiRepository.update(sesi, parsed_data)
        return updated.to_dict(), None

    @staticmethod
    def tutup_sesi(sesi_id: int) -> tuple:
        """
        Menutup sesi absensi secara manual oleh fasilitator.
        Kembalikan (data_dict, error_str).
        """
        sesi = SesiAbsensiRepository.get_by_id(sesi_id)
        if not sesi:
            return None, "Sesi absensi tidak ditemukan."
        if sesi.status == 'ditutup':
            return None, "Sesi ini sudah ditutup sebelumnya."

        updated = SesiAbsensiRepository.update(sesi, {"status": "ditutup"})
        return updated.to_dict(), None


# ─── Presensi Service (Fasilitator) ──────────────────────────────────────────

class PresensiService:
    """Business logic untuk monitoring dan pengelolaan presensi oleh Fasilitator."""

    @staticmethod
    def get_rekap_sesi(tipe_sesi: str, tanggal_str: str) -> tuple:
        """
        Ambil rekapitulasi lengkap satu sesi:
        - Daftar mahasiswa yang SUDAH absen (beserta statusnya).
        - Daftar mahasiswa yang BELUM absen.
        """
        try:
            tanggal = date.fromisoformat(tanggal_str)
        except (ValueError, TypeError):
            return None, "Format 'tanggal' tidak valid. Gunakan YYYY-MM-DD."

        sudah = PresensiRepository.get_by_sesi(tipe_sesi, tanggal)
        belum = PresensiRepository.get_mahasiswa_belum_absen(tipe_sesi, tanggal)

        return {
            "tanggal": tanggal_str,
            "sesi": tipe_sesi,
            "total_sudah_absen": len(sudah),
            "total_belum_absen": len(belum),
            "sudah_absen": [p.to_dict() for p in sudah],
            "belum_absen": [
                {"user_id": u.id, "nim": u.nim, "nama": u.nama, "kamar_id": u.kamar_id}
                for u in belum
            ],
        }, None

    @staticmethod
    def update_status_manual(presensi_id: int, parsed_data: dict) -> tuple:
        """
        Ubah status presensi mahasiswa secara manual.
        Kembalikan (data_dict, error_str).
        """
        presensi = PresensiRepository.get_by_id(presensi_id)
        if not presensi:
            return None, "Record presensi tidak ditemukan."

        updated = PresensiRepository.update_status(
            presensi,
            status=parsed_data["status"],
            keterangan=parsed_data.get("keterangan")
        )
        return updated.to_dict(), None

    @staticmethod
    def input_presensi_manual(user_id: int, tipe_sesi: str,
                              status: str, keterangan: str = None,
                              tanggal: date = None) -> tuple:
        """
        Buat record presensi baru secara manual (untuk mahasiswa yang belum absen sama sekali).
        Kembalikan (data_dict, error_str).
        """
        from app.models.presensi import Presensi
        from app.core.extensions import db

        tanggal = tanggal or date.today()

        # Cek apakah sudah ada record untuk hari ini dan sesi ini
        existing = Presensi.query.filter_by(
            user_id=user_id, tanggal=tanggal, sesi=tipe_sesi
        ).first()
        if existing:
            return None, (
                f"Mahasiswa sudah memiliki record presensi untuk sesi '{tipe_sesi}' "
                f"pada tanggal {tanggal.isoformat()}. Gunakan endpoint update status."
            )

        # Ambil data user
        user = User.query.get(user_id)
        if not user or user.role != 'mahasiswa':
            return None, "Mahasiswa tidak ditemukan."

        presensi = PresensiRepository.create_manual({
            "user_id": user_id,
            "nim": user.nim,
            "tanggal": tanggal,
            "waktu": datetime.utcnow(),
            "sesi": tipe_sesi,
            "status": status,
            "keterangan": keterangan,
        })
        return presensi.to_dict(), None

    @staticmethod
    def get_rekap_rentang(
        tanggal_mulai_str: str,
        tanggal_selesai_str: str,
        tipe_sesi: str = None,
        user_id: int = None,
        page: int = 1,
        per_page: int = 20,
        summary: bool = False
    ) -> tuple:
        """
        Ambil rekapitulasi presensi berdasarkan rentang tanggal.
        - Jika summary=True, kembalikan ringkasan per mahasiswa.
        - Jika summary=False, kembalikan daftar detail record presensi (paginated).
        """
        try:
            tgl_mulai = date.fromisoformat(tanggal_mulai_str)
            tgl_selesai = date.fromisoformat(tanggal_selesai_str)
        except (ValueError, TypeError):
            return None, "Format tanggal tidak valid. Gunakan YYYY-MM-DD."

        if tgl_selesai < tgl_mulai:
            return None, "'tanggal_selesai' tidak boleh sebelum 'tanggal_mulai'."

        if summary:
            data = PresensiRepository.get_rekap_summary(tgl_mulai, tgl_selesai, tipe_sesi)
            return {
                "tanggal_mulai": tanggal_mulai_str,
                "tanggal_selesai": tanggal_selesai_str,
                "sesi": tipe_sesi or "semua",
                "summary": data,
                "total_mahasiswa": len(data),
            }, None
        else:
            pagination = PresensiRepository.get_rekap(
                tgl_mulai, tgl_selesai, tipe_sesi, user_id, page, per_page
            )
            return {
                "tanggal_mulai": tanggal_mulai_str,
                "tanggal_selesai": tanggal_selesai_str,
                "items": [p.to_dict() for p in pagination.items],
                "total": pagination.total,
                "page": pagination.page,
                "pages": pagination.pages,
                "per_page": pagination.per_page,
            }, None


# ─── Izin Service (Fasilitator) ───────────────────────────────────────────────

class IzinService:
    """Business logic untuk pengelolaan pengajuan izin oleh Fasilitator."""

    @staticmethod
    def get_daftar_izin(status: str = None, page: int = 1, per_page: int = 15) -> dict:
        """Ambil semua pengajuan izin dengan filter status opsional."""
        pagination = IzinRepository.get_all(status=status, page=page, per_page=per_page)
        return {
            "items": [i.to_dict() for i in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
        }

    @staticmethod
    def get_detail_izin(izin_id: int) -> dict | None:
        """Ambil detail satu pengajuan izin."""
        izin = IzinRepository.get_by_id(izin_id)
        return izin.to_dict() if izin else None

    @staticmethod
    def proses_izin(izin_id: int, fasil_id: int, parsed_data: dict) -> tuple:
        """
        Setujui atau tolak pengajuan izin.
        Kembalikan (data_dict, error_str).
        Mencegah pemrosesan ulang izin yang sudah diputuskan.
        """
        izin = IzinRepository.get_by_id(izin_id)
        if not izin:
            return None, "Pengajuan izin tidak ditemukan."

        if izin.status != 'pending':
            return None, (
                f"Izin ini sudah diproses sebelumnya dengan status '{izin.status}'. "
                "Tidak dapat diubah lagi."
            )

        updated = IzinRepository.update_status(
            izin,
            status=parsed_data["status"],
            fasil_id=fasil_id,
            catatan=parsed_data.get("catatan_fasil")
        )
        return updated.to_dict(), None
