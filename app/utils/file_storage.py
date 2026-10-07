"""
Helper untuk menyimpan dan mengelola file upload (foto absensi).
Mengikuti pattern util yang sudah ada (geofence.py, polygon.py).

Struktur folder penyimpanan:
    uploads/absensi/{user_id}/absensi_{user_id}_{YYYYMMDD}_{HHMMSS}_{uuid8}.jpg
"""

import os
import uuid
from datetime import datetime

from flask import current_app

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_image_file(file) -> tuple[bool, str | None]:
    """
    Validasi file foto:
    - Content-Type harus termasuk daftar yang diizinkan
    - Ukuran file tidak boleh melebihi batas

    Returns:
        (is_valid: bool, error_message: str | None)
    """
    if not file or not file.filename:
        return False, "File foto wajib diunggah."

    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type not in ALLOWED_CONTENT_TYPES:
        return False, (
            f"Format foto tidak didukung: '{content_type}'. "
            "Gunakan JPEG, PNG, atau WebP."
        )

    # Baca ukuran file tanpa menyimpan ke memori sepenuhnya
    file.seek(0, 2)  # Seek ke akhir
    size = file.tell()
    file.seek(0)     # Kembalikan ke awal

    if size > MAX_FILE_SIZE_BYTES:
        mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        return False, f"Ukuran foto melebihi batas maksimal {mb} MB."

    if size == 0:
        return False, "File foto tidak boleh kosong."

    return True, None


def save_absensi_photo(file, user_id: int) -> str:
    """
    Simpan foto absensi ke direktori upload.

    Args:
        file: Werkzeug FileStorage object
        user_id: ID user untuk organisasi folder

    Returns:
        Path relatif dari UPLOAD_FOLDER, contoh:
        "absensi/1/absensi_1_20261005_213000_a1b2c3d4.jpg"

    Raises:
        OSError: Jika direktori tidak dapat dibuat atau file tidak dapat ditulis.
    """
    upload_root = current_app.config["UPLOAD_FOLDER"]
    user_folder = os.path.join(upload_root, "absensi", str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    now = datetime.utcnow()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"absensi_{user_id}_{date_str}_{time_str}_{unique_id}.jpg"

    abs_path = os.path.join(user_folder, filename)
    file.save(abs_path)

    # Return path relatif terhadap UPLOAD_FOLDER
    return os.path.join("absensi", str(user_id), filename).replace("\\", "/")


def delete_file(relative_path: str) -> None:
    """
    Hapus file dari storage. Dipanggil jika terjadi error setelah file disimpan.
    Tidak melempar exception jika file tidak ditemukan.

    Args:
        relative_path: Path relatif dari UPLOAD_FOLDER
    """
    if not relative_path:
        return
    try:
        upload_root = current_app.config["UPLOAD_FOLDER"]
        abs_path = os.path.join(upload_root, relative_path)
        if os.path.isfile(abs_path):
            os.remove(abs_path)
    except Exception:
        pass  # Jangan gagalkan proses utama karena error cleanup
