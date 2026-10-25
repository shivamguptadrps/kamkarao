from math import asin, cos, radians, sin, sqrt


def km_between(lat1, lon1, lat2, lon2):
    """Straight-line distance in km (haversine). Good enough inside one town."""
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def nearest_area(areas, lat, lon):
    best, best_km = None, None
    for area in areas:
        d = km_between(lat, lon, area.lat, area.lon)
        if best_km is None or d < best_km:
            best, best_km = area, d
    return best, best_km
