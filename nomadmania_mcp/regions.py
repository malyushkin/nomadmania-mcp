import re

from shapely.geometry import Point
from shapely.ops import nearest_points
from wanderfill.geo.tiles import haversine_km

from .geo import tiles_for_radius

COUNTRY_SEP = re.compile(r" [–-] ")

# Distances are planar lon/lat to the nearest edge: fine for "how far", wrong across the antimeridian (Fiji, Chukotka).
# z6 keeps a 1500 km search to ~50 tiles; region outlines are coarse there, which is fine for "how far away".
REGION_ZOOM = 6


def near(reader, catalogue: dict[int, dict], visited: set[int], lat: float, lon: float, radius_km: float,
         z: int = REGION_ZOOM) -> dict:
    tiles = tiles_for_radius(lat, lon, radius_km, z)
    pt = Point(lon, lat)
    dist: dict[int, float] = {}
    empty = 0
    for x, y in tiles:
        # Not reader.shapes(): it memoises, and an empty tile from a failed fetch would stick for the process lifetime.
        shapes = list(reader.polygons("regions", z, x, y))
        if not shapes:
            empty += 1
        for props, geom in shapes:
            rid = int(props.get("id", -1))
            row = catalogue.get(rid)
            if row is None or row.get("hidden"):
                continue
            if geom.covers(pt):
                d = 0.0
            else:
                q = nearest_points(geom, pt)[0]
                d = haversine_km(lat, lon, q.y, q.x)
            dist[rid] = min(d, dist.get(rid, d))
    in_range = {rid: d for rid, d in dist.items() if d <= radius_km}
    unvisited = [
        {
            "id": rid,
            "name": catalogue[rid]["name"].strip(),
            "country": COUNTRY_SEP.split(catalogue[rid]["name"], maxsplit=1)[0].strip(),
            "distance_km": round(d, 1),
        }
        for rid, d in sorted(in_range.items(), key=lambda kv: kv[1])
        if rid not in visited
    ]
    return {
        "unvisited": unvisited,
        "visited_nearby": sum(1 for rid in in_range if rid in visited),
        "tiles_total": len(tiles),
        "tiles_empty": empty,
    }
