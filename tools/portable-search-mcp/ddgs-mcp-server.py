#!/usr/bin/env python3
"""Backward-compatible entry point for Portable Search MCP."""

import sys

from search_mcp.server import run_stdio


if __name__ == "__main__":
    sys.stdin.reconfigure(encoding="utf-8", errors="strict")
    sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    run_stdio()
