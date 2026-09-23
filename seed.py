import os
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

def seed_users():
    """Buat tabel dan isi user awal untuk pengujian."""
    from app import create_app
    from app.core.extensions import db
    from app.models.user import User

    app = create_app()
    with app.app_context():
        # Buat tabel jika belum ada
        print("[*] Membuat tabel-tabel di database jika belum ada...")
        db.create_all()
        print("[OK] Tabel berhasil diperiksa/dibuat.")

        # Data user awal
        initial_users = [
            {
                "nim": "2211522001",
                "nama": "Afiq (Mahasiswa)",
                "role": "mahasiswa",
                "kamar": "Gedung A - Kamar 204",
                "password": "password123"
            },
            {
                "nim": "admin",
                "nama": "Administrator Asrama",
                "role": "admin",
                "kamar": None,
                "password": "admin123"
            }
        ]

        for user_data in initial_users:
            existing = User.query.filter_by(nim=user_data['nim']).first()
            if not existing:
                u = User(
                    nim=user_data['nim'],
                    nama=user_data['nama'],
                    role=user_data['role'],
                    kamar=user_data['kamar']
                )
                u.set_password(user_data['password'])
                db.session.add(u)
                print(f"[OK] Menambahkan user: {user_data['nim']} ({user_data['role']})")
            else:
                # Update password jika diperlukan agar selalu sinkron saat re-seed
                existing.set_password(user_data['password'])
                existing.nama = user_data['nama']
                existing.role = user_data['role']
                existing.kamar = user_data['kamar']
                print(f"[i] User {user_data['nim']} sudah ada, memperbarui data & password.")

        db.session.commit()
        print("\n=== Data Akun Uji Coba Tersedia ===")
        print("1. Mahasiswa:")
        print("   NIM      : 2211522001")
        print("   Password : password123")
        print("2. Admin:")
        print("   NIM      : admin")
        print("   Password : admin123")
        print("====================================")

if __name__ == '__main__':
    ensure_database()
    seed_users()
