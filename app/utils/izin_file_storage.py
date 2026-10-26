"""
Helper penyimpanan dan validasi file dokumen izin mahasiswa.
Fitur keamanan:
- Whitelist ekstensi (.jpg, .jpeg, .png, .pdf)
- Validasi tipe asli file menggunakan magic bytes (bukan hanya Content-Type dari client)
- Verifikasi kesesuaian antara ekstensi dan tipe file terdeteksi
- Batas ukuran maksimal file (default 5 MB)
- Nama file acak menggunakan UUID v4 hex + ekstensi
- Simpan di folder privat di luar web root / publik
- Pengecekan realpath untuk mencegah directory / path traversal
"""

import os
import uuid
from typing import Tuple, Optional
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from flask import current_app

MAGIC_SIGNATURES = {
    "image/jpeg": [b"\xFF\xD8\xFF"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "application/pdf": [b"%PDF-"],
}

EXTENSION_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
}


def detect_mime_from_magic_bytes(header: bytes) -> Optional[str]:
    """Mendeteksi MIME type sebenarnya dari byte awal file."""
    for mime, signatures in MAGIC_SIGNATURES.items():
        for sig in signatures:
            if header.startswith(sig):
                return mime
    return None


def validate_izin_document(file: Optional[FileStorage], max_size_bytes: int = 5 * 1024 * 1024) -> Tuple[bool, Optional[str], Optional[str], int]:
    """
    Validasi file dokumen pengajuan izin.

    Returns:
        (is_valid: bool, error_message: Optional[str], mime_type: Optional[str], file_size: int)
    """
    if not file or not file.filename:
        return False, "File dokumen wajib diunggah.", None, 0

    original_filename = file.filename
    _, ext = os.path.splitext(original_filename.lower())

    if ext not in EXTENSION_MIME_MAP:
        return False, f"Format file '{ext}' tidak didukung. Harap unggah JPG, PNG, atau PDF.", None, 0

    expected_mime = EXTENSION_MIME_MAP[ext]

    # Cek ukuran file
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    if size == 0:
        return False, "File dokumen tidak boleh kosong.", None, 0

    if size > max_size_bytes:
        max_mb = max_size_bytes // (1024 * 1024)
        return False, f"Ukuran file dokumen melebihi batas maksimal {max_mb} MB.", None, 0

    # Baca header untuk verifikasi magic bytes
    header = file.read(16)
    file.seek(0)

    actual_mime = detect_mime_from_magic_bytes(header)
    if not actual_mime:
        return False, "Konten file tidak valid atau rusak (gagal verifikasi tanda tangan format).", None, 0

    # Pastikan ekstensi cocok dengan tipe biner
    if actual_mime != expected_mime:
        return False, f"Ekstensi file '{ext}' tidak cocok dengan tipe konten sebenarnya.", None, 0

    return True, None, actual_mime, size


def save_izin_document(file: FileStorage) -> Tuple[str, str, str, int]:
    """
    Menyimpan dokumen izin ke direktori aman privat.

    Returns:
        (stored_name, sanitized_original_name, mime_type, size_bytes)
    """
    folder = current_app.config.get("IZIN_UPLOAD_FOLDER")
    os.makedirs(folder, exist_ok=True)

    max_size = current_app.config.get("IZIN_MAX_FILE_BYTES", 5 * 1024 * 1024)
    is_valid, err, mime_type, size = validate_izin_document(file, max_size)
    if not is_valid:
        raise ValueError(err)

    _, ext = os.path.splitext(file.filename.lower())
    stored_name = f"{uuid.uuid4().hex}{ext}"
    sanitized_original = secure_filename(file.filename) or f"dokumen{ext}"

    dest_path = os.path.abspath(os.path.join(folder, stored_name))

    # Pastikan dest_path berada dalam folder upload yang diizinkan (Anti Path Traversal)
    upload_root = os.path.abspath(folder)
    if not dest_path.startswith(upload_root + os.sep) and dest_path != upload_root:
        raise ValueError("Indikasi path traversal terdeteksi.")

    file.save(dest_path)
    return stored_name, sanitized_original, mime_type, size


def get_izin_document_abs_path(stored_name: str) -> Optional[str]:
    """
    Mendapatkan path absolut dokumen izin dan memvalidasi keamanannya.
    """
    if not stored_name or ".." in stored_name or "/" in stored_name or "\\" in stored_name:
        return None

    folder = os.path.abspath(current_app.config.get("IZIN_UPLOAD_FOLDER"))
    candidate = os.path.abspath(os.path.join(folder, stored_name))

    if not candidate.startswith(folder + os.sep):
        return None

    if not os.path.isfile(candidate):
        return None

    return candidate


def delete_izin_document_file(stored_name: str) -> None:
    """Menghapus file fisik dokumen jika transaksi DB dibatalkan."""
    if not stored_name:
        return
    path = get_izin_document_abs_path(stored_name)
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
