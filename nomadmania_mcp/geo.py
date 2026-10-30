import math

from wanderfill.geo.tiles import deg2tile


def tiles_for_radius(lat: float, lon: float, radius_km: float, z: int) -> set[tuple[int, int]]:
    """Every tile intersecting the circle's bounding box, wrapping across the antimeridian."""
    n = 2**z
    dlat = radius_km / 111.32
    dlon = radius_km / (111.32 * max(math.cos(math.radians(lat)), 0.01))
    north, south = min(lat + dlat, 85.0), max(lat - dlat, -85.0)
    # floor, not deg2tile's int(): west of -180 must land on column -1, i.e. n-1 after wrapping.
    x0 = math.floor((lon - dlon + 180.0) / 360.0 * n)
    x1 = math.floor((lon + dlon + 180.0) / 360.0 * n)
    _, y0 = deg2tile(north, lon, z)
    _, y1 = deg2tile(south, lon, z)
    return {(x % n, y) for x in range(x0, x1 + 1) for y in range(max(y0, 0), min(y1, n - 1) + 1)}
