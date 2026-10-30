<h1 align="center">
  <img src="assets/logo.svg" alt="" width="72"><br>
  nomadmania-mcp
</h1>

<p align="center">Your <a href="https://nomadmania.com">NomadMania</a> profile in your AI agent: series, regions, trips.</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.6.0-blue?style=for-the-badge" alt="version">
  <img src="https://img.shields.io/badge/python-3.13%2B-blue?style=for-the-badge" alt="python 3.13+">
  <img src="https://img.shields.io/badge/protocol-MCP-6366f1?style=for-the-badge" alt="MCP">
  <img src="https://img.shields.io/badge/license-Apache--2.0-green?style=for-the-badge" alt="Apache-2.0">
  <a href="https://github.com/malyushkin/nomadmania-mcp/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/malyushkin/nomadmania-mcp/tests.yml?branch=main&label=tests&style=for-the-badge" alt="tests"></a>
</p>

> **Unofficial and unaffiliated.** NomadMania is a trademark of NomadMania OÜ. This project is not affiliated with,
> endorsed by or supported by NomadMania. Please do not contact them about bugs in this tool.

An MCP server for your own NomadMania profile. An AI agent can read the profile, find series objects and unvisited
regions near a point, list and edit trips, and tick a series object. Every write is a preview until the agent passes
`confirm=true`, and every write is read back to check it landed.

