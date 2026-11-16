# BharatCrop Intelligence: Proposed Implementation Backlog

**Status:** Conditional backlog approval for planning. These phases are proposals, not implementation evidence or release approval. The existing notebooks, datasets, model artifacts, metadata, reports, and research outputs are preserved and remain outside the application build lifecycle.

## Backlog principles and current disposition

- Use the locked Next.js/TypeScript, FastAPI modular monolith, and PostgreSQL direction. Do not add microservices without measured justification.
- Backend authorization is authoritative. Never treat a hidden UI control, model artifact, registry row, smoke report, or a name-matched district as approval.
- Design/implement only contracts whose evidence and lifecycle requirements are resolved. Unsupported geography, unknown yield units/seasons, absent model artifacts, unapproved data sources, and insufficient assistant evidence fail closed.
- The first implementation backlog can start with repository/tooling decisions and provider-independent scaffolding. Account/farm data collection, location-dependent features, prediction/ranking, expert sharing, weather, assistant-provider calls, and public deployment each have explicit dependency gates.
- This backlog does not mark the five P0 findings resolved. Their dispositions and exit criteria are in `p0-resolution-plan.md`.

## Work that can begin immediately after human backlog approval

1. Establish the proposed application workspace boundary and preservation policy without moving or overwriting research assets.
2. Inventory available developer/build tools and select project conventions for the approved stack; create no stack-specific assumptions from the existing IntelliJ Java module configuration.
3. Define automated quality/security checks and their ownership for new application code.
4. Prepare provider comparison and data/domain evidence work items with accountable reviewers.
5. Draft provider-independent API envelope, correlation, pagination, and test fixtures that do not encode unknown yield units, geographic identifiers, provider behavior, or model versions.

These are backlog items only; no application source, configuration, migration, or dependency was changed in this task.

## Phase 1 — Repository and tooling foundation

**Scope**

- Confirm root/workspace boundaries and how new application code will coexist with the research repository without altering protected notebooks/data/model outputs.
- Establish reproducible Next.js/TypeScript and FastAPI modular-monolith project conventions, dependency locking, formatting/type checks, automated tests, API documentation generation approach, and continuous integration.
- Define environment separation and local developer onboarding without committing secrets.
- Add baseline secret/dependency/license scanning and a preservation check for restricted research paths.

**Exclusions**

- No model inference, production database, identity provider, AI/weather provider, farm/location capture, or public deployment.
- No migration or source ingestion before their later gates.

**Dependencies and blockers**

- Requires human approval of application workspace boundary and build tooling/package-manager choices.
- Does not require provider selection or model unit/coverage decisions.
- Current root has no app manifests, app source, Git metadata, or existing automated test suite according to `repository-audit.md`; exact organization/CI ownership must be chosen.

**Deliverables**

- Documented developer setup and locked dependency manifests for the approved app stack.
- Minimal application skeleton and modular boundary conventions (future implementation work).
- Automated checks, safe configuration pattern, CI workflow, and explicit protected-research path rules.

**Automated and manual tests**

- Clean-environment dependency install/build and type-check for each application component.
- Unit-test discovery and CI pass/fail behavior.
- Secret/dependency/license scans on new application scope.
- Manual review that application setup/checks do not overwrite or execute notebooks/artifacts.

**Acceptance criteria**

- Fresh checkout can reproduce documented app checks using locked dependencies.
- No secrets are required in source or committed config.
- CI validates only defined application paths and does not mutate research outputs.
- Architecture/module ownership and quality-gate owner are documented.

**Release gate**

- Gate to Phase 2: tooling builds reproducibly; automated checks pass; research preservation boundary and application ownership are reviewed. This does not approve any user-data feature or release.

**Begin status:** Can be prepared immediately; implementation starts only after backlog approval.

## Phase 2 — Database, migrations, authentication, and authorization

**Scope**

- Compare and select an established authentication provider/standards-based managed solution; specify browser/API session and logout/revocation lifecycle.
- Define the minimal PostgreSQL schema and migrations for accounts, roles, preferences, audit records, and any approved operational records.
- Implement server-side authentication integration, role mapping, deny-by-default authorization primitives, correlation context, and durable idempotency for retained state-changing operations.
- Decide whether export/deletion workflows are included; if included, specify durable request entities, transitions, retention, legal holds, secure export delivery, and backup/dependency deletion behavior before exposing endpoints.
- Define expert role issuance/verification and audit authority before granting expert privileges.

**Exclusions**

- No farmer farm/location capture until F-04 location authority and data-minimization/retention decisions pass.
- No active expert cases until F-02 lifecycle and legal/privacy review pass.
- No yield/ranking inference or assistant provider calls.

**Dependencies and blockers**

