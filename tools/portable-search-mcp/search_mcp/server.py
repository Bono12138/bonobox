"""Small, dependency-light MCP stdio server."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from search_mcp import __version__
from search_mcp.search import SearchService, SearchUnavailable

PROTOCOL_VERSION = "2024-11-05"
TOOL_TO_CATEGORY = {
    "search_web": "web",
    "search_news": "news",
    "search_images": "images",
    "ddgs_search": "web",
    "ddgs_news": "news",
    "ddgs_images": "images",
}


def _tool_schema(name: str, description: str) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Public-web search terms. Do not include secrets or customer data.",
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 10,
                },
                "region": {
                    "type": "string",
                    "description": "Search locale such as wt-wt, cn-zh, or us-en.",
                    "default": "wt-wt",
                },
                "timelimit": {
                    "type": "string",
                    "enum": ["d", "w", "m", "y"],
                    "description": "Optional recency: day, week, month, or year.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    }


TOOLS = [
    _tool_schema("search_web", "Search the public web and return titles, URLs, and snippets."),
    _tool_schema("search_news", "Search public news sources and return titles, URLs, and snippets."),
    _tool_schema("search_images", "Search public images and return source and image URLs."),
]


class McpServer:
    def __init__(self, search_service: SearchService | None = None) -> None:
        self._search = search_service or SearchService()

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return _success(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "portable-search-mcp", "version": __version__},
                },
            )
        if method == "ping":
            return _success(request_id, {})
        if method == "tools/list":
            return _success(request_id, {"tools": TOOLS})
        if method == "tools/call":
            return self._call_tool(request_id, params)

        if request_id is None:
            return None
        return _error(request_id, -32601, "Method not found.")

    def _call_tool(self, request_id: Any, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            return _error(request_id, -32602, "Invalid tool parameters.")
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in TOOL_TO_CATEGORY or not isinstance(arguments, dict):
            return _error(request_id, -32602, "Unknown tool or invalid arguments.")

        query = arguments.get("query")
        max_results = arguments.get("max_results", 10)
        region = arguments.get("region", "wt-wt")
        timelimit = arguments.get("timelimit")
        if not isinstance(query, str) or not query.strip():
            return _error(request_id, -32602, "query must be a non-empty string.")
        if len(query) > 500:
            return _error(request_id, -32602, "query must not exceed 500 characters.")
        allowed_arguments = {"query", "max_results", "region", "timelimit"}
        if set(arguments) - allowed_arguments:
            return _error(request_id, -32602, "Unexpected tool argument.")
        if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 20:
            return _error(request_id, -32602, "max_results must be an integer from 1 to 20.")
        if not isinstance(region, str) or not region.strip():
            return _error(request_id, -32602, "region must be a non-empty string.")
        if timelimit not in {None, "d", "w", "m", "y"}:
            return _error(request_id, -32602, "timelimit must be d, w, m, or y.")

        category = TOOL_TO_CATEGORY[name]
        try:
            results = self._search.search(
                category,
                query.strip(),
                max_results=max_results,
                region=region.strip(),
                timelimit=timelimit,
            )
        except SearchUnavailable:
            message = "Public search is temporarily unavailable. Try again later."
            return _success(
                request_id,
                {
                    "content": [{"type": "text", "text": message}],
                    "structuredContent": {"results": []},
                    "isError": True,
                },
            )

        if category == "news" and timelimit is not None and not results:
            return _success(
                request_id,
                {
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
                },
            )

        return _success(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(results, ensure_ascii=False, indent=2),
                    }
                ],
                "structuredContent": {"results": results},
                "isError": False,
            },
        )


def process_line(line: str, server: McpServer) -> dict[str, Any] | None:
    try:
        request = json.loads(line)
    except (json.JSONDecodeError, TypeError):
        return _error(None, -32700, "Parse error.")
    if not isinstance(request, dict):
        return _error(None, -32600, "Invalid Request.")
    return server.handle(request)


def run_stdio(
    server: McpServer | None = None,
    *,
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
) -> None:
    active_server = server or McpServer()
    for raw_line in input_stream:
        if not raw_line.strip():
            continue
        response = process_line(raw_line, active_server)
        if response is not None:
            output_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
            output_stream.flush()


def _success(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }
