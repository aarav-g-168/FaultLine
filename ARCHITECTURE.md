# Faultline architecture

Status: proposed; implementation starts after foundation review.

## Shape and repository layout

Use a modular monolith with a separately deployed worker and isolated execution infrastructure. PostgreSQL owns durable state; Redis carries transient queues and notifications. No microservice split is needed for the first release.

```text
apps/mobile/                 Expo, React Native, TypeScript, Expo Router
services/api/                FastAPI application and domain modules
services/api/alembic/        PostgreSQL migrations
services/worker/             Celery entry points using shared backend modules
services/executor/           Restricted verification runner and policies
packages/api-client/         Generated TypeScript client from OpenAPI
demo/checkout-service/       Reproducible failing service and tests
demo/scenarios/              Versioned event fixtures and labels
evals/                      Investigation evaluation harness and reports
infra/                      Compose, images, deployment examples
docs/                       Setup, threat model, runbooks, screenshots
```

Pin supported dependency versions and commit lockfiles during foundation work. Avoid duplicated client/server schemas: generate the client from FastAPI's OpenAPI contract. Use TanStack Query for server state and small local state for session/navigation preferences.

## Runtime boundaries

```text
Expo client --HTTPS--> API --transactions--> PostgreSQL
Provider webhooks ----> API --outbox-------> Dispatcher --> Redis/Celery
                                                Worker --> GitHub/model APIs
                                                Worker --> Executor control API
Executor --> disposable sandbox --> bounded test artifacts
API <-- durable job state and events <-- Worker
Client <-- authenticated WebSocket updates; REST reconnect reconciliation
```

API and workers share application code and database models, but have separate process identities and least-privilege secrets. The mobile bundle contains only public configuration. The executor has no production database, integration credentials, model keys, or access to production networks. A worker can request an execution but cannot send arbitrary shell commands.

## Domain modules and relationships

| Module | Main records and relationships |
| --- | --- |
| Identity | users, credential hashes, refresh sessions; workspace memberships connect users to workspaces |
| Projects | workspaces own projects; project grants connect members to projects; projects own environments |
| Integrations | project connections reference GitHub installations/provider configuration; encrypted credential records carry key versions |
| Repositories | project repositories hold provider identity and allowed base branches; snapshots record immutable commit SHAs and manifest digests |
| Ingestion | webhook deliveries have provider delivery IDs, receipt times, signature outcomes, and retention limits; normalized events belong to project/environment |
| Incidents | incidents group event occurrences; incident events and notes form the timeline; state transitions are audited |
| Evidence | evidence items reference redacted events, deployments, commit metadata, or content-addressed source excerpts and revision/line metadata |
| Investigation | investigations reference incident, source snapshot, model/prompt versions, usage, status; hypotheses and claim/evidence links belong to an investigation |
| Patches | patch revisions reference selected hypothesis, repository, base SHA, diff artifact, and digest |
| Verification | runs reference exact patch revisions, runner image digest, policy version, baseline/patched outcomes, artifact digests, and expiry |
| GitHub writes | approvals bind user, patch digest, base SHA, verification ID, and target; PR operations store idempotency key and remote PR identity |
| Operations | jobs, outbox entries, audit events, and notifications provide retries, delivery tracking, and activity |

Use UUID identifiers and UTC timestamps. Include workspace/project scope on security-sensitive records. Foreign keys and compound uniqueness constraints enforce scope and idempotency. Use transactions for state transitions. Immutable evidence and patch records are superseded rather than overwritten.

## Authentication and authorization

- Foundation: email/password authentication using Argon2id, short-lived signed access tokens, rotating opaque refresh tokens stored hashed, revocation, and login throttling. No hard-coded users or signing secrets.
- Store mobile refresh credentials in OS-backed secure storage; keep access tokens in memory. Explicitly design a secure cookie/session strategy if browser support is added.
- Enforce membership and project grants in every query and background job. Recheck authorization before writes; WebSocket subscriptions use the same policy.
- Check audience, issuer, expiry, token identifier, and refresh reuse. Logout revokes the refresh family. Require current authority at PR execution even after approval.
- Configure HTTPS, strict origin policy where relevant, bounded request sizes, and redacted structured logs. Add email verification and recovery before public registration opens.

## Ingestion and job flow

