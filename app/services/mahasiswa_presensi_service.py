"""
Service Layer untuk absensi self-service mahasiswa.
Business logic:
  1. Catat akurasi GPS
  2. Cek sesi absensi aktif
  3. Cek duplikat absensi
  4. Point-in-Polygon validation via MySQL ST_Contains:
     - Jika berada di dalam area: dicatat dengan area_absensi_id dan location_valid = True
     - Jika berada di luar area (jarak jauh): tetap dicatat dan disimpan berhasil (area_absensi_id = None, location_valid = False, keterangan = 'Di luar area absensi')
  5. Simpan foto
  6. Simpan record presensi
"""

from datetime import date, datetime

from config import Config
from app.repositories.area_absensi_repository import AreaAbsensiRepository
from app.repositories.mahasiswa_presensi_repository import MahasiswaPresensiRepository
from app.repositories.sesi_absensi_repository import SesiAbsensiRepository
from app.utils.file_storage import save_absensi_photo, delete_file


class MahasiswaPresensiService:
    """Business logic untuk submit absensi mahasiswa (selfie + GPS)."""

    @staticmethod
    def submit_absensi(user_id: int, nim: str, parsed: dict) -> tuple:
        """
        Proses submit absensi mahasiswa.

        Args:
            user_id : ID user dari JWT
            nim     : NIM mahasiswa
            parsed  : dict dari validate_submit_absensi(), berisi:
                      foto, latitude, longitude, accuracy, keterangan

        Returns:
            (result_dict, error_dict)  — error_dict adalah None jika sukses.
        """
        latitude = parsed["latitude"]
        longitude = parsed["longitude"]
        accuracy = parsed.get("accuracy")
        user_keterangan = parsed.get("keterangan")

        # ── 1. Cek sesi absensi aktif & waktu server ─────────────────────────
        from app.services.sesi_manager import resolve_sesi_info
        now = datetime.now()
        tanggal_hari_ini = date.today()

        requested_sesi = parsed.get("sesi")
        if requested_sesi:
            sesi_info = resolve_sesi_info(requested_sesi, target_date=tanggal_hari_ini, current_time=now)
            if not sesi_info["is_aktif"]:
                return None, {
                    "message": (
                        f"Sesi {sesi_info['nama_sesi']} sedang tidak aktif. "
                        f"{sesi_info['pesan_status']} (Batas waktu: {sesi_info['jam_mulai']} - {sesi_info['jam_selesai']} WIB)"
                    ),
                    "code": "SESSION_NOT_ACTIVE",
                    "location_valid": False,
                }
            tipe_sesi = requested_sesi
        else:
            # Fallback jika client tidak mengirim field sesi: cari sesi yang aktif saat ini
            subuh_info = resolve_sesi_info("subuh", target_date=tanggal_hari_ini, current_time=now)
            malam_info = resolve_sesi_info("malam", target_date=tanggal_hari_ini, current_time=now)
            if subuh_info["is_aktif"]:
                sesi_info = subuh_info
                tipe_sesi = "subuh"
            elif malam_info["is_aktif"]:
                sesi_info = malam_info
                tipe_sesi = "malam"
            else:
                return None, {
                    "message": (
                        f"Tidak ada sesi absensi yang aktif saat ini. "
                        f"Jadwal Subuh: {subuh_info['jam_mulai']} - {subuh_info['jam_selesai']} WIB | "
                        f"Jadwal Malam: {malam_info['jam_mulai']} - {malam_info['jam_selesai']} WIB."
                    ),
                    "code": "NO_ACTIVE_SESSION",
                    "location_valid": False,
                }

        # ── 2. Cek duplikat absensi ──────────────────────────────────────────
        existing = MahasiswaPresensiRepository.get_by_user_tanggal_sesi(
            user_id, tanggal_hari_ini, tipe_sesi
        )
        if existing:
            return None, {
                "message": (
                    f"Anda sudah melakukan absensi untuk sesi '{tipe_sesi.capitalize()}' "
                    f"pada tanggal {tanggal_hari_ini.isoformat()}."
                ),
                "code": "DUPLICATE_ATTENDANCE",
                "location_valid": True,
            }

        # ── 3. Resolusi Gedung Mahasiswa & Point-in-Polygon validation ───────
        from app.models.user import User
        student = User.query.get(user_id)
        student_gedung_id = None
        if student and student.kamar_ref:
            student_gedung_id = student.kamar_ref.gedung_id

        # Validasi GPS khusus terhadap polygon gedung binaan mahasiswa
        area = AreaAbsensiRepository.find_area_containing_point(
            latitude, longitude, gedung_id=student_gedung_id
        )
        area_id = area.id if area else None
        area_nama = area.nama if area else "Di Luar Area Gedung"
        location_valid = True if area else False

        keterangan_items = []
        if user_keterangan:
            keterangan_items.append(user_keterangan)

        if not area:
            keterangan_items.append("Di luar area absensi gedung")

        max_accuracy = Config.MAX_GPS_ACCURACY_METERS
        if accuracy is not None and accuracy > max_accuracy:
            keterangan_items.append(f"Akurasi GPS +/- {accuracy:.0f}m")

        final_keterangan = " | ".join(keterangan_items) if keterangan_items else None

        # ── 4. Simpan foto ──────────────────────────────────────────────────
        foto_path = None
        try:
            foto_path = save_absensi_photo(parsed["foto"], user_id)
        except Exception:
            return None, {
                "message": "Gagal menyimpan foto absensi. Coba lagi.",
                "code": "PHOTO_SAVE_ERROR",
                "location_valid": location_valid,
            }

        # ── 5. Tentukan status absensi ───────────────────────────────────────
        now = datetime.now()
        status = "hadir"
        # Jika sesi sudah lewat 15 menit dari waktu mulai, tandai terlambat
        waktu_mulai_dt = sesi_info.get("waktu_mulai_dt")
        if waktu_mulai_dt and (now - waktu_mulai_dt).total_seconds() > 15 * 60:
            status = "terlambat"

        # ── 6. Simpan record presensi ────────────────────────────────────────
        try:
            presensi = MahasiswaPresensiRepository.create_from_selfie({
                "user_id": user_id,
                "nim": nim,
                "tanggal": tanggal_hari_ini,
                "waktu": now,
                "sesi": tipe_sesi,
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": accuracy,
                "status": status,
                "foto_wajah": foto_path,
                "area_absensi_id": area_id,
                "keterangan": final_keterangan,
                "gedung_id": student_gedung_id,
            })
        except Exception:
            # Rollback: hapus foto yang sudah tersimpan
            delete_file(foto_path)
            return None, {
                "message": "Gagal menyimpan data absensi. Coba lagi.",
                "code": "DB_ERROR",
                "location_valid": location_valid,
            }

        return {
            "id": presensi.id,
            "sesi": tipe_sesi,
            "status": status,
            "area_nama": area_nama,
            "location_valid": location_valid,
            "keterangan": final_keterangan,
            "waktu": presensi.waktu.isoformat(),
            "foto_wajah": foto_path,
        }, None
