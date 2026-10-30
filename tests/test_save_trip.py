import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import nomadmania_mcp.server as server
from nomadmania_mcp import trips

FIX = Path(__file__).parent / "fixtures"
CATALOGUE = {
    9: {"id": 9, "name": "Croatia – Dalmatia (Split, Dubrovnik)"},
    47: {"id": 47, "name": "Montenegro – Central and Coastal (Podgorica, Kotor)"},
    5: {"id": 5, "name": "Bosnia and Herzegovina – Federation (Sarajevo, Mostar)"},
    4: {"id": 4, "name": "Bosnia and Herzegovina – Srpska (Banja Luka)"},
}
NEW_LEGS = [
    {"region_id": 9, "date_from": "2024-05-18", "date_to": "2024-05-23"},
    {"region_id": 47, "date_from": "2024-05-18", "date_to": "2024-05-19", "quality": 1},
    {"region_id": 5, "date_from": "2024-05-23", "date_to": "2024-05-27"},
]


def test_payload_matches_the_site_form():
    out = trips.payload("Trip to Dubrovnik", NEW_LEGS)
    assert out["description"] == "Trip to Dubrovnik"
    assert (out["date_from"], out["date_to"]) == ("2024-05-18", "2024-05-27")
    assert out["regions"] == "[object Object],[object Object],[object Object]"
    first, transit = json.loads(out["regions_json"])[:2]
    assert first == {
        "id": 9, "quality": 3, "hidden": 0,
        "year_from": 2024, "month_from": 5, "day_from": 18,
        "year_to": 2024, "month_to": 5, "day_to": 23,
    }
    assert transit["quality"] == 1


@pytest.mark.parametrize(
    "leg, match",
    [
        ({"region_id": 9, "date_from": "2024-05-20", "date_to": "2024-05-18"}, "ends before"),
        ({"region_id": 9, "date_from": "2024-05-18", "date_to": "2024-05-19", "quality": 5}, "quality"),
        ({"region_id": 999, "date_from": "2024-05-18", "date_to": "2024-05-19"}, "unknown region"),
    ],
)
def test_check_legs_refuses_bad_input(leg, match):
    with pytest.raises(ValueError, match=match):
        trips.check_legs([leg], CATALOGUE)


def test_check_legs_refuses_empty():
    with pytest.raises(ValueError, match="at least one"):
        trips.check_legs([], CATALOGUE)


def fake_nm(saved=None):
    """The Balkans trip 100001; once a write is called, the year lists `saved` instead."""
    state = {"written": False}
    nm = MagicMock()
    nm.regions.return_value = CATALOGUE
    original = json.loads((FIX / "trip_100001.json").read_text())

    def year(y):
        if state["written"] and saved is not None:
            return {"trips": [{"id": saved["id"]}]}
        return {"trips": [{"id": 100001}]}

    def trip(tid):
        return saved_trip if state["written"] and saved is not None and tid == saved["id"] else original

    def webapi(action, **fields):
        state["written"] = True
        return {"result": "OK"}

    if saved is not None:
        regions = [
            {"region": leg["region_id"], "region_name": CATALOGUE[leg["region_id"]]["name"],
             "date_from": leg["date_from"], "date_to": leg["date_to"], "quality": leg.get("quality", 3)}
            for leg in saved["legs"]
        ]
        dates = [leg["date_from"] for leg in saved["legs"]] + [leg["date_to"] for leg in saved["legs"]]
        saved_trip = {"trip": {"id": saved["id"], "description": saved["title"], "date_from": min(dates),
                               "date_to": max(dates), "regions": regions}}
    nm.trips_for_year.side_effect = year
    nm.trip.side_effect = trip
    nm.t.webapi.side_effect = webapi
    return nm


def save(nm, **kw):
    with patch("nomadmania_mcp.server.get_client", return_value=nm):
        return server.save_trip(**kw)


def test_update_preview_shows_before_after_and_region_changes():
    nm = fake_nm()
    out = save(nm, title="Trip to Dubrovnik", legs=NEW_LEGS, trip_id=100001)
    assert out["preview"] is True and out["action"] == "update"
    assert out["before"]["title"] == "Balkans trip"
    assert {leg["region_id"]: leg["name"] for leg in out["after"]["legs"]}[9] == CATALOGUE[9]["name"]
    region_4 = next(leg["name"] for leg in out["before"]["legs"] if leg["region_id"] == 4)
    assert out["regions_removed"] == [region_4] and out["regions_added"] == []
    nm.t.webapi.assert_not_called()


def test_update_writes_trip_id_and_verifies_by_dates():
    nm = fake_nm(saved={"id": 500001, "title": "Trip to Dubrovnik", "legs": NEW_LEGS})
    out = save(nm, title="Trip to Dubrovnik", legs=NEW_LEGS, trip_id=100001, confirm=True)
    action, fields = nm.t.webapi.call_args.args[0], nm.t.webapi.call_args.kwargs
    assert action == "trips/update-trip" and fields["trip_id"] == 100001
    assert out["saved"] is True and out["verified"] is True and out["trip_id"] == 500001


def test_create_uses_new_trip_and_lists_overlaps_in_preview():
    nm = fake_nm()
    out = save(nm, title="Trip to Dubrovnik", legs=NEW_LEGS)
    assert out["action"] == "create" and out["before"] is None
    assert [t["trip_id"] for t in out["overlapping"]] == [100001]
    nm.t.webapi.assert_not_called()
    nm = fake_nm(saved={"id": 500002, "title": "Trip to Dubrovnik", "legs": NEW_LEGS})
    save(nm, title="Trip to Dubrovnik", legs=NEW_LEGS, confirm=True)
    assert nm.t.webapi.call_args.args[0] == "trips/new-trip"
    assert "trip_id" not in nm.t.webapi.call_args.kwargs


def test_unverified_when_saved_trip_differs():
    nm = fake_nm(saved={"id": 500003, "title": "Trip to Dubrovnik", "legs": NEW_LEGS[:1]})
    out = save(nm, title="Trip to Dubrovnik", legs=NEW_LEGS, trip_id=100001, confirm=True)
    assert out["verified"] is False


def test_refuses_bad_legs_before_writing():
    nm = fake_nm()
    with pytest.raises(RuntimeError, match="unknown region"):
        save(nm, title="x", legs=[{"region_id": 999, "date_from": "2024-05-18", "date_to": "2024-05-19"}], confirm=True)
    nm.t.webapi.assert_not_called()
