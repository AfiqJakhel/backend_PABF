from flask import jsonify, request

from app.services.user_import_service import import_users


def import_users_file():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"success": False, "message": "File CSV atau XLSX wajib diunggah.", "data": None}), 400
    try:
        result = import_users(uploaded.filename, uploaded.read())
    except (ValueError, UnicodeDecodeError) as error:
        return jsonify({"success": False, "message": str(error), "data": None}), 422
    return jsonify({"success": True, "message": f"{result['created']} pengguna berhasil diimpor.", "data": result}), 201