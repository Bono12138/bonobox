# Superset query public Beta test report

> Review date: 2026-08-17
> Release: `1.0.0-beta.1`

## What was tested

The automated suite covers:

- accepted and rejected SQL forms;
- keywords inside strings and comments;
- error classification;
- retry limits;
- dynamic query timeouts;
- query lifecycle and status snapshots;
- bounded observer output that does not copy other SQL;
- encrypted-session identity binding;
- invalidation after username changes;
- result-row enforcement and CSV formula neutralization.

The exact local test count is recorded by the release workflow rather than frozen in this document.

Before release, GitHub Actions must build the allowlisted ZIP, verify its SHA-256, extract it, run the verifier from the extracted package, install from that package, and verify the installed Skill on Python 3.10 and 3.13. A release is not ready while that workflow is failing.

## Real-deployment evidence

The underlying Windows client and legacy synchronous SQL Lab transport were previously exercised by the maintainer on one private enterprise Superset deployment with username/password form login. The private environment and evidence cannot be independently inspected by public users.

Observed checks included:

- a fresh login followed by `SELECT 1`;
- reuse of a DPAPI-encrypted session;
- a cached-session request completing faster than a fresh-login request;
- query result, SQL, timing, hashes, and Superset query ID written to a local run manifest;

Error classification, policy rejection, limit enforcement, and other failure paths are covered by synthetic automated tests, not claimed as public real-deployment evidence.

The public package does not contain or disclose that deployment's URL, organization, username, database connection IDs, schemas, SQL, results, customer data, credentials, cookies, sessions, or private write capability.

## What this does not prove

One working deployment does not prove compatibility with every Superset version or configuration. The following remain outside the confirmed release scope:

- SSO, OAuth, MFA, CAPTCHA, and custom login flows;
- modern `/api/v1/sqllab/execute/` transport;
- API-token-only authentication;
- macOS or Linux secret storage;
- asynchronous or bulk result downloads;
- Power BI and other platforms.

For each new deployment, the acceptance test is a successful `doctor` run using `SELECT 1` without weakening TLS, identity, or read-only controls.
