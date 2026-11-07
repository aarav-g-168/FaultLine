# Faultline implementation plan

Status: planning only. No application implementation has started.

## Working agreement

Implement one milestone at a time. At its end, run the relevant tests, fix regressions, update documentation, demonstrate the accepted workflow, and stop for user review before beginning the next milestone. Do not equate scaffolded UI, replayed AI output, or unconfigured integrations with completed functionality.

This initial checkpoint delivers PRODUCT.md, ARCHITECTURE.md, and this plan after inspection of the empty workspace. The next action after review is M1, not the entire application.

## M1 — Foundation, identity, and mobile shell

Tasks:
- Initialize the repository and monorepo layout, pinned dependencies, formatting/type checks, CI, and configuration validation.
- Build FastAPI, SQLAlchemy models, Alembic migrations, PostgreSQL/Redis Compose services, and generated TypeScript API client.
- Implement registration, login, refresh rotation/reuse detection, logout, workspaces, membership, projects, environments, and project grants.
- Build Expo Router shell, theme tokens, workspace switcher, sign-in/create-workspace screens, and accessible state components.
- Document environment variables with example values and no real secrets; provide database boot/migration and mobile startup commands.

Acceptance:
- A clean database migrates successfully. A user registers, signs in on mobile, creates a workspace/project, and sees it after restart.
- Separate users cannot read or mutate one another's projects; revoked grants and expired/reused credentials are rejected.
- Mobile securely stores refresh credentials; API errors and offline/session expiry states are usable.
- Backend identity/authorization tests, client type checks, and relevant mobile tests pass. Capture the first running-app screenshots.

Review checkpoint: demonstrate two users and project access boundaries; review the navigation and visual foundation.

## M2 — Real ingestion and reproducible incident

Tasks:
- Add delivery receipts, redaction, normalized events, grouping, lifecycle, notes, deployment correlation, and timeline APIs.
- Add transactional outbox, Celery dispatch, idempotent jobs, retry/lease recovery, and authenticated activity subscriptions.
- Implement the reproducible checkout fixture and signed telemetry/deployment producer.
- Build incident feed/detail/timeline with source evidence drilldown and honest empty/error states.

Acceptance:
- Running the demo creates a real persisted incident and timeline; repeated deliveries do not inflate occurrence counts.
- Concurrent repeated failures group correctly; separate projects/environments remain separate.
- Invalid signatures, replayed deliveries, oversized payloads, and sensitive fields are handled correctly.
- Queue interruption recovers from the outbox; retrying a partially processed event creates no duplicate incident.
- Demo reset is explicitly scoped to demo data and is repeatable.

Review checkpoint: trigger the failure and inspect the original redacted evidence from mobile.

## M3 — Evidence-grounded investigation

Tasks:
- Add immutable evidence packs, investigation jobs, strict schemas, bounded read tools, and server-side reference validation.
- Add live model adapter, usage/cost tracking, cancellation, timeout/error states, and clearly labeled offline replay.
- Build ranked hypotheses, supporting/contradicting evidence, uncertainty, and missing-information views.
- Start the labeled evaluation harness with at least five scenarios including misleading correlations and insufficient evidence.

Acceptance:
- A configured live model investigates the demo using actual stored telemetry/source; every evidence link resolves within the authorized snapshot.
- Unknown IDs, cross-project IDs, false source locations, malformed output, and tool-budget violations fail safely.
- Malicious instructions embedded in logs cannot invoke write tools or bypass evidence checks.
- Missing credentials show setup requirements. Replay results are marked as replay everywhere they appear.
- Evaluation reports distinguish reference validity from whether evidence actually supports the claim.

Review checkpoint: inspect one correct diagnosis and one honest insufficient-evidence result.

## M4 — GitHub App and repository analysis

Tasks:
- Implement verified App installation lifecycle, repository selection, backend token handling, scope checks, webhook validation, and revocation.
- Retrieve immutable source snapshots, deployment commit metadata, diffs, and bounded code-search context.
- Connect GitHub evidence to investigations and provide installation/setup documentation.

Acceptance:
- A configured installation reads only selected authorized repositories; revoked installations lose access.
- No installation token or source credential reaches the mobile app, model prompt, logs, or executor.
- Live commit/file references match the recorded SHA. Pagination, rate limits, signature failures, and delivery retries are covered.
- Tests use protocol fixtures; a real configured installation gets a recorded smoke test before integration is marked connected.

