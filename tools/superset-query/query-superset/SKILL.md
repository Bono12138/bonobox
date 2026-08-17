---
name: query-superset
description: Run bounded SELECT queries through an Apache Superset SQL Lab connection on Windows. Use when a user wants an Agent to configure a supported Superset instance, test connectivity, inspect tables or columns, execute SELECT queries, export small results, preserve query evidence, or diagnose authentication, permission, SQL, resource, timeout, network, and server failures.
---

# Query Superset

Use `scripts/superset_query.py` as the only query implementation. This release supports Windows, username/password form login, and the legacy synchronous SQL Lab endpoint used by some Superset deployments. Do not claim support for SSO, MFA, API-token login, Power BI, or every Superset version.

## 1. Check compatibility before setup

Read `references/capabilities.md`. Confirm all of the following:

- the user is on Windows with Python 3.10 or newer;
- the user can open Superset and use SQL Lab with their own account;
- the deployment accepts username/password form login;
- the user knows the SQL Lab database connection ID and default schema;
- the organization allows the selected Agent and model to process the intended data.

If the deployment uses SSO, MFA, a custom login form, disables the legacy SQL Lab endpoint, or is not Superset, do not force it through the current client. Diagnose the boundary first. In a separate local branch, an Agent may make the smallest general adaptation or add a separate connector when it can do so without changing the enterprise platform or weakening authentication, TLS, VPN, or permissions. Test the original path and the new path. Record every outcome in a redacted compatibility Issue; prepare a linked Pull Request for a general, minimal, tested code change. If the Agent cannot adapt it safely, the Issue remains the useful result.

## 2. Configure without exposing credentials

Run in an interactive Windows terminal:

```powershell
python scripts/superset_query.py configure
python scripts/superset_query.py auth
python scripts/superset_query.py status
python scripts/superset_query.py doctor
```

`auth` hides the password while it is typed and stores it with Windows DPAPI. Never ask the user to paste a password, cookie, CSRF token, or session into chat, a project file, an Issue, or Git.

`doctor` must execute a real `SELECT 1`. Do not describe the installation as working until it passes. Keep TLS verification enabled. If an internal certificate requires a CA bundle, configure the approved CA file rather than disabling verification.

## 3. Form a bounded read-only query

Follow these rules:

1. Submit one statement.
2. Use `SELECT`, `WITH ... SELECT`, or `EXPLAIN SELECT`.
3. Use `information_schema.tables` and `information_schema.columns` for discovery.
4. Prefer aggregates and necessary columns.
5. Add date, product, entity, or other scope boundaries whenever possible.
6. Add `LIMIT` to exploratory detail queries.
7. Never send `CREATE`, CTAS, `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `DROP`, `ALTER`, `TRUNCATE`, `SHOW`, `DESCRIBE`, or multiple statements.

The local validator blocks common write and administration forms, but it is not a complete SQL parser or a database firewall. The Superset connection and underlying database account must enforce read-only access.

## 4. Execute and preserve evidence

For a SQL file:

```powershell
python scripts/superset_query.py run --sql-file C:\path\query.sql
```

For a short query:

```powershell
python scripts/superset_query.py run --sql "SELECT 1 AS connection_test"
```

The command prints a small JSON preview. Unless `--no-save` is used, it stores the SQL, accepted CSV result, and a manifest under the current Windows user's local application-data directory. The default result limit is 10,000 rows and can be lowered in the profile. The manifest records the configured limit, timing, row count, hashes, query state, and Superset query ID. It does not store the password or session cookies.

Do not paste large or sensitive result sets into chat. Summarize the result and give the local output path.

## 5. Diagnose without blind retries

Use the returned `category`, `message`, `query_id`, and bounded `details`:

- `auth`: confirm login mode and rerun `auth` only when needed;
- `policy`: rewrite as one read-only statement;
- `sql`: correct the SQL;
- `object`: inspect `information_schema`;
- `permission`: stop and request the proper access;
- `resource`: reduce scan size, columns, joins, or detail;
- `timeout`: optimize before retrying;
- `network`: check the required network, VPN, DNS, proxy, and CA bundle;
- `server`: preserve the query ID and report the deployment/version context.

Automatic retries are deliberately limited to transient failures.

## 6. Report a public issue safely

Use the repository's Superset compatibility or bug Issue template. Include the tool version, Windows and Python versions, Superset version if known, login type, command name, error category, HTTP status, and a redacted error excerpt.

Before submission, remove usernames, Superset URLs, database and schema names, SQL, query results, query IDs when sensitive, cookies, tokens, passwords, local paths, customer data, and company-only information.

## 7. Return a compatibility result after real use

After installation or a genuine stop state, prepare one compatibility report. Success, partial success, failure, and an unsupported environment are all useful.

Use `scripts/superset_query.py compatibility-report` with only the fixed public fields. The command must not read or expose the configured URL, username, database connection ID, schema, SQL, results, query IDs, credentials, session, or local state paths. Ask the user to review the complete report before any public Issue is created.

Use the repository's `Data platform compatibility report` template. A request for Superset modern API, Power BI, Metabase, DBX, Databricks, or another platform is evidence for prioritization, not a claim that this Skill already supports that platform. Keep platform implementations as separate connectors. Never weaken TLS, enterprise authentication, row-level security, or database permissions to turn a failed compatibility check into a success. Original success, adapted success, failed adaptation, and an environment the Agent cannot adapt should all be reported.
