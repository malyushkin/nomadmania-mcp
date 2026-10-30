from unittest.mock import MagicMock, patch

import nomadmania_mcp.server as server


def test_profile_summary_shape():
    nm = MagicMock()
    nm.account_id.return_value = 42
    nm.profile.return_value = {"scores": {"score_nm": 300}}
    nm.visited_region_ids.return_value = {1, 2, 3}
    with patch("nomadmania_mcp.server.get_client", return_value=nm):
        out = server.profile_summary()
    assert out == {"account_id": 42, "scores": {"score_nm": 300}, "visited_regions": 3}
    nm.profile.assert_called_once_with(42)


def test_series_near_caps_radius_and_marks_ticked():
    nm = MagicMock()
    nm.series.return_value = {"visited": [82]}
    seen = {}

    def fake_near(reader, lat, lon, radius_km, series_ids=None):
        seen["radius"] = radius_km
        return {"objects": [{"id": 82, "series_id": 1}], "tiles_total": 1, "tiles_empty": 0}

    with (
        patch("nomadmania_mcp.server.get_client", return_value=nm),
        patch("nomadmania_mcp.server.get_tiles"),
        patch("nomadmania_mcp.server.series.objects_near", side_effect=fake_near),
    ):
        out = server.series_near(41.9, 12.5, radius_km=5000)
    assert seen["radius"] == 200
    assert out["objects"][0]["ticked"] is True
    assert "warning" not in out


def test_series_near_warns_when_every_tile_is_empty():
    with (
        patch("nomadmania_mcp.server.get_client"),
        patch("nomadmania_mcp.server.get_tiles"),
        patch(
            "nomadmania_mcp.server.series.objects_near",
            return_value={"objects": [], "tiles_total": 4, "tiles_empty": 4},
        ),
    ):
        out = server.series_near(0, 0)
    assert "warning" in out


def test_unvisited_regions_near_caps_radius():
    nm = MagicMock()
    nm.regions.return_value = {}
    nm.visited_region_ids.return_value = set()
    seen = {}

    def fake_near(reader, catalogue, visited, lat, lon, radius_km):
        seen["radius"] = radius_km
        return {"unvisited": [], "visited_nearby": 0, "tiles_total": 2, "tiles_empty": 0}

    with (
        patch("nomadmania_mcp.server.get_client", return_value=nm),
        patch("nomadmania_mcp.server.get_tiles"),
        patch("nomadmania_mcp.server.regions.near", side_effect=fake_near),
    ):
        server.unvisited_regions_near(52.37, 4.9, radius_km=9000)
    assert seen["radius"] == 1500


def test_visited_ids_read_strict_and_as_ints():
    nm = MagicMock()
    nm.regions.return_value = {}
    nm.visited_region_ids.return_value = {"29"}
    seen = {}

    def fake_near(reader, catalogue, visited, lat, lon, radius_km):
        seen["visited"] = visited
        return {"unvisited": [], "visited_nearby": 0, "tiles_total": 1, "tiles_empty": 0}

    with (
        patch("nomadmania_mcp.server.get_client", return_value=nm),
        patch("nomadmania_mcp.server.get_tiles"),
        patch("nomadmania_mcp.server.regions.near", side_effect=fake_near),
    ):
        server.unvisited_regions_near(41.9, 12.5)
    nm.visited_region_ids.assert_called_with(strict=True)
    assert seen["visited"] == {29}


def test_series_rules_strips_html():
    nm = MagicMock()
    nm.series.return_value = {
        "title": "Railway",
        "description": "<p>Trains &amp; metros.</p>\n<p><b>Note:</b> the   platform does not count.</p>",
    }
    with patch("nomadmania_mcp.server.get_client", return_value=nm):
        out = server.series_rules(11)
    assert out == {"id": 11, "title": "Railway", "description": "Trains & metros. Note: the platform does not count."}
    nm.series.assert_called_once_with(11)


def test_series_rules_empty_description():
    nm = MagicMock()
    nm.series.return_value = {"title": "Culinary Delights", "description": None}
    with patch("nomadmania_mcp.server.get_client", return_value=nm):
        assert server.series_rules(67)["description"] == ""
