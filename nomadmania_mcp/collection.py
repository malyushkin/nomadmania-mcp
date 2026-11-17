"""The region collection for a public page: every region with the date of its first real visit, numbered."""
import re

from .regions import COUNTRY_SEP

VISIT = 3  # trip leg quality; 1 = transit, which never counts

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

_PARENS = re.compile(r"\s*\(.*\)\s*$")


class UnknownCountry(ValueError):
    pass


def region_label(name: str) -> str:
    return _PARENS.sub("", COUNTRY_SEP.split(name, maxsplit=1)[-1]).strip()


def _first_visits(trips: list[dict], today: str) -> dict[int, tuple]:
    first: dict[int, tuple] = {}
    for t in trips:
        for i, leg in enumerate(t["legs"]):
            d = leg["date_from"]
            if leg["quality"] != VISIT or not d or d > today:
                continue
            key = (d, t["date_from"] or "", t["trip_id"], i)
            if leg["region_id"] not in first or key < first[leg["region_id"]][0]:
                first[leg["region_id"]] = (key, leg, t)
    return first


def build(trips: list[dict], today: str) -> list[dict]:
    out, seen = [], set()
    for (d, *_), leg, t in sorted(_first_visits(trips, today).values(), key=lambda v: v[0]):
        country = leg["country"]
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
