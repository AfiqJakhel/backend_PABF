# Panduan Lengkap Migrasi Database (Flask-Migrate & Alembic)

Dokumen ini menjelaskan alur kerja, perintah dasar, dan panduan langkah demi langkah untuk mengelola perubahan skema database MySQL pada proyek backend PABF menggunakan **Flask-Migrate** (Alembic).

---

## 1. Konsep Dasar

**Flask-Migrate** bertindak seperti *Git untuk Database*:
* **Model Python (`app/models/`)** adalah *Desired State* (skema yang kita inginkan).
* **Database MySQL** adalah *Current State* (skema fisik yang ada di database saat ini).
* **File Migrasi (`migrations/versions/`)** adalah *Commit* (catatan perubahan langkah demi langkah dari satu versi ke versi berikutnya).

---

## 2. Persiapan Sebelum Menjalankan Perintah

Sebelum menjalankan perintah migrasi, **selalu pastikan**:
1. Berada di direktori `backend/`:
   ```bash
   cd backend
   ```
2. **Virtual Environment (`venv`) sudah aktif**:
   * Windows (PowerShell / CMD):
     ```bash
     venv\Scripts\activate
     ```
   * Jika aktif, terminal akan memiliki tanda `(venv)` di sebelah kiri.
3. Database MySQL lokal (XAMPP / MySQL Service) sudah **running**.

---

## 3. Perintah Utama Flask-Migrate

| Perintah | Deskripsi |
| :--- | :--- |
| `flask db migrate -m "pesan"` | Membandingkan model dengan DB dan membuat file migrasi baru di `migrations/versions/`. |
| `flask db upgrade` | Mengeksekusi file migrasi ke database (menerapkan perubahan). |
| `flask db downgrade` | Membatalkan migrasi terakhir (kembali 1 versi ke belakang). |
| `flask db current` | Menampilkan ID revisi migrasi yang saat ini aktif di database. |
| `flask db history` | Melihat seluruh riwayat perubahan migrasi dari awal sampai akhir. |
| `flask db show <id>` | Melihat detail isi instruksi dari suatu revisi migrasi. |

---

## 4. Alur Kerja Standar (Workflow) Saat Mengubah Database

Ikuti 5 langkah ini setiap kali Anda ingin **menambah tabel baru**, **menambah kolom**, atau **mengubah tipe data**:

### Langkah 1: Ubah / Buat Model di `app/models/`
Contoh: Anda menambahkan kolom baru `no_telepon` pada model `User`:
```python
# app/models/user.py
class User(db.Model):
    # ...
    no_telepon = db.Column(db.String(15), nullable=True)
```

### Langkah 2: Pastikan Model Terdaftar
Jika membuat file model baru (misal `jadwal.py`), daftarkan di [`app/models/__init__.py`](app/models/__init__.py):
```python
from .user import User
from .gedung import Gedung
from .kamar import Kamar
from .presensi import Presensi
from .izin import Izin
from .jadwal import Jadwal  # <--- Import model baru
```

### Langkah 3: Generate File Migrasi
Jalankan perintah:
```bash
flask db migrate -m "tambah kolom no_telepon di users"
```
Alembic akan membuat file baru di `migrations/versions/<hash>_tambah_kolom_no_telepon_di_users.py`.

### Langkah 4: Periksa File Migrasi
Buka file yang baru saja digenerate di folder `migrations/versions/`. Pastikan fungsi `upgrade()` dan `downgrade()` sudah mencerminkan perubahan yang Anda inginkan.

### Langkah 5: Terapkan ke Database
Jalankan:
```bash
flask db upgrade
```
Struktur tabel fisik di MySQL Anda sekarang sudah diperbarui secara otomatis tanpa kehilangan data lama!

---

## 5. Troubleshooting & Hal Penting yang Perlu Diperhatikan

### A. Muncul Pesan `No changes in schema detected`
* **Penyebab**: Perintah `flask db migrate` membandingkan Model Python dengan Database MySQL saat ini. Jika Anda sudah membuat tabel secara manual di MySQL atau menjalankan `db.create_all()`, Alembic melihat database dan model sudah sama persis, sehingga tidak membuat file migrasi.
* **Solusi**: Jangan pernah membuat tabel manual jika ingin menggunakan migrasi. Buat file model terlebih dahulu, lalu selalu gunakan alur `flask db migrate` -> `flask db upgrade`.

### B. Circular Dependency pada Foreign Key
Jika tabel A berelasi dengan tabel B dan tabel B juga berelasi dengan tabel A (contoh: `Gedung` punya `user_id` Fasil, dan `User` punya `kamar_id` yang ada di `Gedung`):
* Gunakan parameter `use_alter=True` dan berikan nama constraint pada salah satu ForeignKey agar Alembic tidak bingung saat menentukan urutan pembuatan tabel:
  ```python
  user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL', use_alter=True, name='fk_gedung_user_id'), nullable=True)
  ```

### C. Cara Melakukan Rollback / Batalkan Perubahan
Jika migrasi terakhir bermasalah dan Anda ingin membatalkannya:
```bash
flask db downgrade
```
Ini akan mengembalikan database ke satu versi sebelumnya. File migrasi di `migrations/versions/` bisa Anda hapus atau edit sebelum melakukan migrasi ulang.

### D. Mengisi Data Uji Coba (Seeding)
Setelah skema database siap dengan `flask db upgrade`, jalankan script seeder untuk memasukkan akun dan data dummy:
```bash
python seed.py
```
Akun yang tersedia:
* **Mahasiswa**: `2211522001` / `password123`
* **Fasilitator**: `fasil01` / `fasil123`
* **Admin**: `admin` / `admin123`
