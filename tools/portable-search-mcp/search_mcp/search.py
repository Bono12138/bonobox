"""Search-provider boundary and result normalization."""

from __future__ import annotations

import os
import re
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

from ddgs import DDGS
from ddgs.exceptions import DDGSException


class SearchUnavailable(RuntimeError):
    """Raised when the upstream search providers cannot return a result."""


class SearchService:
    """Run bounded public-web searches without exposing provider errors."""

    def __init__(
        self,
        *,
        client_factory: Callable[[], Any] = DDGS,
        backend: str | None = None,
        retries: int = 1,
        retry_delay_seconds: float = 0.5,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._client_factory = client_factory
        self._backend = backend or os.getenv("SEARCH_MCP_BACKEND", "auto")
        self._retries = retries
        self._retry_delay_seconds = retry_delay_seconds
        self._now_factory = now_factory or (lambda: datetime.now().astimezone())

    def search(
        self,
        category: str,
        query: str,
        *,
        max_results: int,
        region: str,
        timelimit: str | None,
    ) -> list[dict[str, str]]:
        client = self._client_factory()
        method_name = {"web": "text", "news": "news", "images": "images"}[category]
        method = getattr(client, method_name)
        kwargs: dict[str, Any] = {
            "max_results": max_results,
            "region": region,
            "safesearch": "moderate",
            "backend": self._backend,
        }
        if timelimit is not None:
            kwargs["timelimit"] = timelimit

        for attempt in range(self._retries + 1):
            try:
                raw_results = method(query, **kwargs)
                now = self._now_factory()
                normalized = self._normalize(category, raw_results, now)
                if category == "news" and timelimit is not None:
                    return _filter_news_by_time(normalized, timelimit, now)
                return normalized
            except DDGSException as exc:
                if attempt >= self._retries:
                    raise SearchUnavailable(
                        "Search provider is temporarily unavailable."
                    ) from exc
                if self._retry_delay_seconds:
                    time.sleep(self._retry_delay_seconds)

        raise SearchUnavailable("Search provider is temporarily unavailable.")

    def _normalize(
        self,
        category: str,
        raw_results: list[dict[str, Any]],
        now: datetime,
    ) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        for item in raw_results:
            if category == "images":
                url = str(item.get("image") or item.get("url") or "")
                result = {
                    "title": str(item.get("title") or ""),
                    "url": url,
                    "thumbnail": str(item.get("thumbnail") or ""),
                    "source": str(item.get("source") or ""),
                }
            else:
                url = str(item.get("href") or item.get("url") or "")
                result = {
                    "title": str(item.get("title") or ""),
                    "url": url,
                    "snippet": str(
                        item.get("body")
                        or item.get("snippet")
                        or item.get("description")
                        or ""
                    ),
                    "source": str(item.get("source") or ""),
                }
                if category == "news":
                    result["published_at"] = _normalize_published_at(
                        str(item.get("date") or ""), now
                    )
            if _is_public_web_url(url):
                normalized.append(result)
        if category == "news":
            normalized.sort(
                key=lambda item: (bool(item.get("published_at")), item.get("published_at", "")),
                reverse=True,
            )
        return normalized


def _is_public_web_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_published_at(value: str, now: datetime) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    if parsed is not None:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()

    relative = re.search(r"(\d+)\s*(minute|hour|day)s?\s*ago", value, re.IGNORECASE)
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2).lower()
        delta = {
            "minute": timedelta(minutes=amount),
            "hour": timedelta(hours=amount),
            "day": timedelta(days=amount),
        }[unit]
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return (now.astimezone(timezone.utc) - delta).isoformat()
    return ""


def _filter_news_by_time(
    results: list[dict[str, str]], timelimit: str, now: datetime
) -> list[dict[str, str]]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local_now = now
    filtered: list[dict[str, str]] = []
    max_age_days = {"w": 7, "m": 31, "y": 365}
    for item in results:
        value = item.get("published_at", "")
        if not value:
            continue
        published = datetime.fromisoformat(value).astimezone(local_now.tzinfo)
        if timelimit == "d":
            keep = published.date() == local_now.date()
        else:
            keep = published >= local_now - timedelta(days=max_age_days[timelimit])
        if keep:
            filtered.append(item)
    return filtered
