import os
from datetime import datetime, timedelta, timezone

import pytest

from search_mcp.search import SearchService


pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def live_service():
    if os.getenv("RUN_LIVE_SEARCH_TESTS") != "1":
        pytest.skip("Set RUN_LIVE_SEARCH_TESTS=1 to call public search providers.")
    return SearchService(retries=1, retry_delay_seconds=0.5)


@pytest.mark.parametrize(
    ("category", "query", "timelimit"),
    [
        ("web", "Python official documentation", None),
        ("web", "人工智能 官方文档", None),
        ("images", "Python logo", None),
    ],
)
def test_live_search_returns_public_urls(live_service, category, query, timelimit):
    results = live_service.search(
        category,
        query,
        max_results=3,
        region="wt-wt",
        timelimit=timelimit,
    )

    assert results
    assert all(item["url"].startswith(("http://", "https://")) for item in results)


def test_latest_news_never_returns_undated_or_stale_items(live_service):
    results = live_service.search(
        "news",
        "artificial intelligence",
        max_results=10,
        region="wt-wt",
        timelimit="d",
    )
    parsed_dates = []
    for item in results:
        value = item.get("published_at")
        if value:
            parsed_dates.append(datetime.fromisoformat(value.replace("Z", "+00:00")))

    assert len(parsed_dates) == len(results)
    ages = [datetime.now(timezone.utc) - value.astimezone(timezone.utc) for value in parsed_dates]
    assert all(-timedelta(hours=1) <= age <= timedelta(hours=26) for age in ages)