- Phase 1 checks and project skeleton.
- Authentication provider comparison/decision, data-processing terms, security review, role capability matrix.
- Human privacy/legal decisions on personal data, retention, deletion, consent notices, and any alternative authorized basis.
- F-03: decide MVP API scope and durable idempotency/export/deletion/assignment persistence.

**Deliverables**

- Reviewed logical/physical schema, versioned migration plan, backups/restore expectations, and ownership constraints.
- Authentication integration boundary and verified identity-to-account mapping.
- Backend authorization policies and safe audit events.
- Idempotency semantics and persisted state for each included retryable mutation.
- Data subject request and deletion flow only if approved and fully specified.

**Automated and manual tests**

- Migration up/down or forward-recovery tests; transaction and uniqueness constraints.
- Authentication tests for invalid issuer/audience/expiry, account linking, logout/revocation, and recovery.
- Authorization tests for farmer self-access, cross-user IDs, role escalation, administrator least privilege, suspended accounts, and paginated ownership.
- Idempotency same-key/same-payload replay, same-key/different-payload conflict, concurrency and restart recovery.
- Manual privacy review of data fields, access and retention; confirm audit contains no secrets or unnecessary personal content.

**Acceptance criteria**

- No client-supplied user/owner/role can broaden access.
- Each persistent personal-data class has purpose, owner, access, retention/deletion, and audit classification.
- Any included export/deletion endpoint has durable state and legally reviewed completion/exception behavior; otherwise it is absent/disabled.
- No expert role grants access to farmer resources by role alone.

**Release gate**

- Gate to farmer personal-data capture: identity/session controls, role/ownership tests, retention/deletion rules, and data-minimization review pass.
- Gate to expert-case data: F-02 closure and exact grant/assignment tests pass.

**Blocked work:** Provider-specific auth integration, personal-data retention choices, and any case access await human review/decisions.

## Phase 3 — Data contracts, model evidence, and gated API capabilities

**Scope**

- Establish source and location evidence before location-dependent API contracts.
- Resolve yield target units, APY measurement semantics, `Season = Total`, eligible candidate cohort, feature fields, farm-to-model mapping, supported years/categories, and model artifact provenance.
- Define prediction/ranking execution mode, status transitions, synchronous initial behavior, idempotency, persistence opt-in, and immutable model/evidence provenance.
- Build contract tests and feature flags/release gates. Add only adapters for individually approved capabilities.
- Keep crop ranking described as a derived yield-based ranking, not a separate trained recommendation model.
- Keep weather descriptive and disabled absent source rights, freshness, units, geography, season alignment, and coverage evidence. Keep low-yield classifier and risk warnings out of farmer-facing scope.

**Exclusions**

- No model retraining or notebook execution is part of this backlog phase without a separately approved research task.
- No risk warnings, profitability claims, causal claims, nationwide model-validity claims, or 2025+ extrapolation based only on the current metadata.
- No assumption that the `.joblib` artifact can be safely loaded or is valid.

**Dependencies and blockers**

- Phase 1; Phase 2 auth/ownership primitives for user-bound routes.
- F-01 unit/season/input/eligibility evidence and independent model review.
- F-04 authoritative, versioned location vocabulary and coverage.
- F-05 execution/provenance contract.
- Source rights and data-governance review; weather P1 gates before weather release.

**Deliverables**

- Approved source/feature/model evidence records, location adapter contract, coverage state definitions, model release record schema.
- Versioned request/response contracts for only approved operations.
- Inference adapter with explicit disabled/unavailable states until approval.
- Saved-result provenance and retention contract, if history is in scope.

**Automated and manual tests**

- Schema and semantic validation for required/malformed/unsupported input, location vintage, unit, season, and coverage states.
- Model contract tests against approved artifact only: checksum/provenance gate, input/output shape, missing/unseen/out-of-domain values, finite values, dependency failures, repeatability as required.
- API tests for auth ownership, explicit consent scope, disabled model, timeout, idempotency, persistence and provenance retrieval.
- Manual ML/domain review of temporal/geographic holdouts, target units, data leakage, subgroups, candidate eligibility, and farmer-facing language.

**Acceptance criteria**

- No prediction/ranking route returns an output until the exact component release is approved.
- Saved outputs identify exact approved registry/evidence revision and artifact checksum; no invented model version.
- The route rejects unknown unit/season/location scope rather than guessing.
- Ranking UI/API explicitly states predicted-yield basis and candidate constraints.
- Weather missingness remains unavailable, not zero risk; no low-yield/risk warning route.

**Release gate**

- Per-feature model/data approval by designated domain, data, and model owners. Gate does not follow from artifact presence or documentation wording.

