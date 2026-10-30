import math

from wanderfill.geo.tiles import deg2tile, tile_bounds

from nomadmania_mcp.geo import tiles_for_radius


def test_tiles_for_radius_covers_neighbour_across_edge():
    west, south, east, north = tile_bounds(273, 190, 9)
    lat = (south + north) / 2
    lon = east - 0.5 / (111.32 * math.cos(math.radians(lat)))
    assert deg2tile(lat, lon, 9) == (273, 190)
    tiles = tiles_for_radius(lat, lon, 2, 9)
    assert {(273, 190), (274, 190)} <= tiles


def test_tiles_for_radius_wraps_antimeridian():
    tiles = tiles_for_radius(0.0, 179.99, 5, 4)
    assert (0, deg2tile(0.0, 179.99, 4)[1]) in tiles


def test_tiles_for_radius_wraps_west_of_antimeridian():
    tiles = tiles_for_radius(0.0, -179.99, 5, 4)
    assert any(x == 15 for x, _ in tiles)
