# Faultline

Status: product baseline accepted for M1. Foundation implementation is ready for milestone review; later milestones remain planned.

Faultline takes developers from a production failure to an evidence-backed diagnosis, a tested patch, and a human-approved draft pull request.

Faultline is the working name. Domain, package, and trademark availability have not been checked.

## Repository inspection

On 2026-11-07 the workspace was empty, with no source files, package manifests, or Git repository. No applicable AGENTS.md was found in the workspace or its ancestor directories. Node, npm, Python, and Git are available. Docker was not found on PATH; execution availability must be checked before the verification milestone.

## First release and demonstration

The first release supports one complete workflow with real persisted state:

1. Register, sign in, and create a workspace and project.
2. Run a reproducible checkout-service incident: a deployed currency conversion change handles missing exchange rates incorrectly and produces checkout failures.
3. Ingest signed telemetry and deployment events, redact sensitive values, and group duplicate errors into one incident.
4. Open a chronological timeline with error samples, deployment metadata, and immutable source references.
5. Request an investigation. Inspect ranked hypotheses, supporting and contradicting evidence, missing information, and uncertainty.
6. Select a hypothesis and request a minimal patch against the recorded source commit.
7. Review the actual unified diff and request verification.
8. Compare failing baseline tests with patched tests in a disposable sandbox. Inspect output, skipped checks, and execution restrictions.
9. With a configured GitHub App and a user-owned demo repository, explicitly approve creating a draft PR containing the exact reviewed patch, investigation summary, and verification report.

The local demonstration works without external accounts through step 8 using a checked-in fixture repository. Step 9 requires an actual GitHub installation and repository permission. Without those, show setup requirements and a reviewable PR preview; do not report a PR as created. Live model investigation requires configured model credentials. An explicitly labeled deterministic replay can exercise the offline UX but does not count as a live AI investigation.

## Scope

### Workspace and access

- Users can belong to multiple workspaces and switch projects.
- Workspace roles: owner, admin, member. Project grants: viewer, investigator, maintainer.
- Viewing evidence requires a project grant. Investigation and patch requests require investigator access. Integration changes and PR approval require maintainer access. Workspace owners/admins can manage project grants; grants and changes are audited.
- Projects hold repositories, environments, integration connections, incidents, and verification policies.
- No anonymous access to source, logs, patches, or execution results.

### Incidents and evidence

- Incident states: open, acknowledged, resolved; severity: critical, high, medium, low.
- Normalized events include source, external ID, project/environment, occurrence and receipt times, event kind, release/commit identifiers, redacted payload, and fingerprint version.
- Deduplicate source event IDs independently from grouping repeated failures into incidents.
- Scope grouping by project, environment, normalized exception type, and stable stack frames. Preserve occurrences and counts; do not silently combine projects or unrelated releases.
- Evidence cards open the underlying redacted record and provenance. Temporal correlation alone is never presented as proof of causation.
- Notes, acknowledgment, resolution, and reopen operations are persisted and audited.

### Investigation and fixes

- Every factual AI claim references server-issued evidence IDs. Reject unknown, cross-project, inaccessible, or revision-mismatched references.
- Hypotheses contain rationale, supporting evidence, contradictory evidence, uncertainty, and next steps. Scores are rankings, not calibrated probabilities.
- Missing signals and unsupported conclusions remain visible. A valid reference proves provenance, not the truth of an inference; measure claim support separately.
- Patches are actual diffs anchored to a repository and base commit, with a file list and explanation. Reject unsafe paths, oversized changes, binary changes, and unsupported targets.
- Patches can be rejected or superseded. Each revision requires its own review and verification.
- Verification distinguishes baseline failure, patched failure, pass, timeout, infrastructure failure, canceled, and unavailable. A pass only describes the tests actually run.
- Draft PR approval binds repository, base SHA, patch digest, verification run, and destination branch. Changes invalidate approval. Never auto-merge or deploy.

### Mobile experience

- Primary navigation: Overview, Incidents, Activity, Settings; workspace/project switcher in the header.
- Incident detail leads into Timeline, Investigation, Patch, and Verification with clear progress and prerequisites.
- Overview shows actionable incident counts, recent deployments, and running investigations rather than decorative metrics.
- Integrations show configured, missing configuration, expired authorization, and degraded status truthfully.
- Notifications initially cover in-app job and incident activity. Push delivery comes after the draft PR workflow works.
- Dark graphite and warm off-white themes, restrained copper accents, semantic severity colors, readable typography, and compact evidence cards define the visual direction.
- Support screen readers, text scaling, reduced motion, adequate contrast, and touch targets of at least 44 points. Severity never relies on color alone.
- Handle empty, loading, permission denied, retryable error, expired session, and offline states. Offline mode may show cached redacted summaries; disable consequential actions until the server can revalidate them.

## Integration order

1. Signed demo producer and fixture repository.
2. GitHub App: scoped repository reads, installation lifecycle, commit comparison, and approved draft PR writes.
3. Sentry: signed event ingestion and release correlation.
4. GitHub Actions: checks and workflow-run metadata.
5. Vercel: signed deployment events and deployment metadata.

Each provider must pass its own signature, delivery deduplication, permission, and reconnect tests before it is labeled supported. Provider capabilities and signature schemes must be verified against official documentation during implementation.

## Non-goals for the first release

- Autonomous production writes, deployment, merge, or remediation.
- Arbitrary commands from model output, unrestricted repository execution, or unrestricted outbound network access.
- Every programming language and build system. The first verifiable target is the Python demo service with an administrator-defined pytest policy.
- Billing, enterprise SSO, general observability storage, and a marketplace of integrations.

## Evaluation and definition of done

- Every milestone passes its acceptance tests, updates setup documentation, and is reviewed before the next milestone begins.
- Maintain labeled scenarios with expected cause, relevant evidence, source revision, baseline failure, and expected patched behavior. Grow from the first scenario to at least 30 reviewed scenarios by release.
- Report top-1 diagnosis accuracy, evidence-reference validity and claim-support rate, investigation latency, patch pass rate, duplicate incident rate, API p95 latency, and model usage/cost.
- Separate deterministic replay, live model, infrastructure failure, and unsupported scenarios in results. Record dataset and model versions and denominator counts.
- Release requires an actual end-to-end recording with a live investigation, real diff, isolated test run, and user-approved draft PR, plus setup instructions, architecture, migrations, automated tests, and screenshots captured from the running app.