**Blocked work:** Yield/ranking serving is blocked by F-01/F-04/F-05 exit criteria and model evaluation. Weather is additionally blocked by source, freshness, and season-alignment evidence. Mandi prices remain excluded.

## Phase 4 — Core Next.js farmer experience and localization

**Scope**

- Implement public web shell, account/preferences surfaces, navigation, Hindi/English language switching, consent/privacy UX, accessibility baseline, and error/coverage states.
- Add farm management only after Phase 2 personal-data gate and Phase 3 authoritative location contract pass.
- Add weather/yield/ranking views only for individually approved Phase 3 capabilities.

**Exclusions**

- No client-side authorization as a substitute for backend checks.
- No UI for unsupported models, risk warnings, mandi-price trends, unverified location resolution, or unavailable sources.
- No promises of a full agronomic recommendation from yield ranking.

**Dependencies and blockers**

- Phase 1 frontend tooling and Phase 2 auth/account APIs.
- Reviewed Hindi/English translations and privacy/consent copy.
- Farm views depend on F-04; prediction views depend on Phase 3 release gates.
- Accessibility target and performance budgets are P2 decisions to settle before public launch.

**Deliverables**

- Responsive farmer portal with localized, accessible flows and evidence-aware coverage/results presentation.
- Server-authoritative API integration and safe error/fallback behavior.
- Localization catalog and human-reviewed agricultural vocabulary.

**Automated and manual tests**

- Component/UI tests in both locales; API integration tests; language preference persistence and switching.
- Browser tests for session expiry, forbidden resources, error states, pagination, and low-bandwidth conditions.
- Human Hindi/English review for consent, errors, terms, units, and agricultural terminology.
- Keyboard, screen-reader, mobile and target accessibility conformance tests.

**Acceptance criteria**

- No user-visible English-only required flow in Hindi mode; no silent language fallback.
- UI preserves source attribution and exact limitations/status returned by the API.
- Unsupported/unknown location and disabled feature states are explicit and non-misleading.
- User can access only own data; authorization errors do not reveal other users' content.

**Release gate**

- Farmer experience is not public until data/privacy, API security, localization/accessibility, and any model/weather feature-specific gates pass.

**Blocked work:** Location-specific farm UX and predictions await verified geography and model contract; no user data collection before retention/consent sign-off.

## Phase 5 — Grounded assistant and expert workflows

**Scope**

- Select an AI provider only after privacy/security, legal, quality, Hindi/English, retention/training, data-region, and cost evaluation.
- Establish curated-source provenance, rights review, immutable versions, safe ingestion, retrieval tests, publication/withdrawal workflow, and claim-linked citations.
- Implement assistant conversation/message lifecycle, minimization, abstention, source citations, provider failure handling, and expert referral.
- Implement the two-stage expert-sharing lifecycle only after F-02 approval: non-sensitive share request → explicit named-grantee scope → atomic case activation → audited access → expiry/revocation.
- For MVP, use explicit consent only; alternative legal basis remains out of scope until separately reviewed and approved.

**Exclusions**

- No unrestricted web answers, arbitrary source URL fetching, unreviewed document retrieval, private chat reuse for training, or citation-by-presence.
- No expert access to pending request details or user conversations unless separately included in the explicit grant.
- No assistant-generated farmer risk warnings from exploratory outputs.

**Dependencies and blockers**

- Phase 1 security/test tooling; Phase 2 authentication, ownership, audit, retention and case persistence.
- F-02 closure; expert selection/verification and consent copy review.
- Provider/legal approval and a curated source set with terms and source owners.
- Claim-level citation representation and source-admin state-machine contract (P1).

**Deliverables**

- Approved provider decision and processing controls.
- Versioned knowledge ingestion/review/publish/withdraw workflow.
- Retrieval and assistant orchestration with claim-to-source provenance, validated citations and abstention.
- Scoped expert cases/reviews with assignment history, grant verification, revocation and audited reads.

**Automated and manual tests**

- Grounding tests at claim-level, citation-to-span support, source version/withdrawal, contradictory/stale evidence, and unsupported-question abstention.
- Prompt-injection, poisoned metadata, multilingual injection, cross-user data-leakage, untrusted upload, and tool/URL misuse tests.
- Provider timeout/invalid output/rate limit; minimization and deletion/retention tests.
- Hindi/English terminology and citation-quality review by fluent domain experts.
- Expert role/assignment/consent scope, pending-state invisibility, grant expiry/revocation race and audit integration tests.

**Acceptance criteria**

- Every material agricultural claim is supported by a retrieved, currently approved source version or the assistant abstains.
- No model-provider call receives unnecessary direct identifiers, farm coordinates, or unrelated conversation context.
- Pending/unreviewed/withdrawn documents cannot be retrieved.
- Expert reads are restricted to active, assigned and explicitly authorized resources; revocation blocks subsequent access.
- No exploratory risk output is presented as a validated future-risk warning.

