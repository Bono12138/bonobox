from datetime import datetime, timedelta, timezone

import pytest
from ddgs.exceptions import DDGSException

from search_mcp.search import SearchService, SearchUnavailable


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = []

    def _next(self, method, query, **kwargs):
        self.calls.append((method, query, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def text(self, query, **kwargs):
        return self._next("text", query, **kwargs)

    def news(self, query, **kwargs):
        return self._next("news", query, **kwargs)

    def images(self, query, **kwargs):
        return self._next("images", query, **kwargs)


def test_web_search_normalizes_current_result_shape():
    client = FakeClient(
        [[{"title": "Docs", "href": "https://example.com", "body": "Summary"}]]
    )
    service = SearchService(client_factory=lambda: client, retry_delay_seconds=0)

    results = service.search(
        "web", "docs", max_results=5, region="wt-wt", timelimit=None
    )

    assert results == [
        {
            "title": "Docs",
            "url": "https://example.com",
            "snippet": "Summary",
            "source": "",
        }
    ]
    assert client.calls == [
        (
            "text",
            "docs",
            {
                "max_results": 5,
                "region": "wt-wt",
                "safesearch": "moderate",
                "backend": "auto",
            },
        )
    ]


def test_news_search_maps_url_and_source_fields():
    client = FakeClient(
        [
            [
                {
                    "title": "News",
                    "url": "https://example.com/news",
                    "body": "Summary",
                    "source": "Publisher",
                    "date": "2026-08-05T02:30:00+00:00",
                }
            ]
        ]
    )
    service = SearchService(client_factory=lambda: client, retry_delay_seconds=0)

    results = service.search(
        "news", "topic", max_results=2, region="us-en", timelimit="d"
    )

    assert results[0] == {
        "title": "News",
        "url": "https://example.com/news",
        "snippet": "Summary",
        "source": "Publisher",
        "published_at": "2026-08-05T02:30:00+00:00",
    }
    assert client.calls[0][2]["timelimit"] == "d"


def test_news_results_are_sorted_by_published_time_with_undated_items_last():
    client = FakeClient(
        [
            [
                {
                    "title": "Older",
                    "url": "https://example.com/older",
                    "date": "2026-08-04T08:00:00+00:00",
                },
                {"title": "Undated", "url": "https://example.com/undated"},
                {
                    "title": "Newer",
                    "url": "https://example.com/newer",
                    "date": "2026-08-05T08:00:00+00:00",
                },
            ]
        ]
    )
    service = SearchService(client_factory=lambda: client, retry_delay_seconds=0)

    results = service.search(
        "news", "topic", max_results=3, region="wt-wt", timelimit=None
    )

    assert [item["title"] for item in results] == ["Newer", "Older", "Undated"]
    assert results[-1]["published_at"] == ""


def test_news_relative_time_with_prefix_is_normalized_to_utc_iso_time():
    client = FakeClient(
        [
            [
                {
                    "title": "Recent",
                    "url": "https://example.com/recent",
                    "date": "Opinion44 minutes ago",
                }
            ]
        ]
    )
    service = SearchService(
        client_factory=lambda: client,
        retry_delay_seconds=0,
        now_factory=lambda: datetime(2026, 8, 5, 4, 0, tzinfo=timezone.utc),
    )

    results = service.search(
        "news", "topic", max_results=1, region="wt-wt", timelimit=None
    )

    assert results[0]["published_at"] == "2026-08-05T03:16:00+00:00"


def test_unparseable_news_time_is_not_presented_as_a_date():
    client = FakeClient(
        [[{"title": "Unknown", "url": "https://example.com/unknown", "date": "recent"}]]
    )
    service = SearchService(client_factory=lambda: client, retry_delay_seconds=0)

    results = service.search(
        "news", "topic", max_results=1, region="wt-wt", timelimit=None
    )

    assert results[0]["published_at"] == ""


def test_day_limited_news_keeps_only_current_local_calendar_day():
    client = FakeClient(
        [
            [
                {
                    "title": "Today",
                    "url": "https://example.com/today",
                    "date": "2026-08-05T01:00:00+00:00",
                },
                {
                    "title": "Yesterday",
                    "url": "https://example.com/yesterday",
                    "date": "2026-08-04T23:30:00+00:00",
                },
                {"title": "Undated", "url": "https://example.com/undated"},
            ]
        ]
    )
    service = SearchService(
        client_factory=lambda: client,
        retry_delay_seconds=0,
        now_factory=lambda: datetime(2026, 8, 5, 2, 0, tzinfo=timezone.utc),
    )

    results = service.search(
        "news", "topic", max_results=3, region="wt-wt", timelimit="d"
    )

    assert [item["title"] for item in results] == ["Today"]


@pytest.mark.parametrize(
    ("timelimit", "kept_age", "removed_age"),
    [("w", 6, 8), ("m", 30, 32), ("y", 364, 366)],
)
def test_longer_news_limits_remove_results_outside_window(
    timelimit, kept_age, removed_age
):
    now = datetime(2026, 8, 5, 2, 0, tzinfo=timezone.utc)
    client = FakeClient(
        [
            [
                {
                    "title": "Inside",
                    "url": "https://example.com/inside",
                    "date": (now - timedelta(days=kept_age)).isoformat(),
                },
                {
                    "title": "Outside",
                    "url": "https://example.com/outside",
                    "date": (now - timedelta(days=removed_age)).isoformat(),
                },
            ]
        ]
    )
    service = SearchService(
        client_factory=lambda: client,
        retry_delay_seconds=0,
        now_factory=lambda: now,
    )

    results = service.search(
        "news", "topic", max_results=2, region="wt-wt", timelimit=timelimit
    )

    assert [item["title"] for item in results] == ["Inside"]


def test_image_search_uses_full_image_url_and_thumbnail():
    client = FakeClient(
        [
            [
                {
                    "title": "Diagram",
                    "image": "https://example.com/full.png",
                    "thumbnail": "https://example.com/thumb.png",
                    "source": "Example",
                }
            ]
        ]
    )
    service = SearchService(client_factory=lambda: client, retry_delay_seconds=0)

    results = service.search(
        "images", "diagram", max_results=1, region="wt-wt", timelimit=None
    )

    assert results[0] == {
        "title": "Diagram",
        "url": "https://example.com/full.png",
        "thumbnail": "https://example.com/thumb.png",
        "source": "Example",
    }


def test_results_without_http_url_are_removed():
    client = FakeClient(
        [
            [
                {"title": "Missing", "href": "", "body": "No URL"},
                {"title": "Unsafe", "href": "file:///secret", "body": "Local"},
                {"title": "Good", "href": "https://example.com", "body": "OK"},
            ]
        ]
    )
    service = SearchService(client_factory=lambda: client, retry_delay_seconds=0)

    results = service.search(
        "web", "x", max_results=3, region="wt-wt", timelimit=None
    )

    assert [item["title"] for item in results] == ["Good"]


def test_transient_failure_is_retried_once():
    client = FakeClient(
        [
            DDGSException("temporary failure"),
            [{"title": "Recovered", "href": "https://example.com", "body": "OK"}],
        ]
    )
    service = SearchService(client_factory=lambda: client, retries=1, retry_delay_seconds=0)

    results = service.search(
        "web", "retry", max_results=1, region="wt-wt", timelimit=None
    )

    assert results[0]["title"] == "Recovered"
    assert len(client.calls) == 2


def test_exhausted_failures_raise_sanitized_error():
    client = FakeClient(
        [DDGSException("upstream included query text"), DDGSException("still unavailable")]
    )
    service = SearchService(client_factory=lambda: client, retries=1, retry_delay_seconds=0)

    try:
        service.search("web", "sensitive query", max_results=1, region="wt-wt", timelimit=None)
    except SearchUnavailable as exc:
        assert str(exc) == "Search provider is temporarily unavailable."
    else:
        raise AssertionError("SearchUnavailable was not raised")
