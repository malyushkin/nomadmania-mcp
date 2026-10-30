# Live API facts

Probed 2026-10-26 against a real account with `scripts/probe.py` (raw answers go to `.probe/`, not committed; the
fixtures in `tests/fixtures/` are synthetic). Wanderfill rev `d08c03e`.

1. **`series/get-list`** → `{"result", "data": [69 entries]}`. Entry: `id`, `name`, `count`, `label`, `new`, `icon`,
   `new_icon`. No two-state marker. Ids include a virtual `-2` ("Top of the tops - by country").
2. **Catalogue row** (`regions/get-regions-list-2`, 1381 rows): `id`, `name`, `flag`, `hidden`. No country field; the
   country is the part of `name` before `–` (en dash), e.g. `Italy – Lazio (Rome, Latina, Civitavecchia)` = id 29.
3. **Region tiles** carry `id` and `name` only. Rome (41.9028, 12.4964) is inside id 29 at z6 tile 34/23.
4. **One place in several series has a different id per series.** Rome is `82` in World Capitals (1) and `1692` in
   European Cities (3), same point in `series2` z9 tile 273/190. Inside one series an id can repeat (multi-site WHS
   such as Via Appia, 8 points). So "which other series does a tick move" can only be guessed from same name and
   coordinates, and has to be checked by re-reading those series after the write.
5. **Two-state series** are recognisable from `series(id)`: items with `double_point != "0"` (only `14` Borders, 511
   items, with `checked2`). Two more series use `items1` instead of `items2`: `17` Experiences, `-2` Top of the tops.
   All other series have empty `items1`, `double_point == "0"` everywhere.
6. **Ticked state:** `series(id)["visited"]` is the list of ticked ids (ints, may repeat); an item's `checked` holds
   the account id when ticked, `"0"` otherwise. The two agree as sets.
7. **A tick moves the same place in other series.** 2026-10-26, with the account owner's approval: `tick_series_item(1, 82)` (Rome,
   World Capitals) → read-back showed `82` ticked in series 1, and also `1692` in European Cities (3) and `20817` in
   World Cities and Popular Towns (19), all three matched by `likely_also` beforehand.
