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
CREATE DATABASE absensi_asrama;
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

### 5. Migrasi Database (Opsional/Jika Diperlukan)
Jika terdapat pembaruan skema database (menggunakan Flask-Migrate), Anda bisa menjalankan migrasi dengan cara:
```bash
flask db upgrade
```
*Catatan: Pastikan Anda berada dalam virtual environment yang aktif.*

## Menjalankan Aplikasi

Setelah semua setup selesai, Anda dapat menjalankan server backend dengan perintah:
```bash
python run.py
```
atau (jika Anda ingin menggunakan perintah flask secara langsung):
```bash
flask run
```

Server akan berjalan secara default di `http://127.0.0.1:5000/`.

## Struktur Direktori Utama

- `app/` : Berisi kode utama aplikasi (models, routes, auth, dll).
- `uploads/` : Folder tempat menyimpan file hasil upload.
- `venv/` : Virtual environment Python.
- `.env` : File konfigurasi kredensial dan variabel environment.
- `config.py` : Pengaturan konfigurasi aplikasi Flask.
- `requirements.txt` : Daftar semua dependensi library Python.
- `run.py` : Entry point untuk menjalankan aplikasi Flask.
