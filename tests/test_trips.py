import json
from pathlib import Path
from unittest.mock import MagicMock

from nomadmania_mcp import trips

FIX = Path(__file__).parent / "fixtures"


def fake_nm():
    nm = MagicMock()
    nm.trips_for_year.return_value = json.loads((FIX / "trips_2024.json").read_text())
    nm.trip.side_effect = lambda tid: json.loads((FIX / f"trip_{tid}.json").read_text())
    return nm


def test_for_year_newest_first_with_dated_legs():
    out = trips.for_year(fake_nm(), 2024)
    assert [t["trip_id"] for t in out] == [100001, 100002]
    balkans = out[0]
    assert (balkans["date_from"], balkans["date_to"]) == ("2024-05-18", "2024-05-27")
    assert [(leg["region_id"], leg["date_from"], leg["date_to"]) for leg in balkans["legs"]] == [
        (9, "2024-05-18", "2024-05-18"),
        (47, "2024-05-18", "2024-05-19"),
        (9, "2024-05-19", "2024-05-23"),
        (5, "2024-05-23", "2024-05-25"),
        (4, "2024-05-25", "2024-05-27"),
    ]
    assert balkans["legs"][0]["country"] == "Croatia"
    assert out[1]["legs"][0]["country"] == "United States"


def test_for_year_empty():
    nm = MagicMock()
    nm.trips_for_year.return_value = {"result": "OK", "trips": []}
    assert trips.for_year(nm, 1990) == []
    nm.trip.assert_not_called()


def test_for_year_country_from_hyphenated_name():
    nm = MagicMock()
    nm.trips_for_year.return_value = {"trips": [{"id": 1}]}
    leg = {"region": 7, "region_name": "Austria - Greater Vienna", "date_from": "2026-06-08", "date_to": "2026-06-12"}
    nm.trip.return_value = {"trip": {"date_from": "2026-06-08", "date_to": "2026-06-12", "regions": [leg | {"quality": 3}]}}
    assert trips.for_year(nm, 2026)[0]["legs"][0]["country"] == "Austria"
