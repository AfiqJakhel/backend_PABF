"""
Schemas validasi input untuk fitur Fasilitator.
Menggunakan teknik validasi manual berbasis Python (tanpa dependensi pihak ketiga tambahan)
agar konsisten dengan arsitektur project yang sudah ada.
"""

from datetime import datetime


# ─── Konstanta yang Diizinkan ────────────────────────────────────────────────

TIPE_SESI_VALID = {"subuh", "malam", "kegiatan"}
STATUS_SESI_VALID = {"aktif", "ditutup"}
STATUS_PRESENSI_VALID = {"hadir", "terlambat", "alfa", "izin", "sakit"}
STATUS_IZIN_VALID = {"disetujui", "ditolak"}


# ─── Helper ──────────────────────────────────────────────────────────────────

def _parse_datetime(value: str, field_name: str) -> tuple:
    """
    Parse string ISO-8601 menjadi objek datetime.
    Kembalikan (datetime_obj, None) jika berhasil, atau (None, pesan_error) jika gagal.
    """
    try:
        return datetime.fromisoformat(value), None
    except (ValueError, TypeError):
        return None, f"Format '{field_name}' tidak valid. Gunakan format ISO-8601 (contoh: '2024-08-17T22:00:00')."


# ─── Schema Sesi Absensi ─────────────────────────────────────────────────────

def validate_buat_sesi(data: dict) -> tuple:
    """
    Validasi payload untuk membuat sesi absensi baru.
    Return: (errors: list, parsed_data: dict)
    """
    errors = []
    parsed = {}

    # nama_sesi
    nama_sesi = data.get("nama_sesi", "").strip()
    if not nama_sesi:
        errors.append("'nama_sesi' wajib diisi.")
    elif len(nama_sesi) > 100:
        errors.append("'nama_sesi' maksimal 100 karakter.")
    else:
        parsed["nama_sesi"] = nama_sesi

    # tipe_sesi
    tipe_sesi = data.get("tipe_sesi", "malam").strip().lower()
    if tipe_sesi not in TIPE_SESI_VALID:
        errors.append(f"'tipe_sesi' harus salah satu dari: {', '.join(sorted(TIPE_SESI_VALID))}.")
    else:
        parsed["tipe_sesi"] = tipe_sesi

    # waktu_mulai
    waktu_mulai_str = data.get("waktu_mulai", "")
    if not waktu_mulai_str:
        errors.append("'waktu_mulai' wajib diisi.")
    else:
        dt, err = _parse_datetime(waktu_mulai_str, "waktu_mulai")
        if err:
            errors.append(err)
        else:
            parsed["waktu_mulai"] = dt

    # waktu_selesai
    waktu_selesai_str = data.get("waktu_selesai", "")
    if not waktu_selesai_str:
        errors.append("'waktu_selesai' wajib diisi.")
    else:
        dt, err = _parse_datetime(waktu_selesai_str, "waktu_selesai")
        if err:
            errors.append(err)
        else:
            parsed["waktu_selesai"] = dt

    # Validasi urutan waktu (hanya jika keduanya valid)
    if "waktu_mulai" in parsed and "waktu_selesai" in parsed:
        if parsed["waktu_selesai"] <= parsed["waktu_mulai"]:
            errors.append("'waktu_selesai' harus lebih besar dari 'waktu_mulai'.")

    # keterangan (opsional)
    parsed["keterangan"] = data.get("keterangan", None)

    return errors, parsed


def validate_update_sesi(data: dict) -> tuple:
    """
    Validasi payload untuk memperbarui atau menutup sesi absensi.
    Semua field bersifat opsional, minimal satu harus ada.
    Return: (errors: list, parsed_data: dict)
    """
    errors = []
    parsed = {}

    # status
    if "status" in data:
        status = data["status"].strip().lower()
        if status not in STATUS_SESI_VALID:
            errors.append(f"'status' harus salah satu dari: {', '.join(sorted(STATUS_SESI_VALID))}.")
        else:
            parsed["status"] = status

    # nama_sesi
    if "nama_sesi" in data:
        nama_sesi = data["nama_sesi"].strip()
        if not nama_sesi:
            errors.append("'nama_sesi' tidak boleh kosong jika disertakan.")
        elif len(nama_sesi) > 100:
            errors.append("'nama_sesi' maksimal 100 karakter.")
        else:
            parsed["nama_sesi"] = nama_sesi

    # waktu_selesai (untuk perpanjangan atau pengurungan waktu)
    if "waktu_selesai" in data:
        dt, err = _parse_datetime(data["waktu_selesai"], "waktu_selesai")
        if err:
            errors.append(err)
        else:
            parsed["waktu_selesai"] = dt

    # keterangan
    if "keterangan" in data:
        parsed["keterangan"] = data["keterangan"]

    if not parsed and not errors:
        errors.append("Tidak ada field yang dapat diperbarui. Sertakan setidaknya satu field.")

    return errors, parsed


# ─── Schema Presensi Manual ───────────────────────────────────────────────────

def validate_update_presensi_manual(data: dict) -> tuple:
    """
    Validasi payload untuk mengubah status presensi mahasiswa secara manual.
    Return: (errors: list, parsed_data: dict)
    """
    errors = []
    parsed = {}

    # status
    status = data.get("status", "").strip().lower()
    if not status:
        errors.append("'status' wajib diisi.")
    elif status not in STATUS_PRESENSI_VALID:
        errors.append(f"'status' harus salah satu dari: {', '.join(sorted(STATUS_PRESENSI_VALID))}.")
    else:
        parsed["status"] = status

    # keterangan (opsional, tapi wajib jika status 'izin' atau 'sakit')
    keterangan = data.get("keterangan", "").strip()
    if status in ("izin", "sakit") and not keterangan:
        errors.append("'keterangan' wajib diisi ketika status adalah 'izin' atau 'sakit'.")
    else:
        parsed["keterangan"] = keterangan or None

    return errors, parsed


# ─── Schema Approval Izin ─────────────────────────────────────────────────────

def validate_approval_izin(data: dict) -> tuple:
    """
    Validasi payload untuk menyetujui atau menolak pengajuan izin mahasiswa.
    Return: (errors: list, parsed_data: dict)
    """
    errors = []
    parsed = {}

    # status
    status = data.get("status", "").strip().lower()
    if not status:
        errors.append("'status' wajib diisi.")
    elif status not in STATUS_IZIN_VALID:
        errors.append(f"'status' harus salah satu dari: {', '.join(sorted(STATUS_IZIN_VALID))}.")
    else:
        parsed["status"] = status

    # catatan_fasil (opsional, tapi wajib jika ditolak)
    catatan = data.get("catatan_fasil", "").strip()
    if status == "ditolak" and not catatan:
        errors.append("'catatan_fasil' wajib diisi ketika izin ditolak.")
    else:
        parsed["catatan_fasil"] = catatan or None

    return errors, parsed
