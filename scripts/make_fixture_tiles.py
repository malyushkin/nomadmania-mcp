"""Writes the synthetic map tiles in tests/fixtures/.

The repo ships no NomadMania data, so the tiles hold a handful of hand-placed objects around Rome instead of the
real ones. Run with `uv run python scripts/make_fixture_tiles.py`.
"""

from pathlib import Path

import mapbox_vector_tile
from shapely.geometry import Point, box
from wanderfill.geo.tiles import tile_bounds

FIX = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

ROME = (41.9024, 12.4964)
VIA_APPIA_NEAR = (41.8461, 12.5308)
VIA_APPIA_FAR = (41.7219, 12.6650)

SERIES_NAMES = {
    1: "World Capitals",
    3: "European Cities",
    11: "Railway",
    19: "World Cities and Popular Towns",
    22: "UNESCO World Heritage Sites",
    68: "Vestiges of the Past",
}

# (id, series_id, name, (lat, lon)). One place has a different id per series (Rome); a multi-site object repeats
# its id at several points, some of them more than once (Via Appia).
OBJECTS = [
    (82, 1, "Rome", ROME),
    (1692, 3, "Rome", ROME),
    (20817, 19, "Rome", ROME),
    (22134, 11, "Rome Metro", ROME),
    (192, 1, "Vatican City", (41.9025, 12.4533)),
    (70147, 68, "Rome: Colosseum", (41.8898, 12.4923)),
    (19743, 22, "Via Appia", VIA_APPIA_NEAR),
    (19743, 22, "Via Appia", VIA_APPIA_NEAR),
    (19743, 22, "Via Appia", VIA_APPIA_FAR),
]

# (id, name, (west, south, east, north)); names match tests/fixtures/catalogue_tile.json.
REGIONS = [
    (29, "Italy – Lazio (Rome, Latina, Civitavecchia)", (12.0, 41.5, 13.0, 42.5)),
    (30, "Italy – Abruzzo (L'Aquila, Pescara, Teramo)", (13.5, 41.7, 14.5, 42.8)),
]


def write(layer: str, name: str, z: int, x: int, y: int, features: list) -> None:
    west, south, east, north = tile_bounds(x, y, z)
    data = mapbox_vector_tile.encode(
        [{"name": name, "features": features}],
        default_options={"quantize_bounds": (west, south, east, north), "extents": 4096},
    )
    (FIX / f"{layer}_z{z}_{x}_{y}.pbf").write_bytes(data)


def main() -> None:
    write("series2", "series", 9, 273, 190, [
        {
            "geometry": Point(lon, lat),
            "properties": {
                "id": oid, "series_id": sid, "name": name, "series_name": SERIES_NAMES[sid],
                "description": name, "no_visited": 0, "avatars": "[]",
            },
        }
        for oid, sid, name, (lat, lon) in OBJECTS
    ])
    write("regions", "regions", 6, 34, 23, [
        {"geometry": box(*bounds), "properties": {"id": rid, "name": name}} for rid, name, bounds in REGIONS
    ])


if __name__ == "__main__":
    main()
