from unittest.mock import MagicMock

from nomadmania_mcp import series

COLOSSEUM = (41.8902, 12.4922)


def test_objects_near_reads_fixture(reader):
    out = series.objects_near(reader, *COLOSSEUM, 5)
    rome = [o for o in out["objects"] if o["series_id"] == 1 and o["name"] == "Rome"]
    assert rome and rome[0]["id"] == 82 and rome[0]["series_name"] == "World Capitals"
    dists = [o["distance_km"] for o in out["objects"]]
    assert dists == sorted(dists) and max(dists) <= 5
    assert out["tiles_total"] >= 1 and out["tiles_empty"] < out["tiles_total"]


def test_objects_near_filters_by_series(reader):
    out = series.objects_near(reader, *COLOSSEUM, 5, series_ids=[3])
    assert {o["series_id"] for o in out["objects"]} == {3}


def test_objects_near_dedupes_repeated_points(reader):
    out = series.objects_near(reader, *COLOSSEUM, 30, series_ids=[22])
    ids = [o["id"] for o in out["objects"]]
    assert len(ids) == len(set(ids))


def test_objects_near_reports_empty_tiles(reader):
    out = series.objects_near(reader, 0.0, -30.0, 5)
    assert out["objects"] == []
    assert out["tiles_empty"] == out["tiles_total"] > 0


def test_mark_ticked_one_read_per_series():
    nm = MagicMock()
    nm.series.side_effect = lambda sid: {"visited": {1: [82], 3: []}[sid]}
    objs = [{"id": 82, "series_id": 1}, {"id": 192, "series_id": 1}, {"id": 1692, "series_id": 3}]
    out = series.mark_ticked(nm, objs)
    assert nm.series.call_count == 2
    assert [o["ticked"] for o in out] == [True, False, False]


def test_list_series_shape():
    nm = MagicMock()
    nm.series_list.return_value = {"data": [{"id": 1, "name": "World Capitals", "count": 211, "icon": "x"}]}
    assert series.list_series(nm) == [{"id": 1, "name": "World Capitals", "count": 211}]
