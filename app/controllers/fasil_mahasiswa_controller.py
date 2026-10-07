"""
Controller khusus Fasilitator untuk Data Master Mahasiswa Penghuni Asrama.
Prinsip Inti:
  FACILITATOR -> 1 GEDUNG -> DATA MAHASISWA

Setiap operasi CRUD dan import pada controller ini diisolasi secara ketat
pada Gedung Asrama yang dibina oleh Fasilitator yang sedang login.
IDOR Protection: Mahasiswa di luar gedung binaan akan ditolak dengan HTTP 403 Forbidden.
"""

import io
import csv
from flask import request, jsonify, Response
from app.core.extensions import db
from app.models.user import User
from app.models.kamar import Kamar
from app.models.gedung import Gedung
from app.services.fasil_scope_service import (
    resolve_fasil_building,
    validate_student_in_building,
    validate_kamar_in_building,
)


def get_gedung_saya():
    """
    GET /api/fasil/gedung-saya
    Mengambil data gedung asrama binaan fasilitator beserta daftar kamar valid.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    kamar_list = [
        {
            "id": k.id,
            "nomor_kamar": k.nomor_kamar,
            "lantai": k.lantai,
            "total_penghuni": k.penghuni.count() if hasattr(k.penghuni, 'count') else len(k.penghuni)
        }
        for k in gedung.daftar_kamar.order_by(Kamar.lantai, Kamar.nomor_kamar).all()
    ]

    return jsonify({
        "success": True,
        "message": "Data gedung binaan berhasil diambil.",
        "data": {
            "id": gedung.id,
            "nama_gedung": gedung.nama_gedung,
            "total_kamar": len(kamar_list),
            "daftar_kamar": kamar_list
        }
    }), 200


def get_mahasiswa_fasil():
    """
    GET /api/fasil/mahasiswa
    Mengambil seluruh mahasiswa yang menghuni kamar di gedung binaan fasilitator.
    Query params:
        search : str (opsional, filter nama atau NIM)
        kamar  : str (opsional, filter nomor kamar)
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    search = request.args.get("search", "").strip()
    kamar_filter = request.args.get("kamar", "").strip()

    # Query mahasiswa yang kamarnya berada di gedung ini
    query = (
        User.query
        .join(Kamar, User.kamar_id == Kamar.id)
        .filter(User.role == 'mahasiswa')
        .filter(Kamar.gedung_id == gedung.id)
    )

    if search:
        search_like = f"%{search}%"
        query = query.filter(
            db.or_(User.nama.ilike(search_like), User.nim.ilike(search_like))
        )

    if kamar_filter and kamar_filter != "all":
        query = query.filter(Kamar.nomor_kamar == kamar_filter)

    mahasiswa_list = query.order_by(Kamar.nomor_kamar, User.nama).all()

    items = []
    for mhs in mahasiswa_list:
        items.append({
            "id": mhs.id,
            "nim": mhs.nim,
            "nama": mhs.nama,
            "email": mhs.email or "-",
            "asal": mhs.asal or "-",
            "jekel": mhs.jekel or "-",
            "kamar_id": mhs.kamar_id,
            "nomor_kamar": mhs.kamar_ref.nomor_kamar if mhs.kamar_ref else "-",
            "lantai": mhs.kamar_ref.lantai if mhs.kamar_ref else 1,
            "nama_gedung": gedung.nama_gedung,
            "created_at": mhs.created_at.isoformat() if mhs.created_at else None
        })

    return jsonify({
        "success": True,
        "message": f"Daftar mahasiswa gedung {gedung.nama_gedung} berhasil dimuat.",
        "data": {
            "gedung_id": gedung.id,
            "nama_gedung": gedung.nama_gedung,
            "total": len(items),
            "mahasiswa": items
        }
    }), 200


