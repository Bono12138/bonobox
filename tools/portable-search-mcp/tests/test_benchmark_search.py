import scripts.benchmark_search as benchmark
from scripts.benchmark_search import CASES, run_benchmark


class FakeSearchService:
    def search(self, category, query, *, max_results, region, timelimit):
        case = next(item for item in CASES if item.query == query)
        if case.expected_domain:
            return [{"url": f"https://{case.expected_domain}/example"}]
        if category == "news" and query == "人工智能":
            return []
        return [{"url": "https://example.com/result"}]


def test_benchmark_reports_availability_precision_yield_and_valid_urls():
    report = run_benchmark(FakeSearchService(), rounds=2, max_results=5)
    summary = report["summary"]

    assert summary["requests"] == len(CASES) * 2
    assert summary["request_success_rate"] == 1.0
    assert summary["web_image_nonempty_rate"] == 1.0
    assert summary["plain_query_top5_hit_rate"] == 1.0
    assert summary["site_query_top5_hit_rate"] == 1.0
    assert summary["news_nonempty_rate"] == 0.875
    assert summary["valid_url_rate"] == 1.0
    assert summary["unique_url_rate"] == 1.0
    assert summary["news_dated_result_rate"] == 0.0
    assert summary["plain_query_top1_hit_rate"] == 1.0
    assert summary["site_query_top3_hit_rate"] == 1.0


def test_benchmark_does_not_store_titles_or_snippets():
    report = run_benchmark(FakeSearchService(), rounds=1, max_results=5)

    assert all("title" not in item and "snippet" not in item for item in report["observations"])


def test_benchmark_covers_web_images_news_and_both_languages():
    assert len(CASES) == 30
    assert {case.category for case in CASES} == {"web", "images", "news"}
    assert any(case.region == "cn-zh" for case in CASES)
    assert any(case.region in {"us-en", "wt-wt"} for case in CASES)
    assert sum(case.query_style == "plain" for case in CASES) == 6
    assert sum(case.query_style == "site" for case in CASES) == 6


def test_benchmark_can_summarize_a_subset_without_site_queries(monkeypatch):
    monkeypatch.setattr(
        benchmark,
        "CASES",
        [case for case in CASES if case.query_style == "plain" or case.category == "news"],
    )

    report = benchmark.run_benchmark(FakeSearchService(), rounds=1, max_results=5)

    assert report["summary"]["site_query_runs"] == 0
    assert report["summary"]["site_query_top5_hit_rate"] == 0.0
