from functools import cache

from wanderfill.api.cache import ReadCache
from wanderfill.api.client import NomadMania
from wanderfill.api.errors import ApiError, AuthError
from wanderfill.geo.tiles import TileReader

from . import config


@cache
def get_client() -> NomadMania:
    if not config.TOKEN:
        raise ValueError("NM_TOKEN is not set")
    return NomadMania(config.TOKEN, cache=ReadCache(config.CACHE_DIR / "api"))


@cache
def get_tiles() -> TileReader:
    return TileReader(cache_dir=config.CACHE_DIR / "tiles")


def friendly(exc: Exception) -> str:
    # ApiError keeps the raw payload on `.payload`; only the action and description are safe to show.
    if isinstance(exc, AuthError):
        return "NomadMania rejected the token; refresh NM_TOKEN"
    if isinstance(exc, ApiError):
        return f"{exc.action}: {exc.description}"
    return str(exc)
