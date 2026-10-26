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
import random
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
        search : str (opsional, filter nama, nama panggilan, NIM, email, asal)
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
            db.or_(
                User.nama.ilike(search_like),
                User.nim.ilike(search_like),
                User.nama_panggilan.ilike(search_like),
                User.asal.ilike(search_like),
                User.email.ilike(search_like)
            )
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
            "nama_panggilan": mhs.nama_panggilan or "-",
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


def assign_room_in_building(gedung_id: int, room_occupancy_tracker: dict = None) -> Kamar:
    """
    Menemukan atau mengalokasikan kamar secara otomatis/acak di dalam gedung.
    Memilih kamar dengan jumlah penghuni tersedikit (dengan tie-breaker acak).
    """
    kamar_list = Kamar.query.filter_by(gedung_id=gedung_id).order_by(Kamar.lantai, Kamar.nomor_kamar).all()
    if not kamar_list:
        default_rooms = [
            ('101', 1), ('102', 1), ('103', 1), ('104', 1),
            ('201', 2), ('202', 2), ('203', 2), ('204', 2),
            ('301', 3), ('302', 3), ('303', 3), ('304', 3),
        ]
        for n_k, lt in default_rooms:
            k = Kamar(gedung_id=gedung_id, nomor_kamar=n_k, lantai=lt)
            db.session.add(k)
        db.session.flush()
        kamar_list = Kamar.query.filter_by(gedung_id=gedung_id).order_by(Kamar.lantai, Kamar.nomor_kamar).all()

    if room_occupancy_tracker is not None:
        min_occ = min(room_occupancy_tracker.get(k.id, 0) for k in kamar_list)
        candidates = [k for k in kamar_list if room_occupancy_tracker.get(k.id, 0) == min_occ]
        chosen = random.choice(candidates)
        room_occupancy_tracker[chosen.id] = room_occupancy_tracker.get(chosen.id, 0) + 1
        return chosen
    else:
        kamar_counts = [
            (k, k.penghuni.count() if hasattr(k.penghuni, 'count') else len(k.penghuni))
            for k in kamar_list
        ]
        min_count = min(count for _, count in kamar_counts)
        candidates = [k for k, count in kamar_counts if count == min_count]
        return random.choice(candidates)