1. Resolve the provider connection without trusting a project ID in the payload. Enforce body-size limits and verify the signature over the raw request body.
2. Apply provider timestamp windows when supported. For providers without signed timestamps, combine signature validation with durable delivery-ID deduplication and documented replay limits.
3. Insert a delivery receipt with a unique connection/provider delivery key. Duplicates return an accepted response without enqueuing new work.
4. Commit a durable outbox entry before acknowledging. A dispatcher retries publication; workers tolerate duplicate queue deliveries.
5. Normalize and redact before evidence storage or model access. Preserve allowlisted attributes; remove authorization headers, tokens, cookies, and configured sensitive fields.
6. Deduplicate normalized source events and upsert grouping under a transaction/unique active grouping constraint to avoid concurrent incident creation.
7. Correlate deployments using environment, release/commit, and time bounds. Store the correlation method and uncertainty.
8. Publish activity after committing durable state. Clients reconnect using a cursor and recover state through REST.

Jobs use explicit states, bounded retries with backoff, leases/heartbeats, attempt records, and terminal failure reasons. Side effects use unique operation keys. Recovery reconciles ambiguous remote outcomes before retrying writes.

## Evidence-grounded investigation

The worker assembles a bounded evidence pack from authorized persisted records and immutable repository snapshots. Treat logs, code, comments, and provider content as untrusted data, never operational instructions. Allowlist read tools and cap tool calls, retrieved bytes, latency, and spend.

The model returns a strict schema containing hypotheses, claims, support/contradiction evidence IDs, uncertainty, missing information, and next steps. Validate the schema and every ID against the investigation's evidence pack and project. Validate source paths, revisions, and excerpt locations against the stored snapshot. Unsupported output is rejected or retried within a small budget; never silently fill gaps with fabricated records.

Store redacted evidence-pack digest, tool trace, schema/prompt/model versions, timing, and usage. Do not log full prompts by default. Keep deterministic demo replay separate from the live model adapter and label it in both API responses and UI.

## Patch and verification boundary

1. Generate a unified diff against a fixed source snapshot. Parse it server-side and validate paths, file types, size, and permitted scope.
2. Materialize the immutable source and patch without carrying repository credential files into execution. Reject traversal, symlink escapes, submodule execution, and repository-specified build hooks.
3. Run baseline and patched tests in separate disposable environments with identical image, policy, fixtures, and resource limits.
4. Use a non-root user, read-only root filesystem, bounded scratch space, dropped capabilities, no host mounts/socket, no privileged mode, disabled network, process/CPU/memory/output/time limits, and enforced cleanup.
5. Test commands come from administrator-controlled policies, not model output or untrusted repository configuration. Dependencies are prebuilt into a pinned image; dependency changes are unsupported initially.
6. Collect bounded redacted logs, exit status, test counts, durations, runner/policy versions, and cleanup status. A reaper cleans orphaned runs after crashes.

Containers alone are not a sufficient hostile multi-tenant execution boundary. Local trusted fixtures may use hardened Docker containers. Arbitrary customer code must run on dedicated ephemeral VMs or an appropriately sandboxed runtime with an independently enforced boundary. Public untrusted execution stays disabled until that deployment and its escape/network tests are verified. Docker unavailability must produce an explicit unavailable state, never a fabricated test pass.

## Draft PR boundary

Use a GitHub App with repository metadata/content reads and only the content/PR write permissions needed by the approved workflow. Keep installation tokens short-lived and backend-only; encrypt persisted credentials with externally managed versioned keys.

The user approves a concrete request showing destination, exact diff, and verification limits. The API issues a single-use, expiring approval bound to immutable inputs. The worker rechecks grants, installation scope, base commit, patch digest, and verification policy, then creates a dedicated branch and draft PR. Record remote side effects as a resumable operation. If a network response is lost, reconcile branch/PR state before retrying. Audit approval and outcome. No production deployment or merge capability is exposed.

## Operations and deployment

- Compose for PostgreSQL, Redis, API, worker, and local demo; executor opt-in on a suitable host. Do not expose Docker's socket to API or worker containers.
- Health/readiness endpoints distinguish API, database, queue, and executor availability. Queue outages retain outbox work.
- Document migration ownership, rollback/forward recovery, backups and restoration, credential rotation, incident response, and evidence/artifact retention.
- Production uses TLS, managed secrets, private database/queue access, restricted egress, separate executor infrastructure, and encrypted artifact storage. Local development secrets never become production defaults.
- Record API latency, ingestion lag, queue age, investigation duration/cost, verification outcomes, duplicate grouping, and integration failures without raw sensitive payloads.

## Decisions to validate during implementation

- Confirm supported Expo/FastAPI/library versions and each provider's current APIs using official documentation.
- Select a model supporting validated structured output; keep provider behavior behind one narrow adapter.
- Confirm a Docker-capable local or remote executor and select the production sandbox boundary before accepting arbitrary repositories for execution.
- Review default evidence retention and credential-key management before deployment.
