import io
from datetime import date, timedelta
from app.services.izin_service import IzinService
from app.models.sesi_presensi import SesiPresensi


def _create_fake_jpg(content=b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xFF\xDB"):
    return (io.BytesIO(content), "surat_dokter.jpg")


def _create_fake_pdf(content=b"%PDF-1.4\n%testpdfcontent\n%%EOF"):
    return (io.BytesIO(content), "surat_izin.pdf")


def test_pengajuan_izin_full_dan_half(client, token_mhs_a):
    headers = {"Authorization": f"Bearer {token_mhs_a}"}
    today = date.today()

    # 1. Full day TANPA dokumen -> wajib gagal 422
    res_no_doc = client.post("/api/izin", headers=headers, data={
        "jenis": "full",
        "tanggal_mulai": today.isoformat(),
        "tanggal_selesai": (today + timedelta(days=2)).isoformat(),
        "keterangan": "Izin pulang kampung keperluan keluarga"
    })
    assert res_no_doc.status_code == 422
    assert "Dokumen bukti wajib diunggah" in str(res_no_doc.get_json())

    # 2. Full day DENGAN dokumen valid -> sukses 201
    file_stream, filename = _create_fake_jpg()
    res_full = client.post("/api/izin", headers=headers, data={
        "jenis": "full",
        "tanggal_mulai": today.isoformat(),
        "tanggal_selesai": (today + timedelta(days=2)).isoformat(),
        "keterangan": "Izin pulang kampung keperluan keluarga",
        "dokumen": (file_stream, filename)
    }, content_type="multipart/form-data")
    assert res_full.status_code == 201
    data_full = res_full.get_json()["data"]
    assert data_full["status"] == "pending"
    assert data_full["has_dokumen"] is True
    assert len(data_full["dokumen"]) == 1


def test_pengajuan_izin_half_day(client, token_mhs_b):
    headers = {"Authorization": f"Bearer {token_mhs_b}"}
    today = date.today()

    sesi = SesiPresensi.query.filter_by(kode="subuh").first()
    assert sesi is not None

    # Half day tanpa sesi_id -> 422
    res_no_sesi = client.post("/api/izin", headers=headers, data={
        "jenis": "half",
        "tanggal_mulai": today.isoformat(),
        "keterangan": "Izin tidak ikut subuh karena sakit ringan"
    })
    assert res_no_sesi.status_code == 422

    # Half day dengan sesi_id dan TANPA dokumen -> sukses 201 (dokumen opsional)
    res_half = client.post("/api/izin", headers=headers, data={
        "jenis": "half",
        "tanggal_mulai": today.isoformat(),
        "sesi_id": sesi.id,
        "keterangan": "Izin tidak ikut subuh karena sakit ringan"
    })
    assert res_half.status_code == 201
    data_half = res_half.get_json()["data"]
    assert data_half["jenis"] == "half"
    assert data_half["tanggal_selesai"] == today.isoformat()
    assert data_half["has_dokumen"] is False


def test_overlap_izin_aktif_ditolak(client, token_mhs_a):
    headers = {"Authorization": f"Bearer {token_mhs_a}"}
    today = date.today()

    # Buat izin 1: hari ini s.d. lusa
    file_stream, filename = _create_fake_jpg()
    res1 = client.post("/api/izin", headers=headers, data={
        "jenis": "full",
        "tanggal_mulai": today.isoformat(),
        "tanggal_selesai": (today + timedelta(days=2)).isoformat(),
        "keterangan": "Izin sakit istirahat di rumah",
        "dokumen": (file_stream, filename)
    })
    assert res1.status_code == 201

    # Coba ajukan izin 2 yang tumpang tindih (besok s.d. 3 hari lagi) -> Wajib 409
    file_stream2, filename2 = _create_fake_jpg()
    res2 = client.post("/api/izin", headers=headers, data={
        "jenis": "full",
        "tanggal_mulai": (today + timedelta(days=1)).isoformat(),
        "tanggal_selesai": (today + timedelta(days=3)).isoformat(),
        "keterangan": "Izin urusan lain yang tumpang tindih",
        "dokumen": (file_stream2, filename2)
    })
    assert res2.status_code == 409
    assert "tumpang tindih" in res2.get_json()["message"]


def test_akses_lintas_gedung_fasilitator_ditolak_404(client, token_mhs_b, token_fasil_a, token_fasil_b):
    # Mahasiswa B (Gedung B) mengajukan izin
    today = date.today()
    file_stream, filename = _create_fake_jpg()
    res = client.post("/api/izin", headers={"Authorization": f"Bearer {token_mhs_b}"}, data={
        "jenis": "full",
        "tanggal_mulai": today.isoformat(),
        "tanggal_selesai": today.isoformat(),
        "keterangan": "Izin lomba delegasi kampus",
        "dokumen": (file_stream, filename)
    })
    assert res.status_code == 201
    izin_b_id = res.get_json()["data"]["id"]

    # Fasil A (Gedung A) mencoba melihat detail izin Mahasiswa B -> Wajib 404 (bukan 403)
    res_fasil_a_detail = client.get(f"/api/izin/{izin_b_id}", headers={"Authorization": f"Bearer {token_fasil_a}"})
    assert res_fasil_a_detail.status_code == 404
    assert "tidak ditemukan" in res_fasil_a_detail.get_json()["message"]

    # Fasil A mencoba mereview izin Mahasiswa B -> Wajib 404 (bukan 403)
    res_fasil_a_rev = client.patch(f"/api/izin/{izin_b_id}/review", headers={"Authorization": f"Bearer {token_fasil_a}"}, json={
        "aksi": "approve"
    })
    assert res_fasil_a_rev.status_code == 404

    # Fasil B (Gedung B) berhak mereview izin ini -> Sukses 200
    res_fasil_b_rev = client.patch(f"/api/izin/{izin_b_id}/review", headers={"Authorization": f"Bearer {token_fasil_b}"}, json={
        "aksi": "approve"
    })
    assert res_fasil_b_rev.status_code == 200
    assert res_fasil_b_rev.get_json()["data"]["status"] == "approved"


def test_double_review_atomic(client, token_mhs_b, token_fasil_b):
    today = date.today()
    file_stream, filename = _create_fake_jpg()
    res = client.post("/api/izin", headers={"Authorization": f"Bearer {token_mhs_b}"}, data={
        "jenis": "full",
        "tanggal_mulai": today.isoformat(),
        "tanggal_selesai": today.isoformat(),
        "keterangan": "Izin kegiatan kemahasiswaan",
        "dokumen": (file_stream, filename)
    })
    izin_id = res.get_json()["data"]["id"]

    # Review pertama: Approve
    res_rev1 = client.patch(f"/api/izin/{izin_id}/review", headers={"Authorization": f"Bearer {token_fasil_b}"}, json={
        "aksi": "approve"
    })
    assert res_rev1.status_code == 200

    # Review kedua: Coba reject setelah approved -> Wajib 409 Conflict
    res_rev2 = client.patch(f"/api/izin/{izin_id}/review", headers={"Authorization": f"Bearer {token_fasil_b}"}, json={
        "aksi": "reject",
        "catatan": "Alasan penolakan terlambat"
    })
    assert res_rev2.status_code == 409
    assert "sudah diproses" in res_rev2.get_json()["message"]


def test_mahasiswa_mengakses_izin_dan_dokumen_orang_lain_404(client, token_mhs_a, token_mhs_b):
    today = date.today()
    file_stream, filename = _create_fake_jpg()
    res = client.post("/api/izin", headers={"Authorization": f"Bearer {token_mhs_a}"}, data={
        "jenis": "full",
        "tanggal_mulai": today.isoformat(),
        "tanggal_selesai": today.isoformat(),
        "keterangan": "Izin pribadi mahasiswa A",
        "dokumen": (file_stream, filename)
    })
    izin_a_id = res.get_json()["data"]["id"]

    # Mahasiswa B mencoba melihat detail izin Mahasiswa A -> Wajib 404
    res_detail = client.get(f"/api/izin/{izin_a_id}", headers={"Authorization": f"Bearer {token_mhs_b}"})
    assert res_detail.status_code == 404

    # Mahasiswa B mencoba mengunduh dokumen Mahasiswa A -> Wajib 404
    res_doc = client.get(f"/api/izin/{izin_a_id}/dokumen", headers={"Authorization": f"Bearer {token_mhs_b}"})
    assert res_doc.status_code == 404

    # Mahasiswa B mencoba membatalkan izin Mahasiswa A -> Wajib 404
    res_batal = client.patch(f"/api/izin/{izin_a_id}/batal", headers={"Authorization": f"Bearer {token_mhs_b}"})
    assert res_batal.status_code == 404


def test_upload_file_tidak_valid(client, token_mhs_a):
    headers = {"Authorization": f"Bearer {token_mhs_a}"}
    today = date.today()

    # 1. Ekstensi salah (.exe)
    fake_exe = (io.BytesIO(b"MZ\x90\x00"), "program.exe")
    res1 = client.post("/api/izin", headers=headers, data={
        "jenis": "full",
        "tanggal_mulai": today.isoformat(),
        "tanggal_selesai": today.isoformat(),
        "keterangan": "Coba upload file terlarang",
        "dokumen": fake_exe
    })
    assert res1.status_code == 422
    assert "tidak didukung" in str(res1.get_json())

    # 2. File palsu: Ekstensi .jpg tetapi isi text biasa (magic bytes salah)
    fake_spoofed = (io.BytesIO(b"Hello this is just a plain text file pretending to be image"), "spoof.jpg")
    res2 = client.post("/api/izin", headers=headers, data={
        "jenis": "full",
        "tanggal_mulai": today.isoformat(),
        "tanggal_selesai": today.isoformat(),
        "keterangan": "Coba upload file spoofed",
        "dokumen": fake_spoofed
    })
    assert res2.status_code == 422
    assert "tanda tangan format" in str(res2.get_json())


def test_get_izin_status_untuk_modul_rekap(client, token_mhs_a, token_fasil_a):
    today = date.today()
    file_stream, filename = _create_fake_jpg()

    # Mahasiswa A mengajukan izin
    res = client.post("/api/izin", headers={"Authorization": f"Bearer {token_mhs_a}"}, data={
        "jenis": "full",
        "tanggal_mulai": today.isoformat(),
        "tanggal_selesai": today.isoformat(),
        "keterangan": "Izin sakit flu",
        "dokumen": (file_stream, filename)
    })
    izin_id = res.get_json()["data"]["id"]
    mhs_a_id = res.get_json()["data"]["user_id"]

    # Saat masih pending -> get_izin_status harus None
    assert IzinService.get_izin_status(mhs_a_id, today) is None

    # Fasilitator approve izin
    client.patch(f"/api/izin/{izin_id}/review", headers={"Authorization": f"Bearer {token_fasil_a}"}, json={
        "aksi": "approve"
    })

    # Setelah approved -> get_izin_status harus 'izin'
    assert IzinService.get_izin_status(mhs_a_id, today) == "izin"
    # Pada tanggal lain -> harus None
    assert IzinService.get_izin_status(mhs_a_id, today + timedelta(days=5)) is None