def tambah_mahasiswa_fasil():
    """
    POST /api/fasil/mahasiswa
    Menambahkan mahasiswa baru ke kamar pada gedung binaan fasilitator.
    Body JSON:
        nim          : str (wajib)
        nama         : str (wajib)
        email        : str (opsional)
        kamar_id     : int (opsional jika nomor_kamar diisi)
        nomor_kamar  : str (opsional jika kamar_id diisi)
        lantai       : int (opsional, default 1)
        asal         : str (opsional)
        jekel        : str ('L' | 'P', opsional)
        password     : str (opsional, default 'password123')
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    body = request.get_json(silent=True) or {}
    nim = str(body.get("nim", "")).strip()
    nama = str(body.get("nama", "")).strip()
    kamar_id = body.get("kamar_id")
    nomor_kamar = str(body.get("nomor_kamar", "")).strip()
    lantai = int(body.get("lantai") or 1)
    email = str(body.get("email", "")).strip() or None
    asal = str(body.get("asal", "")).strip() or None
    jekel = str(body.get("jekel", "")).strip() or None
    password = str(body.get("password", "")).strip() or "password123"

    if not nim or not nama:
        return jsonify({
            "success": False,
            "message": "NIM dan Nama Mahasiswa wajib diisi.",
            "data": None
        }), 400

    # Cek duplikasi NIM
    if User.query.filter_by(nim=nim).first():
        return jsonify({
            "success": False,
            "message": f"Mahasiswa dengan NIM '{nim}' sudah terdaftar dalam sistem.",
            "data": None
        }), 409

    # Cek duplikasi email jika ada
    if email and User.query.filter_by(email=email).first():
        return jsonify({
            "success": False,
            "message": f"Email '{email}' sudah digunakan oleh pengguna lain.",
            "data": None
        }), 409

    # Resolusi Kamar di dalam gedung fasilitator
    target_kamar = None
    if kamar_id:
        target_kamar, err_msg, status_code = validate_kamar_in_building(int(kamar_id), gedung.id)
        if err_msg:
            return jsonify({"success": False, "message": err_msg, "data": None}), status_code
    elif nomor_kamar:
        target_kamar = Kamar.query.filter_by(gedung_id=gedung.id, nomor_kamar=nomor_kamar).first()
        if not target_kamar:
            # Auto buat kamar di gedung ini jika belum ada
            target_kamar = Kamar(gedung_id=gedung.id, nomor_kamar=nomor_kamar, lantai=lantai)
            db.session.add(target_kamar)
            db.session.flush()
    else:
        return jsonify({
            "success": False,
            "message": "Kamar wajib dipilih atau nomor kamar wajib diisi.",
            "data": None
        }), 400

    # Buat User Mahasiswa
    new_mhs = User(
        nim=nim,
        nama=nama,
        role='mahasiswa',
        kamar_id=target_kamar.id,
        email=email,
        asal=asal,
        jekel=jekel
    )
    new_mhs.set_password(password)

    db.session.add(new_mhs)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Mahasiswa '{nama}' ({nim}) berhasil ditambahkan ke Gedung {gedung.nama_gedung}, Kamar {target_kamar.nomor_kamar}.",
        "data": {
            "id": new_mhs.id,
            "nim": new_mhs.nim,
            "nama": new_mhs.nama,
            "kamar_id": target_kamar.id,
            "nomor_kamar": target_kamar.nomor_kamar,
            "lantai": target_kamar.lantai,
            "nama_gedung": gedung.nama_gedung
        }
    }), 201


def update_mahasiswa_fasil(student_id: int):
    """
    PUT /api/fasil/mahasiswa/<student_id>
    Memperbarui data mahasiswa.
    IDOR Protection: Menolak jika mahasiswa bukan penghuni gedung binaan fasilitator.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    # IDOR Check
    student, err_msg, status_code = validate_student_in_building(student_id, gedung.id)
    if err_msg:
        return jsonify({"success": False, "message": err_msg, "data": None}), status_code

    body = request.get_json(silent=True) or {}
    nama = body.get("nama")
    email = body.get("email")
    asal = body.get("asal")
    jekel = body.get("jekel")
    kamar_id = body.get("kamar_id")
    nomor_kamar = body.get("nomor_kamar")

    if nama is not None:
        student.nama = str(nama).strip()
    if email is not None:
        email_clean = str(email).strip() or None
        if email_clean and email_clean != student.email:
            if User.query.filter(User.email == email_clean, User.id != student.id).first():
                return jsonify({"success": False, "message": "Email sudah digunakan.", "data": None}), 409
            student.email = email_clean
    if asal is not None:
        student.asal = str(asal).strip() or None
    if jekel is not None:
        student.jekel = str(jekel).strip() or None

    # Pemindahan Kamar (harus tetap di gedung yang sama!)
    if kamar_id is not None:
        target_kamar, err_msg, status_code = validate_kamar_in_building(int(kamar_id), gedung.id)
        if err_msg:
            return jsonify({"success": False, "message": err_msg, "data": None}), status_code
        student.kamar_id = target_kamar.id
    elif nomor_kamar:
        nomor_clean = str(nomor_kamar).strip()
        target_kamar = Kamar.query.filter_by(gedung_id=gedung.id, nomor_kamar=nomor_clean).first()
        if not target_kamar:
            target_kamar = Kamar(gedung_id=gedung.id, nomor_kamar=nomor_clean, lantai=1)
            db.session.add(target_kamar)
            db.session.flush()
        student.kamar_id = target_kamar.id

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Data mahasiswa '{student.nama}' berhasil diperbarui.",
        "data": {
            "id": student.id,
            "nim": student.nim,
            "nama": student.nama,
            "kamar_id": student.kamar_id,
            "nomor_kamar": student.kamar_ref.nomor_kamar if student.kamar_ref else "-",
            "nama_gedung": gedung.nama_gedung
        }
    }), 200


