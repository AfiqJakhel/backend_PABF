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

def put_json(url, data, headers=None):
    headers = headers or {}
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def patch_json(url, data=None, headers=None):
    headers = headers or {}
    data_bytes = json.dumps(data).encode("utf-8") if data else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method="PATCH")
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

def get_json(url, headers=None):
    headers = headers or {}
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def test_scoped_polygon():
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

    # 3. Get Polygon Fasil A
    status, poly_a = get_json(f"{BASE_URL}/api/fasil/polygon", headers=headers_a)
    print("Fasil A Polygon Status:", status)
    assert status == 200
    areas_a = poly_a["data"]["areas"]
    print(f"Fasil A has {len(areas_a)} polygon(s): {[a['nama'] for a in areas_a]}")
    for a in areas_a:
        assert a["gedung_id"] == 1

    # 4. Get Polygon Fasil B
    status, poly_b = get_json(f"{BASE_URL}/api/fasil/polygon", headers=headers_b)
    print("Fasil B Polygon Status:", status)
    assert status == 200
    areas_b = poly_b["data"]["areas"]
    print(f"Fasil B has {len(areas_b)} polygon(s): {[b['nama'] for b in areas_b]}")
    for b in areas_b:
        assert b["gedung_id"] == 2

    area_b_id = areas_b[0]["id"]

    # 5. IDOR Test: Fasil A attempts to update Polygon of Gedung B
    status_put, res_put = put_json(
        f"{BASE_URL}/api/fasil/polygon/{area_b_id}",
        {"nama": "Hacked Gedung B"},
        headers=headers_a
    )
    print("IDOR PUT Polygon Status:", status_put, res_put)
    assert status_put == 403, f"Expected 403 Forbidden on IDOR PUT, got {status_put}"

    # 6. IDOR Test: Fasil A attempts to toggle active Polygon of Gedung B
    status_patch, res_patch = patch_json(
        f"{BASE_URL}/api/fasil/polygon/{area_b_id}/toggle",
        headers=headers_a
    )
    print("IDOR PATCH Toggle Polygon Status:", status_patch, res_patch)
    assert status_patch == 403, f"Expected 403 Forbidden on IDOR PATCH, got {status_patch}"

    # 7. IDOR Test: Fasil A attempts to delete Polygon of Gedung B
    status_del, res_del = delete_req(
        f"{BASE_URL}/api/fasil/polygon/{area_b_id}",
        headers=headers_a
    )
    print("IDOR DELETE Polygon Status:", status_del, res_del)
    assert status_del == 403, f"Expected 403 Forbidden on IDOR DELETE, got {status_del}"

    print("\n==============================================")
    print(" ALL PHASE 6 POLYGON SCOPE & IDOR TESTS PASSED!")
    print("==============================================")

if __name__ == '__main__':
    test_scoped_polygon()
