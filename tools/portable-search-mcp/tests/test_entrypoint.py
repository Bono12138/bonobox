import json
import subprocess
import sys
from pathlib import Path


def test_legacy_entrypoint_runs_the_hardened_server():
    project_root = Path(__file__).resolve().parents[1]
    requests = "\n".join(
        [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {},
                }
            ),
            json.dumps(
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            ),
        ]
    )

    completed = subprocess.run(
        [sys.executable, str(project_root / "ddgs-mcp-server.py")],
        input=requests,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
        cwd=project_root,
    )

    messages = [json.loads(line) for line in completed.stdout.splitlines()]
    assert messages[0]["result"]["serverInfo"]["name"] == "portable-search-mcp"
    assert [tool["name"] for tool in messages[1]["result"]["tools"]] == [
        "search_web",
        "search_news",
        "search_images",
    ]
    assert completed.stderr == ""
