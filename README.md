# Backend API - Absensi Asrama

Ini adalah backend service untuk proyek **Absensi Asrama**, dibangun menggunakan **Flask** (Python) dengan **MySQL** sebagai database utama. Proyek ini menggunakan `Flask-SQLAlchemy` untuk ORM, `Flask-Migrate` untuk manajemen migrasi database, dan `Flask-JWT-Extended` untuk autentikasi.

## Prasyarat

Sebelum menjalankan proyek ini, pastikan Anda telah menginstal:
- [Python 3.x](https://www.python.org/downloads/)
- [MySQL Server](https://dev.mysql.com/downloads/mysql/) atau [XAMPP](https://www.apachefriends.org/) (untuk MariaDB/MySQL)
- Pip (Python Package Installer)

## Cara Instalasi dan Setup

### 1. Setup Database
Pastikan server MySQL berjalan. Buat database baru untuk aplikasi ini:
```sql
CREATE DATABASE pabf;
```

### 2. Setup Virtual Environment (Disarankan)
Buka terminal/command prompt di dalam folder `backend` ini, lalu buat dan aktifkan *virtual environment*:

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalasi Dependencies
Instal semua package yang dibutuhkan yang ada di file `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Environment Variables
Aplikasi menggunakan file `.env` untuk konfigurasi. File `.env` sudah ada di folder ini dengan konfigurasi default:
```env
# Database
DB_USERNAME=username
DB_PASSWORD=password
DB_HOST=hostname
DB_PORT=port
DB_NAME=nama_database

# JWT Secret Key
JWT_SECRET_KEY=super-secret-key-for-development

# Upload Folder
UPLOAD_FOLDER=uploads
```
*Catatan: Sesuaikan `DB_USERNAME` dan `DB_PASSWORD` dengan konfigurasi MySQL di komputer Anda.*

### 5. Menjalankan Migrasi Database & Seeder
Database dikelola menggunakan **Flask-Migrate** (Alembic). Jalankan perintah berikut untuk memastikan struktur tabel terbaru diaplikasikan ke database MySQL:

```bash
flask db upgrade
```

Setelah struktur tabel terbentuk, jalankan script `seed.py` untuk mengisi data akun awal untuk keperluan pengujian:
```bash
python seed.py
```

**Akun Demo Bawaan:**
- **Mahasiswa:** NIM: `2211522001`, Kata Sandi: `password123`
- **Admin:** NIM: `admin`, Kata Sandi: `admin123`

---

## Panduan Migrasi Database (Flask-Migrate)

Gunakan alur migrasi ini setiap kali Anda **menambah tabel baru** atau **mengubah kolom** pada database:

### 1. Menambahkan Model / Mengubah Kolom
1. Tambahkan model baru di dalam folder `app/models/` (misal: `app/models/absensi.py`).
2. Pastikan model baru tersebut di-import ke dalam `app/models/__init__.py` agar terbaca oleh Flask-Migrate.

### 2. Membuat Skrip Migrasi Otomatis
Jalankan perintah ini di terminal untuk mendeteksi perubahan model dan membuat file migrasi baru:
```bash
flask db migrate -m "deskripsi perubahan, misal: membuat tabel absensi"
```
File migrasi baru akan otomatis terbuat di folder `migrations/versions/`.

### 3. Menerapkan Perubahan ke Database
Jalankan perintah ini untuk mengeksekusi perubahan DDL (`CREATE TABLE`, `ALTER TABLE`) ke database MySQL:
```bash
flask db upgrade
```

### 4. Membatalkan Perubahan (Rollback)
Jika ada kesalahan pada migrasi terakhir dan Anda ingin mengembalikannya:
```bash
flask db downgrade
```

---

## Menjalankan Aplikasi (Development)

Setelah semua setup selesai, Anda dapat menjalankan server backend dengan perintah:
```bash
python run.py
```
atau:
```bash
flask run
```

Server backend akan berjalan di `http://127.0.0.1:5000/`.

---

## Struktur Direktori Utama

- `app/` : Berisi kode utama aplikasi (models, routes, auth, core, dll).
  - `models/` : Model database SQLAlchemy (`user.py`, dll).
  - `routes/` : Endpoint API Flask (`auth_routes.py`, dll).
  - `core/` : Ekstensi aplikasi (`extensions.py` untuk db, jwt, migrate, cors).
- `migrations/` : Riwayat version control skema database (Alembic / Flask-Migrate).
  - `versions/` : File-file revisi migrasi yang dijalankan ke database.
- `uploads/` : Folder tempat menyimpan file hasil upload.
- `venv/` : Virtual environment Python.
- `.env` : File konfigurasi kredensial dan variabel environment.
- `config.py` : Pengaturan konfigurasi aplikasi Flask.
- `requirements.txt` : Daftar semua dependensi library Python.
- `run.py` : Entry point untuk menjalankan aplikasi Flask (Development).
- `seed.py` : Script inisialisasi database dan akun awal.
- `wsgi.py` : Entry point untuk menjalankan aplikasi via WSGI server (Production).
