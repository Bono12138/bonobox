#!/usr/bin/env python3
"""Run local protocol checks and an optional public-web search check."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


class SmokeTestError(RuntimeError):
    """Raised when the packaged server does not satisfy its public contract."""


def _run_requests(
    python_executable: str,
    server_path: Path,
    requests: list[dict],
    *,
    timeout: int,
) -> list[dict]:
    completed = subprocess.run(
        [python_executable, str(server_path)],
        input="\n".join(json.dumps(item) for item in requests) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=True,
        cwd=server_path.parent,
    )
    if completed.stderr:
        raise SmokeTestError("Server wrote unexpected diagnostic output.")
    try:
        return [json.loads(line) for line in completed.stdout.splitlines() if line]
    except json.JSONDecodeError as exc:
        raise SmokeTestError("Server returned invalid JSON-RPC output.") from exc


def check_protocol(python_executable: str, server_path: Path) -> dict:
    messages = _run_requests(
        python_executable,
        server_path,
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ],
        timeout=10,
    )
    if len(messages) != 2:
        raise SmokeTestError("Expected two protocol responses.")
    return {
        "server": messages[0]["result"]["serverInfo"]["name"],
        "tools": [item["name"] for item in messages[1]["result"]["tools"]],
    }


def validate_live_results(results: list[dict]) -> int:
    valid = 0
    for item in results:
        parsed = urlsplit(str(item.get("url", "")))
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            valid += 1
    if valid == 0:
        raise SmokeTestError("Live search returned no public HTTP(S) results.")
    return valid


def check_live_search(python_executable: str, server_path: Path) -> int:
    messages = _run_requests(
        python_executable,
        server_path,
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "search_web",
                    "arguments": {
                        "query": "Python official documentation",
                        "max_results": 3,
                    },
                },
            },
        ],
        timeout=60,
    )
    if len(messages) != 2 or messages[1].get("result", {}).get("isError"):
        raise SmokeTestError("Live search tool call failed.")
    return validate_live_results(messages[1]["result"]["structuredContent"]["results"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Also make one public-web request.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    server_path = root / "ddgs-mcp-server.py"
    protocol = check_protocol(sys.executable, server_path)
    print(f"PASS protocol server={protocol['server']} tools={len(protocol['tools'])}")
    if args.live:
        count = check_live_search(sys.executable, server_path)
        print(f"PASS live_search valid_results={count}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SmokeTestError, subprocess.SubprocessError, KeyError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
