---
description: Rules for the nomadmania MCP tools. Use when the user asks about their NomadMania profile, series, regions or trips, or wants to tick a series object or edit a trip.
---

Follow these rules whenever you call a `nomadmania` tool.

1. `tick_series_item` and `save_trip` return a preview unless you pass `confirm=true`. Show the preview to the user and write only after they agree to that exact change.
2. There is no untick and no trip delete. A wrong write has to be fixed by hand on nomadmania.com, so check ids, dates and regions before you confirm.
3. Before saying what counts as a visit for a series, call `series_rules` and quote the rule. Do not rely on what you know about NomadMania.
4. A tick can also tick the same place in other series (Rome in World Capitals and in European Cities). After a write, report `also_ticked` and `scores_changed`, and say so if `verified` is false.
5. For objects without a map pin, such as Borders country pairs, find the id with `series_items`, then tick without `lat`/`lon`.
6. A `warning` from `series_near` or `unvisited_regions_near` means every map tile came back empty. Treat it as a network problem and retry; do not tell the user there is nothing nearby.
7. `save_trip` sends the whole trip, not a patch: pass every leg you want to keep. The trip can come back under a new `trip_id`.