It is built on [`faeton/wanderfill`](https://github.com/faeton/wanderfill), an unofficial client for NomadMania's
private API that does the hard part: the API client, the tile reader and the region catalogue. This repo adds the MCP
layer and the series and trip logic on top. API facts confirmed live: [`docs/live-facts.md`](docs/live-facts.md).

## Try asking

- "Which World Capitals within 200 km of Vienna haven't I ticked yet?"
- "What counts as a visit for UNESCO World Heritage Sites?"
- "I crossed the Croatia-Montenegro border last week. Tick it."
- "Which regions within 500 km of Lisbon have I not visited?"
- "Show my trips for this year, with the dates in each region."

## Install

You need [uv](https://docs.astral.sh/uv/) and a NomadMania token: on nomadmania.com, run
`localStorage.getItem('token')` in the browser console. The token is valid for about a year and gives full access to
your account, so keep it private.

### Claude Code

As a plugin. It asks for the token and adds the agent rules from [`skills/nomadmania`](skills/nomadmania/SKILL.md):

```text
/plugin install nomadmania --marketplace malyushkin/nomadmania-mcp
```

Or the server alone:

```bash
claude mcp add nomadmania --env NM_TOKEN=<token> -- uvx --from git+https://github.com/malyushkin/nomadmania-mcp nomadmania-mcp
```

### Cursor, VS Code

Install links: [Cursor](https://cursor.com/en/install-mcp?name=nomadmania&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyItLWZyb20iLCJnaXQraHR0cHM6Ly9naXRodWIuY29tL21hbHl1c2hraW4vbm9tYWRtYW5pYS1tY3AiLCJub21hZG1hbmlhLW1jcCJdLCJlbnYiOnsiTk1fVE9LRU4iOiIifX0=) (fill in `NM_TOKEN` in the install dialog), [VS Code](https://insiders.vscode.dev/redirect/mcp/install?name=nomadmania&inputs=%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22nm_token%22%2C%22description%22%3A%22NomadMania%20token%22%2C%22password%22%3Atrue%7D%5D&config=%7B%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22git%2Bhttps%3A%2F%2Fgithub.com%2Fmalyushkin%2Fnomadmania-mcp%22%2C%22nomadmania-mcp%22%5D%2C%22env%22%3A%7B%22NM_TOKEN%22%3A%22%24%7Binput%3Anm_token%7D%22%7D%7D) (asks for the token).

### Other MCP clients

```json
{
  "mcpServers": {
    "nomadmania": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/malyushkin/nomadmania-mcp", "nomadmania-mcp"],
      "env": { "NM_TOKEN": "<token>" }
    }
  }
}
```

`NM_CACHE_DIR` (default `~/.cache/nomadmania-mcp`) holds the region catalogue and map tiles.

## Tools

| Tool                     | What                                                                                                                 |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| `profile_summary`        | Account id, the scores the profile page shows, visited region count                                                  |
| `list_series`            | All 69 series: id, name, object count                                                                                |
| `series_rules`           | A series' description as plain text, read live: the only place its visit rule is stated                              |
| `series_near`            | Series objects within `radius_km` (≤200) of a point, nearest first, with `ticked`                                    |
| `series_items`           | One series' objects from its catalogue, pinned or not, filtered by name/country, with `ticked`                       |
| `save_trip`              | Preview by default; edits (`trip_id`) or creates a trip with `confirm=true`, then finds it again to verify           |
| `trips_for_year`         | Trips entered in NomadMania for a year, newest first, with dated legs (region per stretch of the route)              |
| `unvisited_regions_near` | Regions not marked visited within `radius_km` (≤1500), nearest first, plus visited count                             |
| `tick_series_item`       | Preview by default; ticks with `confirm=true`, then re-reads to verify (`verified`, `also_ticked`, `scores_changed`) |

The writes are `tick_series_item` and `save_trip`. One place has a different id in each series (Rome: `82` in World Capitals,
`1692` in European Cities), so the preview lists `likely_also` by name and position, and the result reports what
actually got ticked. Objects without a map pin (Borders country pairs) come from `series_items` and tick without
`lat`/`lon`. A Borders pair has a second box, "other border crossing between same countries": `other_crossing=true`
ticks it, only once the first box is ticked. Experiences (`17`) and Top of the tops (`-2`) are read-only. There is no
untick.

`save_trip` posts what the site's trip form posts (`trips/update-trip`, `trips/new-trip`): the whole trip, not a
patch. An edited trip can come back under a new `trip_id`, so verification finds it by title and legs. There is no
trip delete.

## For AI agents

The plugin loads these rules as a skill; with the server alone, give them to your agent yourself
([`skills/nomadmania/SKILL.md`](skills/nomadmania/SKILL.md) has the full list).

- Writes (`tick_series_item`, `save_trip`) return a preview by default. Show it to the user and pass `confirm=true`
  only after they agree.
- There is no untick and no trip delete. A wrong write has to be fixed by hand on the site.
- Read `series_rules` before telling the user what counts as a visit. The rule lives only in the series description.
- A tick can also tick the same place in other series. Check `also_ticked` in the result.
- A `warning` from a geo tool means every tile came back empty. That usually means the network failed.

## Development

```bash
uv sync
printf 'NM_TOKEN=...\n' > .env && chmod 600 .env
uv run nomadmania-mcp
```

## Updating wanderfill

wanderfill is pinned to a commit in `pyproject.toml` (`[tool.uv.sources]`), because it is alpha and wraps a private
API. To update:

1. Set `rev` to the new commit, run `uv lock`.
2. `uv run pytest`, then a live `series_near` and `unvisited_regions_near`.
3. Bump the version (`pyproject.toml`, badge, `CHANGELOG.md` with the new rev).

`scripts/probe.py` dumps real API answers into `.probe/` (git-ignored) to check a fact before changing the synthetic
fixtures (`tiles` needs no token, `api` does).

## Tests

`uv run pytest`. The fixtures in `tests/fixtures/` are synthetic: a few hand-placed objects around Rome, made-up trips
and account id `12345`. `scripts/make_fixture_tiles.py` writes the map tiles. The repo holds no real profile data and
no NomadMania catalogue.

## For NomadMania

If you would like this changed or taken down, open an issue and it will happen.

This project ships none of NomadMania's data: no catalogue, no polygons, no tiles. Everything is fetched at runtime
with the user's own token, and the server only does what an account holder can do on the site with their own profile.
Anything that looks like a missing authorisation check gets reported privately and stays out of this repo.

## License

Apache-2.0, same as wanderfill. See [LICENSE](LICENSE).
