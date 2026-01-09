from __future__ import annotations

import math


# Chennai (rough) polygon for MVP boundary checks.
# Source: manually approximated bounding polygon around Chennai metro.
CHENNAI_POLYGON_LATLNG = [
    (13.2608, 80.0509),  # NW
    (13.2608, 80.3300),  # NE
    (12.9600, 80.3300),  # SE
    (12.9600, 80.0509),  # SW
]


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def point_in_polygon(lat: float, lng: float, polygon_latlng: list[tuple[float, float]]) -> bool:
    # Ray casting algorithm
    x = lng
    y = lat
    inside = False
    n = len(polygon_latlng)
    for i in range(n):
        y1, x1 = polygon_latlng[i]
        y2, x2 = polygon_latlng[(i + 1) % n]
        intersects = ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1)
        if intersects:
            inside = not inside
    return inside

