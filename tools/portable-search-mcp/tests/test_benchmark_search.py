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

    assert summary["requests"] == 22
    assert summary["request_success_rate"] == 1.0
    assert summary["web_image_nonempty_rate"] == 1.0
    assert summary["plain_query_top5_hit_rate"] == 1.0
    assert summary["site_query_top5_hit_rate"] == 1.0
    assert summary["news_nonempty_rate"] == 0.5
    assert summary["valid_url_rate"] == 1.0


def test_benchmark_does_not_store_titles_or_snippets():
    report = run_benchmark(FakeSearchService(), rounds=1, max_results=5)

    assert all("title" not in item and "snippet" not in item for item in report["observations"])
