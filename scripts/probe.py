"""One-off live probe that dumps real API answers into `.probe/` (git-ignored). Read-only.

The committed fixtures are synthetic; use this to check a fact against the live API before changing them.
`uv run python scripts/probe.py tiles` needs no token; `api` reads NM_TOKEN from env or `.env`.
"""

import json
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

from wanderfill.geo.tiles import TileReader, deg2tile

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / ".probe"
ROME = (41.9028, 12.4964)


def dump(name: str, data) -> None:
    FIX.mkdir(exist_ok=True)
    (FIX / name).write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True))


def tiles() -> None:
    reader = TileReader(cache_dir=ROOT / ".probe-cache")
    for layer, z in (("series2", 9), ("regions", 6)):
        x, y = deg2tile(*ROME, z)
        reader.raw(layer, z, x, y)
        FIX.mkdir(exist_ok=True)
        shutil.copy(reader.cache / layer / str(z) / str(x) / f"{y}.pbf", FIX / f"{layer}_z{z}_{x}_{y}.pbf")
        print(layer, z, x, y)


def api() -> None:
    import os

    from wanderfill.api.client import NomadMania

    load_dotenv(ROOT / ".env")
    nm = NomadMania(os.environ["NM_TOKEN"])
    dump("series_list.json", nm.series_list())
    dump("series_1.json", nm.series(1))
    catalogue = nm.regions()
    dump("catalogue_sample.json", {str(k): v for k, v in list(catalogue.items())[:20]})
    x, y = deg2tile(*ROME, 6)
    in_tile = {int(p["id"]) for p, _ in TileReader(cache_dir=ROOT / ".probe-cache").polygons("regions", 6, x, y)}
    dump("catalogue_tile.json", {str(i): catalogue[i] for i in sorted(in_tile) if i in catalogue})
    uid = nm.account_id()
    dump("profile_scores.json", nm.profile(uid)["scores"])
    print("account", uid, "regions", len(catalogue))


if __name__ == "__main__":
    {"tiles": tiles, "api": api}[sys.argv[1]]()
