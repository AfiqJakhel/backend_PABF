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
    from app.models import User, Gedung, Kamar, Presensi, Izin

    app = create_app()
    with app.app_context():
        print("[*] Membuat / memeriksa tabel-tabel di database...")
        db.create_all()
        print("[OK] Tabel berhasil diperiksa/dibuat.")

        # 1. Seed Fasil & Admin dahulu
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

        # Fasil 01 -> Gedung A
        fasil_a = User.query.filter_by(nim='fasil01').first()
        if not fasil_a:
            fasil_a = User(
                nim='fasil01',
                nama='Ust. Hendra (Fasilitator A)',
                role='fasil',
                asal='Padang',
                jekel='L',
                email='fasil.hendra@asrama.ac.id'
            )
            fasil_a.set_password('fasil123')
            db.session.add(fasil_a)
            db.session.flush()
            print("[OK] User Fasil A dibuat (fasil01 / fasil123)")
        else:
            fasil_a.nama = 'Ust. Hendra (Fasilitator A)'
            fasil_a.set_password('fasil123')

        # Fasil 02 -> Gedung B
        fasil_b = User.query.filter_by(nim='fasil02').first()
        if not fasil_b:
            fasil_b = User(
                nim='fasil02',
                nama='Ust. Rahmat (Fasilitator B)',
                role='fasil',
                asal='Bukittinggi',
                jekel='L',
                email='fasil.rahmat@asrama.ac.id'
            )
            fasil_b.set_password('fasil123')
            db.session.add(fasil_b)
            db.session.flush()
            print("[OK] User Fasil B dibuat (fasil02 / fasil123)")
        else:
            fasil_b.nama = 'Ust. Rahmat (Fasilitator B)'
            fasil_b.set_password('fasil123')

        # 2. Seed Gedung A & B
        gedung_a = Gedung.query.filter_by(nama_gedung='Gedung Asrama Putra A').first()
        if not gedung_a:
            gedung_a = Gedung(
                nama_gedung='Gedung Asrama Putra A',
                user_id=fasil_a.id
            )
            db.session.add(gedung_a)
            db.session.flush()
            print(f"[OK] Gedung '{gedung_a.nama_gedung}' dibuat (Fasil: {fasil_a.nama})")
        else:
            gedung_a.user_id = fasil_a.id

        gedung_b = Gedung.query.filter_by(nama_gedung='Gedung Asrama Putra B').first()
        if not gedung_b:
            gedung_b = Gedung(
                nama_gedung='Gedung Asrama Putra B',
                user_id=fasil_b.id
            )
            db.session.add(gedung_b)
            db.session.flush()
            print(f"[OK] Gedung '{gedung_b.nama_gedung}' dibuat (Fasil: {fasil_b.nama})")
        else:
            gedung_b.user_id = fasil_b.id

        # 3. Seed Kamar
        # Kamar di Gedung A
        kamar_204_a = Kamar.query.filter_by(gedung_id=gedung_a.id, nomor_kamar='204').first()
        if not kamar_204_a:
            kamar_204_a = Kamar(gedung_id=gedung_a.id, nomor_kamar='204', lantai=2)
            db.session.add(kamar_204_a)
            db.session.flush()
            print(f"[OK] Kamar 204 Lantai 2 di {gedung_a.nama_gedung} dibuat")

        kamar_205_a = Kamar.query.filter_by(gedung_id=gedung_a.id, nomor_kamar='205').first()
        if not kamar_205_a:
            kamar_205_a = Kamar(gedung_id=gedung_a.id, nomor_kamar='205', lantai=2)
            db.session.add(kamar_205_a)
            db.session.flush()
            print(f"[OK] Kamar 205 Lantai 2 di {gedung_a.nama_gedung} dibuat")

        # Kamar di Gedung B
        kamar_101_b = Kamar.query.filter_by(gedung_id=gedung_b.id, nomor_kamar='101').first()
        if not kamar_101_b:
            kamar_101_b = Kamar(gedung_id=gedung_b.id, nomor_kamar='101', lantai=1)
            db.session.add(kamar_101_b)
            db.session.flush()
            print(f"[OK] Kamar 101 Lantai 1 di {gedung_b.nama_gedung} dibuat")

        kamar_102_b = Kamar.query.filter_by(gedung_id=gedung_b.id, nomor_kamar='102').first()
        if not kamar_102_b:
            kamar_102_b = Kamar(gedung_id=gedung_b.id, nomor_kamar='102', lantai=1)
            db.session.add(kamar_102_b)
            db.session.flush()
            print(f"[OK] Kamar 102 Lantai 1 di {gedung_b.nama_gedung} dibuat")

        # 4. Seed Mahasiswa
        # Mahasiswa Gedung A
        mhs_a1 = User.query.filter_by(nim='2211522001').first()
        if not mhs_a1:
            mhs_a1 = User(
                nim='2211522001',
                nama='Muhammad Afiq',
                role='mahasiswa',
                asal='Bukittinggi',
                jekel='L',
                email='afiq@student.unand.ac.id',
                kamar_id=kamar_204_a.id
            )
            mhs_a1.set_password('password123')
            db.session.add(mhs_a1)
            db.session.flush()
            print("[OK] Mahasiswa Afiq dibuat (Gedung A: 2211522001 / password123)")
        else:
            mhs_a1.kamar_id = kamar_204_a.id
            mhs_a1.set_password('password123')

        mhs_a2 = User.query.filter_by(nim='2211521019').first()
        if not mhs_a2:
            mhs_a2 = User(
                nim='2211521019',
                nama='Fajar Maulana',
                role='mahasiswa',
                asal='Padang Panjang',
                jekel='L',
                email='fajar@student.unand.ac.id',
                kamar_id=kamar_205_a.id
            )
            mhs_a2.set_password('password123')
            db.session.add(mhs_a2)
            db.session.flush()
            print("[OK] Mahasiswa Fajar dibuat (Gedung A: 2211521019 / password123)")
        else:
            mhs_a2.kamar_id = kamar_205_a.id
            mhs_a2.set_password('password123')

        # Mahasiswa Gedung B
        mhs_b1 = User.query.filter_by(nim='2211522045').first()
        if not mhs_b1:
            mhs_b1 = User(
                nim='2211522045',
                nama='Rifqi Pratama',
                role='mahasiswa',
                asal='Payakumbuh',
                jekel='L',
                email='rifqi@student.unand.ac.id',
                kamar_id=kamar_101_b.id
            )
            mhs_b1.set_password('password123')
            db.session.add(mhs_b1)
            db.session.flush()
            print("[OK] Mahasiswa Rifqi dibuat (Gedung B: 2211522045 / password123)")
        else:
            mhs_b1.kamar_id = kamar_101_b.id
            mhs_b1.set_password('password123')

        mhs_b2 = User.query.filter_by(nim='2211522010').first()
        if not mhs_b2:
            mhs_b2 = User(
                nim='2211522010',
                nama='Ilham Ramadhan',
                role='mahasiswa',
                asal='Solok',
                jekel='L',
                email='ilham@student.unand.ac.id',
                kamar_id=kamar_102_b.id
            )
            mhs_b2.set_password('password123')
            db.session.add(mhs_b2)
            db.session.flush()
            print("[OK] Mahasiswa Ilham dibuat (Gedung B: 2211522010 / password123)")
        else:
            mhs_b2.kamar_id = kamar_102_b.id
            mhs_b2.set_password('password123')

        db.session.commit()

        # 5. Seed Area Polygon Absensi Berbasis Gedung
        from app.models.area_absensi import AreaAbsensi
        area_a = AreaAbsensi.query.filter_by(gedung_id=gedung_a.id).first()
        if not area_a:
            area_a = AreaAbsensi(
                nama='Area Presensi Asrama Putra A',
                deskripsi='Zona radius geofencing Gedung Asrama Putra A Kampus Limau Manis',
                polygon_wkt='POLYGON((100.4590 -0.9160, 100.4630 -0.9160, 100.4630 -0.9130, 100.4590 -0.9130, 100.4590 -0.9160))',
                gedung_id=gedung_a.id,
                is_active=True,
                dibuat_oleh=fasil_a.id
            )
            db.session.add(area_a)
            print(f"[OK] Area Polygon untuk '{gedung_a.nama_gedung}' dibuat.")
        else:
            area_a.gedung_id = gedung_a.id

        area_b = AreaAbsensi.query.filter_by(gedung_id=gedung_b.id).first()
        if not area_b:
            area_b = AreaAbsensi(
                nama='Area Presensi Asrama Putra B',
                deskripsi='Zona radius geofencing Gedung Asrama Putra B Kampus Limau Manis',
                polygon_wkt='POLYGON((100.4635 -0.9160, 100.4675 -0.9160, 100.4675 -0.9130, 100.4635 -0.9130, 100.4635 -0.9160))',
                gedung_id=gedung_b.id,
                is_active=True,
                dibuat_oleh=fasil_b.id
            )
            db.session.add(area_b)
            print(f"[OK] Area Polygon untuk '{gedung_b.nama_gedung}' dibuat.")
        else:
            area_b.gedung_id = gedung_b.id

        db.session.commit()

        # 6. Seed Sample Presensi Hari Ini
        hari_ini = date.today()
        # Presensi Afiq (Gedung A)
        p_a1 = Presensi.query.filter_by(user_id=mhs_a1.id, tanggal=hari_ini, sesi='subuh').first()
        if not p_a1:
            p_a1 = Presensi(
                user_id=mhs_a1.id,
                nim=mhs_a1.nim,
                tanggal=hari_ini,
                waktu=datetime.now(),
                sesi='subuh',
                latitude=-0.9145,
                longitude=100.4607,
                accuracy=12.5,
                area_absensi_id=area_a.id,
                gedung_id=gedung_a.id,
                status='hadir',
                keterangan='Presensi Subuh Asrama Tepat Waktu'
            )
            db.session.add(p_a1)
            print(f"[OK] Sample Presensi Gedung A ({mhs_a1.nama}) dibuat.")
        else:
            p_a1.gedung_id = gedung_a.id
            p_a1.area_absensi_id = area_a.id

        # Presensi Rifqi (Gedung B)
        p_b1 = Presensi.query.filter_by(user_id=mhs_b1.id, tanggal=hari_ini, sesi='subuh').first()
        if not p_b1:
            p_b1 = Presensi(
                user_id=mhs_b1.id,
                nim=mhs_b1.nim,
                tanggal=hari_ini,
                waktu=datetime.now(),
                sesi='subuh',
                latitude=-0.9148,
                longitude=100.4650,
                accuracy=15.0,
                area_absensi_id=area_b.id,
                gedung_id=gedung_b.id,
                status='hadir',
                keterangan='Presensi Subuh Asrama Putra B'
            )
            db.session.add(p_b1)
            print(f"[OK] Sample Presensi Gedung B ({mhs_b1.nama}) dibuat.")
        else:
            p_b1.gedung_id = gedung_b.id
            p_b1.area_absensi_id = area_b.id

        # 7. Seed Sample Izin
        izin_sample = Izin.query.filter_by(user_id=mhs_a1.id).first()
        if not izin_sample:
            izin_sample = Izin(
                user_id=mhs_a1.id,
                tanggal_mulai=hari_ini,
                tanggal_selesai=hari_ini,
                alasan='Izin sakit demam berobat ke klinik kampus',
                status='disetujui',
                disetujui_oleh=fasil_a.id,
                catatan_fasil='Istirahat yang cukup dan minum obat teratur.'
            )
            db.session.add(izin_sample)
            print("[OK] Sample Izin sakit disetujui ditambahkan.")

        db.session.commit()

        print("\n==============================================")
        print(" [OK] SEEDING MULTI-GEDUNG BERHASIL!")
        print("==============================================")
        print(" Akun Uji Coba:")
        print(f" 1. Fasil A    : fasil01 / fasil123  -> Binaan: {gedung_a.nama_gedung}")
        print(f"    Mahasiswa : {mhs_a1.nim} ({mhs_a1.nama}), {mhs_a2.nim} ({mhs_a2.nama})")
        print(f" 2. Fasil B    : fasil02 / fasil123  -> Binaan: {gedung_b.nama_gedung}")
        print(f"    Mahasiswa : {mhs_b1.nim} ({mhs_b1.nama}), {mhs_b2.nim} ({mhs_b2.nama})")
        print(" 3. Admin      : admin / admin123")
        print("==============================================")

if __name__ == '__main__':
    ensure_database()
    seed_database()
