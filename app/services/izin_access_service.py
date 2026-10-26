"""
Service Otorisasi Level Objek (Object-Level Authorization) untuk fitur Perizinan.
Aturan:
- Mahasiswa hanya berhak atas izin miliknya sendiri; jika mengakses milik orang lain -> 404.
- Fasilitator hanya berhak atas izin mahasiswa di gedung tanggung jawabnya; jika mengakses izin di luar gedungnya -> 404 (bukan 403) agar tidak membocorkan keberadaan data.
- Admin berhak melihat (read-only) semua izin.
"""

from typing import Tuple, Optional
from app.models.izin import Izin
from app.models.user import User
from app.repositories.izin_repository import IzinRepository, FasilitatorGedungRepository


class IzinAccessService:
    @staticmethod
    def get_mahasiswa_gedung_id(user: User) -> Optional[int]:
        """Mendapatkan gedung_id tempat mahasiswa tinggal."""
        if user and user.kamar_ref:
            return user.kamar_ref.gedung_id
        return None

    @staticmethod
    def authorize_and_get_izin(izin_id: int, user: User) -> Tuple[Optional[Izin], Optional[str], int]:
        """
        Validasi otorisasi dan ambil objek Izin.
        Mengembalikan (izin, error_message, http_status_code).
        Jika tidak berhak atau tidak ditemukan, kembalikan 404.
        """
        izin = IzinRepository.get_by_id(izin_id)
        if not izin:
            return None, "Pengajuan izin tidak ditemukan.", 404

        role = user.role

        # 1. Admin memiliki hak akses baca ke semua data izin
        if role == "admin":
            return izin, None, 200

        # 2. Mahasiswa hanya boleh melihat izin miliknya sendiri
        if role == "mahasiswa":
            if izin.user_id != user.id:
                # 404 agar tidak membocorkan keberadaan ID izin orang lain
                return None, "Pengajuan izin tidak ditemukan.", 404
            return izin, None, 200

        # 3. Fasilitator hanya boleh melihat izin mahasiswa di gedungnya
        if role in ("fasil", "fasilitator"):
            pemohon = izin.pemohon
            pemohon_gedung_id = pemohon.kamar_ref.gedung_id if (pemohon and pemohon.kamar_ref) else None

            if not pemohon_gedung_id:
                return None, "Pengajuan izin tidak ditemukan.", 404

            is_authorized = FasilitatorGedungRepository.is_fasilitator_of_building(user.id, pemohon_gedung_id)
            if not is_authorized:
                # Wajib 404 (bukan 403) sesuai aturan bisnis untuk mencegah data leakage
                return None, "Pengajuan izin tidak ditemukan.", 404

            return izin, None, 200

        return None, "Pengajuan izin tidak ditemukan.", 404

    @staticmethod
    def authorize_for_cancellation(izin_id: int, user: User) -> Tuple[Optional[Izin], Optional[str], int]:
        """
        Validasi apakah pengguna berhak membatalkan izin.
        Hanya mahasiswa pemohon yang boleh membatalkan izinnya sendiri.
        """
        if user.role != "mahasiswa":
            return None, "Hanya mahasiswa pemohon yang dapat membatalkan pengajuan izin.", 403

        izin = IzinRepository.get_by_id(izin_id)
        if not izin:
            return None, "Pengajuan izin tidak ditemukan.", 404

        if izin.user_id != user.id:
            return None, "Pengajuan izin tidak ditemukan.", 404

        if izin.status != "pending":
            return None, f"Izin dengan status '{izin.status}' tidak dapat dibatalkan.", 409

        return izin, None, 200

    @staticmethod
    def authorize_for_review(izin_id: int, user: User) -> Tuple[Optional[Izin], Optional[str], int]:
        """
        Validasi apakah pengguna berhak mereview (approve/reject) izin.
        Hanya fasilitator gedung terkait yang boleh mereview.
        Admin bersifat READ-ONLY untuk perizinan.
        """
        if user.role == "admin":
            return None, "Akses ditolak: Administrator hanya memiliki akses baca (read-only) pada izin.", 403

        if user.role not in ("fasil", "fasilitator"):
            return None, "Akses ditolak: Hanya Fasilitator yang berwenang mereview izin.", 403

        izin = IzinRepository.get_by_id(izin_id)
        if not izin:
            return None, "Pengajuan izin tidak ditemukan.", 404

        pemohon = izin.pemohon
        pemohon_gedung_id = pemohon.kamar_ref.gedung_id if (pemohon and pemohon.kamar_ref) else None

        if not pemohon_gedung_id or not FasilitatorGedungRepository.is_fasilitator_of_building(user.id, pemohon_gedung_id):
            # Wajib 404 (bukan 403) sesuai aturan bisnis
            return None, "Pengajuan izin tidak ditemukan.", 404

        if izin.status != "pending":
            return None, f"Izin ini sudah diproses sebelumnya dengan status '{izin.status}'.", 409

        return izin, None, 200
