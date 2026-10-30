# Changelog

All notable changes to `nomadmania-mcp` are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/).

## [0.6.0]

### Added

- Claude Code plugin: `.claude-plugin/` makes the repo a one-plugin marketplace. The plugin asks for the token, starts
  the server with `uvx` from git and loads `skills/nomadmania`, the agent rules for writes, series rules and empty-tile
  warnings.
- Install without cloning: `uvx --from git+https://github.com/malyushkin/nomadmania-mcp nomadmania-mcp`, plus Cursor
  and VS Code install links in the README.
- GitHub Actions workflow running the tests.
- Standalone public repo with synthetic test fixtures, Apache-2.0 license, logo and social preview image.

## [0.5.0]

### Added

- `save_trip(title, legs, trip_id, confirm)`: edit a trip's name and legs (region, dates, transit) or create a new
  trip, the way the site's trip form saves it. Preview shows before/after, regions added/removed and overlapping
  trips; after the write the trip is found again by content. No delete.

### Fixed

- README version badge (was left at 0.3.1 in 0.4.0).

## [0.4.0]

### Added

- `series_items(series_id, query)`: a series' objects from its catalogue, including those with no map pin (Borders
  country pairs), with `ticked` and, for two-state objects, `other_crossing`.

### Changed

- `tick_series_item`: `lat`/`lon` are optional for objects found with `series_items`; Borders is writable;
  `other_crossing=true` ticks a pair's second box ("other border crossing between same countries").

## [0.3.1]

### Changed

- Tool descriptions say "the user" instead of a name, so the server reads right for any account.

## [0.3.0]

### Added

- `trips_for_year(year)`: a year's NomadMania trips, newest first, each with legs (region, country, dates, quality)
  in route order. Read live, one request per trip.

## [0.2.0]

### Added

- `series_rules(series_id)`: the series description as plain text, read live, so visit rules come from NomadMania
  instead of a direct-client script.

## [0.1.0]

### Added

- `profile_summary`, `list_series`, `series_near`, `unvisited_regions_near`, `tick_series_item` (`confirm=true`).
- wanderfill pinned at `d08c03ed8e0509afc9c788e2b5dbdcc9a23b13de`.
