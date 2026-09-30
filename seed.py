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

        fasil = User.query.filter_by(nim='fasil01').first()
        if not fasil:
            fasil = User(
                nim='fasil01',
                nama='Ust. Hendra (Fasilitator)',
                role='fasil',
                asal='Padang',
                jekel='L',
                email='fasil.hendra@asrama.ac.id'
            )
            fasil.set_password('fasil123')
            db.session.add(fasil)
            db.session.flush()
            print("[OK] User Fasil dibuat (fasil01 / fasil123)")
        else:
            fasil.set_password('fasil123')

        # 2. Seed Gedung
        gedung_a = Gedung.query.filter_by(nama_gedung='Gedung Asrama Putra A').first()
        if not gedung_a:
            gedung_a = Gedung(
                nama_gedung='Gedung Asrama Putra A',
                user_id=fasil.id
            )
            db.session.add(gedung_a)
            db.session.flush()
            print(f"[OK] Gedung '{gedung_a.nama_gedung}' dibuat (Fasil: {fasil.nama})")
        else:
            gedung_a.user_id = fasil.id

        # 3. Seed Kamar
        kamar_204 = Kamar.query.filter_by(gedung_id=gedung_a.id, nomor_kamar='204').first()
        if not kamar_204:
            kamar_204 = Kamar(
                gedung_id=gedung_a.id,
                nomor_kamar='204',
                lantai=2
            )
            db.session.add(kamar_204)
            db.session.flush()
            print(f"[OK] Kamar 204 Lantai 2 di {gedung_a.nama_gedung} dibuat")

        # 4. Seed Mahasiswa
        mhs = User.query.filter_by(nim='2211522001').first()
        if not mhs:
            mhs = User(
                nim='2211522001',
                nama='Muhammad Afiq',
                role='mahasiswa',
                asal='Bukittinggi',
                jekel='L',
                email='afiq@student.unand.ac.id',
                kamar_id=kamar_204.id
            )
            mhs.set_password('password123')
            db.session.add(mhs)
            db.session.flush()
            print("[OK] Mahasiswa Afiq dibuat (2211522001 / password123)")
        else:
            mhs.set_password('password123')
            mhs.kamar_id = kamar_204.id
            mhs.asal = 'Bukittinggi'
            mhs.jekel = 'L'

        db.session.commit()

        # 5. Seed Sample Presensi Hari Ini
        hari_ini = date.today()
        presensi_subuh = Presensi.query.filter_by(user_id=mhs.id, tanggal=hari_ini, sesi='subuh').first()
        if not presensi_subuh:
            presensi_subuh = Presensi(
                user_id=mhs.id,
                nim=mhs.nim,
                tanggal=hari_ini,
                waktu=datetime.now(),
                sesi='subuh',
                latitude=-0.9145,
                longitude=100.4607,
                status='hadir',
                keterangan='Presensi Subuh Asrama Tepat Waktu'
            )
            db.session.add(presensi_subuh)
            print("[OK] Sample Presensi Subuh hari ini ditambahkan.")

        # 6. Seed Sample Izin
        izin_sample = Izin.query.filter_by(user_id=mhs.id).first()
        if not izin_sample:
            izin_sample = Izin(
                user_id=mhs.id,
                tanggal_mulai=hari_ini,
                tanggal_selesai=hari_ini,
                alasan='Izin sakit demam berobat ke klinik kampus',
                status='disetujui',
                disetujui_oleh=fasil.id,
                catatan_fasil='Istirahat yang cukup dan minum obat teratur.'
            )
            db.session.add(izin_sample)
            print("[OK] Sample Izin sakit disetujui ditambahkan.")

        db.session.commit()

        print("\n==============================================")
        print(" [OK] SEEDING DATABASE RELASIONAL BERHASIL!")
        print("==============================================")
        print(" Akun Uji Coba:")
        print(" 1. Mahasiswa : 2211522001 / password123")
        print("    Kamar     : Gedung Asrama Putra A - Kamar 204")
        print(" 2. Fasil     : fasil01 / fasil123")
        print("    Binaan    : Gedung Asrama Putra A")
        print(" 3. Admin     : admin / admin123")
        print("==============================================")

if __name__ == '__main__':
    ensure_database()
    seed_database()
