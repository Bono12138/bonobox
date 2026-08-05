<p align="center">
  <img src="docs/bono-tools-banner.svg" alt="Bono Tools" width="900" />
</p>

# bono-tools

[简体中文](README.md) · [Tool catalog](#tool-catalog) · [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md)

> Small tools with real tests, a short path to first use, and clearly documented limits.

If one of these tools saves you time, star the repository to follow future releases.

## Tool catalog

| Tool | Problem solved | Quick start | Status |
|---|---|---|---|
| [Portable Search MCP](tools/portable-search-mcp/) | Adds public web, news, and image search to MCP-compatible agents and local models | Download the ZIP, run `install.ps1`, then `verify.ps1 -Live` | v2.0.0 · tested |

## Portable Search MCP

Portable Search MCP exposes `search_web`, `search_news`, and `search_images` through the Model Context Protocol. It does not require a commercial search API key, but the machine running it must have public internet access.

Download [Portable Search MCP v2.0.0](https://github.com/Bono12138/bono-tools/releases/tag/portable-search-mcp-v2.0.0), extract the ZIP, and run:

```powershell
.\install.ps1
.\verify.ps1 -Live
```

The release includes Windows setup, locked dependencies, protocol checks, live verification, security notes, troubleshooting, and a per-file hash manifest. See the [full tool documentation](tools/portable-search-mcp/README.md).

## Release bar

Every published tool must solve a concrete problem, offer a short first-use path, define observable success, include relevant tests, document limitations, and ship from an allowlisted build without local state or secrets.

Use [Issues](https://github.com/Bono12138/bono-tools/issues) for reproducible problems and tool ideas, [Discussions](https://github.com/Bono12138/bono-tools/discussions) for general questions, and [SECURITY.md](SECURITY.md) for private security reports.

## License

Original code in this repository is released under the [MIT License](LICENSE). Third-party components keep their own licenses; see each tool's notices.
