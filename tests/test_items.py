import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import nomadmania_mcp.server as server
from nomadmania_mcp import series

BORDERS = json.loads((Path(__file__).parent / "fixtures" / "series_14.json").read_text())
CRO_HUN, CRO_MNE, KOMARNO = 39676, 39677, 666


def test_items_dedupes_rows_repeated_per_country():
    out = series.items(BORDERS)
    assert len(out) == len({o["id"] for o in out}) == 5
    cro_hun = next(o for o in out if o["id"] == CRO_HUN)
    assert cro_hun == {
        "id": CRO_HUN,
        "name": "Croatia-Hungary",
        "countries": ["Croatia", "Hungary"],
        "ticked": True,
        "other_crossing": False,
    }


def test_items_one_state_objects_have_no_other_crossing():
    komarno = next(o for o in series.items(BORDERS) if o["id"] == KOMARNO)
    assert "other_crossing" not in komarno and komarno["ticked"] is False


def test_items_query_matches_name_or_country():
    assert {o["id"] for o in series.items(BORDERS, "croatia")} == {8990, CRO_HUN, CRO_MNE}
    assert {o["id"] for o in series.items(BORDERS, "Slovakia")} == {KOMARNO}


def test_writable_allows_two_state_borders():
    assert series.writable(BORDERS) is True
    assert series.writable({"items1": [{"id": "1"}], "items2": []}) is False


def fake_nm(other_after=False, first_after=False):
    """Borders as NomadMania answers it; the flags flip once the matching write is called."""
    state = {"toggle": False, "toggle2": False}
    nm = MagicMock()

    def read(sid):
        p = json.loads(json.dumps(BORDERS))
        for row in p["items2"]:
            if state["toggle2"] and other_after and row["id"] == str(CRO_HUN):
                row["checked2"] = "12345"
        if state["toggle"] and first_after:
            p["visited"].append(CRO_MNE)
        return p

    def ajax_text(path, action, **kw):
        state[action] = True
        return "OK"

    nm.series.side_effect = read
    nm.tick_series_item.side_effect = lambda sid, item: ajax_text("my_series/", "toggle")
    nm.t.ajax_text.side_effect = ajax_text
    nm.account_id.return_value = 12345
    nm.profile.side_effect = lambda uid: {"scores": {"series": "15" if any(state.values()) else "14"}}
    return nm


def tick(nm, item_id, **kw):
    with patch("nomadmania_mcp.server.get_client", return_value=nm), patch("nomadmania_mcp.server.get_tiles"):
        return server.tick_series_item(14, item_id, **kw)


def test_unpinned_item_preview_without_coordinates():
    nm = fake_nm()
    out = tick(nm, CRO_MNE)
    assert out["preview"] is True and out["already_ticked"] is False and out["writable"] is True
    assert out["item"]["name"] == "Croatia-Montenegro" and out["likely_also"] == []
    nm.tick_series_item.assert_not_called()


def test_unpinned_item_first_tick():
    nm = fake_nm(first_after=True)
    out = tick(nm, CRO_MNE, confirm=True)
    assert out["ticked"] is True and out["verified"] is True and out["scores_changed"] == {"series": ["14", "15"]}
    nm.tick_series_item.assert_called_once_with(14, CRO_MNE)


def test_other_crossing_uses_toggle2_and_verifies():
    nm = fake_nm(other_after=True)
    out = tick(nm, CRO_HUN, other_crossing=True, confirm=True)
    assert out["verified"] is True
    nm.t.ajax_text.assert_called_once_with("my_series/", action="toggle2", item=CRO_HUN, state=1, series=14)
    nm.tick_series_item.assert_not_called()


def test_other_crossing_needs_first_tick():
    nm = fake_nm()
    with pytest.raises(RuntimeError, match="first"):
        tick(nm, CRO_MNE, other_crossing=True, confirm=True)
    nm.t.ajax_text.assert_not_called()


def test_other_crossing_needs_two_state_object():
    nm = fake_nm()
    with pytest.raises(RuntimeError, match="two-state"):
        tick(nm, KOMARNO, other_crossing=True, confirm=True)
    nm.t.ajax_text.assert_not_called()


def test_unknown_unpinned_item():
    with pytest.raises(RuntimeError, match="not found"):
        tick(fake_nm(), 1, confirm=True)
