# Superset Read-only Query Skill

This BonoBox tool lets an Agent execute bounded read-only SQL through a Superset SQL Lab connection that the user already has.

The public beta currently supports Windows, Python 3.10+, username/password form login, and the legacy synchronous `/superset/sql_json/` endpoint. It does not support SSO, MFA, API-token-only deployments, Power BI, write queries, or every Superset version.

Download `bonobox-superset-query-v1.0.0-beta.2.zip` and its `.sha256` file from the GitHub Release. On Windows, verify the checksum with `Get-FileHash`, extract the ZIP, then run `install.ps1`, `verify.ps1`, `configure`, `auth`, and `doctor`. A real `SELECT 1` must succeed before the installation is treated as working. The detailed walkthrough and copyable Agent prompt are in [QUICKSTART.md](QUICKSTART.md).

The tool locally rejects common write and administration forms and multi-statement SQL. This is not a complete SQL parser. Final read-only enforcement must come from Superset and the underlying database permissions. It also protects credentials and cached sessions with Windows DPAPI, classifies common failures, limits results to 10,000 rows by default, and saves run evidence. The legacy synchronous endpoint may still receive a server response before the local row-count check runs, so use it only for small results.

Run `compatibility-report` to prepare a bounded public draft, then use the repository's [data platform compatibility report](https://github.com/Bono12138/bonobox/issues/new?template=data_platform_compatibility.yml). Successes, partial successes, failures, unsupported environments, Power BI, Metabase, DBX, Databricks, and other connector requests are all useful. DBX is kept separate until contributors identify the exact product and interface. The current evidence is recorded in [COMPATIBILITY.md](COMPATIBILITY.md).

An Agent may also adapt the local tool in a separate branch when the original version does not work. The adaptation must change only the local tool or add a separate connector; it must not weaken enterprise authentication, TLS, VPN, or permissions. Every outcome should produce a redacted compatibility Issue. A general, minimal, tested code change should also produce a Pull Request linked to that Issue. Original success, adapted success, failed adaptation, and an environment the Agent cannot yet adapt are all useful evidence.

Use the dedicated [bug template](https://github.com/Bono12138/bonobox/issues/new?template=superset_query_bug.yml) for a reproducible Superset failure. Never submit company names, URLs, usernames, passwords, cookies, tokens, private SQL, query results, raw manifests, object names, query IDs, local paths, customer data, or internal screenshots to a public Issue. Report vulnerabilities privately through the repository security policy.