**Release gate**

- Assistant and expert features are independently approved after privacy/legal review, corpus rights, provider contract, grounding/security/localization evaluation, and authorization tests. One feature's approval does not approve the other.

**Blocked work:** AI provider, source corpus rights, citation schema, expert selection, legal consent wording and retention are unresolved.

## Phase 6 — Deployment hardening, observability, security, and release validation

**Scope**

- Containerized application services, selected hosting/region, managed PostgreSQL, secrets management, encrypted backups, restore/recovery, least-privilege networking, monitoring, alerting, incident response, and rollback.
- Set and measure SLO/latency/capacity/RTO/RPO from approved requirements.
- Run complete public-launch security, privacy, accessibility, localization, integration, and operational gates.

**Exclusions**

- No public launch on unresolved source rights, privacy basis, feature approval, or provider terms.
- No numerical operational target assumed without owner approval and measurement.

**Dependencies and blockers**

- Prior service/features included in launch scope.
- Hosting, region, database and AI/auth/weather provider decisions as applicable.
- Security threat model, legal/privacy review, SLO/RTO/RPO, operational owner, support and incident contact.

**Deliverables**

- Reproducible release images and provenance; production configuration/secrets design; managed database operational plan.
- Monitoring and sanitized logs with correlation IDs; backup, restore, rollback and incident runbooks.
- Evidence package for all release gates, including data/source notices and model/assistant cards.

**Automated and manual tests**

- Container/dependency/SBOM/secret scans, authorization regression and security assessment.
- TLS/secrets injection/rotation, database migration and rollback/recovery, backup restore and deletion propagation tests.
- Load/latency/capacity and provider failure tests against approved objectives.
- Incident response tabletop and human legal/privacy, accessibility, Hindi/English and domain sign-offs.

**Acceptance criteria**

- All critical/high security findings are closed or explicitly accepted by accountable security owner with compensating control; no secrets or unnecessary personal data in logs.
- Restore and rollback are demonstrated; backup access/retention and data deletion semantics are reviewed.
- Monitoring exposes failure/coverage/feature status without revealing sensitive configuration or personal content.
- Every launched feature has source/model/provider provenance and evidence appropriate to its claim.

**Release gate**

- Public release only after product, domain, engineering, security, privacy/legal and operations owners sign off; all unresolved gates affecting shipped features are closed. “India-wide target” is not a release claim of nationwide coverage.

## Cross-phase required acceptance checks

- **API:** schema/validation, stable sanitized errors, timestamps, known units, pagination, correlation IDs, idempotency, concurrency and timeout semantics.
- **Authorization:** ownership, roles, case assignment, consent scope/expiry/revocation, admin least privilege, IDOR/enumeration, audit and deletion.
- **Model/data:** artifact provenance, independent evidence, target units, season semantics, geography coverage, missing/unseen input rejection, versioned result provenance, no unsupported predictions.
- **Assistant:** approved source versions, claim-level grounding/citations, abstention, injection, privacy minimization, provider failure and Hindi/English evaluation.
- **Localization/accessibility:** Hindi and English parity, reviewed agricultural language, switch/fallback, screen-reader/keyboard/mobile review.
- **Operations/security:** container/dependency/secret scanning, logging redaction, rate limits, backups/restore, monitoring, incident response, rollback and approved service objectives.

## Blocker register

| Blocker | Blocks |
|---|---|
| Yield units, `Total` season semantics, feature/eligibility schema, independent validation | Yield and ranking API/inference and related UI. |
| Authoritative versioned location reference and coverage | Farm location, location coverage, weather, yield/ranking geography and any district-specific advice. |
| Case-share lifecycle, expert selection, consent language and retention | Expert cases/reviews and any expert access to farmer data. |
| Durable export/deletion/idempotency and approved retention | Personal-data capture and all retryable mutations; export/deletion routes remain absent until specified. |
| Auth provider/session decision | Production account authentication; provider-independent scaffolding and comparison work may proceed. |
| Assistant provider, corpus rights, source-admin contract and claim-linked citation model | Assistant implementation/public answers. |
| Mandi source status, rights and historical coverage | Any mandi-price feature; excluded from MVP absent explicit approval. |
| Hosting/region, SLO/RTO/RPO, security/legal sign-off | Public deployment and launch. |

## Backlog approval status

**Conditionally approved for backlog planning only.** Phase 1 tooling and evidence-resolution work may be prioritized immediately. Phase 2–6 may be decomposed and estimated with the blockers above tagged explicitly. This document does not approve starting implementation, closing any P0 finding, serving the existing yield artifact, collecting farmer data, enabling expert access, adding mandi prices, or launching publicly.
