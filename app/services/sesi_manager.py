"""
Manager terpusat untuk penentuan dan jadwal sesi absensi asrama.
Source of truth jadwal operasional harian:
  - Subuh : 04:30 - 06:00 WIB
  - Malam : 19:00 - 21:00 WIB
"""

from datetime import date, datetime, time
from app.models.sesi_absensi import SesiAbsensi

DEFAULT_SESI_SCHEDULE = {
    "subuh": {
        "tipe_sesi": "subuh",
        "nama_sesi": "Subuh",
        "jam_mulai_time": time(4, 30, 0),
        "jam_selesai_time": time(6, 0, 0),
        "jam_mulai_str": "04:30",
        "jam_selesai_str": "06:00",
    },
    "malam": {
        "tipe_sesi": "malam",
        "nama_sesi": "Malam",
        "jam_mulai_time": time(19, 0, 0),
        "jam_selesai_time": time(21, 0, 0),
        "jam_mulai_str": "19:00",
        "jam_selesai_str": "21:00",
    },
}


def resolve_sesi_info(tipe_sesi: str, target_date: date = None, current_time: datetime = None) -> dict:
    """
    Menentukan detail rentang waktu sesi untuk tanggal target.
    Mengutamakan data tabel SesiAbsensi di database jika telah dibuat oleh fasilitator.
    Jika tidak ada record kustom di database, menggunakan DEFAULT_SESI_SCHEDULE.
    """
    if target_date is None:
        target_date = date.today()
    if current_time is None:
        current_time = datetime.now()

    sesi_cfg = DEFAULT_SESI_SCHEDULE.get(tipe_sesi, {
        "tipe_sesi": tipe_sesi,
        "nama_sesi": tipe_sesi.capitalize(),
        "jam_mulai_time": time(8, 0, 0),
        "jam_selesai_time": time(17, 0, 0),
        "jam_mulai_str": "08:00",
        "jam_selesai_str": "17:00",
    })

    sesi_record = SesiAbsensi.query.filter(
        SesiAbsensi.tipe_sesi == tipe_sesi,
        SesiAbsensi.tanggal == target_date
    ).order_by(SesiAbsensi.created_at.desc()).first()

    is_forced_closed = False
    if sesi_record:
        waktu_mulai = sesi_record.waktu_mulai
        waktu_selesai = sesi_record.waktu_selesai
        is_forced_closed = (sesi_record.status == 'ditutup')
        jam_mulai_str = waktu_mulai.strftime("%H:%M") if waktu_mulai else sesi_cfg["jam_mulai_str"]
        jam_selesai_str = waktu_selesai.strftime("%H:%M") if waktu_selesai else sesi_cfg["jam_selesai_str"]
        nama_sesi = sesi_record.nama_sesi or sesi_cfg["nama_sesi"]
    else:
        waktu_mulai = datetime.combine(target_date, sesi_cfg["jam_mulai_time"])
        waktu_selesai = datetime.combine(target_date, sesi_cfg["jam_selesai_time"])
        jam_mulai_str = sesi_cfg["jam_mulai_str"]
        jam_selesai_str = sesi_cfg["jam_selesai_str"]
        nama_sesi = sesi_cfg["nama_sesi"]

    # Evaluasi status aktif berdasarkan waktu server
    today = date.today()
    if target_date < today:
        is_aktif = False
        is_ended = True
        pesan_status = "Sesi telah berakhir pada tanggal sebelumnya."
    elif target_date > today:
        is_aktif = False
        is_ended = False
        pesan_status = "Sesi belum dimulai (hari mendatang)."
    else:
        if is_forced_closed:
            is_aktif = False
            is_ended = True
            pesan_status = "Sesi telah ditutup oleh fasilitator."
        elif current_time < waktu_mulai:
            is_aktif = False
            is_ended = False
            pesan_status = f"Sesi belum dimulai. Dibuka pukul {jam_mulai_str} WIB."
        elif current_time > waktu_selesai:
            is_aktif = False
            is_ended = True
            pesan_status = f"Sesi telah berakhir pada pukul {jam_selesai_str} WIB."
        else:
            is_aktif = True
            is_ended = False
            pesan_status = f"Sesi sedang aktif sampai pukul {jam_selesai_str} WIB."

    return {
        "tipe_sesi": tipe_sesi,
        "nama_sesi": nama_sesi,
        "tanggal": target_date.isoformat(),
        "waktu_mulai": waktu_mulai.isoformat() if waktu_mulai else None,
        "waktu_selesai": waktu_selesai.isoformat() if waktu_selesai else None,
        "waktu_mulai_dt": waktu_mulai,
        "waktu_selesai_dt": waktu_selesai,
        "jam_mulai": jam_mulai_str,
        "jam_selesai": jam_selesai_str,
        "is_aktif": is_aktif,
        "is_ended": is_ended,
        "status_sesi": "aktif" if is_aktif else "tidak_aktif",
        "pesan_status": pesan_status,
        "is_forced_closed": is_forced_closed,
        "sesi_record_id": sesi_record.id if sesi_record else None,
    }
