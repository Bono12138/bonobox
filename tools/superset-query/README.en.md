# Superset Read-only Query Skill

This BonoBox tool lets an Agent execute bounded read-only SQL through a Superset SQL Lab connection that the user already has.

The public beta currently supports Windows, Python 3.10+, username/password form login, and the legacy synchronous `/superset/sql_json/` endpoint. It does not support SSO, MFA, API-token-only deployments, Power BI, write queries, or every Superset version.

Download `bonobox-superset-query-v1.0.0-beta.1.zip` and its `.sha256` file from the GitHub Release. On Windows, verify the checksum with `Get-FileHash`, extract the ZIP, then run `install.ps1`, `verify.ps1`, `configure`, `auth`, and `doctor`. A real `SELECT 1` must succeed before the installation is treated as working. The detailed walkthrough is currently in [QUICKSTART.md](QUICKSTART.md).

The tool locally rejects common write and administration forms and multi-statement SQL. This is not a complete SQL parser. Final read-only enforcement must come from Superset and the underlying database permissions. It also protects credentials and cached sessions with Windows DPAPI, classifies common failures, limits results to 10,000 rows by default, and saves run evidence. The legacy synchronous endpoint may still receive a server response before the local row-count check runs, so use it only for small results.

Use the repository's [bug template](https://github.com/Bono12138/bonobox/issues/new?template=superset_query_bug.yml) or [compatibility template](https://github.com/Bono12138/bonobox/issues/new?template=superset_compatibility.yml) for redacted feedback. Never submit URLs, usernames, passwords, cookies, tokens, private SQL, query results, raw manifests, query IDs, customer data, or internal screenshots to a public Issue. Report vulnerabilities privately through the repository security policy.