def hapus_mahasiswa_fasil(student_id: int):
    """
    DELETE /api/fasil/mahasiswa/<student_id>
    Menghapus mahasiswa dari gedung binaan fasilitator.
    IDOR Protection: Menolak jika mahasiswa bukan penghuni gedung binaan fasilitator.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    # IDOR Check
    student, err_msg, status_code = validate_student_in_building(student_id, gedung.id)
    if err_msg:
        return jsonify({"success": False, "message": err_msg, "data": None}), status_code

    nama_mhs = student.nama
    nim_mhs = student.nim

    db.session.delete(student)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Mahasiswa {nama_mhs} ({nim_mhs}) berhasil dihapus dari Gedung {gedung.nama_gedung}.",
        "data": None
    }), 200


def download_template_csv():
    """
    GET /api/fasil/mahasiswa/template-csv
    Mengunduh berkas template CSV untuk import mahasiswa ke gedung binaan.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    output = io.StringIO()
    writer = csv.writer(output)
    # Header
    writer.writerow(["nim", "nama", "email", "nomor_kamar", "lantai", "jekel", "asal", "password"])
    # Contoh baris
    writer.writerow(["2211529901", "Contoh Mahasiswa 1", "mhs1@unand.ac.id", "101", "1", "L", "Padang", "password123"])
    writer.writerow(["2211529902", "Contoh Mahasiswa 2", "mhs2@unand.ac.id", "102", "1", "P", "Bukittinggi", "password123"])

    csv_data = output.getvalue()
    filename = f"template_import_mahasiswa_{gedung.nama_gedung.replace(' ', '_').lower()}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def import_mahasiswa_csv():
    """
    POST /api/fasil/mahasiswa/import-csv
    Mengimpor data mahasiswa dari CSV secara massal.
    Semua mahasiswa yang diimpor DIKUNCI OTOMATIS ke gedung binaan fasilitator!
    Kolom building_id atau gedung_id apapun di CSV akan DIABAIKAN untuk mencegah spoofing.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    if 'file' not in request.files:
        return jsonify({
            "success": False,
            "message": "File CSV tidak ditemukan pada form-data (key: 'file').",
            "data": None
        }), 400

    file = request.files['file']
    if not file.filename.lower().endswith(('.csv', '.txt')):
        return jsonify({
            "success": False,
            "message": "Format file tidak didukung. Mohon unggah file format .csv.",
            "data": None
        }), 400

    try:
        content = file.read().decode('utf-8-sig')
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Gagal membaca encoding file CSV: {str(e)}",
            "data": None
        }), 400

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return jsonify({
            "success": False,
            "message": "File CSV kosong atau header tidak valid.",
            "data": None
        }), 400

    # Normalisasi header
    normalized_headers = {h.strip().lower(): h for h in reader.fieldnames if h}
    if 'nim' not in normalized_headers or 'nama' not in normalized_headers:
        return jsonify({
            "success": False,
            "message": "Header CSV wajib memiliki kolom 'nim' dan 'nama'.",
            "data": None
        }), 400

    # Cache kamar yang ada di gedung ini untuk efisiensi
    kamar_map = {k.nomor_kamar: k for k in Kamar.query.filter_by(gedung_id=gedung.id).all()}

    success_count = 0
    updated_count = 0
    error_list = []
    seen_file_nims = set()

    for idx, row in enumerate(reader, start=2):
        row_clean = {k.strip().lower(): (v.strip() if v else '') for k, v in row.items() if k}
        nim = row_clean.get('nim', '')
        nama = row_clean.get('nama', '')
        email = row_clean.get('email') or None
        nomor_kamar = row_clean.get('nomor_kamar') or '101'
        lantai_str = row_clean.get('lantai') or '1'
        jekel = row_clean.get('jekel') or None
        asal = row_clean.get('asal') or None
        password = row_clean.get('password') or 'password123'

        if not nim or not nama:
            error_list.append(f"Baris {idx}: NIM dan Nama wajib diisi.")
            continue

        if nim in seen_file_nims:
            error_list.append(f"Baris {idx}: NIM '{nim}' terduplikasi di dalam berkas CSV.")
            continue
        seen_file_nims.add(nim)

        try:
            lantai = int(lantai_str)
        except ValueError:
            lantai = 1

        # Pastikan kamar berada pada gedung fasilitator
        if nomor_kamar not in kamar_map:
            new_k = Kamar(gedung_id=gedung.id, nomor_kamar=nomor_kamar, lantai=lantai)
            db.session.add(new_k)
            db.session.flush()
            kamar_map[nomor_kamar] = new_k

        target_kamar = kamar_map[nomor_kamar]

        # Cek apakah user mahasiswa sudah ada
        existing_user = User.query.filter_by(nim=nim).first()
        if existing_user:
            # Jika mahasiswa sudah ada di gedung lain, cegah pembajakan gedung tanpa izin admin!
            if existing_user.kamar_ref and existing_user.kamar_ref.gedung_id != gedung.id:
                error_list.append(
                    f"Baris {idx}: NIM '{nim}' sudah terdaftar di gedung lain ({existing_user.kamar_ref.gedung.nama_gedung}). Tidak dapat dimutasi antar-gedung via import fasilitator."
                )
                continue

            # Update info mahasiswa di gedung ini
            existing_user.nama = nama
            existing_user.kamar_id = target_kamar.id
            if email:
                existing_user.email = email
            if asal:
                existing_user.asal = asal
            if jekel:
                existing_user.jekel = jekel
            updated_count += 1
        else:
            # Buat mahasiswa baru di gedung ini
            new_student = User(
                nim=nim,
                nama=nama,
                role='mahasiswa',
                kamar_id=target_kamar.id,
                email=email,
                asal=asal,
                jekel=jekel
            )
            new_student.set_password(password)
            db.session.add(new_student)
            success_count += 1

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Proses import selesai untuk Gedung {gedung.nama_gedung}.",
        "data": {
            "total_baris_diproses": len(seen_file_nims),
            "berhasil_dibuat": success_count,
            "berhasil_diperbarui": updated_count,
            "gagal_count": len(error_list),
            "errors": error_list
        }
    }), 200
