"""MCP server over wanderfill's NomadMania client. Reads freely; the writes (a series tick, saving a trip) wait for
`confirm=true` (see README)."""

from functools import wraps
from importlib.metadata import version

from mcp.server.fastmcp import FastMCP
from wanderfill.api.errors import WanderfillError

from . import regions, series, trips
from .client import friendly, get_client, get_tiles

mcp = FastMCP("nomadmania")
mcp._mcp_server.version = version("nomadmania-mcp")


def _plain_errors(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except WanderfillError as exc:
            raise RuntimeError(friendly(exc)) from None

    return inner


@mcp.tool()
@_plain_errors
def profile_summary() -> dict:
    """Account id, the scores as the profile page shows them (`score_nm`, `score_un`, `score_unp`, `score_mqp` = DARE,
    `score_whs`, ...) and how many regions are marked visited."""
    nm = get_client()
    uid = nm.account_id()
    return {
        "account_id": uid,
        "scores": nm.profile(uid)["scores"],
        "visited_regions": len(_visited(nm)),
    }


def _visited(nm) -> set[int]:
    # strict: a malformed answer raises instead of reading as "nothing visited".
    return {int(i) for i in nm.visited_region_ids(strict=True)}


def _warn_if_blind(out: dict) -> dict:
    # wanderfill's TileReader returns an empty tile on network errors, so "nothing here" may mean "no connection".
    if out["tiles_total"] and out["tiles_empty"] == out["tiles_total"]:
        out["warning"] = "every map tile came back empty: either nothing is here or the tile server is unreachable"
    return out


@mcp.tool()
@_plain_errors
def list_series() -> list[dict]:
    """All NomadMania series (World Heritage Sites, World Capitals, Art Museums, ...) with id, name and object
    count."""
    return series.list_series(get_client())


@mcp.tool()
@_plain_errors
def series_rules(series_id: int) -> dict:
    """A series' own description as plain text, read live from NomadMania. It is the only place the series states what
    counts as a visit (ride vs. stand on the platform, inside vs. seen outside). Quote it before proposing a tick; many
    series state no rule at all. Accepts ids missing from `list_series` (Culinary Delights, 67)."""
    return series.rules(get_client(), series_id)


@mcp.tool()
@_plain_errors
def series_near(lat: float, lon: float, radius_km: float = 25, series_ids: list[int] | None = None) -> dict:
    """Series objects within `radius_km` (max 200) of a point, nearest first, each with `ticked` from the profile.

    Distance is evidence of nothing on its own: venue series pack hundreds of objects into one city centre. Propose
    candidates to the user; never tick from proximity alone. The same place has a different `id` in each series."""
    out = series.objects_near(get_tiles(), lat, lon, min(radius_km, 200), series_ids)
    out["objects"] = series.mark_ticked(get_client(), out["objects"])
    return _warn_if_blind(out)


@mcp.tool()
@_plain_errors
def trips_for_year(year: int) -> list[dict]:
    """Trips entered in NomadMania for `year`, newest first, read live. Each trip has `legs` in route order: the region
    and the dates spent there (the same region repeats when the route came back to it).

    Only trips the user entered in NomadMania appear, so this is not a full travel history. Regions marked visited without
    dates belong to no year: "no trip" does not mean "never there"."""
    return trips.for_year(get_client(), year)


@mcp.tool()
@_plain_errors
def save_trip(title: str, legs: list[dict], trip_id: int | None = None, confirm: bool = False) -> dict:
    """Edit a trip (`trip_id` from `trips_for_year`) or create one (no `trip_id`). `title` is the trip name; `legs` is
    the full new list, each `{"region_id", "date_from", "date_to", "quality"}` with ISO dates and quality 3 (visit,
    default) or 1 (transit). The same region may repeat for a route that came back to it. An edit replaces the whole
    trip, like the site's Save button.

    Without `confirm` it only previews: `before` (the trip now, or null), `after`, `regions_added`/`regions_removed`,
    and `overlapping` - trips already covering these dates (on create, a likely duplicate). Show the preview to the
    user and call again with `confirm=true` only after they approve that exact preview. NomadMania may give the edited
    trip a new id: the result's `trip_id` is the one to use from now on. There is no delete."""
    nm = get_client()
    try:
        after = trips.check_legs(legs, nm.regions())
    except ValueError as exc:
        raise RuntimeError(str(exc)) from None
    before = trips.read(nm, trip_id) if trip_id is not None else None
    if not confirm:
        old = {leg["region_id"]: leg["name"] for leg in before["legs"]} if before else {}
        new = {leg["region_id"]: leg["name"] for leg in after}
        others = trips.overlapping(nm, after[0]["date_from"], max(leg["date_to"] for leg in after))
        return {
            "preview": True,
            "action": "update" if before else "create",
            "before": before,
            "after": {"title": title, "legs": after},
            "regions_added": [n for r, n in new.items() if r not in old],
            "regions_removed": [n for r, n in old.items() if r not in new],
            "overlapping": [
                {k: t[k] for k in ("trip_id", "title", "date_from", "date_to")}
                for t in others
                if t["trip_id"] != trip_id
            ],
        }
    trips.save(nm, title, after, trip_id)
    saved = trips.find_saved(nm, title, after)
    return {"saved": True, "verified": saved is not None, "trip_id": saved["trip_id"] if saved else None, "trip": saved}


@mcp.tool()
@_plain_errors
def unvisited_regions_near(lat: float, lon: float, radius_km: float = 300) -> dict:
    """NomadMania regions not yet marked visited within `radius_km` (max 1500) of a point, nearest first (0 = the point
    is inside), plus how many visited regions are in the same radius. Use it to find where one trip closes the most
    new regions; routes and travel time are not part of this."""
    nm = get_client()
    out = regions.near(get_tiles(), nm.regions(), _visited(nm), lat, lon, min(radius_km, 1500))
    return _warn_if_blind(out)


@mcp.tool()
@_plain_errors
def series_items(series_id: int, query: str | None = None) -> list[dict]:
    """Objects of one series from its catalogue, including those with no map pin that `series_near` cannot see (Borders
    country pairs such as "Croatia-Montenegro"). `query` filters by name or country, case-insensitive.

    Each object has `ticked`. Two-state objects (Borders country pairs) also have `other_crossing`: the second box, for
    crossing the same pair of countries at a different place."""
    return series.items(get_client().series(series_id), query)


@mcp.tool()
@_plain_errors
def tick_series_item(
    series_id: int,
    item_id: int,
    lat: float | None = None,
    lon: float | None = None,
    other_crossing: bool = False,
    confirm: bool = False,
) -> dict:
    """Mark one series object visited. `lat`/`lon` are the object's own, as returned by `series_near`; leave them out
    for an object found with `series_items`.

    Without `confirm` it only previews: the object, whether it is already ticked, whether the series can be written,
    and `likely_also` - the same place in other series (a guess by name and position, only with `lat`/`lon`), which
    NomadMania ticks along with it. After the write, `scores_changed` shows every profile score that moved, including
    series the guess missed. Show the preview to the user and call again with `confirm=true` only after they approve
    that exact preview. One object per call; there is no untick.

    `other_crossing=true` ticks the second box of a two-state object (Borders pair): the user crossed the same two
    countries at a different place. Only after the first box is ticked; ask the user whether a new crossing was the
    same place or a different one."""
    nm = get_client()
    payload = nm.series(series_id)
    listed = next((o for o in series.items(payload) if o["id"] == item_id), None)
    if lat is None or lon is None:
        target, likely = listed, []
        if target is None:
            raise RuntimeError(f"object {item_id} not found in series {series_id}")
    else:
        found = series.affected(get_tiles(), series_id, item_id, lat, lon)
        target = found["target"]
        if target is None:
            raise RuntimeError(f"object {item_id} of series {series_id} not found within 1 km of ({lat}, {lon})")
        likely = series.mark_ticked(nm, found["likely_also"])
    first = item_id in set(map(int, payload["visited"]))
    already = listed.get("other_crossing") if other_crossing and listed else first
    if not confirm:
        return {
            "preview": True,
            "item": target,
            "already_ticked": already,
            "writable": series.writable(payload),
            "likely_also": likely,
        }
    if not series.writable(payload):
        raise RuntimeError(f"series {series_id} is read-only here (non-standard items)")
    if other_crossing:
        if listed is None or "other_crossing" not in listed:
            raise RuntimeError(f"object {item_id} is not a two-state object; there is no second box")
        if not first:
            raise RuntimeError(f"object {item_id}: tick the first box first")
    if already:
        raise RuntimeError(f"object {item_id} is already ticked in series {series_id}")
    uid = nm.account_id()
    before = nm.profile(uid)["scores"]
    if other_crossing:
        series.tick_other_crossing(nm, series_id, item_id)
        after_item = next(o for o in series.items(nm.series(series_id)) if o["id"] == item_id)
        verified = after_item["other_crossing"]
    else:
        nm.tick_series_item(series_id, item_id)
        verified = item_id in set(map(int, nm.series(series_id)["visited"]))
    after_likely = series.mark_ticked(nm, likely)
    also = [
        {"series_id": b["series_id"], "id": b["id"], "before": b["ticked"], "after": a["ticked"]}
        for b, a in zip(likely, after_likely, strict=True)
    ]
    # likely_also is a name/position guess; the profile scores show every series that moved, guessed or not.
    after = nm.profile(uid)["scores"]
    changed = {k: [before.get(k), v] for k, v in after.items() if before.get(k) != v}
    return {"ticked": True, "verified": verified, "item": target, "also_ticked": also, "scores_changed": changed}


def main() -> None:
    mcp.run()
