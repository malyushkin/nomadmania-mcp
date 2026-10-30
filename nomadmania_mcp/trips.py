import datetime as dt
import json

from .regions import COUNTRY_SEP

# The site's trip form: 3 = a visit, 1 = transit (the plane icon on a leg).
QUALITIES = (3, 1)


def for_year(nm, year: int) -> list[dict]:
    # The year list names each trip's regions but not when; per-leg dates come only from the trip itself.
    out = [read(nm, int(t["id"])) for t in nm.trips_for_year(year).get("trips") or []]
    return sorted(out, key=lambda t: t["date_from"] or "", reverse=True)


def read(nm, trip_id: int) -> dict:
    trip = nm.trip(trip_id)["trip"]
    legs = [
        {
            "region_id": int(r["region"]),
            "name": r["region_name"],
            "country": COUNTRY_SEP.split(r["region_name"], maxsplit=1)[0].strip(),
            "date_from": r["date_from"],
            "date_to": r["date_to"],
            "quality": r["quality"],
        }
        for r in trip.get("regions") or []
    ]
    return {
        "trip_id": trip_id,
        "title": trip.get("description", ""),
        "date_from": trip["date_from"],
        "date_to": trip["date_to"],
        "legs": sorted(legs, key=lambda leg: (leg["date_from"] or "", leg["date_to"] or "")),
    }


def check_legs(legs: list[dict], catalogue: dict[int, dict]) -> list[dict]:
    """Legs as the user approves them: region, dates, quality; named from the live catalogue."""
    if not legs:
        raise ValueError("a trip needs at least one leg")
    out = []
    for leg in legs:
        rid = int(leg["region_id"])
        if rid not in catalogue:
            raise ValueError(f"unknown region {rid}")
        start, end = dt.date.fromisoformat(leg["date_from"]), dt.date.fromisoformat(leg["date_to"])
        if end < start:
            raise ValueError(f"leg in region {rid} ends before it starts")
        quality = int(leg.get("quality", 3))
        if quality not in QUALITIES:
            raise ValueError(f"leg in region {rid}: quality must be 3 (visit) or 1 (transit)")
        name = catalogue[rid]["name"].strip()
        out.append(
            {
                "region_id": rid,
                "name": name,
                "country": COUNTRY_SEP.split(name, maxsplit=1)[0].strip(),
                "date_from": start.isoformat(),
                "date_to": end.isoformat(),
                "quality": quality,
            }
        )
    return sorted(out, key=lambda leg: (leg["date_from"], leg["date_to"]))


def payload(title: str, legs: list[dict]) -> dict:
    """What the site's saveTrip() posts. `regions` is the "[object Object]" accident the server insists on (see
    wanderfill create_trip); the real legs travel in `regions_json`."""
    regions = []
    for leg in legs:
        start, end = dt.date.fromisoformat(leg["date_from"]), dt.date.fromisoformat(leg["date_to"])
        regions.append(
            {
                "id": int(leg["region_id"]),
                "quality": int(leg.get("quality", 3)),
                "hidden": 0,
                "year_from": start.year,
                "month_from": start.month,
                "day_from": start.day,
                "year_to": end.year,
                "month_to": end.month,
                "day_to": end.day,
            }
        )
    return {
        "description": title,
        "date_from": min(leg["date_from"] for leg in legs),
        "date_to": max(leg["date_to"] for leg in legs),
        "regions": ",".join("[object Object]" for _ in regions),
        "regions_json": json.dumps(regions),
    }


def save(nm, title: str, legs: list[dict], trip_id: int | None = None) -> dict:
    fields = payload(title, legs)
    if trip_id is None:
        return nm.t.webapi("trips/new-trip", **fields)
    return nm.t.webapi("trips/update-trip", trip_id=trip_id, **fields)


def overlapping(nm, date_from: str, date_to: str) -> list[dict]:
    years = range(int(date_from[:4]), int(date_to[:4]) + 1)
    found = {t["trip_id"]: t for y in years for t in for_year(nm, y)}
    return [t for t in found.values() if t["date_from"] <= date_to and t["date_to"] >= date_from]


def find_saved(nm, title: str, legs: list[dict]) -> dict | None:
    """The trip as NomadMania now stores it. An edit can come back under a new trip_id, so match by content."""
    want = [(leg["region_id"], leg["date_from"], leg["date_to"], leg["quality"]) for leg in legs]
    start, end = min(leg["date_from"] for leg in legs), max(leg["date_to"] for leg in legs)
    for t in overlapping(nm, start, end):
        got = [(leg["region_id"], leg["date_from"], leg["date_to"], int(leg["quality"])) for leg in t["legs"]]
        if t["title"] == title and sorted(got) == sorted(want):
            return t
    return None
