"""Run a broad, reproducible live benchmark without storing result content."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from search_mcp.search import SearchService, SearchUnavailable


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    category: str
    query: str
    region: str
    timelimit: str | None = None
    expected_domain: str | None = None
    query_style: str | None = None


CASES = [
    BenchmarkCase(
        "web-python-docs",
        "web",
        "Python 3.13 official documentation",
        "us-en",
        expected_domain="docs.python.org",
        query_style="plain",
    ),
    BenchmarkCase(
        "web-mcp-docs",
        "web",
        "Model Context Protocol official documentation",
        "us-en",
        expected_domain="modelcontextprotocol.io",
        query_style="plain",
    ),
    BenchmarkCase(
        "web-pbc",
        "web",
        "中国人民银行 官方网站",
        "cn-zh",
        expected_domain="pbc.gov.cn",
        query_style="plain",
    ),
    BenchmarkCase(
        "web-microsoft-learn",
        "web",
        "Microsoft Learn PowerShell official documentation",
        "us-en",
        expected_domain="learn.microsoft.com",
        query_style="plain",
    ),
    BenchmarkCase(
        "web-github-docs",
        "web",
        "GitHub official documentation",
        "us-en",
        expected_domain="docs.github.com",
        query_style="plain",
    ),
    BenchmarkCase(
        "web-china-government",
        "web",
        "中国政府网 官方网站",
        "cn-zh",
        expected_domain="gov.cn",
        query_style="plain",
    ),
    BenchmarkCase(
        "web-chinese-topic",
        "web",
        "生成式人工智能 服务管理 暂行办法 官方",
        "cn-zh",
    ),
    BenchmarkCase("web-rfc-9110", "web", "RFC 9110 HTTP semantics", "us-en"),
    BenchmarkCase(
        "web-cisa-zero-trust", "web", "CISA zero trust maturity model", "us-en"
    ),
    BenchmarkCase(
        "web-eu-ai-act", "web", "European Union AI Act official text", "us-en"
    ),
    BenchmarkCase(
        "web-python-release", "web", "Python latest stable release notes", "us-en"
    ),
    BenchmarkCase(
        "web-cn-data-security-law", "web", "中华人民共和国数据安全法 原文", "cn-zh"
    ),
    BenchmarkCase("image-python", "images", "Python logo", "wt-wt"),
    BenchmarkCase("image-toolbox", "images", "cute toolbox icon", "wt-wt"),
    BenchmarkCase("image-world-map", "images", "world map outline", "wt-wt"),
    BenchmarkCase("image-rabbit", "images", "长耳兔 工具箱 插画", "cn-zh"),
    BenchmarkCase("news-ai-en", "news", "artificial intelligence", "wt-wt", "d"),
    BenchmarkCase("news-ai-zh", "news", "人工智能", "cn-zh", "d"),
    BenchmarkCase("news-markets-en", "news", "financial markets", "wt-wt", "d"),
    BenchmarkCase("news-pbc-zh", "news", "中国人民银行", "cn-zh", "d"),
    BenchmarkCase("news-cyber-en", "news", "cybersecurity", "wt-wt", "w"),
    BenchmarkCase("news-tech-policy-zh", "news", "科技政策", "cn-zh", "w"),
    BenchmarkCase("news-climate-en", "news", "climate policy", "wt-wt", "d"),
    BenchmarkCase("news-chip-zh", "news", "半导体", "cn-zh", "w"),
    BenchmarkCase(
        "web-site-python-docs",
        "web",
        "site:docs.python.org Python 3.13",
        "us-en",
        expected_domain="docs.python.org",
        query_style="site",
    ),
    BenchmarkCase(
        "web-site-mcp-docs",
        "web",
        "site:modelcontextprotocol.io specification",
        "us-en",
        expected_domain="modelcontextprotocol.io",
        query_style="site",
    ),
    BenchmarkCase(
        "web-site-pbc",
        "web",
        "site:pbc.gov.cn 中国人民银行",
        "cn-zh",
        expected_domain="pbc.gov.cn",
        query_style="site",
    ),
    BenchmarkCase(
        "web-site-microsoft-learn",
        "web",
        "site:learn.microsoft.com PowerShell documentation",
        "us-en",
        expected_domain="learn.microsoft.com",
        query_style="site",
    ),
    BenchmarkCase(
        "web-site-github-docs",
        "web",
        "site:docs.github.com GitHub actions",
        "us-en",
        expected_domain="docs.github.com",
        query_style="site",
    ),
    BenchmarkCase(
        "web-site-china-government",
        "web",
        "site:gov.cn 国务院 政策",
        "cn-zh",
        expected_domain="gov.cn",
        query_style="site",
    ),
]


def _domain(value: str) -> str:
    return (urlsplit(value).hostname or "").lower().removeprefix("www.")


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction + 0.5)))
    return ordered[index]


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def run_benchmark(
    service: Any,
    *,
    rounds: int = 3,
    max_results: int = 5,
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    for round_number in range(1, rounds + 1):
        for case in CASES:
            started = time.perf_counter()
            error = ""
            results: list[dict[str, str]] = []
            try:
                results = service.search(
                    case.category,
                    case.query,
                    max_results=max_results,
                    region=case.region,
                    timelimit=case.timelimit,
                )
            except SearchUnavailable:
                error = "provider_unavailable"
            latency = time.perf_counter() - started
            domains = [_domain(item.get("url", "")) for item in results]
            domain_rank = None
            if case.expected_domain:
                domain_rank = next(
                    (
                        index
                        for index, domain in enumerate(domains, start=1)
                        if domain == case.expected_domain
                        or domain.endswith(f".{case.expected_domain}")
                    ),
                    None,
                )
            observations.append(
                {
                    "round": round_number,
                    "case_id": case.id,
                    "category": case.category,
                    "query": case.query,
                    "region": case.region,
                    "timelimit": case.timelimit,
                    "latency_seconds": round(latency, 3),
                    "request_ok": not error,
                    "result_count": len(results),
                    "valid_url_count": sum(bool(domain) for domain in domains),
                    "unique_url_count": len(
                        {item.get("url", "") for item in results if item.get("url")}
                    ),
                    "dated_result_count": sum(
                        bool(item.get("published_at")) for item in results
                    )
                    if case.category == "news"
                    else None,
                    "expected_domain": case.expected_domain,
                    "query_style": case.query_style,
                    "expected_domain_rank": domain_rank,
                    "expected_domain_in_top5": domain_rank is not None and domain_rank <= 5,
                    "top_domains": domains[:5],
                    "error": error,
                }
            )

    latencies = [item["latency_seconds"] for item in observations]
    web_image = [item for item in observations if item["category"] in {"web", "images"}]
    navigational_plain = [item for item in observations if item["query_style"] == "plain"]
    navigational_site = [item for item in observations if item["query_style"] == "site"]
    news = [item for item in observations if item["category"] == "news"]
    all_results = sum(item["result_count"] for item in observations)
    summary = {
        "requests": len(observations),
        "request_successes": sum(item["request_ok"] for item in observations),
        "request_success_rate": _rate(
            sum(item["request_ok"] for item in observations), len(observations)
        ),
        "web_image_nonempty_runs": sum(item["result_count"] > 0 for item in web_image),
        "web_image_runs": len(web_image),
        "web_image_nonempty_rate": _rate(
            sum(item["result_count"] > 0 for item in web_image), len(web_image)
        ),
        "plain_query_top5_hits": sum(
            item["expected_domain_in_top5"] is True for item in navigational_plain
        ),
        "plain_query_top1_hits": sum(
            item["expected_domain_rank"] == 1 for item in navigational_plain
        ),
        "plain_query_top3_hits": sum(
            item["expected_domain_rank"] is not None
            and item["expected_domain_rank"] <= 3
            for item in navigational_plain
        ),
        "plain_query_runs": len(navigational_plain),
        "plain_query_top5_hit_rate": _rate(
            sum(item["expected_domain_in_top5"] is True for item in navigational_plain)
            , len(navigational_plain)
        ),
        "plain_query_top1_hit_rate": _rate(
            sum(item["expected_domain_rank"] == 1 for item in navigational_plain),
            len(navigational_plain),
        ),
        "plain_query_top3_hit_rate": _rate(
            sum(
                item["expected_domain_rank"] is not None
                and item["expected_domain_rank"] <= 3
                for item in navigational_plain
            ),
            len(navigational_plain),
        ),
        "site_query_top5_hits": sum(
            item["expected_domain_in_top5"] is True for item in navigational_site
        ),
        "site_query_top1_hits": sum(
            item["expected_domain_rank"] == 1 for item in navigational_site
        ),
        "site_query_top3_hits": sum(
            item["expected_domain_rank"] is not None
            and item["expected_domain_rank"] <= 3
            for item in navigational_site
        ),
        "site_query_runs": len(navigational_site),
        "site_query_top5_hit_rate": _rate(
            sum(item["expected_domain_in_top5"] is True for item in navigational_site)
            , len(navigational_site)
        ),
        "site_query_top1_hit_rate": _rate(
            sum(item["expected_domain_rank"] == 1 for item in navigational_site),
            len(navigational_site),
        ),
        "site_query_top3_hit_rate": _rate(
            sum(
                item["expected_domain_rank"] is not None
                and item["expected_domain_rank"] <= 3
                for item in navigational_site
            ),
            len(navigational_site),
        ),
        "news_nonempty_runs": sum(item["result_count"] > 0 for item in news),
        "news_runs": len(news),
        "news_nonempty_rate": _rate(
            sum(item["result_count"] > 0 for item in news), len(news)
        ),
        "valid_url_rate": round(
            sum(item["valid_url_count"] for item in observations) / all_results, 4
        ) if all_results else 0.0,
        "unique_url_rate": round(
            sum(item["unique_url_count"] for item in observations) / all_results, 4
        ) if all_results else 0.0,
        "news_dated_result_rate": round(
            sum(item["dated_result_count"] or 0 for item in news)
            / sum(item["result_count"] for item in news),
            4,
        )
        if sum(item["result_count"] for item in news)
        else 0.0,
        "latency_p50_seconds": round(statistics.median(latencies), 3),
        "latency_p95_seconds": round(_percentile(latencies, 0.95), 3),
        "median_result_count": statistics.median(item["result_count"] for item in observations),
    }
    return {
        "benchmark": "portable-search-mcp-live-v3",
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "rounds": rounds,
        "max_results": max_results,
        "cases": [asdict(case) for case in CASES],
        "summary": summary,
        "observations": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 10:
        parser.error("--rounds must be from 1 to 10")
    if not 1 <= args.max_results <= 20:
        parser.error("--max-results must be from 1 to 20")

    report = run_benchmark(
        SearchService(retries=1, retry_delay_seconds=0.5),
        rounds=args.rounds,
        max_results=args.max_results,
    )
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        print(f"PASS benchmark={args.output}")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["request_success_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
