from unittest.mock import patch

import pytest
from wanderfill.api.errors import ApiError, AuthError

from nomadmania_mcp import client


def test_get_client_without_token_raises():
    client.get_client.cache_clear()
    with patch("nomadmania_mcp.client.config.TOKEN", None):
        with pytest.raises(ValueError, match="NM_TOKEN is not set"):
            client.get_client()


def test_friendly_auth_error_hides_token():
    with patch("nomadmania_mcp.client.config.TOKEN", "secret-token"):
        msg = client.friendly(AuthError("server rejected the token (401)"))
    assert msg == "NomadMania rejected the token; refresh NM_TOKEN"
    assert "secret-token" not in msg


def test_friendly_api_error_drops_payload():
    msg = client.friendly(ApiError("series/get-list", "boom", {"token": "secret-token"}))
    assert msg == "series/get-list: boom"
