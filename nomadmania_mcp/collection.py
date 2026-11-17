"""The region collection for a public page: every region with the date of its first real visit, numbered."""
import datetime as dt
import json
import re
import sys

from wanderfill.api.client import MARKS_REGION_FROM

from . import trips as trips_mod
from .client import friendly, get_client
from .regions import COUNTRY_SEP

FIRST_YEAR = 2011

# NomadMania country name -> (ISO 3166-1 alpha-2 for the flag, part of the world). Parts follow the page's legend:
# Russia is its own part. Crimea has no flag of its own on the page.
COUNTRIES: dict[str, tuple[str | None, str]] = {
    "Russia": ("ru", "ru"), "Ukraine (occupied)": (None, "ru"),
    "Andorra": ("ad", "eu"), "Austria": ("at", "eu"), "Belarus": ("by", "eu"), "Belgium": ("be", "eu"),
    "Bosnia and Herzegovina": ("ba", "eu"), "Croatia": ("hr", "eu"), "Cyprus": ("cy", "eu"),
    "Czechia": ("cz", "eu"), "Denmark": ("dk", "eu"), "Estonia": ("ee", "eu"), "Finland": ("fi", "eu"),
    "France": ("fr", "eu"), "Germany": ("de", "eu"), "Hungary": ("hu", "eu"), "Iceland": ("is", "eu"),
    "Italy": ("it", "eu"), "Latvia": ("lv", "eu"), "Liechtenstein": ("li", "eu"), "Moldova": ("md", "eu"),
    "Montenegro": ("me", "eu"), "Netherlands": ("nl", "eu"), "Norway": ("no", "eu"), "Poland": ("pl", "eu"),
    "Portugal": ("pt", "eu"), "Romania": ("ro", "eu"), "Serbia": ("rs", "eu"), "Slovakia": ("sk", "eu"),
    "Spain": ("es", "eu"), "Sweden": ("se", "eu"), "Switzerland": ("ch", "eu"), "United Kingdom": ("gb", "eu"),
    "Armenia": ("am", "as"), "Georgia": ("ge", "as"), "Kyrgyzstan": ("kg", "as"), "Türkiye": ("tr", "as"),
    "United Arab Emirates": ("ae", "as"),
    "United States": ("us", "am"),
    "Egypt": ("eg", "af"),
}

_PARENS = re.compile(r"\s*\([^)]*\)")


class UnknownCountry(ValueError):
    pass


def region_label(name: str) -> str:
    return _PARENS.sub("", COUNTRY_SEP.split(name, maxsplit=1)[-1]).strip()


def _first_visits(trips: list[dict], today: str) -> dict[int, tuple]:
    first: dict[int, tuple] = {}
    for t in trips:
        for i, leg in enumerate(t["legs"]):
            d = leg["date_from"]
            # Quality 1 is transit, which NomadMania itself does not count; 2 ("minimal visit") and up do.
            if leg["quality"] < MARKS_REGION_FROM or not d or d > today:
                continue
            key = (d, t["date_from"] or "", t["trip_id"], i)
            if leg["region_id"] not in first or key < first[leg["region_id"]][0]:
                first[leg["region_id"]] = (key, leg, t)
    return first


def build(trips: list[dict], today: str) -> list[dict]:
    out, seen = [], set()
    for (d, *_), leg, t in sorted(_first_visits(trips, today).values(), key=lambda v: v[0]):
        # A one-region country has no "Country – Region" separator, so its name carries the parentheses too.
        country = leg["country"] if COUNTRY_SEP.search(leg["name"]) else region_label(leg["name"])
        if country not in COUNTRIES:
            raise UnknownCountry(f"Unknown country: {country}; add it to collection.COUNTRIES")
        iso, part = COUNTRIES[country]
        new = country not in seen
        seen.add(country)
        out.append({"n": len(out) + 1, "date": d, "region": region_label(leg["name"]), "country": country,
                    "iso": iso, "part": part, "trip": t["title"], "new_country": new, "cn": len(seen)})
    return out


def undated(trips: list[dict], visited: set[int], today: str) -> set[int]:
    return visited - set(_first_visits(trips, today))


def main() -> None:
    """`nm-collection-export`: print the collection JSON; read-only. Exit 1 with nothing on stdout on any error."""
    try:
        now = dt.datetime.now(dt.UTC)
        today = now.date().isoformat()
        nm = get_client()
        trips = [t for y in range(FIRST_YEAR, now.year + 1) for t in trips_mod.for_year(nm, y)]
        regions = build(trips, today)
        missing = undated(trips, {int(i) for i in nm.visited_region_ids(strict=True)}, today)
    except Exception as exc:
        print(friendly(exc), file=sys.stderr)
        sys.exit(1)
    if missing:
        print(f"undated region ids: {sorted(missing)}", file=sys.stderr)
    print(json.dumps({"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "regions": regions}, ensure_ascii=False))
    sys.exit(0)
