from unittest.mock import MagicMock, patch

import pytest

import nomadmania_mcp.server as server
from nomadmania_mcp import series

COLOSSEUM = (41.8902, 12.4922)


def rome(reader):
    objs = series.objects_near(reader, *COLOSSEUM, 3, series_ids=[1])["objects"]
    return next(o for o in objs if o["id"] == 82)


def fake_nm(visited=None, after=None, items1=False):
    """`visited` before the write, `after` once tick_series_item has been called."""
    visited = visited or {}
    state = {"written": False}
    nm = MagicMock()

    def read(sid):
        src = after if state["written"] and after is not None else visited
        row = {"id": "82", "name": "Rome", "double_point": "0"}
        return {"visited": src.get(sid, []), "items1": [row] if items1 else [], "items2": [] if items1 else [row]}

    def write(sid, item):
        state["written"] = True
        return True

    nm.series.side_effect = read
    nm.tick_series_item.side_effect = write
    nm.account_id.return_value = 12345
    nm.profile.side_effect = lambda uid: {"scores": {"series": "453" if state["written"] else "450", "score_nm": 107}}
    return nm


def call(reader, nm, **kw):
    r = rome(reader)
    with patch("nomadmania_mcp.server.get_client", return_value=nm), patch(
        "nomadmania_mcp.server.get_tiles", return_value=reader
    ):
        return server.tick_series_item(1, 82, r["lat"], r["lon"], **kw)


def test_affected_finds_same_place_in_other_series(reader):
    r = rome(reader)
    out = series.affected(reader, 1, 82, r["lat"], r["lon"])
    assert out["target"]["name"] == "Rome"
    assert {(o["series_id"], o["id"]) for o in out["likely_also"]} == {(3, 1692), (19, 20817)}


def test_preview_does_not_write(reader):
    nm = fake_nm()
    out = call(reader, nm)
    assert out["preview"] is True and out["already_ticked"] is False and out["writable"] is True
    assert sorted(o["series_id"] for o in out["likely_also"]) == [3, 19]
    nm.tick_series_item.assert_not_called()


def test_confirm_ticks_and_verifies(reader):
    nm = fake_nm(after={1: [82], 3: [1692]})
    out = call(reader, nm, confirm=True)
    assert out["ticked"] is True and out["verified"] is True
    assert {"series_id": 3, "id": 1692, "before": False, "after": True} in out["also_ticked"]
    assert {"series_id": 19, "id": 20817, "before": False, "after": False} in out["also_ticked"]
    assert out["scores_changed"] == {"series": ["450", "453"]}
    nm.tick_series_item.assert_called_once_with(1, 82)


def test_confirm_refuses_already_ticked(reader):
    nm = fake_nm(visited={1: [82]})
    with pytest.raises(RuntimeError, match="already ticked"):
        call(reader, nm, confirm=True)
    nm.tick_series_item.assert_not_called()


def test_confirm_refuses_items1_series(reader):
    nm = fake_nm(items1=True)
    with pytest.raises(RuntimeError, match="read-only"):
        call(reader, nm, confirm=True)
    nm.tick_series_item.assert_not_called()


def test_refuses_unknown_item(reader):
    nm = fake_nm()
    with patch("nomadmania_mcp.server.get_client", return_value=nm), patch(
        "nomadmania_mcp.server.get_tiles", return_value=reader
    ):
        with pytest.raises(RuntimeError, match="not found"):
            server.tick_series_item(1, 999999, *COLOSSEUM, confirm=True)
    nm.tick_series_item.assert_not_called()


def test_confirm_reports_unverified(reader):
    nm = fake_nm(after={})
    out = call(reader, nm, confirm=True)
    assert out["verified"] is False
    nm.tick_series_item.assert_called_once()
