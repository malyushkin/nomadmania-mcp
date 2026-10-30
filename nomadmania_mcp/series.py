import html
import re

from wanderfill.geo.tiles import haversine_km, tile_bounds

from .geo import tiles_for_radius

# The only zoom where series2 is proven complete (wanderfill docs/nomadmania-api.md, "Tiles").
SERIES_ZOOM = 9


def list_series(nm) -> list[dict]:
    return [{"id": s["id"], "name": s["name"], "count": s["count"]} for s in nm.series_list()["data"]]


def rules(nm, series_id: int) -> dict:
    payload = nm.series(series_id)
    text = html.unescape(re.sub(r"<[^>]+>", " ", payload.get("description") or ""))
    return {"id": series_id, "title": payload.get("title", ""), "description": re.sub(r"\s+", " ", text).strip()}


def objects_near(reader, lat: float, lon: float, radius_km: float, series_ids: list[int] | None = None) -> dict:
    tiles = tiles_for_radius(lat, lon, radius_km, SERIES_ZOOM)
    best: dict[tuple[int, int], dict] = {}
    empty = 0
    for x, y in tiles:
        tile = reader.decode("series2", SERIES_ZOOM, x, y)
        if not tile:
            empty += 1
            continue
        west, south, east, north = tile_bounds(x, y, SERIES_ZOOM)
        for lyr in tile.values():
            extent = lyr.get("extent", 4096)
            for f in lyr.get("features", []):
                p, g = f.get("properties", {}), f.get("geometry", {})
                if g.get("type") != "Point" or "id" not in p:
                    continue
                sid = int(p.get("series_id", 0))
                if series_ids and sid not in series_ids:
                    continue
                px, py = g["coordinates"][:2]
                o_lat = south + (north - south) * (py / extent)
                o_lon = west + (east - west) * (px / extent)
                d = haversine_km(lat, lon, o_lat, o_lon)
                if d > radius_km:
                    continue
                key = (int(p["id"]), sid)
                # Multi-site objects (a WHS with several components) repeat one id; keep the nearest point.
                if key not in best or d < best[key]["distance_km"]:
                    best[key] = {
                        "id": key[0],
                        "series_id": sid,
                        "series_name": p.get("series_name", ""),
                        "name": p.get("name", ""),
                        "lat": round(o_lat, 5),
                        "lon": round(o_lon, 5),
                        "distance_km": round(d, 2),
                    }
    objects = sorted(best.values(), key=lambda o: o["distance_km"])
    return {"objects": objects, "tiles_total": len(tiles), "tiles_empty": empty}


def mark_ticked(nm, objects: list[dict]) -> list[dict]:
    ticked = {sid: set(map(int, nm.series(sid)["visited"])) for sid in {o["series_id"] for o in objects}}
    return [o | {"ticked": o["id"] in ticked[o["series_id"]]} for o in objects]


def affected(reader, series_id: int, item_id: int, lat: float, lon: float) -> dict:
    """The object to tick and the objects that are probably the same place in other series.

    Each series gives the same place its own id (Rome is 82 in World Capitals, 1692 in European Cities), so "same
    place" is a guess from name and position; the tick tool re-reads those series afterwards to see what moved."""
    objs = objects_near(reader, lat, lon, 1.0)["objects"]
    target = next((o for o in objs if o["id"] == item_id and o["series_id"] == series_id), None)
    if target is None:
        return {"target": None, "likely_also": []}
    likely = [
        o
        for o in objs
        if o["series_id"] != series_id
        and o["name"].casefold() == target["name"].casefold()
        and haversine_km(o["lat"], o["lon"], target["lat"], target["lon"]) <= 0.05
    ]
    return {"target": target, "likely_also": likely}


def items(payload: dict, query: str | None = None) -> list[dict]:
    """Every object of a series from its catalogue, pinned on the map or not.

    The catalogue repeats an object once per country it touches (a Borders pair sits under both), so rows merge by id.
    Two-state objects (Borders country pairs) carry `other_crossing`: the second box, "other border crossing between
    same countries"."""
    visited = set(map(int, payload["visited"]))
    merged: dict[int, dict] = {}
    for row in payload.get("items1", []) + payload.get("items2", []):
        oid = int(row["id"])
        if oid not in merged:
            merged[oid] = {"id": oid, "name": row["name"].strip(), "countries": [], "ticked": oid in visited}
            if str(row.get("double_point", "0")) != "0":
                merged[oid]["other_crossing"] = str(row.get("checked2", "0")) != "0"
        if row.get("country") and row["country"] not in merged[oid]["countries"]:
            merged[oid]["countries"].append(row["country"])
    out = list(merged.values())
    if query:
        q = query.casefold()
        out = [o for o in out if q in o["name"].casefold() or any(q in c.casefold() for c in o["countries"])]
    return out


def tick_other_crossing(nm, series_id: int, item_id: int) -> bool:
    # The page's toggle2: same endpoint as a plain tick, second box of a two-state object. wanderfill has no wrapper.
    return nm.t.ajax_text("my_series/", action="toggle2", item=item_id, state=1, series=series_id) == "OK"


def writable(payload: dict) -> bool:
    # Experiences and Top of the tops (items1) don't fit a plain state=1 toggle.
    return not payload.get("items1")