def tambah_mahasiswa_fasil():
    """
    POST /api/fasil/mahasiswa
    Menambahkan mahasiswa baru ke kamar pada gedung binaan fasilitator.
    Jika kamar_id/nomor_kamar tidak diisi, kamar dan lantai dialokasikan otomatis/acak oleh sistem.
    Password awal otomatis menggunakan NIM jika tidak diisi.
    Body JSON:
        nim             : str (wajib)
        nama            : str (wajib, Nama Panjang)
        nama_panggilan  : str (opsional, Nama Panggilan)
        email           : str (opsional)
        asal            : str (opsional, Asal Daerah)
        kamar_id        : int (opsional)
        nomor_kamar     : str (opsional)
        lantai          : int (opsional, default 1)
        jekel           : str ('L' | 'P', opsional)
        password        : str (opsional, default adalah NIM)
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    body = request.get_json(silent=True) or {}
    nim = str(body.get("nim", "")).strip()
    nama = str(body.get("nama", "")).strip()
    nama_panggilan = str(body.get("nama_panggilan", "")).strip() or None
    kamar_id = body.get("kamar_id")
    nomor_kamar = str(body.get("nomor_kamar", "")).strip()
    lantai = int(body.get("lantai") or 1)
    email = str(body.get("email", "")).strip() or None
    asal = str(body.get("asal", "")).strip() or None
    jekel = str(body.get("jekel", "")).strip() or None
    # Password awal berasal dari NIM jika tidak ditentukan
    password = str(body.get("password", "")).strip() or nim

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
            target_kamar = Kamar(gedung_id=gedung.id, nomor_kamar=nomor_kamar, lantai=lantai)
            db.session.add(target_kamar)
            db.session.flush()
    else:
        # Alokasi otomatis/acak oleh sistem
        target_kamar = assign_room_in_building(gedung.id)

    # Buat User Mahasiswa
    new_mhs = User(
        nim=nim,
        nama=nama,
        nama_panggilan=nama_panggilan,
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
            "nama_panggilan": new_mhs.nama_panggilan,
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
    nama_panggilan = body.get("nama_panggilan")
    email = body.get("email")
    asal = body.get("asal")
    jekel = body.get("jekel")
    kamar_id = body.get("kamar_id")
    nomor_kamar = body.get("nomor_kamar")

    if nama is not None:
        student.nama = str(nama).strip()
    if nama_panggilan is not None:
        student.nama_panggilan = str(nama_panggilan).strip() or None
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
            "nama_panggilan": student.nama_panggilan,
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
    Hanya memuat kolom: NIM, Nama Panjang, Nama Panggilan, Email, Asal Daerah.
    Nomor kamar dan lantai dialokasikan otomatis/acak oleh sistem.
    Password awal mahasiswa otomatis berasal dari NIM.
    """
    gedung, err_resp, code = resolve_fasil_building()
    if err_resp:
        return err_resp, code

    output = io.StringIO()
    writer = csv.writer(output)
    # Header minimalis sesuai instruksi user
    writer.writerow(["NIM", "Nama Panjang", "Nama Panggilan", "Email", "Asal Daerah"])
    # Contoh baris
    writer.writerow(["2211529901", "Muhammad Afiq Pratama", "Afiq", "afiq@unand.ac.id", "Padang"])
    writer.writerow(["2211529902", "Siti Nurhaliza Putri", "Siti", "siti@unand.ac.id", "Bukittinggi"])

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
    Kolom template cukup: NIM, Nama Panjang, Nama Panggilan, Email, Asal Daerah.
    Nomor kamar dan lantai diatur secara acak/otomatis oleh sistem,
    dan password awal otomatis berasal dari NIM masing-masing mahasiswa.
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

    # Normalisasi header fleksibel: lowercase, hilangkan spasi dan underscore
    def normalize_header(h: str) -> str:
        return h.strip().lower().replace(" ", "").replace("_", "")

    header_map = {}
    for raw_h in reader.fieldnames:
        if not raw_h:
            continue
        norm = normalize_header(raw_h)
        if norm in ("nim", "nomorindukmahasiswa"):
            header_map["nim"] = raw_h
        elif norm in ("namapanjang", "namalengkap", "nama"):
            header_map["nama"] = raw_h
        elif norm in ("namapanggilan", "panggilan", "nickname"):
            header_map["nama_panggilan"] = raw_h
        elif norm in ("email", "surel"):
            header_map["email"] = raw_h
        elif norm in ("asaldaerah", "asal", "daerah", "kotasal"):
            header_map["asal"] = raw_h
        elif norm in ("nomorkamar", "kamar", "nokamar"):
            header_map["nomor_kamar"] = raw_h
        elif norm in ("lantai",):
            header_map["lantai"] = raw_h
        elif norm in ("jeniskelamin", "jekel", "gender"):
            header_map["jekel"] = raw_h
        elif norm in ("password", "katasandi"):
            header_map["password"] = raw_h

    if "nim" not in header_map or "nama" not in header_map:
        return jsonify({
            "success": False,
            "message": "Header CSV wajib memiliki kolom 'NIM' dan 'Nama Panjang' (atau 'Nama').",
            "data": None
        }), 400

    # Ambil daftar kamar gedung binaan & siapkan tracker penghuni untuk alokasi acak/otomatis seimbang
    kamar_list = Kamar.query.filter_by(gedung_id=gedung.id).order_by(Kamar.lantai, Kamar.nomor_kamar).all()
    if not kamar_list:
        default_rooms = [
            ('101', 1), ('102', 1), ('103', 1), ('104', 1),
            ('201', 2), ('202', 2), ('203', 2), ('204', 2),
            ('301', 3), ('302', 3), ('303', 3), ('304', 3),
        ]
        for n_k, lt in default_rooms:
            k = Kamar(gedung_id=gedung.id, nomor_kamar=n_k, lantai=lt)
            db.session.add(k)
        db.session.flush()
        kamar_list = Kamar.query.filter_by(gedung_id=gedung.id).order_by(Kamar.lantai, Kamar.nomor_kamar).all()

    kamar_by_nomor = {k.nomor_kamar: k for k in kamar_list}
    room_occupancy = {
        k.id: (k.penghuni.count() if hasattr(k.penghuni, 'count') else len(k.penghuni))
        for k in kamar_list
    }

    success_count = 0
    updated_count = 0
    error_list = []
    seen_file_nims = set()

    for idx, row in enumerate(reader, start=2):
        nim = str(row.get(header_map.get("nim", ""), "")).strip()
        nama = str(row.get(header_map.get("nama", ""), "")).strip()
        nama_panggilan = str(row.get(header_map.get("nama_panggilan", ""), "")).strip() or None
        email = str(row.get(header_map.get("email", ""), "")).strip() or None
        asal = str(row.get(header_map.get("asal", ""), "")).strip() or None
        nomor_kamar_raw = str(row.get(header_map.get("nomor_kamar", ""), "")).strip()
        lantai_raw = str(row.get(header_map.get("lantai", ""), "")).strip()
        jekel = str(row.get(header_map.get("jekel", ""), "")).strip() or None
        # Password awal berasal dari NIM (atau fallback ke nilai eksplisit bila ada)
        custom_pwd = str(row.get(header_map.get("password", ""), "")).strip()
        initial_password = custom_pwd if custom_pwd else nim

        if not nim or not nama:
            error_list.append(f"Baris {idx}: NIM dan Nama Panjang wajib diisi.")
            continue

        if nim in seen_file_nims:
            error_list.append(f"Baris {idx}: NIM '{nim}' terduplikasi di dalam berkas CSV.")
            continue
        seen_file_nims.add(nim)

        # Cek apakah user mahasiswa sudah ada
        existing_user = User.query.filter_by(nim=nim).first()
        if existing_user:
            # Jika mahasiswa sudah ada di gedung lain, cegah pembajakan gedung tanpa izin admin
            if existing_user.kamar_ref and existing_user.kamar_ref.gedung_id != gedung.id:
                error_list.append(
                    f"Baris {idx}: NIM '{nim}' sudah terdaftar di gedung lain ({existing_user.kamar_ref.gedung.nama_gedung}). Tidak dapat dimutasi antar-gedung via import fasilitator."
                )
                continue

            # Update info mahasiswa di gedung ini
            existing_user.nama = nama
            if nama_panggilan:
                existing_user.nama_panggilan = nama_panggilan
            if email:
                existing_user.email = email
            if asal:
                existing_user.asal = asal
            if jekel:
                existing_user.jekel = jekel

            # Jika mahasiswa belum punya kamar di gedung ini atau nomor_kamar spesifik diisi
            if nomor_kamar_raw:
                if nomor_kamar_raw not in kamar_by_nomor:
                    try:
                        lt = int(lantai_raw) if lantai_raw else 1
                    except ValueError:
                        lt = 1
                    new_k = Kamar(gedung_id=gedung.id, nomor_kamar=nomor_kamar_raw, lantai=lt)
                    db.session.add(new_k)
                    db.session.flush()
                    kamar_by_nomor[nomor_kamar_raw] = new_k
                    kamar_list.append(new_k)
                    room_occupancy[new_k.id] = 0
                existing_user.kamar_id = kamar_by_nomor[nomor_kamar_raw].id
            elif not existing_user.kamar_id:
                # Alokasi kamar otomatis/acak jika belum memiliki kamar
                target_kamar = assign_room_in_building(gedung.id, room_occupancy)
                existing_user.kamar_id = target_kamar.id

            updated_count += 1
        else:
            # Tentukan kamar untuk mahasiswa baru
            if nomor_kamar_raw:
                if nomor_kamar_raw not in kamar_by_nomor:
                    try:
                        lt = int(lantai_raw) if lantai_raw else 1
                    except ValueError:
                        lt = 1
                    new_k = Kamar(gedung_id=gedung.id, nomor_kamar=nomor_kamar_raw, lantai=lt)
                    db.session.add(new_k)
                    db.session.flush()
                    kamar_by_nomor[nomor_kamar_raw] = new_k
                    kamar_list.append(new_k)
                    room_occupancy[new_k.id] = 0
                target_kamar = kamar_by_nomor[nomor_kamar_raw]
                room_occupancy[target_kamar.id] = room_occupancy.get(target_kamar.id, 0) + 1
            else:
                # Alokasi kamar dan lantai secara otomatis/acak oleh sistem
                target_kamar = assign_room_in_building(gedung.id, room_occupancy)

            new_student = User(
                nim=nim,
                nama=nama,
                nama_panggilan=nama_panggilan,
                role='mahasiswa',
                kamar_id=target_kamar.id,
                email=email,
                asal=asal,
                jekel=jekel
            )
            # Password awal mahasiswa berasal dari NIM
            new_student.set_password(initial_password)
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
