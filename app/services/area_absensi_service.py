"""
Service Layer untuk pengelolaan Area Absensi oleh Administrator.
Mengikuti pola fasil_service.py.
"""

from app.repositories.area_absensi_repository import AreaAbsensiRepository


class AreaAbsensiService:
    """Business logic untuk CRUD area absensi."""

    @staticmethod
    def get_semua_area(aktif_only: bool = False) -> list:
        areas = AreaAbsensiRepository.get_all(aktif_only=aktif_only)
        return [a.to_dict() for a in areas]

    @staticmethod
    def get_area_by_id(area_id: int) -> dict | None:
        area = AreaAbsensiRepository.get_by_id(area_id)
        return area.to_dict() if area else None

    @staticmethod
    def buat_area(parsed_data: dict, admin_id: int) -> dict:
        """Buat area absensi baru."""
        parsed_data["dibuat_oleh"] = admin_id
        area = AreaAbsensiRepository.create(parsed_data)
        return area.to_dict()

    @staticmethod
    def update_area(area_id: int, parsed_data: dict) -> tuple:
        """
        Update area absensi. Return (data_dict, error_str).
        error_str adalah None jika sukses.
        """
        area = AreaAbsensiRepository.get_by_id(area_id)
        if not area:
            return None, "Area absensi tidak ditemukan."
        updated = AreaAbsensiRepository.update(area, parsed_data)
        return updated.to_dict(), None

    @staticmethod
    def hapus_area(area_id: int) -> tuple:
        """Hapus area absensi. Return (True, None) atau (None, error_str)."""
        area = AreaAbsensiRepository.get_by_id(area_id)
        if not area:
            return None, "Area absensi tidak ditemukan."
        AreaAbsensiRepository.delete(area)
        return True, None

    @staticmethod
    def toggle_active(area_id: int) -> tuple:
        """Toggle status aktif/nonaktif area. Return (data_dict, error_str)."""
        area = AreaAbsensiRepository.get_by_id(area_id)
        if not area:
            return None, "Area absensi tidak ditemukan."
        updated = AreaAbsensiRepository.toggle_active(area)
        return updated.to_dict(), None
