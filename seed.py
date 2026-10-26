import os
from datetime import datetime, date, time
import pymysql
from dotenv import load_dotenv

# Load env variables
load_dotenv()

DB_USER = os.getenv('DB_USERNAME', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', 3306))
DB_NAME = os.getenv('DB_NAME', 'pabf')

def ensure_database():
    """Pastikan database pabf sudah dibuat di MySQL."""
    print(f"[*] Menghubungkan ke MySQL di {DB_HOST}:{DB_PORT} sebagai '{DB_USER}'...")
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                print(f"[OK] Database '{DB_NAME}' siap.")
        finally:
            conn.close()
    except Exception as e:
        print(f"[!] Warning koneksi MySQL: {e}")

def seed_database():
    """Buat tabel dan isi data relasional awal untuk pengujian."""
    from app import create_app
    from app.core.extensions import db
    from app.models import (
        User, Gedung, Kamar, Presensi, Izin, SesiAbsensi,
        SesiPresensi, FasilitatorGedung, IzinDokumen
    )
    from app.models.area_absensi import AreaAbsensi

    app = create_app()
    with app.app_context():
        print("[*] Membuat / memeriksa tabel-tabel di database...")
        db.create_all()
        print("[OK] Tabel berhasil diperiksa/dibuat.")

        # =========================================================================
        # 1. SEED ADMIN & FASILITATOR (3 GEDUNG)
        # =========================================================================
        admin = User.query.filter_by(nim='admin').first()
        if not admin:
            admin = User(
                nim='admin',
                nama='Administrator Asrama',
                role='admin',
                email='admin@asrama.ac.id'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.flush()
            print("[OK] User Admin dibuat (admin / admin123)")
        else:
            admin.set_password('admin123')

        fasil_specs = [
            {
                "nim": "fasil01",
                "nama": "Ust. Hendra (Fasilitator A)",
                "asal": "Padang",
                "jekel": "L",
                "email": "fasil.hendra@asrama.ac.id",
                "password": "fasil123"
            },
            {
                "nim": "fasil02",
                "nama": "Ust. Rahmat (Fasilitator B)",
                "asal": "Bukittinggi",
                "jekel": "L",
                "email": "fasil.rahmat@asrama.ac.id",
                "password": "fasil123"
            },
            {
                "nim": "fasil03",
                "nama": "Ust. Farhan (Fasilitator C)",
                "asal": "Payakumbuh",
                "jekel": "L",
                "email": "fasil.farhan@asrama.ac.id",
                "password": "fasil123"
            }
        ]

        fasils = {}
        for spec in fasil_specs:
            fasil = User.query.filter_by(nim=spec["nim"]).first()
            if not fasil:
                fasil = User(
                    nim=spec["nim"],
                    nama=spec["nama"],
                    role='fasil',
                    asal=spec["asal"],
                    jekel=spec["jekel"],
                    email=spec["email"]
                )
                fasil.set_password(spec["password"])
                db.session.add(fasil)
                db.session.flush()
                print(f"[OK] Fasilitator {spec['nama']} dibuat ({spec['nim']} / {spec['password']})")
            else:
                fasil.nama = spec["nama"]
                fasil.asal = spec["asal"]
                fasil.jekel = spec["jekel"]
                fasil.email = spec["email"]
                fasil.set_password(spec["password"])
            fasils[spec["nim"]] = fasil

        db.session.commit()

        # =========================================================================
        # 2. SEED 3 GEDUNG & RELASI FASILITATOR
        # =========================================================================
        gedung_specs = [
            {"nama": "Gedung Asrama Putra A", "fasil_nim": "fasil01"},
            {"nama": "Gedung Asrama Putra B", "fasil_nim": "fasil02"},
            {"nama": "Gedung Asrama Putra C", "fasil_nim": "fasil03"},
        ]

        gedungs = {}
        for g_spec in gedung_specs:
            fasil_obj = fasils[g_spec["fasil_nim"]]
            gedung = Gedung.query.filter_by(nama_gedung=g_spec["nama"]).first()
            if not gedung:
                gedung = Gedung(
                    nama_gedung=g_spec["nama"],
                    user_id=fasil_obj.id
                )
                db.session.add(gedung)
                db.session.flush()
                print(f"[OK] Gedung '{gedung.nama_gedung}' dibuat (Fasil: {fasil_obj.nama})")
            else:
                gedung.user_id = fasil_obj.id
            gedungs[g_spec["nama"]] = gedung

            # Relasi Many-to-Many FasilitatorGedung
            fg = FasilitatorGedung.query.filter_by(
                fasilitator_id=fasil_obj.id,
                gedung_id=gedung.id
            ).first()
            if not fg:
                fg = FasilitatorGedung(fasilitator_id=fasil_obj.id, gedung_id=gedung.id)
                db.session.add(fg)

        db.session.commit()

        # =========================================================================
        # 3. SEED MASTER SESI PRESENSI
        # =========================================================================
        sesi_pagi = SesiPresensi.query.filter_by(kode='subuh').first()
        if not sesi_pagi:
            sesi_pagi = SesiPresensi(
                kode='subuh',
                nama='Pagi',
                jam_mulai=time(5, 0, 0),
                jam_selesai=time(6, 30, 0),
                is_active=True
            )
            db.session.add(sesi_pagi)
            print("[OK] Master Sesi Presensi 'Pagi' (subuh) dibuat.")

        sesi_malam = SesiPresensi.query.filter_by(kode='malam').first()
        if not sesi_malam:
            sesi_malam = SesiPresensi(
                kode='malam',
                nama='Malam',
                jam_mulai=time(21, 0, 0),
                jam_selesai=time(22, 30, 0),
                is_active=True
            )
            db.session.add(sesi_malam)
            print("[OK] Master Sesi Presensi 'Malam' (malam) dibuat.")

        db.session.commit()

        # =========================================================================
        # 4. SEED KAMAR DI SETIAP GEDUNG
        # =========================================================================
        # Gedung A: kamar 101, 102, 103, 204, 205 (5 kamar, masing-masing 2 mhs)
        # Gedung B: kamar 101, 102, 103, 201, 202
        # Gedung C: kamar 101, 102, 103, 201, 202
        kamar_room_list = {
            "Gedung Asrama Putra A": [
                {"nomor": "101", "lantai": 1},
                {"nomor": "102", "lantai": 1},
                {"nomor": "103", "lantai": 1},
                {"nomor": "204", "lantai": 2},
                {"nomor": "205", "lantai": 2},
            ],
            "Gedung Asrama Putra B": [
                {"nomor": "101", "lantai": 1},
                {"nomor": "102", "lantai": 1},
                {"nomor": "103", "lantai": 1},
                {"nomor": "201", "lantai": 2},
                {"nomor": "202", "lantai": 2},
            ],
            "Gedung Asrama Putra C": [
                {"nomor": "101", "lantai": 1},
                {"nomor": "102", "lantai": 1},
                {"nomor": "103", "lantai": 1},
                {"nomor": "201", "lantai": 2},
                {"nomor": "202", "lantai": 2},
            ],
        }

        kamars = {}
        for g_nama, rooms in kamar_room_list.items():
            g_obj = gedungs[g_nama]
            for r in rooms:
                kmr = Kamar.query.filter_by(gedung_id=g_obj.id, nomor_kamar=r["nomor"]).first()
                if not kmr:
                    kmr = Kamar(gedung_id=g_obj.id, nomor_kamar=r["nomor"], lantai=r["lantai"])
                    db.session.add(kmr)
                    db.session.flush()
                kamars[(g_nama, r["nomor"])] = kmr

        db.session.commit()
        print("[OK] Kamar-kamar di ketiga gedung siap.")

        # =========================================================================
        # 5. SEED 10 MAHASISWA PER GEDUNG (TOTAL 30 MAHASISWA)
        # =========================================================================
        mahasiswa_data = {
            "Gedung Asrama Putra A": [
                {"nim": "2211522001", "nama": "Muhammad Afiq", "asal": "Bukittinggi", "kamar": "204"},
                {"nim": "2211521019", "nama": "Fajar Maulana", "asal": "Padang Panjang", "kamar": "205"},
                {"nim": "2211521001", "nama": "Aditia Pratama", "asal": "Bukittinggi", "kamar": "101"},
                {"nim": "2211521002", "nama": "Bima Arya", "asal": "Solok", "kamar": "101"},
                {"nim": "2211521003", "nama": "Candra Wijaya", "asal": "Payakumbuh", "kamar": "102"},
                {"nim": "2211521004", "nama": "Dwi Kurniawan", "asal": "Pariaman", "kamar": "102"},
                {"nim": "2211521005", "nama": "Eka Saputra", "asal": "Batusangkar", "kamar": "103"},
                {"nim": "2211521006", "nama": "Fikri Haikal", "asal": "Padang", "kamar": "103"},
                {"nim": "2211521007", "nama": "Gilang Ramadhan", "asal": "Pekanbaru", "kamar": "204"},
                {"nim": "2211521008", "nama": "Haris Munandar", "asal": "Medan", "kamar": "205"},
            ],
            "Gedung Asrama Putra B": [
                {"nim": "2211522045", "nama": "Rifqi Pratama", "asal": "Payakumbuh", "kamar": "101"},
                {"nim": "2211522010", "nama": "Ilham Ramadhan", "asal": "Solok", "kamar": "102"},
                {"nim": "2211522002", "nama": "Aldy Syahputra", "asal": "Padang", "kamar": "101"},
                {"nim": "2211522003", "nama": "Bayu Nugraha", "asal": "Bukittinggi", "kamar": "102"},
                {"nim": "2211522004", "nama": "Danu Pratama", "asal": "Padang Pariaman", "kamar": "103"},
                {"nim": "2211522005", "nama": "Fauzan Azim", "asal": "Sawahlunto", "kamar": "103"},
                {"nim": "2211522006", "nama": "Habib Al-Farizi", "asal": "Sijunjung", "kamar": "201"},
                {"nim": "2211522007", "nama": "Ihsan Kamil", "asal": "Dharmasraya", "kamar": "201"},
                {"nim": "2211522008", "nama": "Kiki Ramadhan", "asal": "Pesisir Selatan", "kamar": "202"},
                {"nim": "2211522009", "nama": "Lucky Ananda", "asal": "Padang", "kamar": "202"},
            ],
            "Gedung Asrama Putra C": [
                {"nim": "2211523001", "nama": "Arya Permana", "asal": "Padang", "kamar": "101"},
                {"nim": "2211523002", "nama": "Bagas Danendra", "asal": "Bukittinggi", "kamar": "101"},
                {"nim": "2211523003", "nama": "Dimas Setiawan", "asal": "Payakumbuh", "kamar": "102"},
                {"nim": "2211523004", "nama": "Fadil Akbar", "asal": "Solok", "kamar": "102"},
                {"nim": "2211523005", "nama": "Gusti Randa", "asal": "Pariaman", "kamar": "103"},
                {"nim": "2211523006", "nama": "Hafidz Pratama", "asal": "Batusangkar", "kamar": "103"},
                {"nim": "2211523007", "nama": "Iqbal Maulana", "asal": "Padang", "kamar": "201"},
                {"nim": "2211523008", "nama": "Jefri Ramadhan", "asal": "Lubuk Basung", "kamar": "201"},
                {"nim": "2211523009", "nama": "Miftahul Huda", "asal": "Solok Selatan", "kamar": "202"},
                {"nim": "2211523010", "nama": "Naufal Rizky", "asal": "Pasaman", "kamar": "202"},
            ],
        }

        mhs_objects = {}
        for g_nama, students in mahasiswa_data.items():
            for s in students:
                kamar_obj = kamars[(g_nama, s["kamar"])]
                mhs = User.query.filter_by(nim=s["nim"]).first()
                if not mhs:
                    mhs = User(
                        nim=s["nim"],
                        nama=s["nama"],
                        role='mahasiswa',
                        asal=s["asal"],
                        jekel='L',
                        email=f"{s['nim']}@student.unand.ac.id",
                        kamar_id=kamar_obj.id
                    )
                    mhs.set_password('password123')
                    db.session.add(mhs)
                    db.session.flush()
                else:
                    mhs.nama = s["nama"]
                    mhs.asal = s["asal"]
                    mhs.kamar_id = kamar_obj.id
                    mhs.set_password('password123')
                mhs_objects[s["nim"]] = mhs

        db.session.commit()
        print(f"[OK] Total 30 Mahasiswa (10 orang per gedung) berhasil di-seed.")

        # =========================================================================
        # 6. SEED AREA POLYGON ABSENSI (3 GEDUNG)
        # =========================================================================
        area_specs = [
            {
                "gedung": gedungs["Gedung Asrama Putra A"],
                "fasil": fasils["fasil01"],
                "nama": "Area Presensi Asrama Putra A",
                "deskripsi": "Zona radius geofencing Gedung Asrama Putra A Kampus Limau Manis",
                "polygon_wkt": "POLYGON((100.4590 -0.9160, 100.4630 -0.9160, 100.4630 -0.9130, 100.4590 -0.9130, 100.4590 -0.9160))"
            },
            {
                "gedung": gedungs["Gedung Asrama Putra B"],
                "fasil": fasils["fasil02"],
                "nama": "Area Presensi Asrama Putra B",
                "deskripsi": "Zona radius geofencing Gedung Asrama Putra B Kampus Limau Manis",
                "polygon_wkt": "POLYGON((100.4635 -0.9160, 100.4675 -0.9160, 100.4675 -0.9130, 100.4635 -0.9130, 100.4635 -0.9160))"
            },
            {
                "gedung": gedungs["Gedung Asrama Putra C"],
                "fasil": fasils["fasil03"],
                "nama": "Area Presensi Asrama Putra C",
                "deskripsi": "Zona radius geofencing Gedung Asrama Putra C Kampus Limau Manis",
                "polygon_wkt": "POLYGON((100.4680 -0.9160, 100.4720 -0.9160, 100.4720 -0.9130, 100.4680 -0.9130, 100.4680 -0.9160))"
            },
        ]

        areas = {}
        for a_spec in area_specs:
            g_obj = a_spec["gedung"]
            area = AreaAbsensi.query.filter_by(gedung_id=g_obj.id).first()
            if not area:
                area = AreaAbsensi(
                    nama=a_spec["nama"],
                    deskripsi=a_spec["deskripsi"],
                    polygon_wkt=a_spec["polygon_wkt"],
                    gedung_id=g_obj.id,
                    is_active=True,
                    dibuat_oleh=a_spec["fasil"].id
                )
                db.session.add(area)
                print(f"[OK] Area Polygon untuk '{g_obj.nama_gedung}' dibuat.")
            else:
                area.gedung_id = g_obj.id
                area.nama = a_spec["nama"]
                area.polygon_wkt = a_spec["polygon_wkt"]
            areas[g_obj.id] = area

        db.session.commit()

        # =========================================================================
        # 7. SEED CONTOH DATA PRESENSI HARI INI
        # =========================================================================
        hari_ini = date.today()
        sample_presensi = [
            {
                "mhs": mhs_objects["2211522001"], # Afiq (Gedung A)
                "gedung": gedungs["Gedung Asrama Putra A"],
                "area": areas[gedungs["Gedung Asrama Putra A"].id],
                "lat": -0.9145, "lon": 100.4607,
                "ket": "Presensi Subuh Asrama Tepat Waktu"
            },
            {
                "mhs": mhs_objects["2211522045"], # Rifqi (Gedung B)
                "gedung": gedungs["Gedung Asrama Putra B"],
                "area": areas[gedungs["Gedung Asrama Putra B"].id],
                "lat": -0.9148, "lon": 100.4650,
                "ket": "Presensi Subuh Asrama Putra B"
            },
            {
                "mhs": mhs_objects["2211523001"], # Arya (Gedung C)
                "gedung": gedungs["Gedung Asrama Putra C"],
                "area": areas[gedungs["Gedung Asrama Putra C"].id],
                "lat": -0.9150, "lon": 100.4695,
                "ket": "Presensi Subuh Asrama Putra C"
            },
        ]

        for sp in sample_presensi:
            p = Presensi.query.filter_by(user_id=sp["mhs"].id, tanggal=hari_ini, sesi='subuh').first()
            if not p:
                p = Presensi(
                    user_id=sp["mhs"].id,
                    nim=sp["mhs"].nim,
                    tanggal=hari_ini,
                    waktu=datetime.now(),
                    sesi='subuh',
                    latitude=sp["lat"],
                    longitude=sp["lon"],
                    accuracy=12.0,
                    area_absensi_id=sp["area"].id,
                    gedung_id=sp["gedung"].id,
                    status='hadir',
                    keterangan=sp["ket"]
                )
                db.session.add(p)
                print(f"[OK] Sample Presensi {sp['gedung'].nama_gedung} ({sp['mhs'].nama}) dibuat.")
            else:
                p.gedung_id = sp["gedung"].id
                p.area_absensi_id = sp["area"].id

        # =========================================================================
        # 8. SEED CONTOH IZIN PER GEDUNG
        # =========================================================================
        # Gedung A: Izin sakit (Approved)
        izin_a = Izin.query.filter_by(user_id=mhs_objects["2211522001"].id).first()
        if not izin_a:
            izin_a = Izin(
                user_id=mhs_objects["2211522001"].id,
                tanggal_mulai=hari_ini,
                tanggal_selesai=hari_ini,
                alasan='Izin sakit demam berobat ke klinik kampus',
                status='approved',
                disetujui_oleh=fasils["fasil01"].id,
                catatan_fasil='Istirahat yang cukup dan minum obat teratur.',
                jenis='full',
                reviewed_at=datetime.utcnow()
            )
            db.session.add(izin_a)
            print("[OK] Sample Izin disetujui untuk Gedung A dibuat.")

        # Gedung B: Izin pulang kampung (Pending)
        izin_b = Izin.query.filter_by(user_id=mhs_objects["2211522010"].id).first()
        if not izin_b:
            izin_b = Izin(
                user_id=mhs_objects["2211522010"].id,
                tanggal_mulai=hari_ini,
                tanggal_selesai=hari_ini,
                alasan='Izin keperluan keluarga mendesak di Solok',
                status='pending',
                jenis='full'
            )
            db.session.add(izin_b)
            print("[OK] Sample Izin pending untuk Gedung B dibuat.")

        # Gedung C: Izin kegiatan lomba akademik (Pending)
        izin_c = Izin.query.filter_by(user_id=mhs_objects["2211523002"].id).first()
        if not izin_c:
            izin_c = Izin(
                user_id=mhs_objects["2211523002"].id,
                tanggal_mulai=hari_ini,
                tanggal_selesai=hari_ini,
                alasan='Mengikuti delegasi lomba karya tulis ilmiah nasional',
                status='pending',
                jenis='full'
            )
            db.session.add(izin_c)
            print("[OK] Sample Izin pending untuk Gedung C dibuat.")

        # =========================================================================
        # 9. SEED SESI JADWAL KEGIATAN HARI INI & RIWAYAT
        # =========================================================================
        sesi_kegiatan_today = SesiAbsensi.query.filter_by(tanggal=hari_ini, tipe_sesi='kegiatan').first()
        if not sesi_kegiatan_today:
            sesi_kegiatan_today = SesiAbsensi(
                nama_sesi='Kajian Akbar Asrama & Doa Bersama',
                tipe_sesi='kegiatan',
                tanggal=hari_ini,
                waktu_mulai=datetime.combine(hari_ini, time(8, 0, 0)),
                waktu_selesai=datetime.combine(hari_ini, time(22, 0, 0)),
                status='aktif',
                dibuat_oleh=fasils["fasil01"].id,
                keterangan='Kegiatan rutin mingguan pembinaan karakter dan silaturahmi penghuni asrama.'
            )
            db.session.add(sesi_kegiatan_today)
            print(f"[OK] Sesi Kegiatan Hari Ini '{sesi_kegiatan_today.nama_sesi}' dibuat.")

        kegiatan_dummies = [
            {"tanggal": date(hari_ini.year, hari_ini.month, 4) if hari_ini.day >= 4 else hari_ini, "jam": 8, "menit": 30, "keterangan": "Gotong Royong & Kerja Bakti Lingkungan Asrama", "status": "hadir"},
            {"tanggal": date(hari_ini.year, hari_ini.month, 8) if hari_ini.day >= 8 else hari_ini, "jam": 20, "menit": 15, "keterangan": "Kajian Rutin & Pembinaan Karakter", "status": "hadir"},
            {"tanggal": date(hari_ini.year, hari_ini.month, 11) if hari_ini.day >= 11 else hari_ini, "jam": 7, "menit": 10, "keterangan": "Senam Pagi Bersama & Cek Kebugaran", "status": "hadir"},
            {"tanggal": date(hari_ini.year, hari_ini.month, 14) if hari_ini.day >= 14 else hari_ini, "jam": 14, "menit": 45, "keterangan": "Seminar Kepemimpinan & Soft Skills", "status": "hadir"},
        ]

        mhs_sample = mhs_objects["2211522001"]
        area_a = areas[gedungs["Gedung Asrama Putra A"].id]
        for item in kegiatan_dummies:
            p_keg = Presensi.query.filter_by(
                user_id=mhs_sample.id,
                tanggal=item["tanggal"],
                sesi='kegiatan'
            ).first()
            if not p_keg:
                p_keg = Presensi(
                    user_id=mhs_sample.id,
                    nim=mhs_sample.nim,
                    tanggal=item["tanggal"],
                    waktu=datetime.combine(item["tanggal"], time(item["jam"], item["menit"])),
                    sesi='kegiatan',
                    latitude=-0.9145,
                    longitude=100.4607,
                    accuracy=10.0,
                    area_absensi_id=area_a.id,
                    gedung_id=gedungs["Gedung Asrama Putra A"].id,
                    status=item["status"],
                    keterangan=item["keterangan"]
                )
                db.session.add(p_keg)

        # =========================================================================
        # 10. SEED SAMPLE PENGAJUAN PERIZINAN (IZIN)
        # =========================================================================
        fasil_a = fasils["fasil01"]
        mhs_a1 = mhs_objects.get("2211522001") # Muhammad Fathur
        mhs_a2 = mhs_objects.get("2211522002") # Ahmad Zaky
        mhs_a3 = mhs_objects.get("2211522003") # Rizky Ramadhan
        mhs_a4 = mhs_objects.get("2211522004") # Ilham Pratama
        mhs_a5 = mhs_objects.get("2211522005") # Daffa Al Ghifari

        sample_izins = []
        if mhs_a1:
            sample_izins.append({
                "user_id": mhs_a1.id,
                "tanggal_mulai": date(hari_ini.year, hari_ini.month, hari_ini.day),
                "tanggal_selesai": date(hari_ini.year, hari_ini.month, min(hari_ini.day + 2, 28)),
                "alasan": "Menghadiri resepsi pernikahan kakak kandung di kampung halaman (Bukittinggi).",
                "jenis": "full",
                "status": "pending",
                "sesi_id": None
            })
        if mhs_a2:
            sample_izins.append({
                "user_id": mhs_a2.id,
                "tanggal_mulai": date(hari_ini.year, hari_ini.month, hari_ini.day),
                "tanggal_selesai": date(hari_ini.year, hari_ini.month, hari_ini.day),
                "alasan": "Demam tinggi dan flu berat, istirahat di klinik kampus.",
                "jenis": "half",
                "status": "pending",
                "sesi_id": sesi_malam.id
            })
        if mhs_a3:
            sample_izins.append({
                "user_id": mhs_a3.id,
                "tanggal_mulai": date(hari_ini.year, hari_ini.month, min(hari_ini.day + 1, 28)),
                "tanggal_selesai": date(hari_ini.year, hari_ini.month, min(hari_ini.day + 3, 28)),
                "alasan": "Mengikuti delegasi Lomba Debat Mahasiswa Nasional di Universitas Riau mewakili kampus.",
                "jenis": "full",
                "status": "pending",
                "sesi_id": None
            })
        if mhs_a4:
            sample_izins.append({
                "user_id": mhs_a4.id,
                "tanggal_mulai": date(hari_ini.year, hari_ini.month, max(hari_ini.day - 3, 1)),
                "tanggal_selesai": date(hari_ini.year, hari_ini.month, max(hari_ini.day - 1, 1)),
                "alasan": "Pulang ke rumah orang tua untuk melengkapi berkas administrasi beasiswa daerah.",
                "jenis": "full",
                "status": "approved",
                "disetujui_oleh": fasil_a.id,
                "catatan_fasil": "Disetujui. Berkas pendukung lengkap dan telah dikonfirmasi.",
                "reviewed_at": datetime.now(),
                "sesi_id": None
            })
        if mhs_a5:
            sample_izins.append({
                "user_id": mhs_a5.id,
                "tanggal_mulai": date(hari_ini.year, hari_ini.month, max(hari_ini.day - 4, 1)),
                "tanggal_selesai": date(hari_ini.year, hari_ini.month, max(hari_ini.day - 2, 1)),
                "alasan": "Acara kumpul dan nongkrong bersama teman di kafe luar kampus.",
                "jenis": "half",
                "status": "rejected",
                "disetujui_oleh": fasil_a.id,
                "catatan_fasil": "Alasan tidak memenuhi kriteria perizinan asrama.",
                "reviewed_at": datetime.now(),
                "sesi_id": sesi_malam.id
            })

        for s_iz in sample_izins:
            iz_exist = Izin.query.filter_by(
                user_id=s_iz["user_id"],
                tanggal_mulai=s_iz["tanggal_mulai"],
                status=s_iz["status"]
            ).first()
            if not iz_exist:
                new_iz = Izin(
                    user_id=s_iz["user_id"],
                    tanggal_mulai=s_iz["tanggal_mulai"],
                    tanggal_selesai=s_iz["tanggal_selesai"],
                    alasan=s_iz["alasan"],
                    status=s_iz["status"],
                    jenis=s_iz["jenis"],
                    sesi_id=s_iz["sesi_id"],
                    disetujui_oleh=s_iz.get("disetujui_oleh"),
                    catatan_fasil=s_iz.get("catatan_fasil"),
                    reviewed_at=s_iz.get("reviewed_at")
                )
                db.session.add(new_iz)

        db.session.commit()
        print("[OK] Seeding 5 sample perizinan (pending, approved, rejected) berhasil.")

        print("\n" + "="*70)
        print(" [OK] SEEDING 3 GEDUNG DENGAN MASING-MASING 10 MAHASISWA BERHASIL!")
        print("="*70)
        print(" [Akun Administrator]")
        print("   Username: admin | Password: admin123")
        print("\n [Akun Fasilitator & 10 Mahasiswa per Gedung]")
        for g_nama in ["Gedung Asrama Putra A", "Gedung Asrama Putra B", "Gedung Asrama Putra C"]:
            g_obj = gedungs[g_nama]
            f_obj = g_obj.fasil
            print(f"\n * {g_nama}")
            print(f"   Fasilitator : {f_obj.nim} / fasil123 ({f_obj.nama})")
            print(f"   Mahasiswa ({len(mahasiswa_data[g_nama])} orang):")
            for idx, m in enumerate(mahasiswa_data[g_nama], 1):
                print(f"     {idx:2d}. {m['nim']} | {m['nama']:<20} | Kamar {m['kamar']:<3} | Password: password123")
        print("="*70)

if __name__ == '__main__':
    ensure_database()
    seed_database()
