import pytest

from nomadmania_mcp.collection import UnknownCountry, build, region_label, undated

TODAY = "2026-11-18"


def leg(region_id, name, date_from, quality=3):
    return {"region_id": region_id, "name": name, "country": name.split(" – ")[0], "date_from": date_from,
            "date_to": date_from, "quality": quality}


def trip(tid, date_from, *legs, title="Trip"):
    return {"trip_id": tid, "title": title, "date_from": date_from, "date_to": date_from, "legs": list(legs)}


def test_region_label_drops_country_and_parentheses():
    assert region_label("Croatia – Dalmatia (Split, Dubrovnik)") == "Dalmatia"
    assert region_label("Serbia - Belgrade, West") == "Belgrade, West"
    assert region_label("Poland – Mazovia (Warsaw, Radom) and Łódź") == "Mazovia and Łódź"


def test_first_visit_wins():
    out = build([
        trip(2, "2024-05-18", leg(9, "Croatia – Dalmatia", "2024-05-18")),
        trip(1, "2019-08-14", leg(9, "Croatia – Dalmatia", "2019-08-14")),
    ], TODAY)
    assert [(r["region"], r["date"]) for r in out] == [("Dalmatia", "2019-08-14")]


def test_transit_ignored():
    out = build([
        trip(1, "2018-01-01", leg(5, "Austria – Vienna", "2018-01-01", quality=1),
             leg(6, "Germany – Bavaria", "2018-01-01", quality=1)),
        trip(2, "2020-02-02", leg(5, "Austria – Vienna", "2020-02-02")),
    ], TODAY)
    assert [(r["region"], r["date"]) for r in out] == [("Vienna", "2020-02-02")]


def test_future_legs_ignored():
    out = build([trip(1, "2027-01-20", leg(7, "Germany – Bavaria", "2027-01-20"))], TODAY)
    assert out == []


def test_leg_without_date_skipped():
    out = build([trip(1, "2020-01-01", leg(7, "Germany – Bavaria", None))], TODAY)
    assert out == []


def test_numbering_and_country_count():
    out = build([trip(1, "2020-01-01",
                      leg(1, "Spain – Catalonia", "2020-01-01"),
                      leg(2, "Spain – Aragón", "2020-01-02"),
                      leg(3, "France – Paris", "2020-01-03"))], TODAY)
    assert [r["n"] for r in out] == [1, 2, 3]
    assert [r["cn"] for r in out] == [1, 1, 2]
    assert [r["new_country"] for r in out] == [True, False, True]


def test_same_day_tie_keeps_leg_order():
    out = build([trip(1, "2020-01-01",
                      leg(2, "Spain – Aragón", "2020-01-01"),
                      leg(1, "Spain – Catalonia", "2020-01-01"))], TODAY)
    assert [r["region"] for r in out] == ["Aragón", "Catalonia"]


def test_same_day_tie_across_trips():
    out = build([
        trip(9, "2020-01-01", leg(1, "Spain – Catalonia", "2020-01-05")),
        trip(3, "2020-01-01", leg(2, "Spain – Aragón", "2020-01-05")),
        trip(1, "2020-01-04", leg(4, "Spain – Valencia", "2020-01-05")),
    ], TODAY)
    assert [r["region"] for r in out] == ["Aragón", "Catalonia", "Valencia"]


def test_entry_fields():
    out = build([trip(1, "2019-08-14", leg(9, "Croatia – Dalmatia (Split)", "2019-08-14"), title="Balkans")], TODAY)
    assert out == [{"n": 1, "date": "2019-08-14", "region": "Dalmatia", "country": "Croatia", "iso": "hr",
                    "part": "eu", "trip": "Balkans", "new_country": True, "cn": 1}]


def test_crimea():
    out = build([trip(1, "2015-07-01", leg(8, "Ukraine (occupied) – Crimea", "2015-07-01"))], TODAY)
    assert (out[0]["iso"], out[0]["part"]) == (None, "ru")


def test_unknown_country_raises():
    with pytest.raises(UnknownCountry, match="Japan"):
        build([trip(1, "2020-01-01", leg(1, "Japan – Tokyo", "2020-01-01"))], TODAY)


def test_undated():
    trips = [trip(1, "2020-01-01", leg(9, "Croatia – Dalmatia", "2020-01-01"))]
    assert undated(trips, {9, 77}, TODAY) == {77}


# --- nm-collection-export

import json  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

from nomadmania_mcp import collection  # noqa: E402
from tests.test_trips import FIX  # noqa: E402


def export(monkeypatch, capsys, visited=(989, 967, 9, 47, 5, 4), fail=False):
    nm = MagicMock()
    if fail:
        nm.trips_for_year.side_effect = RuntimeError("network down")
    else:
        nm.trips_for_year.side_effect = lambda y: json.loads((FIX / "trips_2024.json").read_text()) if y == 2024 \
            else {"trips": []}
    nm.trip.side_effect = lambda tid: json.loads((FIX / f"trip_{tid}.json").read_text())
    nm.visited_region_ids.return_value = list(visited)
    monkeypatch.setattr(collection, "get_client", lambda: nm)
    with pytest.raises(SystemExit) as exit_:
        collection.main()
    out, err = capsys.readouterr()
    return exit_.value.code, out, err


def test_main_prints_json(monkeypatch, capsys):
    code, out, err = export(monkeypatch, capsys)
    data = json.loads(out)
    assert code == 0 and err == ""
    assert data["generated_at"].endswith("Z")
    assert [r["n"] for r in data["regions"]] == [1, 2, 3, 4, 5, 6]
    assert data["regions"][0]["region"] == "New York - New York City and Long Island"


def test_main_reports_undated(monkeypatch, capsys):
    code, out, err = export(monkeypatch, capsys, visited=(989, 967, 9, 47, 5, 4, 999))
    assert code == 0 and "undated region ids: [999]" in err


def test_main_fails_closed(monkeypatch, capsys):
    code, out, err = export(monkeypatch, capsys, fail=True)
    assert code == 1 and out == "" and "network down" in err


def test_single_region_country_drops_parentheses():
    one = {"region_id": 3, "name": "Moldova (Chisinau, Soroca)", "country": "Moldova (Chisinau, Soroca)",
           "date_from": "2018-05-01", "date_to": "2018-05-01", "quality": 3}
    out = build([trip(1, "2018-05-01", one)], TODAY)
    assert (out[0]["country"], out[0]["region"], out[0]["iso"]) == ("Moldova", "Moldova", "md")


def test_minimal_visit_counts():
    out = build([trip(1, "2013-06-29", leg(304, "Russia – Buryatia Republic", "2013-06-29", quality=2))], TODAY)
    assert [r["region"] for r in out] == ["Buryatia Republic"]
