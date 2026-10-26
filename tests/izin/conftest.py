import os
import shutil
import tempfile
import pytest
from datetime import date, time, datetime
from app import create_app
from config import TestingConfig
from app.core.extensions import db
from app.models import (
    User, Gedung, Kamar, SesiPresensi, FasilitatorGedung, Izin, IzinDokumen
)


@pytest.fixture(scope="session")
def app():
    # Setup upload folder sementara untuk test
    temp_upload_dir = tempfile.mkdtemp()
    
    class CustomTestingConfig(TestingConfig):
        IZIN_UPLOAD_FOLDER = os.path.join(temp_upload_dir, "private_izin")
        LOGIN_RATE_LIMIT_ATTEMPTS = 5
        LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60

    app = create_app(CustomTestingConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

    shutil.rmtree(temp_upload_dir, ignore_errors=True)


from app.utils.rate_limiter import login_rate_limiter

@pytest.fixture(scope="function", autouse=True)
def clean_db(app):
    """Membersihkan dan mengisi ulang database sebelum tiap test function."""
    login_rate_limiter._attempts.clear()
    with app.app_context():
        # Kosongkan semua tabel
        IzinDokumen.query.delete()
        Izin.query.delete()
        FasilitatorGedung.query.delete()
        SesiPresensi.query.delete()
        User.query.delete()
        Kamar.query.delete()
        Gedung.query.delete()
        db.session.commit()

        # Seed Master Sesi Presensi
        sesi_pagi = SesiPresensi(kode="subuh", nama="Pagi", jam_mulai=time(5, 0), jam_selesai=time(6, 30))
        sesi_malam = SesiPresensi(kode="malam", nama="Malam", jam_mulai=time(21, 0), jam_selesai=time(22, 30))
        db.session.add_all([sesi_pagi, sesi_malam])

        # Seed Users
        admin = User(nim="admin", nama="Admin Asrama", role="admin")
        admin.set_password("admin123")

        fasil_a = User(nim="fasil01", nama="Fasilitator A", role="fasil")
        fasil_a.set_password("fasil123")

        fasil_b = User(nim="fasil02", nama="Fasilitator B", role="fasil")
        fasil_b.set_password("fasil123")

        db.session.add_all([admin, fasil_a, fasil_b])
        db.session.flush()

        # Seed Gedung & FasilitatorGedung
        gedung_a = Gedung(nama_gedung="Gedung A", user_id=fasil_a.id)
        gedung_b = Gedung(nama_gedung="Gedung B", user_id=fasil_b.id)
        db.session.add_all([gedung_a, gedung_b])
        db.session.flush()

        fg_a = FasilitatorGedung(fasilitator_id=fasil_a.id, gedung_id=gedung_a.id)
        fg_b = FasilitatorGedung(fasilitator_id=fasil_b.id, gedung_id=gedung_b.id)
        db.session.add_all([fg_a, fg_b])

        # Seed Kamar
        kamar_a = Kamar(gedung_id=gedung_a.id, nomor_kamar="101")
        kamar_b = Kamar(gedung_id=gedung_b.id, nomor_kamar="201")
        db.session.add_all([kamar_a, kamar_b])
        db.session.flush()

        # Seed Mahasiswa
        mhs_a = User(nim="mhs01", nama="Mahasiswa Gedung A", role="mahasiswa", kamar_id=kamar_a.id)
        mhs_a.set_password("mhs123")

        mhs_b = User(nim="mhs02", nama="Mahasiswa Gedung B", role="mahasiswa", kamar_id=kamar_b.id)
        mhs_b.set_password("mhs123")

        db.session.add_all([mhs_a, mhs_b])
        db.session.commit()

        yield db


@pytest.fixture
def client(app):
    return app.test_client()


def get_token(client, nim, password):
    res = client.post("/api/auth/login", json={"nim": nim, "password": password})
    assert res.status_code == 200, f"Login gagal untuk {nim}: {res.get_json()}"
    return res.get_json()["data"]["access_token"]


@pytest.fixture
def token_admin(client):
    return get_token(client, "admin", "admin123")


@pytest.fixture
def token_fasil_a(client):
    return get_token(client, "fasil01", "fasil123")


@pytest.fixture
def token_fasil_b(client):
    return get_token(client, "fasil02", "fasil123")


@pytest.fixture
def token_mhs_a(client):
    return get_token(client, "mhs01", "mhs123")


@pytest.fixture
def token_mhs_b(client):
    return get_token(client, "mhs02", "mhs123")
