# Portable Search MCP 2.0.1

The first BonoBox maintenance release adds evidence and branding without changing the three MCP tool interfaces.

## Changes

- adds a reproducible 33-request live benchmark;
- publishes anonymized benchmark metrics without result titles or snippets;
- expands automated coverage to 40 passing tests;
- forces UTF-8 on the MCP process standard streams so non-ASCII search results work on Windows systems whose default code page is not UTF-8;
- includes the benchmark script and data in the allowlisted ZIP;
- updates public documentation for BonoBox and the measured capability limits.

## Download

Download `portable-search-mcp-v2.0.1.zip`, extract it, and run:

```powershell
.\install.ps1
.\verify.ps1 -Live
```

The MCP tools remain `search_web`, `search_news`, and `search_images`.
