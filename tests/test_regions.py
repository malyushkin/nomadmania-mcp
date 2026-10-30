import json
from pathlib import Path

from shapely.geometry import box

from nomadmania_mcp import regions

FIX = Path(__file__).parent / "fixtures"
ROME = (41.9028, 12.4964)


class ShapesReader:
    def __init__(self, by_tile):
        self.by_tile = by_tile

    def polygons(self, layer, z, x, y):
        return self.by_tile.get((x, y), [])


def cat(*ids):
    return {i: {"id": i, "name": f"Italy – Region {i}", "hidden": 0} for i in ids}


def test_near_lists_region_once_across_tiles():
    near_part = box(12.6, 41.8, 12.7, 42.0)  # ~8 km east of Rome
    far_part = box(13.5, 41.8, 13.6, 42.0)
    reader = ShapesReader({(34, 23): [({"id": 2}, far_part)], (35, 23): [({"id": 2}, near_part)]})
    out = regions.near(reader, cat(2), set(), *ROME, 1000)
    assert [r["id"] for r in out["unvisited"]] == [2]
    assert out["unvisited"][0]["distance_km"] < 15


def test_near_excludes_visited_and_counts_them():
    shapes = [({"id": i}, box(12.6 + i, 41.8, 12.7 + i, 42.0)) for i in (0, 1, 2)]
    reader = ShapesReader({(34, 23): shapes})
    out = regions.near(reader, cat(0, 1, 2), {0}, *ROME, 300)
    assert {r["id"] for r in out["unvisited"]} == {1, 2}
    assert out["visited_nearby"] == 1


def test_near_inside_region_distance_zero_and_country():
    reader = ShapesReader({(34, 23): [({"id": 29}, box(12.0, 41.5, 13.0, 42.5))]})
    out = regions.near(reader, cat(29), set(), *ROME, 50)
    assert out["unvisited"][0]["distance_km"] == 0
    assert out["unvisited"][0]["country"] == "Italy"


def test_near_skips_ids_missing_from_catalogue_and_hidden():
    c = cat(1) | {2: {"id": 2, "name": "X – hidden", "hidden": 1}}
    reader = ShapesReader({(34, 23): [({"id": i}, box(12.4, 41.8, 12.6, 42.0)) for i in (1, 2, 3)]})
    out = regions.near(reader, c, set(), *ROME, 50)
    assert [r["id"] for r in out["unvisited"]] == [1]


def test_near_fixture_rome(reader):
    catalogue = {int(k): v for k, v in json.loads((FIX / "catalogue_tile.json").read_text()).items()}
    out = regions.near(reader, catalogue, set(), *ROME, 50)
    assert out["unvisited"][0]["id"] == 29
    assert out["unvisited"][0]["distance_km"] == 0


def test_near_reports_empty_tiles():
    out = regions.near(ShapesReader({}), cat(1), set(), 0.0, -30.0, 50)
    assert out["unvisited"] == []
    assert out["tiles_empty"] == out["tiles_total"] > 0


def test_country_from_hyphenated_name():
    c = {1: {"id": 1, "name": "Netherlands - East - Flevoland, Overijssel", "hidden": 0}}
    reader = ShapesReader({(34, 23): [({"id": 1}, box(12.4, 41.8, 12.6, 42.0))]})
    assert regions.near(reader, c, set(), *ROME, 50)["unvisited"][0]["country"] == "Netherlands"


def test_near_recovers_after_a_network_blip(reader):
    # wanderfill memoises decoded shapes; an empty tile from a failed fetch must not stick for the process lifetime.
    catalogue = {int(k): v for k, v in json.loads((FIX / "catalogue_tile.json").read_text()).items()}
    real_raw, calls = reader.raw, {"n": 0}

    def flaky(layer, z, x, y):
        calls["n"] += 1
        return b"" if calls["n"] == 1 else real_raw(layer, z, x, y)

    reader.raw = flaky
    regions.near(reader, catalogue, set(), *ROME, 50)
    assert regions.near(reader, catalogue, set(), *ROME, 50)["unvisited"][0]["id"] == 29
