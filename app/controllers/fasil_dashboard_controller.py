"""
Controller untuk Summary Dashboard Fasilitator Berbasis Data Riil.
Menyediakan ringkasan eksekutif untuk gedung binaan:
- Identitas gedung & fasilitator
- KPI Mahasiswa, Izin Pending, Izin Aktif Hari Ini, Kamar
- Banner Sesi Aktif / Sesi Hari Ini
- Daftar perizinan yang menunggu review (Actionable)
- Breakdown distribusi kamar per lantai
- Kegiatan / Sesi terbaru
"""

from datetime import date, datetime
from flask import jsonify
from app.core.extensions import db
from app.models.user import User
from app.models.kamar import Kamar
from app.models.izin import Izin
from app.models.sesi_absensi import Kegiatan
from app.models.presensi import Presensi
from app.services.fasil_scope_service import resolve_fasil_building


def get_dashboard_summary():
    """
    GET /api/fasil/dashboard/summary
    Mengambil data agregat komprehensif untuk halaman dashboard fasilitator.
    Semua metrik terkunci pada gedung binaan fasilitator login.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    today = date.today()

    # 1. Mahasiswa Binaan
    mhs_list = (
        User.query
        .join(Kamar, User.kamar_id == Kamar.id)
        .filter(User.role == 'mahasiswa', Kamar.gedung_id == gedung.id)
        .all()
    )
    total_mhs = len(mhs_list)
    mhs_ids = [m.id for m in mhs_list]

    # 2. Distribusi Kamar & Lantai
    kamar_list = gedung.daftar_kamar.order_by(Kamar.lantai, Kamar.nomor_kamar).all()
    lantai_dict = {}
    for k in kamar_list:
        lt = k.lantai
        if lt not in lantai_dict:
            lantai_dict[lt] = {
                'lantai': lt,
                'total_kamar': 0,
                'total_penghuni': 0,
                'kamar': []
            }
        penghuni_count = k.penghuni.count() if hasattr(k.penghuni, 'count') else len(k.penghuni)
        lantai_dict[lt]['total_kamar'] += 1
        lantai_dict[lt]['total_penghuni'] += penghuni_count
        lantai_dict[lt]['kamar'].append({
            'id': k.id,
            'nomor_kamar': k.nomor_kamar,
            'total_penghuni': penghuni_count
        })
    distribusi_lantai = [lantai_dict[lt] for lt in sorted(lantai_dict.keys())]

    # 3. Izin Pending & Izin Aktif Hari Ini
    pending_izin_items = []
    total_pending_izin = 0
    total_izin_aktif_hari_ini = 0

    if mhs_ids:
        # Izin pending yang butuh review
        pending_query = (
            Izin.query
            .filter(Izin.user_id.in_(mhs_ids), Izin.status == 'pending')
            .order_by(Izin.created_at.desc(), Izin.id.desc())
        )
        total_pending_izin = pending_query.count()
        for p in pending_query.limit(5).all():
            mhs_ref = p.pemohon
            nomor_kamar = mhs_ref.kamar_ref.nomor_kamar if mhs_ref and mhs_ref.kamar_ref else '-'
            lantai = mhs_ref.kamar_ref.lantai if mhs_ref and mhs_ref.kamar_ref else 1
            pending_izin_items.append({
                'id': p.id,
                'nim': mhs_ref.nim if mhs_ref else '-',
                'nama': mhs_ref.nama if mhs_ref else '-',
                'nomor_kamar': nomor_kamar,
                'lantai': lantai,
                'jenis': p.jenis,
                'tanggal_mulai': p.tanggal_mulai.isoformat() if p.tanggal_mulai else None,
                'tanggal_selesai': p.tanggal_selesai.isoformat() if p.tanggal_selesai else None,
                'alasan': p.alasan,
                'created_at': p.created_at.isoformat() if p.created_at else None
            })

        # Izin yang sah/approved dan sedang aktif hari ini (di luar asrama)
        total_izin_aktif_hari_ini = Izin.query.filter(
            Izin.user_id.in_(mhs_ids),
            Izin.status == 'approved',
            Izin.tanggal_mulai <= today,
            Izin.tanggal_selesai >= today
        ).count()

    # 4. Sesi Presensi Aktif & Agenda Hari Ini
    sesi_aktif = Kegiatan.query.filter_by(is_aktif=True).first()
    sesi_aktif_data = None
    if sesi_aktif and mhs_ids:
        sudah_absen = Presensi.query.filter(
            Presensi.user_id.in_(mhs_ids),
            Presensi.tanggal == (sesi_aktif.tanggal or today),
            Presensi.sesi == (sesi_aktif.tipe_sesi or sesi_aktif.nama_sesi)
        ).count()
        sesi_aktif_data = {
            'id': sesi_aktif.id,
            'nama_sesi': sesi_aktif.nama_sesi,
            'tipe_sesi': sesi_aktif.tipe_sesi,
            'tanggal': sesi_aktif.tanggal.isoformat() if sesi_aktif.tanggal else None,
            'waktu_mulai': sesi_aktif.waktu_mulai.isoformat() if sesi_aktif.waktu_mulai else None,
            'waktu_selesai': sesi_aktif.waktu_selesai.isoformat() if sesi_aktif.waktu_selesai else None,
            'status': sesi_aktif.status,
            'is_aktif': True,
            'sudah_absen': sudah_absen,
            'belum_absen': max(0, total_mhs - sudah_absen),
        }

    # Sesi hari ini
    sesi_hari_ini_raw = Kegiatan.query.filter(Kegiatan.tanggal == today).order_by(Kegiatan.waktu_mulai.asc()).all()
    sesi_hari_ini_list = [
        {
            'id': s.id,
            'nama_sesi': s.nama_sesi,
            'tipe_sesi': s.tipe_sesi,
            'tanggal': s.tanggal.isoformat() if s.tanggal else None,
            'waktu_mulai': s.waktu_mulai.isoformat() if s.waktu_mulai else None,
            'waktu_selesai': s.waktu_selesai.isoformat() if s.waktu_selesai else None,
            'status': s.status,
            'is_aktif': bool(s.is_aktif)
        }
        for s in sesi_hari_ini_raw
    ]

    # Kegiatan terbaru (5 item)
    kegiatan_terbaru_raw = Kegiatan.query.order_by(Kegiatan.tanggal.desc(), Kegiatan.id.desc()).limit(5).all()
    kegiatan_terbaru_list = [
        {
            'id': k.id,
            'nama_sesi': k.nama_sesi,
            'tipe_sesi': k.tipe_sesi,
            'tanggal': k.tanggal.isoformat() if k.tanggal else None,
            'waktu_mulai': k.waktu_mulai.isoformat() if k.waktu_mulai else None,
            'waktu_selesai': k.waktu_selesai.isoformat() if k.waktu_selesai else None,
            'status': k.status,
            'is_aktif': bool(k.is_aktif),
            'keterangan': k.keterangan
        }
        for k in kegiatan_terbaru_raw
    ]

    # Rata-rata penghuni per kamar
    rata_penghuni = round(total_mhs / len(kamar_list), 1) if kamar_list else 0

    return jsonify({
        "success": True,
        "message": "Data summary dashboard fasilitator berhasil dimuat.",
        "data": {
            "gedung": {
                "id": gedung.id,
                "nama_gedung": gedung.nama_gedung,
                "total_kamar": len(kamar_list),
                "total_mahasiswa": total_mhs,
                "rata_penghuni_per_kamar": rata_penghuni,
                "distribusi_lantai": distribusi_lantai
            },
            "kpi": {
                "total_mahasiswa": total_mhs,
                "total_kamar": len(kamar_list),
                "total_pending_izin": total_pending_izin,
                "total_izin_aktif_hari_ini": total_izin_aktif_hari_ini,
            },
            "izin_pending": {
                "total": total_pending_izin,
                "items": pending_izin_items
            },
            "sesi": {
                "sesi_aktif": sesi_aktif_data,
                "sesi_hari_ini": sesi_hari_ini_list,
                "kegiatan_terbaru": kegiatan_terbaru_list
            },
            "tanggal_hari_ini": today.isoformat()
        }
    }), 200
