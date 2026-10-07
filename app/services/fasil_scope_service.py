"""
Centralized Building-Level Scope and Authorization Service for Facilitators.
Strictly enforces:
  FACILITATOR -> 1 GEDUNG -> DATA MAHASISWA -> PRESENSI -> REKAP & LAPORAN -> POLYGON PRESENSI

All database operations and API requests by facilitators MUST resolve the building
from the authenticated user's JWT identity and never from user-supplied parameters.
"""

from typing import Tuple, Optional
from flask import jsonify, Response
from flask_jwt_extended import get_jwt_identity, get_jwt
from app.models.user import User
from app.models.gedung import Gedung
from app.models.kamar import Kamar
from app.models.presensi import Presensi
from app.models.area_absensi import AreaAbsensi


def get_fasil_assigned_building(fasil_id: int) -> Tuple[Optional[Gedung], Optional[str]]:
    """
    Resolve facilitator's assigned building from authenticated user ID.
    Enforces strict 1-to-1 building ownership.
    Returns: (gedung, error_message)
    """
    fasil = User.query.filter_by(id=fasil_id).first()
    if not fasil or fasil.role not in ('fasil', 'admin'):
        return None, "Pengguna bukan fasilitator atau admin yang valid."
    
    # Check 1-to-1 building mapping
    gedung = Gedung.query.filter_by(user_id=fasil_id).first()
    if not gedung:
        return None, "Fasilitator belum ditugaskan ke gedung asrama manapun. Hubungi administrator."
    
    return gedung, None


def resolve_fasil_building() -> Tuple[Optional[Gedung], Optional[Response], Optional[int]]:
    """
    Helper function to be called in controller endpoints.
    Resolves the building for the currently logged-in JWT user.
    If resolution fails, returns (None, jsonify_error, http_status_code).
    If success, returns (gedung, None, None).
    """
    try:
        current_user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None, jsonify({
            "success": False,
            "message": "Identitas pengguna tidak valid pada token JWT.",
            "data": None
        }), 401

    gedung, err_msg = get_fasil_assigned_building(current_user_id)
    if err_msg:
        return None, jsonify({
            "success": False,
            "message": err_msg,
            "data": None
        }), 403

    return gedung, None, None


# ─── IDOR & Scope Validation Helpers ─────────────────────────────────────────

def validate_student_in_building(student_id: int, gedung_id: int) -> Tuple[Optional[User], Optional[str], Optional[int]]:
    """
    Validates that the student exists and is assigned to a room within the facilitator's building.
    Returns: (student, error_message, status_code)
    """
    student = User.query.filter_by(id=student_id, role='mahasiswa').first()
    if not student:
        return None, f"Mahasiswa dengan ID {student_id} tidak ditemukan.", 404

    if not student.kamar_ref:
        return None, f"Mahasiswa {student.nama} belum ditempatkan pada kamar manapun.", 422

    if student.kamar_ref.gedung_id != gedung_id:
        return None, "Akses ditolak: Mahasiswa ini terdaftar di gedung lain (Pelanggaran batas gedung).", 403

    return student, None, None


def validate_kamar_in_building(kamar_id: int, gedung_id: int) -> Tuple[Optional[Kamar], Optional[str], Optional[int]]:
    """
    Validates that the room exists and belongs to the facilitator's building.
    Returns: (kamar, error_message, status_code)
    """
    kamar = Kamar.query.filter_by(id=kamar_id, gedung_id=gedung_id).first()
    if not kamar:
        return None, f"Kamar dengan ID {kamar_id} tidak ditemukan pada gedung binaan Anda.", 404

    return kamar, None, None


def validate_presensi_in_building(presensi_id: int, gedung_id: int) -> Tuple[Optional[Presensi], Optional[str], Optional[int]]:
    """
    Validates that the attendance record exists and belongs to the facilitator's building.
    Checks `presensi.gedung_id` or student's room building.
    Returns: (presensi, error_message, status_code)
    """
    presensi = Presensi.query.get(presensi_id)
    if not presensi:
        return None, f"Data presensi dengan ID {presensi_id} tidak ditemukan.", 404

    # Direct match on presensi.gedung_id
    if presensi.gedung_id is not None:
        if presensi.gedung_id != gedung_id:
            return None, "Akses ditolak: Data presensi ini bukan milik gedung binaan Anda.", 403
        return presensi, None, None

    # Fallback to student's room building if gedung_id was not populated yet
    if presensi.mahasiswa and presensi.mahasiswa.kamar_ref:
        if presensi.mahasiswa.kamar_ref.gedung_id != gedung_id:
            return None, "Akses ditolak: Data presensi ini milik mahasiswa gedung lain.", 403
        # Backfill gedung_id
        presensi.gedung_id = gedung_id
        return presensi, None, None

    return None, "Akses ditolak: Data presensi tidak memiliki relasi gedung yang valid.", 403


def validate_area_in_building(area_id: int, gedung_id: int) -> Tuple[Optional[AreaAbsensi], Optional[str], Optional[int]]:
    """
    Validates that the attendance polygon exists and belongs to the facilitator's building.
    Returns: (area, error_message, status_code)
    """
    area = AreaAbsensi.query.get(area_id)
    if not area:
        return None, f"Area absensi dengan ID {area_id} tidak ditemukan.", 404

    if area.gedung_id is not None and area.gedung_id != gedung_id:
        return None, "Akses ditolak: Area absensi polygon ini milik gedung lain.", 403

    return area, None, None
