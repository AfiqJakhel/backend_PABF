"""
Final Comprehensive End-to-End Regression Testing.
Simulates real-world workflows for:
  - Facilitator A (Gedung Asrama Putra A)
  - Facilitator B (Gedung Asrama Putra B)
  - Student A (Muhammad Afiq, 2211522001, Gedung A)
  - Student B (Rifqi Pratama, 2211522045, Gedung B)
"""

import unittest
import json
import urllib.request
import urllib.parse
from datetime import date

BASE_URL = "http://127.0.0.1:5000"


class EndToEndBuildingScopeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Login Fasil A
        res_fa = cls._post_json(f"{BASE_URL}/api/auth/login", {"nim": "fasil01", "password": "fasil123"})
        assert res_fa[0] == 200, f"Login Fasil A failed: {res_fa}"
        cls.token_fa = res_fa[1]["data"]["access_token"]
        cls.headers_fa = {"Authorization": f"Bearer {cls.token_fa}"}

        # 2. Login Fasil B
        res_fb = cls._post_json(f"{BASE_URL}/api/auth/login", {"nim": "fasil02", "password": "fasil123"})
        assert res_fb[0] == 200, f"Login Fasil B failed: {res_fb}"
        cls.token_fb = res_fb[1]["data"]["access_token"]
        cls.headers_fb = {"Authorization": f"Bearer {cls.token_fb}"}

        # 3. Login Mahasiswa A (Afiq, Gedung A)
        res_ma = cls._post_json(f"{BASE_URL}/api/auth/login", {"nim": "2211522001", "password": "password123"})
        assert res_ma[0] == 200, f"Login Mahasiswa A failed: {res_ma}"
        cls.token_ma = res_ma[1]["data"]["access_token"]
        cls.headers_ma = {"Authorization": f"Bearer {cls.token_ma}"}

        # 4. Login Mahasiswa B (Rifqi, Gedung B)
        res_mb = cls._post_json(f"{BASE_URL}/api/auth/login", {"nim": "2211522045", "password": "password123"})
        assert res_mb[0] == 200, f"Login Mahasiswa B failed: {res_mb}"
        cls.token_mb = res_mb[1]["data"]["access_token"]
        cls.headers_mb = {"Authorization": f"Bearer {cls.token_mb}"}

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
    def _get_json(url, headers=None):
        headers = headers or {}
        req = urllib.request.Request(url, headers=headers, method="GET")
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
    def _delete_req(url, headers=None):
        headers = headers or {}
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    # ─── 1. Complete Workflow: Fasilitator A ─────────────────────────────────
    def test_workflow_fasil_a(self):
        # a. Profil Gedung
        status, profile = self._get_json(f"{BASE_URL}/api/fasil/gedung-saya", headers=self.headers_fa)
        self.assertEqual(status, 200)
        self.assertEqual(profile["data"]["id"], 1)
        self.assertIn("Gedung Asrama Putra A", profile["data"]["nama_gedung"])

        # b. List Mahasiswa
        status, mhs = self._get_json(f"{BASE_URL}/api/fasil/mahasiswa", headers=self.headers_fa)
        self.assertEqual(status, 200)
        self.assertEqual(mhs["data"]["gedung_id"], 1)
        nims = [m["nim"] for m in mhs["data"]["mahasiswa"]]
        self.assertIn("2211522001", nims)  # Afiq
        self.assertIn("2211521019", nims)  # Fajar
        self.assertNotIn("2211522045", nims)  # Rifqi (in Gedung B)

        # c. List Polygon
        status, poly = self._get_json(f"{BASE_URL}/api/fasil/polygon", headers=self.headers_fa)
        self.assertEqual(status, 200)
        self.assertEqual(poly["data"]["gedung_id"], 1)
        for a in poly["data"]["areas"]:
            self.assertEqual(a["gedung_id"], 1)

        # d. Rekapitulasi Sesi
        today_str = date.today().isoformat()
        status, rekap = self._get_json(f"{BASE_URL}/api/fasil/presensi/sesi?sesi=subuh&tanggal={today_str}", headers=self.headers_fa)
        self.assertEqual(status, 200)
        self.assertEqual(rekap["data"]["gedung_id"], 1)

        # e. Export CSV
        req = urllib.request.Request(f"{BASE_URL}/api/fasil/presensi/export?tanggal_mulai=2026-01-01&tanggal_selesai=2026-12-31", headers=self.headers_fa)
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            self.assertIn("Gedung Asrama Putra A", content)
            self.assertNotIn("Gedung Asrama Putra B", content)

    # ─── 2. Complete Workflow: Fasilitator B ─────────────────────────────────
    def test_workflow_fasil_b(self):
        # a. Profil Gedung
        status, profile = self._get_json(f"{BASE_URL}/api/fasil/gedung-saya", headers=self.headers_fb)
        self.assertEqual(status, 200)
        self.assertEqual(profile["data"]["id"], 2)
        self.assertIn("Gedung Asrama Putra B", profile["data"]["nama_gedung"])

        # b. List Mahasiswa
        status, mhs = self._get_json(f"{BASE_URL}/api/fasil/mahasiswa", headers=self.headers_fb)
        self.assertEqual(status, 200)
        self.assertEqual(mhs["data"]["gedung_id"], 2)
        nims = [m["nim"] for m in mhs["data"]["mahasiswa"]]
        self.assertIn("2211522045", nims)  # Rifqi
        self.assertIn("2211522010", nims)  # Ilham
        self.assertNotIn("2211522001", nims)  # Afiq (in Gedung A)

        # c. List Polygon
        status, poly = self._get_json(f"{BASE_URL}/api/fasil/polygon", headers=self.headers_fb)
        self.assertEqual(status, 200)
        self.assertEqual(poly["data"]["gedung_id"], 2)
        for a in poly["data"]["areas"]:
            self.assertEqual(a["gedung_id"], 2)

        # d. Export CSV
        req = urllib.request.Request(f"{BASE_URL}/api/fasil/presensi/export?tanggal_mulai=2026-01-01&tanggal_selesai=2026-12-31", headers=self.headers_fb)
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            self.assertIn("Gedung Asrama Putra B", content)
            self.assertNotIn("Gedung Asrama Putra A", content)

    # ─── 3. Strict Cross-Building IDOR Isolation ─────────────────────────────
    def test_strict_idor_cross_building(self):
        # Get IDs from Fasil B
        _, mhs_b = self._get_json(f"{BASE_URL}/api/fasil/mahasiswa", headers=self.headers_fb)
        rifqi_id = next(m["id"] for m in mhs_b["data"]["mahasiswa"] if m["nim"] == "2211522045")

        _, poly_b = self._get_json(f"{BASE_URL}/api/fasil/polygon", headers=self.headers_fb)
        poly_b_id = poly_b["data"]["areas"][0]["id"]

        # Fasil A tries to modify student in Gedung B -> 403 Forbidden
        status_put, _ = self._put_json(
            f"{BASE_URL}/api/fasil/mahasiswa/{rifqi_id}",
            {"nama": "Illegal Edit"},
            headers=self.headers_fa
        )
        self.assertEqual(status_put, 403)

        # Fasil A tries to delete student in Gedung B -> 403 Forbidden
        status_del, _ = self._delete_req(
            f"{BASE_URL}/api/fasil/mahasiswa/{rifqi_id}",
            headers=self.headers_fa
        )
        self.assertEqual(status_del, 403)

        # Fasil A tries to modify polygon of Gedung B -> 403 Forbidden
        status_poly_put, _ = self._put_json(
            f"{BASE_URL}/api/fasil/polygon/{poly_b_id}",
            {"nama": "Illegal Polygon Edit"},
            headers=self.headers_fa
        )
        self.assertEqual(status_poly_put, 403)

        # Fasil A tries to delete polygon of Gedung B -> 403 Forbidden
        status_poly_del, _ = self._delete_req(
            f"{BASE_URL}/api/fasil/polygon/{poly_b_id}",
            headers=self.headers_fa
        )
        self.assertEqual(status_poly_del, 403)


if __name__ == "__main__":
    unittest.main()
