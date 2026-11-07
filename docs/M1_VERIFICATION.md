# M1 verification — 2026-11-07

This checkpoint implements foundation behavior only. It does not claim working ingestion, AI, provider integrations, patch execution, or PR creation.

## Measured checks

| Check | Result |
| --- | --- |
| Backend on local PostgreSQL 18.6 | 21 passed, including concurrent refresh reuse; final run 13.58 seconds |
| Backend on SQLite | 20 passed, 1 PostgreSQL-only concurrency test skipped |
| Migration drift | Alembic reports no new upgrade operations |
| Session/client Jest tests | 6 passed: secure-vault restoration, parallel refresh, offline credential retention, refresh revocation, permission failures, logout |
| TypeScript | No errors |
| Python lint and formatting | Ruff checks pass |
| Mobile/client formatting | Prettier checks pass |
| Expo exports | Android, iOS, and web bundles compile successfully |
| Browser end-to-end | 1 passed in 12.7 seconds: real account/workspace/project/environment creation, appearance switching, audit activity, persisted data after signing back in, logout, connection failure and retry |
| Dependency reproducibility | Clean npm ci succeeds; direct manifest declarations match the lockfile; mobile TypeScript compiler pinned to Expo's 6.0.3 |

The backend suite also covers password hashing, input validation, token claim/signature/expiry rejection, absolute session expiry, logout revocation, shared rate limits, project isolation, grant revocation, membership removal, owner protection, duplicate names, and database persistence after API recreation.

## Visual review

Screenshots in `docs/screenshots` come from the running React Native web client at 390 × 844 and 1440 × 1050. Registration, overview, desktop overview, and dark appearance are included. Test records are actual local database records, not hard-coded dashboard data.

The screenshot check initially exposed an empty modal during dismissal. The dialog now unmounts when closed, and the browser test waits for dismissal before taking screenshots. The dark theme logo also uses theme-aware contrast.

## Environment and limits

- Docker is not on PATH. Compose and Dockerfile definitions are supplied but were not executed. PostgreSQL tests instead used a workspace-local PostgreSQL runtime bound to loopback with generated, rotated development credentials. The local test runtime is ignored by Git and is not a production dependency.
- Compose/CI pins use PostgreSQL 17.11 and Redis 7.4.11, selected after reviewing their security-fix release notes: [PostgreSQL 17.11](https://www.postgresql.org/docs/17/release-17-11.html), [Redis 7.4.11](https://redis.io/docs/latest/operate/oss_and_stack/stack-with-enterprise/release-notes/redisce/redisce-7.4-release-notes/). Container startup remains unverified here.
- Native bundles compile, but no physical device or emulator smoke test was run. Device Keychain/Keystore persistence, keyboards, gestures, and screen-reader behavior still need native validation. Browser screenshots cannot establish those properties.
- Hosted GitHub Actions have not run. CI definitions provide disposable PostgreSQL tests, formatting/type checks, schema drift checks, and bundle exports.
- Redis readiness is implemented and configured in Compose, but a live Redis/Compose check was not available here. No queue/worker functionality is claimed in M1.
- Web preview credentials are deliberately memory-only. Reloading requires sign-in; server records persist.
- Public account verification/recovery, retention jobs, deployment backup/restore, and wider security hardening remain release gates. See SECURITY.md.

## Dependency audit

After compatible updates, npm reports **24 transitive/advisory findings: 23 moderate, 1 low; zero high or critical**. Findings trace through `glob`, `minimatch`, and `deepmerge` in the Expo/Jest tooling dependency graph. They are not treated as resolved. The offered automatic forced fix includes a downgrade of Expo to SDK 53; it was not applied because it would replace the selected supported application stack.

Do not pass untrusted glob patterns/configuration into development or test tooling. Review patched upstream versions or narrowly scoped, compatibility-tested overrides before public release. Keep dependency auditing in the release checklist rather than claiming this private preview is production hardened.

## Review checkpoint

Use the README walkthrough to review the mobile shell and two-user authorization behavior. Decide whether to proceed to M2: signed demo telemetry, incident grouping, timelines, and durable background jobs. No M2 implementation is included in this checkpoint.
