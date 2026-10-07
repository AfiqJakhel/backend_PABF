"""
Schemas validasi input untuk Area Absensi (admin).
Mengikuti pola validasi manual dari fasil_schemas.py.
"""

from app.utils.polygon import validate_coordinates, geojson_coords_to_wkt


def validate_buat_area(data: dict) -> tuple[list, dict]:
    """
    Validasi payload untuk membuat area absensi baru.

    Fields:
        nama        : str, maks 100 karakter (wajib)
        deskripsi   : str (opsional)
        coordinates : list GeoJSON [[[lon, lat], ...]] (wajib)
        is_active   : bool (opsional, default True)

    Returns:
        (errors: list[str], parsed: dict)
    """
    errors = []
    parsed = {}

    # nama
    nama = str(data.get("nama", "")).strip()
    if not nama:
        errors.append("'nama' area absensi wajib diisi.")
    elif len(nama) > 100:
        errors.append("'nama' area absensi maksimal 100 karakter.")
    else:
        parsed["nama"] = nama

    # deskripsi (opsional)
    parsed["deskripsi"] = data.get("deskripsi") or None

    # coordinates
    coordinates = data.get("coordinates")
    if coordinates is None:
        errors.append("'coordinates' polygon wajib disertakan.")
    else:
        valid, coord_err = validate_coordinates(coordinates)
        if not valid:
            errors.append(f"'coordinates' tidak valid: {coord_err}")
        else:
            try:
                parsed["polygon_wkt"] = geojson_coords_to_wkt(coordinates)
            except ValueError as e:
                errors.append(str(e))

    # is_active (opsional)
    if "is_active" in data:
        parsed["is_active"] = bool(data["is_active"])
    else:
        parsed["is_active"] = True

    return errors, parsed


def validate_update_area(data: dict) -> tuple[list, dict]:
    """
    Validasi payload untuk mengupdate area absensi.
    Semua field bersifat opsional, minimal satu harus ada.

    Returns:
        (errors: list[str], parsed: dict)
    """
    errors = []
    parsed = {}

    if "nama" in data:
        nama = str(data["nama"]).strip()
        if not nama:
            errors.append("'nama' tidak boleh kosong jika disertakan.")
        elif len(nama) > 100:
            errors.append("'nama' maksimal 100 karakter.")
        else:
            parsed["nama"] = nama

    if "deskripsi" in data:
        parsed["deskripsi"] = data["deskripsi"] or None

    if "coordinates" in data:
        coordinates = data["coordinates"]
        valid, coord_err = validate_coordinates(coordinates)
        if not valid:
            errors.append(f"'coordinates' tidak valid: {coord_err}")
        else:
            try:
                parsed["polygon_wkt"] = geojson_coords_to_wkt(coordinates)
            except ValueError as e:
                errors.append(str(e))

    if "is_active" in data:
        parsed["is_active"] = bool(data["is_active"])

    if not parsed and not errors:
        errors.append("Tidak ada field yang dapat diperbarui.")

    return errors, parsed
