import sys
from pathlib import Path

import pytest

from smoke_test import SmokeTestError, check_protocol, validate_live_results


def test_protocol_smoke_check_uses_real_entrypoint():
    project_root = Path(__file__).resolve().parents[1]

    result = check_protocol(sys.executable, project_root / "ddgs-mcp-server.py")

    assert result == {
        "server": "portable-search-mcp",
        "tools": ["search_web", "search_news", "search_images"],
    }


def test_live_result_validation_requires_at_least_one_public_url():
    with pytest.raises(SmokeTestError):
        validate_live_results([])

    with pytest.raises(SmokeTestError):
        validate_live_results([{"url": "file:///local.txt"}])

    assert validate_live_results([{"url": "https://example.com"}]) == 1
