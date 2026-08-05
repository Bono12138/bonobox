import json
from io import StringIO

from search_mcp.server import McpServer, process_line, run_stdio
from search_mcp.search import SearchUnavailable


class RecordingSearchService:
    def __init__(self):
        self.calls = []

    def search(self, category, query, *, max_results, region, timelimit):
        self.calls.append(
            {
                "category": category,
                "query": query,
                "max_results": max_results,
                "region": region,
                "timelimit": timelimit,
            }
        )
        return [
            {
                "title": "Official documentation",
                "url": "https://example.com/docs",
                "snippet": "A controlled result.",
                "source": "example",
            }
        ]


class UnavailableSearchService:
    def search(self, category, query, *, max_results, region, timelimit):
        raise SearchUnavailable("provider leaked sensitive upstream detail")


class EmptySearchService:
    def search(self, category, query, *, max_results, region, timelimit):
        return []


def request(method, params=None, request_id=1):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }


def test_initialize_advertises_tools_capability():
    server = McpServer(RecordingSearchService())

    response = server.handle(request("initialize"))

    assert response["result"]["protocolVersion"] == "2024-11-05"
    assert response["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert response["result"]["serverInfo"]["name"] == "portable-search-mcp"


def test_tools_list_exposes_stable_supported_tools_only():
    server = McpServer(RecordingSearchService())

    response = server.handle(request("tools/list"))
    names = [tool["name"] for tool in response["result"]["tools"]]

    assert names == ["search_web", "search_news", "search_images"]


def test_tool_call_returns_text_and_structured_results():
    service = RecordingSearchService()
    server = McpServer(service)

    response = server.handle(
        request(
            "tools/call",
            {
                "name": "search_web",
                "arguments": {
                    "query": "official docs",
                    "max_results": 3,
                    "region": "cn-zh",
                    "timelimit": "m",
                },
            },
        )
    )

    assert service.calls == [
        {
            "category": "web",
            "query": "official docs",
            "max_results": 3,
            "region": "cn-zh",
            "timelimit": "m",
        }
    ]
    result = response["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["results"][0]["url"] == "https://example.com/docs"
    assert json.loads(result["content"][0]["text"])[0]["title"] == "Official documentation"


def test_legacy_web_tool_name_remains_compatible():
    service = RecordingSearchService()
    server = McpServer(service)

    response = server.handle(
        request(
            "tools/call",
            {"name": "ddgs_search", "arguments": {"query": "compatibility"}},
        )
    )

    assert response["result"]["isError"] is False
    assert service.calls[0]["category"] == "web"


def test_blank_query_is_rejected_without_calling_search():
    service = RecordingSearchService()
    server = McpServer(service)

    response = server.handle(
        request("tools/call", {"name": "search_web", "arguments": {"query": "   "}})
    )

    assert response["error"]["code"] == -32602
    assert service.calls == []


def test_max_results_outside_safe_range_is_rejected():
    server = McpServer(RecordingSearchService())

    response = server.handle(
        request(
            "tools/call",
            {"name": "search_web", "arguments": {"query": "x", "max_results": 21}},
        )
    )

    assert response["error"]["code"] == -32602


def test_query_longer_than_500_characters_is_rejected():
    service = RecordingSearchService()
    server = McpServer(service)

    response = server.handle(
        request(
            "tools/call",
            {"name": "search_web", "arguments": {"query": "x" * 501}},
        )
    )

    assert response["error"]["code"] == -32602
    assert service.calls == []


def test_unexpected_argument_is_rejected():
    service = RecordingSearchService()
    server = McpServer(service)

    response = server.handle(
        request(
            "tools/call",
            {
                "name": "search_web",
                "arguments": {"query": "x", "secret_option": "not allowed"},
            },
        )
    )

    assert response["error"]["code"] == -32602
    assert service.calls == []


def test_unknown_tool_returns_invalid_params_error():
    server = McpServer(RecordingSearchService())

    response = server.handle(
        request("tools/call", {"name": "made_up", "arguments": {"query": "x"}})
    )

    assert response["error"]["code"] == -32602


def test_provider_error_is_sanitized_as_tool_error():
    server = McpServer(UnavailableSearchService())

    response = server.handle(
        request("tools/call", {"name": "search_web", "arguments": {"query": "x"}})
    )

    assert response["result"] == {
        "content": [
            {
                "type": "text",
                "text": "Public search is temporarily unavailable. Try again later.",
            }
        ],
        "structuredContent": {"results": []},
        "isError": True,
    }


def test_empty_fresh_news_returns_explicit_freshness_warning():
    server = McpServer(EmptySearchService())

    response = server.handle(
        request(
            "tools/call",
            {
                "name": "search_news",
                "arguments": {"query": "latest topic", "timelimit": "d"},
            },
        )
    )

    assert response["result"] == {
        "content": [
            {
                "type": "text",
                "text": "No news with a verifiable publication time satisfied the requested freshness window.",
            }
        ],
        "structuredContent": {
            "results": [],
            "warning": "No results passed the local freshness check.",
        },
        "isError": False,
    }


def test_initialized_notification_has_no_response():
    server = McpServer(RecordingSearchService())

    response = server.handle(
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    )

    assert response is None


def test_process_line_returns_parse_error_for_invalid_json():
    server = McpServer(RecordingSearchService())

    response = process_line("not json", server)

    assert response["error"]["code"] == -32700
    assert response["id"] is None


def test_stdio_keeps_protocol_on_stdout_and_handles_multiple_requests():
    server = McpServer(RecordingSearchService())
    input_stream = StringIO(
        "not json\n"
        + json.dumps(request("ping", request_id=2))
        + "\n"
    )
    output_stream = StringIO()

    run_stdio(server, input_stream=input_stream, output_stream=output_stream)

    messages = [json.loads(line) for line in output_stream.getvalue().splitlines()]
    assert messages[0]["error"]["code"] == -32700
    assert messages[1] == {"jsonrpc": "2.0", "id": 2, "result": {}}
