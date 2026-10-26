from app.utils.rate_limiter import login_rate_limiter


def test_login_sukses_per_role(client):
    # Mahasiswa
    res_mhs = client.post("/api/auth/login", json={"nim": "mhs01", "password": "mhs123"})
    assert res_mhs.status_code == 200
    assert res_mhs.get_json()["data"]["user"]["role"] == "mahasiswa"

    # Fasilitator
    res_fasil = client.post("/api/auth/login", json={"nim": "fasil01", "password": "fasil123"})
    assert res_fasil.status_code == 200
    assert res_fasil.get_json()["data"]["user"]["role"] == "fasil"

    # Admin
    res_adm = client.post("/api/auth/login", json={"nim": "admin", "password": "admin123"})
    assert res_adm.status_code == 200
    assert res_adm.get_json()["data"]["user"]["role"] == "admin"


def test_pesan_error_login_generik(client):
    # Password salah
    res1 = client.post("/api/auth/login", json={"nim": "mhs01", "password": "wrongpassword"})
    assert res1.status_code == 401
    msg1 = res1.get_json()["message"]

    # NIM tidak ada
    res2 = client.post("/api/auth/login", json={"nim": "nonexistent_nim", "password": "anypassword"})
    assert res2.status_code == 401
    msg2 = res2.get_json()["message"]

    # Pesan harus sama persis (tidak membedakan user tidak ada dan password salah)
    assert msg1 == msg2
    assert "NIM atau kata sandi yang Anda masukkan salah." in msg1


def test_rate_limiting_login(client):
    # Bersihkan rate limiter key untuk test client
    login_rate_limiter._attempts.clear()

    # Lakukan 5x gagal
    for _ in range(5):
        res = client.post("/api/auth/login", json={"nim": "mhs01", "password": "salah"})
        assert res.status_code == 401

    # Percobaan ke-6 harus 429 Too Many Requests
    res_block = client.post("/api/auth/login", json={"nim": "mhs01", "password": "salah"})
    assert res_block.status_code == 429
    assert "Terlalu banyak percobaan login" in res_block.get_json()["message"]


def test_auth_me_endpoint(client, token_mhs_a):
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_mhs_a}"})
    assert res.status_code == 200
    assert res.get_json()["data"]["nim"] == "mhs01"
