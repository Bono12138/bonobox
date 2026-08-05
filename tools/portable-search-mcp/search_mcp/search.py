"""Search-provider boundary and result normalization."""

from __future__ import annotations

import os
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from ddgs import DDGS
from ddgs.exceptions import DDGSException


class SearchUnavailable(RuntimeError):
    """Raised when the upstream search providers cannot return a result."""


def _default_client_factory() -> DDGS:
    return DDGS(timeout=3)


class SearchService:
    """Run bounded public-web searches without exposing provider errors."""

    def __init__(
        self,
        *,
        client_factory: Callable[[], Any] = _default_client_factory,
        news_fallback: Callable[[str, str, str | None, int], list[dict[str, Any]]] | None = None,
        backend: str | None = None,
        retries: int = 1,
        retry_delay_seconds: float = 0.5,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._client_factory = client_factory
        self._news_fallback = (
            news_fallback
            if news_fallback is not None
            else (
                _search_google_news_rss
                if client_factory in {DDGS, _default_client_factory}
                else None
            )
        )
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
        navigation_core = _official_navigation_core(query) if category == "web" else None
        candidate_limit = max_results
        if category == "news":
            candidate_limit = max(20, max_results)
        elif navigation_core:
            candidate_limit = max(10, max_results)
        kwargs: dict[str, Any] = {
            "max_results": candidate_limit,
            "region": region,
            "safesearch": "moderate",
            "backend": self._backend_for(category),
        }
        if timelimit is not None:
            kwargs["timelimit"] = timelimit

        news_fallback_tried = False
        if category == "news" and self._news_fallback is not None:
            fallback = self._run_news_fallback(
                query, region, timelimit, candidate_limit, self._now_factory()
            )
            news_fallback_tried = True
            if fallback:
                return fallback[:max_results]
        for attempt in range(self._retries + 1):
            try:
                attempt_kwargs = dict(kwargs)
                if category == "news":
                    regions = _news_region_candidates(region)
                    attempt_kwargs["region"] = regions[min(attempt, len(regions) - 1)]
                now = self._now_factory()
                if category == "web" and navigation_core:
                    normalized: list[dict[str, str]] = []
                    last_error: DDGSException | None = None
                    for planned_query in _navigation_query_plan(query, navigation_core):
                        if _has_confident_navigation_result(normalized, navigation_core):
                            break
                        try:
                            planned_results = method(planned_query, **attempt_kwargs)
                        except DDGSException as exc:
                            last_error = exc
                            continue
                        normalized.extend(self._normalize(category, planned_results, now))
                    if not normalized and last_error is not None:
                        raise last_error
                    normalized = _rank_navigation_results(
                        _deduplicate_results(normalized), navigation_core
                    )
                else:
                    raw_results = method(query, **attempt_kwargs)
                    normalized = self._normalize(category, raw_results, now)
                if category == "news":
                    filtered = (
                        _filter_news_by_time(normalized, timelimit, now)
                        if timelimit is not None
                        else normalized
                    )
                    if filtered:
                        return filtered[:max_results]
                    if not news_fallback_tried:
                        fallback = self._run_news_fallback(
                            query, region, timelimit, candidate_limit, now
                        )
                        news_fallback_tried = True
                        if fallback:
                            return fallback[:max_results]
                    if attempt < self._retries:
                        if self._retry_delay_seconds:
                            time.sleep(self._retry_delay_seconds)
                        continue
                    return []
                return normalized[:max_results]
            except DDGSException as exc:
                if category == "news" and not news_fallback_tried:
                    fallback = self._run_news_fallback(
                        query,
                        region,
                        timelimit,
                        candidate_limit,
                        self._now_factory(),
                    )
                    news_fallback_tried = True
                    if fallback:
                        return fallback[:max_results]
                if attempt >= self._retries:
                    raise SearchUnavailable(
                        "Search provider is temporarily unavailable."
                    ) from exc
                if self._retry_delay_seconds:
                    time.sleep(self._retry_delay_seconds)

        raise SearchUnavailable("Search provider is temporarily unavailable.")

    def _run_news_fallback(
        self,
        query: str,
        region: str,
        timelimit: str | None,
        max_results: int,
        now: datetime,
    ) -> list[dict[str, str]] | None:
        if self._news_fallback is None:
            return None
        try:
            raw_results = self._news_fallback(query, region, timelimit, max_results)
        except Exception:  # noqa: BLE001 - external RSS failures must stay sanitized
            return None
        normalized = self._normalize("news", raw_results, now)
        if timelimit is not None:
            normalized = _filter_news_by_time(normalized, timelimit, now)
        return _deduplicate_results(normalized)

    def _backend_for(self, category: str) -> str:
        if self._backend != "auto":
            return self._backend
        if category == "news":
            return "bing,duckduckgo,yahoo"
        if category == "images":
            return "bing,duckduckgo"
        return "auto"

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


def _search_google_news_rss(
    query: str,
    region: str,
    timelimit: str | None,
    max_results: int,
) -> list[dict[str, Any]]:
    locale = {
        "cn-zh": ("zh-CN", "CN", "CN:zh-Hans"),
        "us-en": ("en-US", "US", "US:en"),
    }.get(region, ("en-US", "US", "US:en"))
    recency = {"d": "1d", "w": "7d", "m": "31d", "y": "365d"}.get(timelimit)
    rss_query = f"{query} when:{recency}" if recency else query
    params = urlencode(
        {"q": rss_query, "hl": locale[0], "gl": locale[1], "ceid": locale[2]}
    )
    request = Request(
        f"https://news.google.com/rss/search?{params}",
        headers={"User-Agent": "BonoBox-Portable-Search/2.0"},
    )
    with urlopen(request, timeout=8) as response:  # noqa: S310 - fixed HTTPS host
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError("News RSS response exceeded the safe size limit.")
    root = ET.fromstring(payload)
    results: list[dict[str, Any]] = []
    for item in root.findall("./channel/item")[:max_results]:
        description = unescape(re.sub(r"<[^>]+>", " ", item.findtext("description") or ""))
        results.append(
            {
                "title": item.findtext("title") or "",
                "url": item.findtext("link") or "",
                "body": re.sub(r"\s+", " ", description).strip(),
                "source": item.findtext("source") or "Google News",
                "date": item.findtext("pubDate") or "",
            }
        )
    return results


def _official_navigation_core(query: str) -> str | None:
    if re.search(r"\bsite\s*:", query, re.IGNORECASE):
        return None
    markers = (
        r"official\s+(?:website|site|documentation|docs?)",
        r"official",
        r"官方网站",
        r"官网",
        r"官方文档",
    )
    if not any(re.search(marker, query, re.IGNORECASE) for marker in markers):
        return None
    core = query
    for marker in markers:
        core = re.sub(marker, " ", core, flags=re.IGNORECASE)
    core = re.sub(r"\s+", " ", core).strip(" -—_:：")
    return core or None


def _navigation_query_plan(query: str, core: str) -> list[str]:
    canonical = query
    if "官方网站" in query or "官网" in query:
        canonical = f"{core} 官方"
        return [canonical, f"site:gov.cn {core}", query]
    else:
        lowered = query.lower()
        if re.search(r"official\s+(?:documentation|docs?)", lowered):
            canonical = f"{core} documentation"
        elif re.search(r"official\s+(?:website|site)", lowered):
            canonical = f"{core} homepage"
    return [canonical] if canonical == query else [canonical, query]


def _news_region_candidates(region: str) -> list[str]:
    candidates = [region]
    for fallback in ("wt-wt", "us-en"):
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


def _compact_text(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _navigation_score(item: dict[str, str], core: str) -> int:
    title = _compact_text(item.get("title", ""))
    core_compact = _compact_text(core)
    domain = _compact_text(urlsplit(item.get("url", "")).hostname or "")
    score = 0
    if title == core_compact:
        score += 20
    elif title.startswith(core_compact):
        score += 12
    elif core_compact and core_compact in title:
        score += 8
    for token in re.findall(r"[a-z0-9]{3,}", core.lower()):
        if token in domain:
            score += 4
    hostname = (urlsplit(item.get("url", "")).hostname or "").lower()
    if hostname.endswith("wikipedia.org") or hostname.endswith("wikidata.org"):
        score -= 20
    if hostname.endswith(".gov") or ".gov." in hostname:
        score += 2
    return score


def _has_confident_navigation_result(
    results: list[dict[str, str]], core: str
) -> bool:
    threshold = 4 if re.search(r"[a-z]", core, re.IGNORECASE) else 12
    return any(_navigation_score(item, core) >= threshold for item in results)


def _rank_navigation_results(
    results: list[dict[str, str]], core: str
) -> list[dict[str, str]]:
    return [
        item
        for _, item in sorted(
            enumerate(results),
            key=lambda pair: (-_navigation_score(pair[1], core), pair[0]),
        )
    ]


def _deduplicate_results(results: list[dict[str, str]]) -> list[dict[str, str]]:
    deduplicated: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in results:
        url = item.get("url", "")
        if url in seen:
            continue
        seen.add(url)
        deduplicated.append(item)
    return deduplicated


def _normalize_published_at(value: str, now: datetime) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    if parsed is None:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
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
