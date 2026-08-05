<p align="center">
  <img src="docs/bonobox-logo.png" alt="BonoBox rabbit mascot in a toolbox" width="260" />
</p>

<h1 align="center">BonoBox · BBX</h1>

<p align="center"><strong>One box. One useful tool at a time. Real tests included.</strong></p>

<p align="center"><a href="README.md">简体中文</a> · <a href="#tool-catalog">Tool catalog</a> · <a href="ROADMAP.md">Roadmap</a> · <a href="CONTRIBUTING.md">Contributing</a></p>

**BonoBox**, shortened to **BBX**, is Bono's public collection of small, useful tools. Every published tool has a short path to first use, observable success checks, real test evidence, and clearly stated limits.

If a tool saves you time, star the repository to follow future releases.

## Tool catalog

| Tool | Problem solved | Measured result | Status |
|---|---|---|---|
| [Portable Search MCP](tools/portable-search-mcp/) | Adds public web, news, and image search to MCP-compatible agents and local models | 31/33 live requests succeeded; web/image returned results in 27/27 runs; median latency 2.244 s | v2.0.1 · released |

## Portable Search MCP

The tool exposes `search_web`, `search_news`, and `search_images` through MCP without requiring a commercial search API key.

In a 33-request live benchmark on 2026-08-05, 93.9% of requests succeeded, every web/image run returned results, every returned URL was a public HTTP(S) URL, and latency was 2.244 s at P50 and 4.618 s at P95. Plain-language navigational queries placed the intended official domain in the top five in 4/9 runs; adding an explicit `site:` constraint improved that to 9/9. Fresh-news queries produced same-day results in 3/6 runs because stale or unverifiable items are deliberately removed.

See the [full test report](tools/portable-search-mcp/docs/TEST-REPORT.md) and [benchmark data](tools/portable-search-mcp/docs/benchmark-2026-08-05.json).

Download [Portable Search MCP v2.0.1](https://github.com/Bono12138/bonobox/releases/tag/portable-search-mcp-v2.0.1), extract the ZIP, and run:

```powershell
.\install.ps1
.\verify.ps1 -Live
```

The release includes Windows setup, locked dependencies, protocol checks, live verification, security notes, troubleshooting, and a per-file hash manifest. See the [full tool documentation](tools/portable-search-mcp/README.md).

## Release bar

Every published tool must solve a concrete problem, offer a short first-use path, define observable success, include relevant tests, document limitations, and ship from an allowlisted build without local state or secrets.

Use [Issues](https://github.com/Bono12138/bonobox/issues) for reproducible problems and tool ideas, [Discussions](https://github.com/Bono12138/bonobox/discussions) for general questions, and [SECURITY.md](SECURITY.md) for private security reports.

## License

Original code in this repository is released under the [MIT License](LICENSE). Third-party components keep their own licenses; see each tool's notices.
