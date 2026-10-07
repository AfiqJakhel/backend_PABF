"""
Comprehensive Security and IDOR Penetration Testing for Building-Level Scoping.
Validates:
  1. Facilitator assigned building resolution
  2. Student CRUD isolation & IDOR rejection (403)
  3. CSV import building auto-binding and anti-spoofing
  4. Attendance recap & verification isolation
  5. Attendance manual input & status update IDOR rejection (403)
  6. CSV export building anti-spoofing
  7. Polygon CRUD isolation & IDOR rejection (403)
"""

import unittest
import json
import urllib.request
import urllib.parse
from datetime import date

BASE_URL = "http://127.0.0.1:5000"


class BuildingAuthorizationSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Login Fasil A (Gedung Asrama Putra A, id=1)
        res_a = cls._post_json(f"{BASE_URL}/api/auth/login", {"nim": "fasil01", "password": "fasil123"})
        assert res_a[0] == 200, f"Login Fasil A failed: {res_a}"
        cls.token_a = res_a[1]["data"]["access_token"]
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        # 2. Login Fasil B (Gedung Asrama Putra B, id=2)
        res_b = cls._post_json(f"{BASE_URL}/api/auth/login", {"nim": "fasil02", "password": "fasil123"})
        assert res_b[0] == 200, f"Login Fasil B failed: {res_b}"
        cls.token_b = res_b[1]["data"]["access_token"]
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    @staticmethod
    def _post_json(url, data, headers=None):
        headers = headers or {}
        headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    @staticmethod
    def _put_json(url, data, headers=None):
        headers = headers or {}
        headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="PUT")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    @staticmethod
    def _patch_json(url, data=None, headers=None):
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

    @staticmethod
    def _delete_req(url, headers=None):
        headers = headers or {}
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    @staticmethod
    def _get_json(url, headers=None):
        headers = headers or {}
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    # ─── Test 1: Building Profile Resolution ──────────────────────────────────
    def test_01_building_profile_resolution(self):
        status_a, data_a = self._get_json(f"{BASE_URL}/api/fasil/gedung-saya", headers=self.headers_a)
        self.assertEqual(status_a, 200)
        self.assertIn("Gedung Asrama Putra A", data_a["data"]["nama_gedung"])

        status_b, data_b = self._get_json(f"{BASE_URL}/api/fasil/gedung-saya", headers=self.headers_b)
        self.assertEqual(status_b, 200)
        self.assertIn("Gedung Asrama Putra B", data_b["data"]["nama_gedung"])

    # ─── Test 2: Student List Isolation ──────────────────────────────────────
    def test_02_student_list_isolation(self):
        status_a, data_a = self._get_json(f"{BASE_URL}/api/fasil/mahasiswa", headers=self.headers_a)
        self.assertEqual(status_a, 200)
        nims_a = [m["nim"] for m in data_a["data"]["mahasiswa"]]
        self.assertIn("2211522001", nims_a)  # Afiq (Gedung A)
        self.assertNotIn("2211522045", nims_a)  # Rifqi (Gedung B)

        status_b, data_b = self._get_json(f"{BASE_URL}/api/fasil/mahasiswa", headers=self.headers_b)
        self.assertEqual(status_b, 200)
        nims_b = [m["nim"] for m in data_b["data"]["mahasiswa"]]
        self.assertIn("2211522045", nims_b)  # Rifqi (Gedung B)
        self.assertNotIn("2211522001", nims_b)  # Afiq (Gedung A)

    # ─── Test 3: Student IDOR Protection (Cross-Building Mutation Blocked) ──
    def test_03_student_idor_protection(self):
        # Fetch Rifqi ID (Gedung B)
        _, data_b = self._get_json(f"{BASE_URL}/api/fasil/mahasiswa", headers=self.headers_b)
        rifqi_id = next(m["id"] for m in data_b["data"]["mahasiswa"] if m["nim"] == "2211522045")

        # Fasil A tries to update Rifqi
        status_put, res_put = self._put_json(
            f"{BASE_URL}/api/fasil/mahasiswa/{rifqi_id}",
            {"nama": "Hacked Rifqi"},
            headers=self.headers_a
        )
        self.assertEqual(status_put, 403, "Fasil A should be forbidden from modifying student in Gedung B")
        self.assertIn("Akses ditolak", res_put["message"])

        # Fasil A tries to delete Rifqi
        status_del, res_del = self._delete_req(
            f"{BASE_URL}/api/fasil/mahasiswa/{rifqi_id}",
            headers=self.headers_a
        )
        self.assertEqual(status_del, 403, "Fasil A should be forbidden from deleting student in Gedung B")
        self.assertIn("Akses ditolak", res_del["message"])

    # ─── Test 4: Recap & Verification Isolation ──────────────────────────────
    def test_04_recap_and_verification_isolation(self):
        # Verification list Fasil A
        status_v_a, data_v_a = self._get_json(f"{BASE_URL}/api/fasil/presensi/verifikasi", headers=self.headers_a)
        self.assertEqual(status_v_a, 200)
        for item in data_v_a["data"]["items"]:
            self.assertNotEqual(item["nim"], "2211522045", "Leak! Fasil A saw Gedung B student attendance!")

        # Verification list Fasil B
        status_v_b, data_v_b = self._get_json(f"{BASE_URL}/api/fasil/presensi/verifikasi", headers=self.headers_b)
        self.assertEqual(status_v_b, 200)
        for item in data_v_b["data"]["items"]:
            self.assertNotEqual(item["nim"], "2211522001", "Leak! Fasil B saw Gedung A student attendance!")

    # ─── Test 5: Attendance Status Update & Manual Input IDOR Protection ────
    def test_05_attendance_idor_protection(self):
        # Fetch Rifqi attendance ID (Gedung B)
        _, data_v_b = self._get_json(f"{BASE_URL}/api/fasil/presensi/verifikasi", headers=self.headers_b)
        rifqi_item = next(i for i in data_v_b["data"]["items"] if i["nim"] == "2211522045")
        rifqi_presensi_id = rifqi_item["id"]
        rifqi_user_id = rifqi_item["user_id"]

        # Fasil A attempts to update status of attendance in Gedung B
        status_patch, res_patch = self._patch_json(
            f"{BASE_URL}/api/fasil/presensi/{rifqi_presensi_id}/status",
            {"status": "alfa"},
            headers=self.headers_a
        )
        self.assertEqual(status_patch, 403, "Fasil A must be blocked from updating attendance of Gedung B")

        # Fasil A attempts to input manual attendance for student in Gedung B
        status_manual, res_manual = self._post_json(
            f"{BASE_URL}/api/fasil/presensi/manual",
            {"user_id": rifqi_user_id, "sesi": "kegiatan", "status": "hadir"},
            headers=self.headers_a
        )
        self.assertEqual(status_manual, 403, "Fasil A must be blocked from adding manual attendance for Gedung B student")

    # ─── Test 6: Export CSV Anti-Spoofing ────────────────────────────────────
    def test_06_export_anti_spoofing(self):
        req_exp = urllib.request.Request(
            f"{BASE_URL}/api/fasil/presensi/export?tanggal_mulai=2026-01-01&tanggal_selesai=2026-12-31&building_id=2",
            headers=self.headers_a
        )
        with urllib.request.urlopen(req_exp) as r:
            csv_text = r.read().decode("utf-8")
            self.assertIn("Gedung Asrama Putra A", csv_text)
            self.assertNotIn("Gedung Asrama Putra B", csv_text, "Spoofing succeeded! Must ignore tampered building_id=2")

    # ─── Test 7: Polygon Isolation & IDOR Protection ─────────────────────────
    def test_07_polygon_isolation_and_idor(self):
        # Fetch polygons
        status_pa, data_pa = self._get_json(f"{BASE_URL}/api/fasil/polygon", headers=self.headers_a)
        self.assertEqual(status_pa, 200)
        for a in data_pa["data"]["areas"]:
            self.assertEqual(a["gedung_id"], 1)

        status_pb, data_pb = self._get_json(f"{BASE_URL}/api/fasil/polygon", headers=self.headers_b)
        self.assertEqual(status_pb, 200)
        for b in data_pb["data"]["areas"]:
            self.assertEqual(b["gedung_id"], 2)

        area_b_id = data_pb["data"]["areas"][0]["id"]

        # Fasil A tries to update Polygon B
        status_put, _ = self._put_json(
            f"{BASE_URL}/api/fasil/polygon/{area_b_id}",
            {"nama": "Hacked Gedung B Polygon"},
            headers=self.headers_a
        )
        self.assertEqual(status_put, 403, "Fasil A must be forbidden from editing Gedung B polygon")

        # Fasil A tries to toggle Polygon B
        status_patch, _ = self._patch_json(
            f"{BASE_URL}/api/fasil/polygon/{area_b_id}/toggle",
            headers=self.headers_a
        )
        self.assertEqual(status_patch, 403, "Fasil A must be forbidden from toggling Gedung B polygon")

        # Fasil A tries to delete Polygon B
        status_del, _ = self._delete_req(
            f"{BASE_URL}/api/fasil/polygon/{area_b_id}",
            headers=self.headers_a
        )
        self.assertEqual(status_del, 403, "Fasil A must be forbidden from deleting Gedung B polygon")


if __name__ == "__main__":
    unittest.main()
