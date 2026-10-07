"""
Utility functions untuk konversi koordinat polygon.

Konvensi koordinat:
  - GeoJSON  : [longitude, latitude]  (X, Y)
  - WKT      : POLYGON((longitude latitude, ...))
  - Leaflet  : LatLng(latitude, longitude) — perhatikan urutan terbalik!

Backend selalu menggunakan (longitude, latitude) di WKT,
konsisten dengan standar GIS / GeoJSON / MySQL Spatial.
"""


def geojson_coords_to_wkt(coordinates: list) -> str:
    """
    Konversi GeoJSON polygon coordinates ke WKT POLYGON string.

    Args:
        coordinates: GeoJSON polygon [[[lon, lat], [lon, lat], ...]]
                     (array of rings — hanya exterior ring yang diproses)

    Returns:
        WKT string: "POLYGON((lon lat, lon lat, ...))"

    Raises:
        ValueError: Jika koordinat tidak valid.
    """
    if not coordinates or not coordinates[0]:
        raise ValueError("Koordinat polygon tidak boleh kosong.")

    exterior_ring = coordinates[0]

    if len(exterior_ring) < 4:
        raise ValueError(
            "Polygon harus memiliki minimal 3 titik unik "
            "(4 koordinat termasuk titik penutup)."
        )

    # Pastikan ring tertutup (titik pertama == titik terakhir)
    if exterior_ring[0] != exterior_ring[-1]:
        exterior_ring = exterior_ring + [exterior_ring[0]]

    points = ", ".join(f"{lon} {lat}" for lon, lat in exterior_ring)
    return f"POLYGON(({points}))"


def wkt_to_geojson_coords(wkt: str) -> list:
    """
    Konversi WKT POLYGON string ke GeoJSON coordinates.

    Args:
        wkt: "POLYGON((lon lat, lon lat, ...))"

    Returns:
        GeoJSON coordinates [[[lon, lat], ...]]
    """
    try:
        # Extract isi antara (( dan ))
        start = wkt.index("((") + 2
        end = wkt.rindex("))")
        inner = wkt[start:end]

        coords = []
        for pair in inner.split(","):
            parts = pair.strip().split()
            if len(parts) >= 2:
                coords.append([float(parts[0]), float(parts[1])])

        return [coords]
    except Exception:
        return [[]]


def validate_coordinates(coordinates: list) -> tuple[bool, str | None]:
    """
    Validasi format GeoJSON polygon coordinates.

    Returns:
        (is_valid: bool, error_message: str | None)
    """
    if not isinstance(coordinates, list) or len(coordinates) == 0:
        return False, "Koordinat harus berupa array GeoJSON yang valid."

    ring = coordinates[0]
    if not isinstance(ring, list) or len(ring) < 3:
        return False, "Polygon harus memiliki minimal 3 titik."

    for point in ring:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            return False, "Setiap titik harus berupa [longitude, latitude]."
        lon, lat = point[0], point[1]
        if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
            return False, "Koordinat harus berupa angka."
        if not (-180 <= lon <= 180):
            return False, f"Longitude harus antara -180 dan 180. Diterima: {lon}"
        if not (-90 <= lat <= 90):
            return False, f"Latitude harus antara -90 dan 90. Diterima: {lat}"

    return True, None
