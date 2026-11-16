# BharatCrop Intelligence: Phase Acceptance Criteria

**Status:** Proposed, testable gates. Phases describe future work and are not evidence that implementation has started or passed.

## Phase 0 — Discovery and specification

Exit only when:

- Repository baseline and model/data coverage are documented, with verified facts distinguished from inferences/unknowns.
- Product scope, role journeys, MVP exclusions, geographic evidence rules, Hindi/English behavior, and initial non-functional requirements are reviewed.
- Proposed architecture, API contracts, logical data model, security/privacy design, assistant design, model coverage, phase gates, and decision log are internally consistent and reviewed by product, engineering, domain, and security/privacy owners.
- Authentication, AI, weather, hosting, legal/privacy review, source rights, model release, retention, and numerical SLO/recovery choices are explicitly tracked as unresolved where not decided.
- No notebook, dataset, model, metadata, or research output has been overwritten or silently promoted.

**Current documentation status:** Specifications are proposed for stakeholder review. Their creation alone does not resolve provider/legal choices or establish that a requirement is technically or legally satisfied.

## Phase 1 — Application foundation (future)

Exit only when:

- Next.js/TypeScript, FastAPI modular monolith, and PostgreSQL services build and run reproducibly from documented, pinned/locked dependencies and safe configuration.
- Versioned API schemas and migrations are reviewed; health/readiness and sanitized error contracts behave as documented.
- Authentication provider is selected after comparison; account subject mapping, session lifecycle, role assignment, and revocation are tested.
- Unit/API tests cover request validation, pagination, timestamps/units, correlation IDs, idempotency replay/conflict, and dependency failure paths.
- Authorization tests prove backend enforcement against cross-user access, role escalation, guessed IDs, expired/revoked consent, unassigned experts, and admin overreach.
- Hindi/English tests cover navigation, errors, consent/privacy text, formatting, language persistence, switching, and fallback on mobile/browser targets.
- Security checks include threat model, secret scanning, dependency/container scanning, input limits, rate limits, logging review, and safe CORS/CSRF/session configuration.
- Container deployment, managed PostgreSQL connectivity, secrets integration, encrypted backups, restore test, and operational ownership are documented and exercised in a non-production environment.

## Phase 2 — Evidence-backed data and domain workflows (future)

Exit only when:

- Every exposed source has owner, legal/terms review, schema/version, provenance, freshness, transformations, coverage, units, and quality checks.
- Geographic identifiers and boundary vintage are verified for the exposed locations; unresolved crosswalk records are rejected or marked unknown.
- Weather observations have source/terms, spatial and temporal mapping, units, missingness, update/failure behavior, and appropriate season semantics validated.
- Farm/location ownership, consent scope, export/deletion, retention, and audit behavior pass integration tests.
- No unsupported nationwide coverage or forecast behavior is represented in API or UI.

## Phase 3 — Model-gated predictions and rankings (future; feature-specific approval)

Exit only for each independently approved model/component when:

- Trusted artifact provenance, checksum, dependency/runtime contract, metadata, target/units, and registry evidence are verified.
- An independent evaluation protocol includes untouched temporal holdout, geographic/unseen-location/category behavior, relevant subgroups, baselines, uncertainty/limitations, and data leakage review.
- Model contract tests cover valid and invalid inputs, missing required values, out-of-domain years/categories, non-finite/negative outputs where relevant, reproducibility expectations, and explicit unavailability.
- API tests prove approval/coverage gates, ownership and consent, idempotency, persistence/deletion policy, and no stale-result-as-current behavior.
- UI labels output as estimate or yield-based ranking with evidence period, units, coverage, and limitations; no claim of profitability/suitability/causal impact without supporting evidence.
- Latency, capacity, monitoring, rollback, incident and model-update plans are tested to approved service objectives.

The yield model's repository-recorded conditional status is not a passed gate. Crop ranking remains derived, not a standalone trained recommender. Risk warnings remain blocked until separate adequate validation and approval.

## Phase 4 — Grounded assistant and expert workflow (future)

Exit only when:

- AI provider and data-processing terms are approved; data minimization and retention/deletion have been verified.
- Knowledge sources have provenance, legal review, immutable versions, approval/withdrawal workflow, language/geography/effective-date metadata, and reproducible index lineage.
- Assistant grounding tests evaluate claim support, citations, citation/version validity, contradictory/stale sources, unsupported questions, abstention, and hallucinated references.
- Prompt-injection/untrusted-document, sensitive-data, cross-user leakage, tool misuse, rate-limit, and provider-failure tests pass.
- Hindi and English answer quality, terminology, source-language disclosure, and fallback/abstention are human-reviewed against acceptance thresholds.
- Expert-case integration tests prove explicit consent or documented authorized basis, exact scope, assignment, expiry/revocation, resource ownership, and audited reads/reviews.
- Exploratory risk indicators are not presented as validated warnings; the assistant does not infer a future risk from them.

## Phase 5 — Public launch readiness (future)

Exit only when:

- Product, engineering, domain, security, and legal/privacy owners sign off their release gates.
- Accessibility and localization review pass; support/escalation and complaints channels are ready.
- Production threat model, penetration/security assessment, authorization regression suite, dependency/SBOM review, secret handling, incident response, monitoring, backup restore, disaster recovery and rollback are tested.
- Hosting, data residency, provider contracts, secrets management, encryption, backup objectives and operational on-call are approved.
- Model/assistant release cards and data-source notices accurately describe evidence, scope, limitations, and update times.
- Operational SLO, RTO, RPO, cost, provider quota, and capacity thresholds are specified and met by measured evidence.

## Cross-phase required test suites

| Suite | Minimum acceptance |
|---|---|
| API contract | Schema/validation, stable errors, timestamps, units, pagination boundaries, request IDs, idempotency replay and payload conflict, timeout/error semantics. |
| Model contracts | Trusted-artifact gate; input/output schema; missing/malformed/unseen values; status/coverage restrictions; no invented model identity or unsupported prediction; explicit non-finite/dependency failure behavior. |
| Authorization | Owner isolation, role boundaries, case assignment, consent scope/expiry/revocation, admin least privilege, enumeration/concealment, deletion, concurrent grant changes. |
| Assistant grounding | Claim-level source support, citation traceability/version, unsupported-question abstention, stale/conflicting evidence, injection, privacy, provider failure, Hindi/English quality. |
| Integration | Database transaction/migration, identity provider, external source adapter, object/artifact storage, assistant provider where selected, audit and deletion propagation. Use test doubles for controlled failure cases. |
| Localization/accessibility | Hindi/English completeness, language switch/persistence, fallback, units/date/number rendering, assistive technologies, keyboard/mobile/low-bandwidth usability. |
| Security/privacy | Threat model, secret/dependency/container scans, abuse/rate limits, logging redaction, session protections, egress controls, backup encryption/restore, incident exercise and legal review. |
| Deployment | Reproducible containers, immutable release provenance, secrets injection, managed database TLS, migrations/rollback, readiness/liveness, monitoring, backup recovery, capacity and rollback exercise. |

## Release blockers

No public release if any of the following remain: unresolved legal/source rights affecting shipped content; missing privacy/retention basis; broken ownership or consent enforcement; untested secret handling or backup recovery; ungrounded or uncited assistant claims; unresolved language fallback that silently changes language; unapproved model/coverage claims; exploratory risk warnings; missing essential security/incident ownership; or unreviewed provider data-processing terms.
