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
| [Portable Search MCP](tools/portable-search-mcp/) | Adds public web, news, and image search to MCP-compatible agents and local models | 90/90 requests succeeded; web/image returned results in 66/66 runs and news in 24/24; P50 latency 2.537 s | v2.1.0 · released |
| [Superset Read-only Query Skill](tools/superset-query/) | Runs bounded SELECT queries through a user's existing Superset SQL Lab path and collects redacted cross-company compatibility reports | Automated tests cover write rejection, result limits, CSV safety, session identity, error classification, and public compatibility reports; the legacy route has private maintainer validation | v1.0.0-beta.2 · public beta |
| [Wiki Connector](tools/wiki-connector/) | Lets an Agent search and read Confluence with the user's existing access, then create a redacted compatibility report | Offline tests cover URL validation, read-only boundaries, local browser control, diagnostics, and redaction; each real environment must pass `doctor` | v0.1.0-beta.1 · public beta |
| [Reality Grounding + Reality Strategy](tools/reality-grounding/) | Recovers the original problem, reconstructs the real relationship chain, then targets the sustaining obstacle with an executable move | Paired installation and structural checks pass locally; ten grounding and nine strategy cases are included, while each model and host still needs an observed invocation check | v0.5.0 · release candidate |

## Portable Search MCP

The tool exposes `search_web`, `search_news`, and `search_images` through MCP without requiring a commercial search API key.

In a 90-request live benchmark on 2026-08-05, all requests completed successfully, web/image searches returned results in 66/66 runs, and news searches returned dated results in 24/24 runs. Plain-language navigational queries placed the intended official domain in the top five in 16/18 runs; explicit `site:` queries placed it first in 18/18. All returned URLs were valid and unique within each response. Latency was 2.537 s at P50 and 9.055 s at P95.

See the [full test report](tools/portable-search-mcp/docs/TEST-REPORT.md) and [final benchmark data](tools/portable-search-mcp/docs/benchmark-2026-08-05-v3.json).

Download [Portable Search MCP v2.1.0](https://github.com/Bono12138/bonobox/releases/tag/portable-search-mcp-v2.1.0), extract the ZIP, and run:

```powershell
.\install.ps1
.\verify.ps1 -Live
```

The release includes Windows setup, locked dependencies, protocol checks, live verification, security notes, troubleshooting, and a per-file hash manifest. See the [full tool documentation](tools/portable-search-mcp/README.md).

## Superset Read-only Query Skill

This public beta keeps an Agent on the user's existing Superset SQL Lab path instead of opening a new direct database connection. It rejects common write and administration forms, protects local secrets with Windows DPAPI, binds cached sessions to the configured identity, classifies failures, applies a default 10,000-row result limit, and records run evidence. The validator is not a complete SQL parser; Superset and database permissions must enforce read-only access.

The current release supports Windows, username/password form login, and the legacy synchronous SQL Lab endpoint. SSO, MFA, the modern API transport, Power BI, Metabase, DBX, and Databricks are not yet supported. Users can give the copyable prompt in the [tool documentation](tools/superset-query/) to their Agent for environment checking, installation, a required live `SELECT 1`, and a redacted [compatibility report](https://github.com/Bono12138/bonobox/issues/new?template=data_platform_compatibility.yml).

## Wiki Connector

This Windows-first beta gives an Agent read-only Confluence search and page retrieval through either an API token or a dedicated local browser profile. Compatibility depends on the Wiki version, authentication flow, permissions, network, and company security policy. Give the Chinese prompt in the [tool documentation](tools/wiki-connector/) to an Agent; it will install the tool, run `doctor`, attempt a minimal safe adaptation when needed, and prepare a redacted Issue for the user to review.

## Reality Grounding + Reality Strategy

`reality-grounding` separates the original result from a proposed method, then reconstructs participants, locations, goods or rights, money, contracts and timing with a few answerable questions. `reality-strategy` distinguishes public explanations from the mechanism that sustains the situation, then changes defaults, burdens, costs, support or decision sequence. It reports feasibility, exposure and consequences while leaving goals and value judgments with the user. See the [tool documentation](tools/reality-grounding/) for paired installation, verification, examples, and limits.

Use [Issues](https://github.com/Bono12138/bonobox/issues) for reproducible problems and tool ideas, [Discussions](https://github.com/Bono12138/bonobox/discussions) for general questions, and [SECURITY.md](SECURITY.md) for private security reports.

## License

Original code in this repository is released under the [MIT License](LICENSE). Third-party components keep their own licenses; see each tool's notices.
