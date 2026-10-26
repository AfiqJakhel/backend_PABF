"""
Skema validasi input untuk fitur perizinan mahasiswa dan review oleh fasilitator.
"""

from datetime import date, timedelta
from typing import Tuple, Dict, Any, List, Optional
from flask import current_app
from app.models.izin import JENIS_FULL, JENIS_HALF, JENIS_VALID


def validate_pengajuan_izin(form_data: Dict[str, Any], has_document: bool) -> Tuple[Optional[List[str]], Optional[Dict[str, Any]]]:
    """
    Validasi form pengajuan izin mahasiswa.

    Args:
        form_data: request.form dict
        has_document: boolean apakah ada file dokumen yang diunggah

    Returns:
        (errors: List[str] | None, parsed_data: Dict[str, Any] | None)
    """
    errors: List[str] = []
    parsed: Dict[str, Any] = {}

    # 1. Jenis Izin
    jenis = str(form_data.get("jenis", JENIS_FULL)).strip().lower()
    if jenis not in JENIS_VALID:
        errors.append(f"Jenis izin tidak valid. Pilih antara '{JENIS_FULL}' atau '{JENIS_HALF}'.")
    parsed["jenis"] = jenis

    # 2. Tanggal Mulai
    raw_tgl_mulai = str(form_data.get("tanggal_mulai", "")).strip()
    tgl_mulai: Optional[date] = None
    if not raw_tgl_mulai:
        errors.append("Tanggal mulai izin wajib diisi.")
    else:
        try:
            tgl_mulai = date.fromisoformat(raw_tgl_mulai)
        except ValueError:
            errors.append("Format tanggal mulai tidak valid (gunakan format YYYY-MM-DD).")

    # 3. Tanggal Selesai
    raw_tgl_selesai = str(form_data.get("tanggal_selesai", "")).strip()
    tgl_selesai: Optional[date] = None

    if jenis == JENIS_HALF:
        # Untuk izin setengah hari, tanggal selesai otomatis sama dengan tanggal mulai
        tgl_selesai = tgl_mulai
    else:
        if not raw_tgl_selesai:
            errors.append("Tanggal selesai izin wajib diisi untuk izin penuh (full).")
        else:
            try:
                tgl_selesai = date.fromisoformat(raw_tgl_selesai)
            except ValueError:
                errors.append("Format tanggal selesai tidak valid (gunakan format YYYY-MM-DD).")

    # Validasi logika tanggal jika parsing sukses
    if tgl_mulai and tgl_selesai:
        if tgl_selesai < tgl_mulai:
            errors.append("Tanggal selesai tidak boleh lebih awal dari tanggal mulai.")

        today = date.today()
        maks_mundur = current_app.config.get("IZIN_MAKS_MUNDUR_HARI", 3)
        maks_maju = current_app.config.get("IZIN_MAKS_MAJU_HARI", 60)
        maks_durasi = current_app.config.get("IZIN_MAX_DURASI_HARI", 14)

        if tgl_mulai < (today - timedelta(days=maks_mundur)):
            errors.append(f"Tanggal mulai tidak boleh mundur lebih dari {maks_mundur} hari yang lalu.")

        if tgl_mulai > (today + timedelta(days=maks_maju)):
            errors.append(f"Pengajuan izin tidak boleh lebih dari {maks_maju} hari ke depan.")

        durasi_hari = (tgl_selesai - tgl_mulai).days + 1
        if durasi_hari > maks_durasi:
            errors.append(f"Durasi izin maksimal adalah {maks_durasi} hari (diajukan: {durasi_hari} hari).")

        parsed["tanggal_mulai"] = tgl_mulai
        parsed["tanggal_selesai"] = tgl_selesai

    # 4. Sesi ID (wajib jika jenis half)
    raw_sesi_id = form_data.get("sesi_id")
    if jenis == JENIS_HALF:
        if not raw_sesi_id:
            errors.append("Sesi presensi wajib dipilih untuk izin setengah hari.")
        else:
            try:
                parsed["sesi_id"] = int(raw_sesi_id)
            except (ValueError, TypeError):
                errors.append("ID sesi presensi tidak valid.")
    else:
        parsed["sesi_id"] = None

    # 5. Keterangan / Alasan
    keterangan = str(form_data.get("keterangan") or form_data.get("alasan") or "").strip()
    if not keterangan:
        errors.append("Keterangan/alasan izin wajib diisi.")
    elif len(keterangan) < 5:
        errors.append("Keterangan/alasan izin minimal 5 karakter.")
    elif len(keterangan) > 1000:
        errors.append("Keterangan/alasan izin maksimal 1000 karakter.")
    else:
        parsed["keterangan"] = keterangan

    # 6. Aturan Dokumen
    # a. full: dokumen WAJIB
    # b. half: dokumen OPSIONAL
    if jenis == JENIS_FULL and not has_document:
        errors.append("Dokumen bukti wajib diunggah untuk izin penuh (full day).")

    if errors:
        return errors, None

    return None, parsed


def validate_review_izin(data: Dict[str, Any]) -> Tuple[Optional[List[str]], Optional[Dict[str, Any]]]:
    """
    Validasi data review / approval izin oleh fasilitator.

    Expected JSON body:
      - aksi / status: 'approve' / 'disetujui' OR 'reject' / 'ditolak'
      - catatan / catatan_fasil: string (wajib jika reject)
    """
    if not data or not isinstance(data, dict):
        return ["Data JSON tidak valid atau kosong."], None

    errors: List[str] = []
    parsed: Dict[str, Any] = {}

    raw_action = str(data.get("aksi") or data.get("status") or "").strip().lower()

    if raw_action in ("approve", "disetujui", "approved"):
        target_status = "approved"
    elif raw_action in ("reject", "ditolak", "rejected"):
        target_status = "rejected"
    else:
        errors.append("Aksi tidak valid. Pilih 'approve' atau 'reject'.")
        target_status = ""

    parsed["status"] = target_status

    catatan = str(data.get("catatan") or data.get("catatan_fasil") or "").strip()
    if target_status == "rejected":
        if not catatan:
            errors.append("Catatan reviewer wajib diisi saat menolak izin.")
        elif len(catatan) < 3:
            errors.append("Catatan penolakan minimal 3 karakter.")
        elif len(catatan) > 1000:
            errors.append("Catatan penolakan maksimal 1000 karakter.")

    parsed["catatan"] = catatan if catatan else None

    if errors:
        return errors, None

    return None, parsed
