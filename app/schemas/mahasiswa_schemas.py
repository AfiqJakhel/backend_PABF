"""
Schemas validasi input untuk Mahasiswa.
Mengikuti pola validasi manual dari fasil_schemas.py.
"""

from app.utils.file_storage import ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE_BYTES


def validate_submit_absensi(form_data, files) -> tuple[list, dict]:
    """
    Validasi payload multipart/form-data untuk submit absensi.

    Fields:
        foto       : file (wajib) — JPEG/PNG/WebP, maks 10 MB
        latitude   : float, -90..90 (wajib)
        longitude  : float, -180..180 (wajib)
        accuracy   : float, >= 0 (opsional)
        keterangan : str (opsional)

    Returns:
        (errors: list[str], parsed: dict)
    """
    errors = []
    parsed = {}

    # ── Foto ────────────────────────────────────────────────────────────────
    foto = files.get("foto")
    if not foto or not foto.filename:
        errors.append("File foto wajib diunggah.")
    else:
        content_type = (foto.content_type or "").lower().split(";")[0].strip()
        if content_type not in ALLOWED_CONTENT_TYPES:
            errors.append(
                f"Format foto tidak didukung: '{content_type}'. "
                "Gunakan JPEG, PNG, atau WebP."
            )
        else:
            foto.seek(0, 2)
            size = foto.tell()
            foto.seek(0)
            if size == 0:
                errors.append("File foto tidak boleh kosong.")
            elif size > MAX_FILE_SIZE_BYTES:
                mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
                errors.append(f"Ukuran foto melebihi batas {mb} MB.")
            else:
                parsed["foto"] = foto

    # ── Latitude ─────────────────────────────────────────────────────────────
    lat_raw = form_data.get("latitude", "")
    try:
        latitude = float(lat_raw)
        if not (-90 <= latitude <= 90):
            errors.append("'latitude' harus antara -90 dan 90.")
        else:
            parsed["latitude"] = latitude
    except (ValueError, TypeError):
        errors.append("'latitude' wajib diisi dan harus berupa angka desimal.")

    # ── Longitude ────────────────────────────────────────────────────────────
    lon_raw = form_data.get("longitude", "")
    try:
        longitude = float(lon_raw)
        if not (-180 <= longitude <= 180):
            errors.append("'longitude' harus antara -180 dan 180.")
        else:
            parsed["longitude"] = longitude
    except (ValueError, TypeError):
        errors.append("'longitude' wajib diisi dan harus berupa angka desimal.")

    # ── Accuracy (opsional) ──────────────────────────────────────────────────
    acc_raw = form_data.get("accuracy")
    if acc_raw is not None and acc_raw != "":
        try:
            accuracy = float(acc_raw)
            if accuracy < 0:
                errors.append("'accuracy' tidak boleh bernilai negatif.")
            else:
                parsed["accuracy"] = accuracy
        except (ValueError, TypeError):
            errors.append("'accuracy' harus berupa angka.")
    else:
        parsed["accuracy"] = None

    # ── Keterangan (opsional) ────────────────────────────────────────────────
    keterangan_raw = form_data.get("keterangan")
    if keterangan_raw:
        parsed["keterangan"] = str(keterangan_raw).strip()[:500]
    else:
        parsed["keterangan"] = None

    # ── Sesi (opsional, 'subuh' | 'malam') ───────────────────────────────────
    sesi_raw = form_data.get("sesi")
    if sesi_raw:
        sesi_clean = str(sesi_raw).strip().lower()
        if sesi_clean not in {"subuh", "malam", "kegiatan"}:
            errors.append("'sesi' harus salah satu dari: subuh, malam.")
        else:
            parsed["sesi"] = sesi_clean
    else:
        parsed["sesi"] = None

    return errors, parsed
