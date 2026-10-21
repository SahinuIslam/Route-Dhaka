"""Distances on the Earth's surface.

The great-circle (haversine) distance is the length of the shortest path
over the sphere between two points. Buses follow roads, so the real road
distance is always at least this long: haversine UNDERESTIMATES travel
distance. Say this in your report.
"""
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between (lat1, lon1) and (lat2, lon2) in degrees."""
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))
