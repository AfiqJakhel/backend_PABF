from math import asin, cos, radians, sin, sqrt


def haversine_distance_meters(latitude_a: float, longitude_a: float,
                              latitude_b: float, longitude_b: float) -> float:
    earth_radius_m = 6_371_000
    delta_lat = radians(latitude_b - latitude_a)
    delta_lon = radians(longitude_b - longitude_a)
    a = (
        sin(delta_lat / 2) ** 2
        + cos(radians(latitude_a))
        * cos(radians(latitude_b))
        * sin(delta_lon / 2) ** 2
    )
    return 2 * earth_radius_m * asin(sqrt(a))


def is_within_radius(latitude: float, longitude: float, center_latitude: float,
                     center_longitude: float, radius_meters: float) -> tuple[bool, float]:
    distance = haversine_distance_meters(
        latitude, longitude, center_latitude, center_longitude
    )
    return distance <= radius_meters, distance