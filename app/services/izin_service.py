"""
Business Logic Service untuk Fitur Perizinan Asrama Unand.
Mengatur aturan bisnis:
- Tanggal selesai >= tanggal mulai, validasi durasi & batas mundur/maju
- Tolak izin yang tumpang tindih dengan izin aktif (pending/approved)
- Upload file aman dengan sanitasi, magic bytes, dan folder privat
- Transisi status atomic (anti race condition / double review / double cancel)
- Menyediakan get_izin_status(mahasiswa_id, tanggal, sesi_id) untuk modul rekap absensi
"""

from datetime import datetime, date
from typing import Tuple, Optional, Dict, Any, List
from werkzeug.datastructures import FileStorage
from app.core.extensions import db
from app.models.izin import (
    Izin, STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_CANCELLED,
    JENIS_FULL, JENIS_HALF
)
from app.models.izin_dokumen import IzinDokumen
from app.models.sesi_presensi import SesiPresensi
from app.models.user import User
from app.repositories.izin_repository import (
    IzinRepository, FasilitatorGedungRepository, SesiPresensiRepository
)
from app.services.izin_access_service import IzinAccessService
from app.utils.izin_file_storage import save_izin_document, delete_izin_document_file


class IzinService:

    @staticmethod
    def ajukan_izin(mahasiswa: User, parsed_data: Dict[str, Any], file_obj: Optional[FileStorage]) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Mengajukan perizinan baru oleh mahasiswa.
        Memvalidasi kamar, overlap izin, menyimpan dokumen, dan mencatat transaksi DB secara atomic.
        """
        if not mahasiswa.kamar_ref:
            return None, "Anda belum ditempatkan pada kamar asrama manapun. Hubungi fasilitator gedung.", 422

        jenis = parsed_data["jenis"]
        tgl_mulai = parsed_data["tanggal_mulai"]
        tgl_selesai = parsed_data["tanggal_selesai"]
        sesi_id = parsed_data.get("sesi_id")
        keterangan = parsed_data["keterangan"]

        # Validasi sesi presensi jika jenis half
        if jenis == JENIS_HALF:
            sesi = SesiPresensiRepository.get_by_id(sesi_id)
            if not sesi or not sesi.is_active:
                return None, "Sesi presensi yang dipilih tidak valid atau tidak aktif.", 422

        saved_stored_name = None

        try:
            # 1. Kunci baris user mahasiswa untuk mencegah submit bersamaan (concurrency lock)
            IzinRepository.lock_user_for_update(mahasiswa.id)

            # 2. Cek izin yang tumpang tindih (overlap) dengan izin aktif (pending / approved)
            overlapping = IzinRepository.find_overlapping_izin(
                mahasiswa_id=mahasiswa.id,
                tgl_mulai=tgl_mulai,
                tgl_selesai=tgl_selesai,
                jenis=jenis,
                sesi_id=sesi_id
            )

            if overlapping:
                first_ov = overlapping[0]
                return None, (
                    f"Pengajuan ditolak karena tumpang tindih dengan izin aktif Anda "
                    f"({first_ov.tanggal_mulai} s.d. {first_ov.tanggal_selesai}, status: {first_ov.status})."
                ), 409

            # 3. Simpan file dokumen jika ada
            doc_metadata = None
            if file_obj:
                try:
                    stored_name, orig_name, mime, size = save_izin_document(file_obj)
                    saved_stored_name = stored_name
                    doc_metadata = {
                        "stored_name": stored_name,
                        "original_name": orig_name,
                        "mime_type": mime,
                        "size_bytes": size,
                    }
                except ValueError as ve:
                    return None, str(ve), 422
                except Exception:
                    return None, "Terjadi kesalahan saat memproses file dokumen.", 500

            # 4. Buat objek Izin
            izin = Izin(
                user_id=mahasiswa.id,
                tanggal_mulai=tgl_mulai,
                tanggal_selesai=tgl_selesai,
                alasan=keterangan,
                status=STATUS_PENDING,
                jenis=jenis,
                sesi_id=sesi_id
            )
            db.session.add(izin)
            db.session.flush()

            # 5. Buat objek IzinDokumen jika ada dokumen
            if doc_metadata:
                dok = IzinDokumen(
                    izin_id=izin.id,
                    stored_name=doc_metadata["stored_name"],
                    original_name=doc_metadata["original_name"],
                    mime_type=doc_metadata["mime_type"],
                    size_bytes=doc_metadata["size_bytes"]
                )
                db.session.add(dok)

            db.session.commit()
            return izin.to_dict(), None, 201

        except Exception as e:
            db.session.rollback()
            if saved_stored_name:
                delete_izin_document_file(saved_stored_name)
            return None, f"Gagal menyimpan pengajuan izin: {str(e)}", 500

    @staticmethod
    def batalkan_izin(izin_id: int, user: User) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Membatalkan pengajuan izin berstatus pending milik mahasiswa sendiri secara atomic.
        """
        izin, err, status_code = IzinAccessService.authorize_for_cancellation(izin_id, user)
        if err:
            return None, err, status_code

        now = datetime.utcnow()
        success = IzinRepository.atomic_cancel(izin_id=izin_id, mahasiswa_id=user.id, cancelled_at=now)
        if not success:
            return None, "Gagal membatalkan izin: status izin telah berubah atau sudah diproses.", 409

        izin = IzinRepository.get_by_id(izin_id)
        return izin.to_dict(), None, 200

    @staticmethod
    def review_izin(izin_id: int, user: User, parsed_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Mereview (approve atau reject) pengajuan izin pending oleh fasilitator gedung terkait.
        Dilakukan secara atomic untuk menghindari double-review / race condition.
        """
        izin, err, status_code = IzinAccessService.authorize_for_review(izin_id, user)
        if err:
            return None, err, status_code

        target_status = parsed_data["status"]
        catatan = parsed_data.get("catatan")
        now = datetime.utcnow()

        success = IzinRepository.atomic_review(
            izin_id=izin_id,
            target_status=target_status,
            reviewer_id=user.id,
            catatan=catatan,
            reviewed_at=now
        )

        if not success:
            return None, "Gagal memperbarui izin: izin ini telah diproses atau dibatalkan sebelumnya.", 409

        izin = IzinRepository.get_by_id(izin_id)
        return izin.to_dict(), None, 200

    @staticmethod
    def get_daftar_izin_saya(mahasiswa_id: int, status: Optional[str] = None, page: int = 1, per_page: int = 15) -> Dict[str, Any]:
        """Mengambil riwayat pengajuan izin milik mahasiswa login."""
        p = IzinRepository.get_mahasiswa_izin_list(mahasiswa_id=mahasiswa_id, status=status, page=page, per_page=per_page)
        return {
            "items": [item.to_dict() for item in p.items],
            "total": p.total,
            "page": p.page,
            "pages": p.pages,
            "per_page": p.per_page,
            "has_next": p.has_next,
            "has_prev": p.has_prev
        }

    @staticmethod
    def get_daftar_izin_review(user: User, status: Optional[str] = None, page: int = 1, per_page: int = 15) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Mengambil daftar pengajuan izin untuk direview:
        - Fasilitator: HANYA mahasiswa di gedung binaannya
        - Admin: Read-only untuk seluruh gedung
        """
        if user.role == "admin":
            gedung_ids = None  # Semua gedung
        elif user.role in ("fasil", "fasilitator"):
            gedung_ids = FasilitatorGedungRepository.get_gedung_ids_by_fasilitator(user.id)
            if not gedung_ids:
                return {
                    "items": [],
                    "total": 0,
                    "page": 1,
                    "pages": 0,
                    "per_page": per_page,
                    "has_next": False,
                    "has_prev": False
                }, None, 200
        else:
            return None, "Akses ditolak.", 403

        p = IzinRepository.get_review_list_by_gedung_ids(gedung_ids=gedung_ids, status=status, page=page, per_page=per_page)
        return {
            "items": [item.to_dict() for item in p.items],
            "total": p.total,
            "page": p.page,
            "pages": p.pages,
            "per_page": p.per_page,
            "has_next": p.has_next,
            "has_prev": p.has_prev
        }, None, 200

    @staticmethod
    def get_detail_izin(izin_id: int, user: User) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """Mengambil detail satu izin dengan pengecekan otorisasi."""
        izin, err, status_code = IzinAccessService.authorize_and_get_izin(izin_id, user)
        if err:
            return None, err, status_code
        return izin.to_dict(), None, 200

    @staticmethod
    def get_izin_status(mahasiswa_id: int, tanggal: date, sesi_id: Optional[int] = None) -> Optional[str]:
        """
        Fungsi publik untuk modul rekap absensi:
        Mengecek apakah mahasiswa memiliki izin berstatus 'approved' yang berlaku
        pada tanggal dan sesi tersebut.
        Mengembalikan 'izin' jika aktif, atau None jika tidak ada.
        """
        # Cari izin berstatus approved yang rentang tanggalnya mencakup tanggal tersebut
        q = Izin.query.filter(
            Izin.user_id == mahasiswa_id,
            Izin.status == STATUS_APPROVED,
            Izin.tanggal_mulai <= tanggal,
            Izin.tanggal_selesai >= tanggal
        )

        izin_list = q.all()
        for iz in izin_list:
            if iz.jenis == JENIS_FULL:
                return "izin"
            if iz.jenis == JENIS_HALF:
                # Jika sesi_id ditentukan, harus cocok; jika sesi_id None, dianggap ada izin pada sebagian hari itu
                if sesi_id is None or iz.sesi_id == sesi_id:
                    return "izin"

        return None

    @staticmethod
    def get_izin_status_by_kode(mahasiswa_id: int, tanggal: date, kode_sesi: str) -> Optional[str]:
        """
        Helper tambahan untuk rekap yang memeriksa berdasarkan kode sesi presensi (misal 'subuh', 'malam').
        """
        sesi = SesiPresensiRepository.get_by_kode(kode_sesi)
        sesi_id = sesi.id if sesi else None
        return IzinService.get_izin_status(mahasiswa_id, tanggal, sesi_id)
