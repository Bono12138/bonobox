# Superset query capability and boundary

## Confirmed release scope

- Windows 10 or 11;
- Python 3.10 or newer;
- username/password form login;
- legacy synchronous SQL Lab endpoint `/superset/sql_json/`;
- one `SELECT`, `WITH ... SELECT`, or `EXPLAIN SELECT` statement;
- local Windows DPAPI protection for the password and cached session;
- small synchronous results saved as CSV with a run manifest.

The underlying implementation has been exercised against one real enterprise Superset deployment. The public package removes that deployment's URL, connection IDs, usernames, schemas, and organization-specific setup. Compatibility with another deployment must be established by running `doctor`.

## Not supported in this release

- macOS or Linux credential storage;
- SSO, OAuth, LDAP pages with custom flows, MFA, or CAPTCHA;
- API-token-only authentication;
- the newer `/api/v1/sqllab/execute/` transport;
- asynchronous large-result downloads;
- Power BI or other data platforms;
- write, administration, DDL, DML, CTAS, or multiple statements;
- automatic discovery of a database connection ID;
- bypassing network, identity, row-level, or database permissions.

Open a compatibility Issue instead of weakening authentication or TLS controls.

## Read-only SQL

Supported:

- `SELECT ...`
- `WITH ... SELECT ...`
- `EXPLAIN SELECT ...`
- metadata discovery through `information_schema.tables`
- column discovery through `information_schema.columns`

Blocked:

- `SHOW` and `DESCRIBE`
- `CREATE`, CTAS, `INSERT`, `UPDATE`, `DELETE`, and `MERGE`
- `DROP`, `ALTER`, and `TRUNCATE`
- multiple statements

The validator removes comments and string contents before checking common write keywords and state-changing functions. It is not a complete SQL parser. Administrators must enforce read-only permissions in Superset and the underlying database.

## Result-size boundary

The profile defaults to 10,000 result rows. The request sends that limit to Superset, and the client refuses to save a response that exceeds it. The synchronous endpoint may still receive a complete JSON response in memory before the local check runs. Narrow the date, entity, product, columns, and aggregation level before execution. Use this tool for metadata, checks, aggregates, and bounded detail—not bulk extraction.

## Error categories

| Category | Meaning | Next action |
|---|---|---|
| `auth` | Login or session failed | Confirm supported login type; rerun `auth` when the password changed |
| `policy` | Statement is blocked | Rewrite as one read-only statement |
| `sql` | SQL is invalid | Correct the syntax and rerun once |
| `object` | Table or column is missing | Inspect `information_schema` |
| `permission` | Account lacks access | Stop and request access |
| `resource` | Query exceeded resources | Reduce scan, columns, joins, or detail |
| `timeout` | Query exceeded the configured wait | Optimize before increasing the timeout |
| `network` | Superset cannot be reached securely | Check VPN, DNS, proxy, access client, and CA bundle |
| `server` | Deployment returned another failure | Preserve a redacted error and report the version/context |

## Public issue boundary

Never attach a profile, DPAPI file, session, raw manifest, SQL containing private objects, result CSV, screenshot with an internal URL, or complete server error page. Reproduce with `SELECT 1` or another harmless synthetic query whenever possible.

## Compatibility feedback

`compatibility-report` produces fixed environment fields for a public Issue. It accepts success, partial success, failure, and unsupported outcomes across Superset legacy, Superset modern API, Power BI, Metabase, DBX, Databricks, and other enterprise platforms. Listing a platform here records demand only; it does not mean the current Superset client can connect to it.

The generated report does not read the local Superset profile, credentials, session, SQL, results, or their paths. The user must review the report before posting it. Free-form reproduction notes belong in the Issue form and must be redacted separately.

An Agent may adapt the local tool in a separate branch or add a separate platform connector. It must preserve the existing security boundary, add tests, run a harmless live check when possible, and report the original and adapted outcomes. A reusable code change belongs in a Pull Request linked to the compatibility Issue. A failed or unavailable adaptation is still a valid Issue result.