Review checkpoint: investigate the same scenario against the user's actual demo repository.

## M5 — Real patches and isolated verification

Tasks:
- Generate and validate minimal patch revisions anchored to a base SHA; provide review/reject and mobile unified diff viewing.
- Implement restricted executor protocol, pinned demo image, separate baseline/patched runs, resource caps, cancellation, artifacts, and cleanup/reaper.
- Build verification result UI and bounded iterative patch generation from test failures.

Acceptance:
- The unmodified demo fails the relevant test; the actual generated patched checkout passes it in separate isolated runs.
- Traversal, symlink escape, disallowed files, oversized diffs, command injection, secret access, network attempts, runaway processes, and timeout/cleanup paths have automated checks.
- Infrastructure failure and unsupported dependency changes never appear as a successful verification.
- Reports bind source SHA, patch/image digests, policy version, commands, outputs, limits, and test counts.
- A running Docker-capable environment is required for this checkpoint. If unavailable locally, configure an authorized remote executor; do not mark execution complete without real runs.

Review checkpoint: review the actual diff and the baseline/patched test evidence on mobile.

## M6 — Approved draft PR and operational integrations

Tasks:
- Implement exact-input, expiring PR approval, reauthorization, idempotent branch/PR operation, remote reconciliation, and status tracking.
- Include incident link, diagnosis, patch rationale, verification results, and limitations in the draft PR body.
- Add real Sentry ingestion, GitHub Actions metadata, and Vercel deployment adapters with setup/status screens.
- Add durable in-app notifications; add push with explicit opt-in and minimal sensitive content after the core flow works.

Acceptance:
- No GitHub write occurs before explicit approval. Changed patch/base/verification or revoked authority invalidates approval.
- An approved request creates exactly one draft PR containing the reviewed patch even after retries or lost network responses.
- Partial branch creation recovers truthfully and is auditable; no merge or deployment action exists.
- Each additional provider passes its signature, replay/deduplication, authorization, normalization, and reconnect checks. Unconfigured providers remain visibly unavailable.

Review checkpoint: explicitly approve and create a real draft PR in the configured demo repository.

## M7 — Release hardening and demonstration

Tasks:
- Complete at least 30 reviewed reproducible scenario labels; report accuracy, evidence validity/support, latency, pass rate, duplicates, API p95, and model costs.
- Add Pytest integration coverage, meaningful mobile Jest tests, and Maestro end-to-end journeys.
- Complete accessibility, light/dark themes, reduced motion, offline/reconnect, retention/deletion, backup/restore, and security review.
- Verify production isolation before enabling untrusted customer execution; document any remaining deployment restrictions.
- Provide Docker/deployment instructions, migration runbooks, environment reference, architecture updates, setup troubleshooting, and captured screenshots in README.
- Record the full incident → live investigation → real diff → isolated tests → approved draft PR demonstration.

Acceptance:
- Fresh setup instructions reproduce the demo; credentials required for live model/GitHub actions are explicit.
- All required tests and CI checks pass, including authorization, webhook validation, output validation, retry recovery, and execution safety.
- Publish measured results with dataset/model/environment versions; do not substitute estimated metrics.
- No unresolved critical security issue or fabricated integration success remains. Document unsupported targets and verification limitations.

Review checkpoint: release candidate review using the complete recorded and repeatable end-to-end workflow.

## Configuration inventory to document as features land

| Area | Configuration |
| --- | --- |
| Mobile | Public API/WebSocket URLs, app environment; no backend secrets |
| API | Database URL, access-token signing key/issuer/audience, allowed origins, rate and payload limits |
| Jobs | Redis URL, queue names, retry budgets, job leases |
| Credentials | External encryption key reference and version; rotation procedure |
| Model | Server-only API credential, model ID, token/tool/cost/time budgets |
| GitHub | App ID, private-key reference, webhook secret, installation callback URL |
| Monitoring/deployment | Provider credentials, webhook secrets, allowed projects/environments |
| Executor | Control endpoint/auth reference, approved image digest, limits, artifact store and retention |
| Demo | Explicit demo-mode flag, scoped fixture IDs, demo signing secret |

## Current checkpoint

- Complete: inspect workspace and available development commands; propose working name and architecture; create planning documents.
- Pending: user review of this plan and M1 authorization.
- Known environment constraint: Docker is not currently on PATH. Verify availability or arrange an executor before M5.
- Not performed: dependency installation, application scaffolding, migrations, runtime tests, provider connections, or GitHub writes.
