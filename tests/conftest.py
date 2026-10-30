import shutil
from pathlib import Path

import pytest
from wanderfill.geo.tiles import TileReader

FIX = Path(__file__).parent / "fixtures"


class FixtureReader(TileReader):
    """Serves fixture tiles and treats every other tile as empty, so tests never touch the network."""

    def raw(self, layer, z, x, y):
        path = self.cache / layer / str(z) / str(x) / f"{y}.pbf"
        return path.read_bytes() if path.exists() else b""


@pytest.fixture
def reader(tmp_path):
    for f in FIX.glob("*.pbf"):
        layer, z, x, y = f.stem.split("_")
        dest = tmp_path / layer / z.lstrip("z") / x / f"{y}.pbf"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(f, dest)
    return FixtureReader(cache_dir=tmp_path)
