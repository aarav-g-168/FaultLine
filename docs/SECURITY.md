# Foundation security boundaries

M1 is a private development preview, not a public authentication service. Email verification, password recovery, session management UI, and broader deployment hardening remain release requirements.

## Implemented

- Argon2id password hashes; password input bounds and no hard-coded signing key.
- Short-lived HS256 access JWTs with required issuer, audience, expiry, issued-at, subject, session identifier, token identifier, and access-token type.
- Random opaque refresh tokens stored only as SHA-256 digests on the backend. Consumed tokens are retained through their family's lifetime so reuse can revoke the entire family.
- Refresh rotation serializes on the session family in PostgreSQL. Every authenticated request checks family expiry/revocation against the database; logout revokes access immediately as well as refresh credentials.
- Shared atomic database counters for login, registration, refresh, and logout attempts. Login uses the same password verification path for unknown accounts.
- Workspace membership and explicit project grants on every project operation. Workspace owner/admin roles inherit project maintainer access. Only workspace administrators manage membership and grants; ordinary project maintainers cannot elevate members.
- Removing workspace membership deletes existing project grants, so rejoining does not resurrect privileges. Owner membership cannot be removed.
- Atomic audit records for successful identity, membership, project, environment, and grant changes. Audit access is restricted to workspace administrators.
- Native Keychain/Keystore refresh storage via Expo SecureStore. Access credentials stay in memory. Web preview keeps both credentials in memory and requires sign-in after a page reload.
- CORS allowlist, no-store responses, nosniff headers, generic login failure messages, parameterized database queries, and foreign-key/role/uniqueness constraints.

## Limits and release gates

- SQLite is for single-process local development only. Concurrent rotation guarantees are validated against PostgreSQL; use PostgreSQL for shared deployments.
- No browser persistent authentication is offered in M1. A production browser client needs a separate reviewed secure-cookie/CSRF design or an equally deliberate session architecture.
- Public registration must remain restricted until email ownership and recovery are implemented. The private preview exposes duplicate-account conflicts and supports adding an existing account by email.
- TLS, request-size limits, ingress timeouts, backup/restore, secret management, and trusted proxy settings require deployment configuration. Compose is a local development configuration.
- Refresh-token garbage collection, comprehensive failed-action auditing, storage retention jobs, MFA/SSO, and a production threat-model review remain tracked hardening work. Do not remove consumed refresh records before the session-family expiry.
- No code execution, model access, external provider tokens, provider writes, or production deployment capability exists at this milestone.

Run the automated authorization/revocation tests against PostgreSQL before changes to identity or permission logic. Never run them against a database containing valuable data.
