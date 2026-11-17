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
