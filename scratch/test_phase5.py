import urllib.request
import urllib.parse
import json

BASE_URL = "http://127.0.0.1:5000"

def post_json(url, data, headers=None):
    headers = headers or {}
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def patch_json(url, data, headers=None):
    headers = headers or {}
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def get_json(url, headers=None):
    headers = headers or {}
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def test_scoped_presensi():
    # 1. Login Fasil A
    status, res_a = post_json(f"{BASE_URL}/api/auth/login", {"nim": "fasil01", "password": "fasil123"})
    assert status == 200
    token_a = res_a["data"]["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Login Fasil B
    status, res_b = post_json(f"{BASE_URL}/api/auth/login", {"nim": "fasil02", "password": "fasil123"})
    assert status == 200
    token_b = res_b["data"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Test Rekap Sesi Scoping
    import datetime
    today_str = datetime.date.today().isoformat()
    status, sesi_a = get_json(f"{BASE_URL}/api/fasil/presensi/sesi?sesi=subuh&tanggal={today_str}", headers=headers_a)
    print("Fasil A Rekap Sesi Status:", status)
    assert status == 200
    sudah_a_nims = [p["nim"] for p in sesi_a["data"]["sudah_absen"]]
    belum_a_nims = [p["nim"] for p in sesi_a["data"]["belum_absen"]]
    print("Fasil A Sudah Absen:", sudah_a_nims, "Belum Absen:", belum_a_nims)
    # 2211522045 (Rifqi in Gedung B) must NEVER be in either list of Fasil A!
    assert "2211522045" not in sudah_a_nims
    assert "2211522045" not in belum_a_nims

    status, sesi_b = get_json(f"{BASE_URL}/api/fasil/presensi/sesi?sesi=subuh&tanggal={today_str}", headers=headers_b)
    print("Fasil B Rekap Sesi Status:", status)
    assert status == 200
    sudah_b_nims = [p["nim"] for p in sesi_b["data"]["sudah_absen"]]
    belum_b_nims = [p["nim"] for p in sesi_b["data"]["belum_absen"]]
    print("Fasil B Sudah Absen:", sudah_b_nims, "Belum Absen:", belum_b_nims)
    # 2211522001 (Afiq in Gedung A) must NEVER be in either list of Fasil B!
    assert "2211522001" not in sudah_b_nims
    assert "2211522001" not in belum_b_nims

    # 4. Test Verifikasi Scoping
    status, verif_a = get_json(f"{BASE_URL}/api/fasil/presensi/verifikasi", headers=headers_a)
    print("Fasil A Verifikasi Count:", verif_a["data"]["total"])
    assert status == 200
    for item in verif_a["data"]["items"]:
        # Verify no Gedung B items in Fasil A's verifikasi
        assert item["nim"] != "2211522045", "Leak! Fasil A saw Gedung B student attendance!"

    status, verif_b = get_json(f"{BASE_URL}/api/fasil/presensi/verifikasi", headers=headers_b)
    print("Fasil B Verifikasi Count:", verif_b["data"]["total"])
    assert status == 200
    for item in verif_b["data"]["items"]:
        # Verify no Gedung A items in Fasil B's verifikasi
        assert item["nim"] != "2211522001", "Leak! Fasil B saw Gedung A student attendance!"

    # 5. IDOR Test: Fasil A tries to update Presensi of Gedung B student
    # Get Rifqi's attendance ID from Fasil B
    rifqi_item = next(i for i in verif_b["data"]["items"] if i["nim"] == "2211522045")
    rifqi_presensi_id = rifqi_item["id"]

    status_idor, res_idor = patch_json(
        f"{BASE_URL}/api/fasil/presensi/{rifqi_presensi_id}/status",
        {"status": "alfa"},
        headers=headers_a
    )
    print("IDOR Update Presensi Status:", status_idor, res_idor)
    assert status_idor == 403, f"Expected 403 Forbidden, got {status_idor}"

    # 6. IDOR Test: Fasil A tries to input manual presensi for student in Gedung B
    rifqi_user_id = rifqi_item["user_id"]
    status_manual_idor, res_manual_idor = post_json(
        f"{BASE_URL}/api/fasil/presensi/manual",
        {
            "user_id": rifqi_user_id,
            "sesi": "malam",
            "status": "hadir"
        },
        headers=headers_a
    )
    print("IDOR Input Manual Presensi Status:", status_manual_idor, res_manual_idor)
    assert status_manual_idor == 403, f"Expected 403 Forbidden, got {status_manual_idor}"

    # 7. Test Export CSV Anti-Spoofing
    req_exp = urllib.request.Request(
        f"{BASE_URL}/api/fasil/presensi/export?tanggal_mulai=2026-01-01&tanggal_selesai=2026-12-31&building_id=2",
        headers=headers_a
    )
    with urllib.request.urlopen(req_exp) as r:
        csv_text = r.read().decode("utf-8")
        assert "Gedung Asrama Putra A" in csv_text
        assert "Gedung Asrama Putra B" not in csv_text, "Spoofing succeeded! Should have ignored building_id=2"
        print("Export CSV Anti-Spoofing Verified: Tampered building_id=2 was strictly ignored!")

    print("\n==============================================")
    print(" ALL PHASE 5 BACKEND RECAP & IDOR TESTS PASSED!")
    print("==============================================")

if __name__ == '__main__':
    test_scoped_presensi()
