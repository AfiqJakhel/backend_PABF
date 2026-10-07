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

def get_json(url, headers=None):
    headers = headers or {}
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def put_json(url, data, headers=None):
    headers = headers or {}
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def delete_req(url, headers=None):
    headers = headers or {}
    req = urllib.request.Request(url, headers=headers, method="DELETE")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def post_multipart(url, file_content, filename, headers=None):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    headers = headers or {}
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
        f"{file_content}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def test_scoped_mahasiswa():
    # 1. Login Fasil A
    status, res_a = post_json(f"{BASE_URL}/api/auth/login", {"nim": "fasil01", "password": "fasil123"})
    assert status == 200, f"Login Fasil A failed: {res_a}"
    token_a = res_a["data"]["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Login Fasil B
    status, res_b = post_json(f"{BASE_URL}/api/auth/login", {"nim": "fasil02", "password": "fasil123"})
    assert status == 200, f"Login Fasil B failed: {res_b}"
    token_b = res_b["data"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Check Gedung Saya Fasil A
    status, gedung_a = get_json(f"{BASE_URL}/api/fasil/gedung-saya", headers=headers_a)
    print("Fasil A Gedung:", gedung_a["data"]["nama_gedung"])
    assert "Gedung Asrama Putra A" in gedung_a["data"]["nama_gedung"]

    # Check Gedung Saya Fasil B
    status, gedung_b = get_json(f"{BASE_URL}/api/fasil/gedung-saya", headers=headers_b)
    print("Fasil B Gedung:", gedung_b["data"]["nama_gedung"])
    assert "Gedung Asrama Putra B" in gedung_b["data"]["nama_gedung"]

    # List Mahasiswa Fasil A
    status, mhs_a = get_json(f"{BASE_URL}/api/fasil/mahasiswa", headers=headers_a)
    nims_a = [m["nim"] for m in mhs_a["data"]["mahasiswa"]]
    print("Fasil A Mahasiswa NIMs:", nims_a)
    assert "2211522001" in nims_a  # Afiq
    assert "2211521019" in nims_a  # Fajar
    assert "2211522045" not in nims_a  # Rifqi is in Gedung B!

    # List Mahasiswa Fasil B
    status, mhs_b = get_json(f"{BASE_URL}/api/fasil/mahasiswa", headers=headers_b)
    nims_b = [m["nim"] for m in mhs_b["data"]["mahasiswa"]]
    print("Fasil B Mahasiswa NIMs:", nims_b)
    assert "2211522045" in nims_b  # Rifqi
    assert "2211522010" in nims_b  # Ilham
    assert "2211522001" not in nims_b  # Afiq is in Gedung A!

    # IDOR Test: Fasil A attempts to update Rifqi (Gedung B)
    rifqi_id = next(m["id"] for m in mhs_b["data"]["mahasiswa"] if m["nim"] == "2211522045")
    status_put, idor_put = put_json(
        f"{BASE_URL}/api/fasil/mahasiswa/{rifqi_id}",
        {"nama": "Rifqi Hack"},
        headers=headers_a
    )
    print("IDOR PUT status:", status_put, idor_put)
    assert status_put == 403, f"Expected 403 Forbidden on IDOR PUT, got {status_put}"

    # IDOR Test: Fasil A attempts to delete Rifqi (Gedung B)
    status_del, idor_del = delete_req(
        f"{BASE_URL}/api/fasil/mahasiswa/{rifqi_id}",
        headers=headers_a
    )
    print("IDOR DELETE status:", status_del, idor_del)
    assert status_del == 403, f"Expected 403 Forbidden on IDOR DELETE, got {status_del}"

    # Test Download Template CSV
    req_t = urllib.request.Request(f"{BASE_URL}/api/fasil/mahasiswa/template-csv", headers=headers_a)
    with urllib.request.urlopen(req_t) as r:
        template_text = r.read().decode("utf-8")
        assert "nim,nama" in template_text
        print("Template CSV OK, length:", len(template_text))

    # Test CSV Import
    csv_content = "nim,nama,nomor_kamar,lantai,jekel,asal\n2211529901,Budi Santoso,205,2,L,Bukittinggi\n"
    status_imp, res_import = post_multipart(
        f"{BASE_URL}/api/fasil/mahasiswa/import-csv",
        csv_content,
        "test.csv",
        headers=headers_a
    )
    print("Import CSV status:", status_imp, res_import)
    assert status_imp == 200
    assert res_import["data"]["berhasil_dibuat"] >= 1

    # Verify Budi Santoso is in Fasil A's list
    status, mhs_a_updated = get_json(f"{BASE_URL}/api/fasil/mahasiswa", headers=headers_a)
    updated_nims = [m["nim"] for m in mhs_a_updated["data"]["mahasiswa"]]
    assert "2211529901" in updated_nims
    print("Imported student confirmed in Gedung A!")

    print("\n==============================================")
    print(" ALL PHASE 4 BACKEND & IDOR TESTS PASSED!")
    print("==============================================")

if __name__ == '__main__':
    test_scoped_mahasiswa()
