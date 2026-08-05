# Portable Search MCP 2.0.0

The first tool published in `bono-tools`.

## What it does

- Adds public web, news, and image search to MCP-compatible agents, local models, IDEs, CLIs, and automation workflows.
- Does not require a commercial search API key.
- Ships with Windows installation and verification scripts.
- Converts parseable relative news times and applies strict local freshness filtering so stale or undated items do not silently pass as current news.

## Install

Download `portable-search-mcp-v2.0.0.zip`, extract it, and run:

```powershell
.\install.ps1
.\verify.ps1 -Live
```

See [QUICKSTART.md](../QUICKSTART.md) for MCP configuration and the observable success checks.

## Verification

- 37 automated tests passed; 4 network-dependent tests are skipped by default.
- Three live rounds covered English web, Chinese web, images, and news freshness: 12/12 checks passed.
- A clean ZIP extraction created its own virtual environment, installed 17 locked dependencies, exposed three MCP tools, and returned valid public URLs.
- The release archive contains 15 allowlisted files plus `MANIFEST.json`.

SHA-256:

```text
84d6321e06667c8406549bd4b66eca1bcbd968cda3bf92c7a44cd548b90128b4
```

## Important limits

- Search terms leave the local machine and go to public search providers. Do not use secrets, customer data, private business information, or sensitive case details as queries.
- Public free search has no stable quota or service-level agreement.
- News dates come from upstream metadata and still require source verification.
- This tool does not search private company systems or fetch full paywalled/login-protected pages.
