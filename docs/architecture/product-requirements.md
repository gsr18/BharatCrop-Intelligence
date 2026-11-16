# BharatCrop Intelligence: Product Requirements

**Status:** Proposed requirements; not implemented.  
**Product decisions:** Nationwide India target, public web application, farmer/agricultural expert/administrator roles, Hindi and English, Next.js/TypeScript, FastAPI, PostgreSQL, and a basic grounded agricultural assistant.

## Personas and journeys

| Persona | Needs and constraints | Proposed MVP journey |
|---|---|---|
| Farmer | Understand useful agricultural information in a familiar language, on a likely low-bandwidth device; retain control of farm/location data and any expert sharing. Advice must distinguish sourced facts, historical estimates, and unknowns. | Select Hindi or English; create/access account; optionally save a farm and location; inspect available weather/history and approved crop/yield information for supported coverage; ask a question grounded in curated sources; review citations; explicitly authorize an expert case if desired; manage consent and request data deletion. |
| Agricultural expert | Review cases within professional permissions and provide contextual guidance without broad access to farmer accounts. | Authenticate; see only assigned/authorized cases; inspect only data shared for the case; provide a review and sources/notes; lose access when authorization expires or is revoked. |
| Administrator | Maintain safe service operation and curated knowledge without unrestricted access to farmer content by default. | Authenticate with stronger administrative controls; manage source/document versions and publication workflow; inspect aggregate operational status; review security/audit events under a documented purpose; avoid reading personal case or conversation content unless specifically authorized and audited. |

These are proposed journeys. Authentication, user research, expert verification, and field usability have not been completed.

## MVP scope

### Included, subject to acceptance gates

- Public Next.js web application with accessible Hindi/English UI and explicit language selection.
- Account identity integration using an established provider or standards-based managed solution selected after comparison; application roles are farmer, agricultural expert, and administrator.
- Farmer-owned farm/location records with data minimization, consent controls, and deletion workflow.
- Coverage lookup that distinguishes supported, unsupported, and unknown geography/data periods. Nationwide access does not imply nationwide data or model validity.
- Weather history/context only where source, period, geographic coverage, and limitations are verified. No implied forecast where none exists.
- Yield estimation or historical candidate ranking only if the specific model/component passes a separate evidence and release gate; clearly label task, coverage, evaluation context, units, and limitations.
- Basic agricultural Q&A grounded exclusively in a curated, versioned corpus with validated citations, abstention, and optional expert referral.
- Scoped expert cases/reviews with explicit consent or documented alternative authorization, revocation/expiry, and audited access.
- Administrative knowledge-source review/publication workflow and operational health checks.

### Explicit exclusions

- Farmer-facing future-risk warnings from exploratory agricultural risk indicators.
- Deployment of the low-yield classifier while its recorded status is NOT READY or its model artifact is unverified.
- Treating crop ranking as a separately trained recommender, profitability estimate, or proof of agronomic suitability.
- Claims of nationwide predictive validity, causal weather impacts, or reliable predictions for unseen categories/locations without evidence.
- Unrestricted web-search answers, uncited assistant claims, or using unreviewed user documents as authoritative policy.
- Payments, marketplace transactions, insurance/credit decisions, procurement, satellite monitoring, or automated agronomic prescriptions unless separately scoped and validated.
- Automatic expert access to farmer accounts, farms, conversations, or predictions.
- Provider-specific authentication, AI, weather, hosting, or map contracts before those decisions are approved.

## Feature dependencies and availability

| Feature | Dependencies | Release condition |
|---|---|---|
| Account and role-aware UI | Selected identity solution; server-side account/role mapping; security/privacy review. | Authentication, account recovery, role changes, session revocation, and authorization tests pass. |
| Farm and location management | Account ownership model; verified location vocabulary/coverage source; consent and retention rules. | Ownership, input validation, delete/export behavior, and location-coverage states tested. |
| Weather context | Verified data source, legal terms, units, freshness, location crosswalk, and coverage map. | Missing/unsupported observations are explicit; no forecast claim without forecast evidence. |
| Yield estimation | Trusted artifact provenance, independent evaluation, validated input contract, defined output units and population/coverage. | Model release gate passes, including required-field and unseen-category handling. A repository artifact alone is insufficient. |
| Crop ranking | Eligible candidate definition, yield model gate, independent temporal/geographic evaluation, clear yield-only interpretation. | UI calls it a yield-based ranking, not a crop recommendation for profitability/suitability. |
| Grounded assistant | Curated corpus, source/version metadata, retrieval, citation validation, AI-provider review, privacy policy, evaluation. | Grounding/citation, unsupported-question, injection, language, and privacy gates pass. |
| Expert cases | Verified expert accounts, scoped consent/authorized basis, case assignment rules, audit and expiry/revocation. | No expert reads case-specific records without a current authorized grant. |
| Knowledge administration | Admin authorization, review workflow, artifact provenance, versioning, publication rollback. | Unreviewed sources cannot be retrieved by the public assistant. |

## Nationwide target versus actual coverage

The product target is India-wide, but each feature must report its actual verified geographic, temporal, crop, and category coverage. API responses and UI must distinguish `supported`, `unsupported`, `unknown`, and `unavailable` as appropriate. Do not infer support from a district name match, a national product goal, an artifact accepting an input, or a dataset's presence.

The repository audit records APY observations from 2013–14 to 2024–25; weather integration is exploratory, uses a starting-calendar-year proxy, and has unmatched locations. Boundary provenance/crosswalks have unresolved identifiers. The yield artifact excludes weather and has unverified unseen-category reliability. Accordingly, no nationwide agronomic or model coverage claim is currently established.

## Hindi and English requirements

- All navigation, form labels, validation, errors, consent, privacy notices, safety explanations, and accessibility text must be available in Hindi and English before public launch.
- Use locale-aware formatting for dates and numbers; keep canonical values/units machine-readable and do not localize identifiers.
- Preserve user-selected language across authenticated sessions subject to user preference; provide visible language switching.
- The assistant responds in the user's selected language when the evidence supports an adequate answer. Citations retain canonical source titles and may include reviewed localized titles; translation must not change source meaning.
- Do not silently substitute English for a Hindi answer. If quality or source language prevents a reliable localized answer, disclose the limitation in the selected UI language and provide source-language material with an appropriate explanation or abstain.
- Translation quality, agricultural terminology, script rendering, and low-bandwidth/mobile usability require human review. Machine translation alone is not an acceptance criterion.

## Functional requirements

1. The backend authenticates every protected request and authorizes role, ownership, assignment, consent, and resource state server-side.
2. Farmers can view/manage only their own farms, preferences, results, conversations, and cases unless another documented authorization applies.
3. Expert access is case-scoped, purpose-limited, auditable, expiring/revocable, and requires explicit consent or another legally documented basis.
4. Administrative knowledge changes are versioned, reviewed, attributable, and reversible; administrator role alone does not provide blanket access to personal content.
5. Every predictive/derived output identifies its task, status, scope/coverage, relevant time period, units, evidence context, and limitations.
6. Missing data, unsupported inputs, unverified categories, unavailable models, and insufficient assistant evidence are surfaced explicitly.
7. Assistant factual agricultural claims include validated citations to approved corpus versions; unsupported requests trigger abstention or referral.
8. Account data, farms, consent, results, cases, and conversations follow approved access, retention, export, and deletion rules.
9. API state-changing retries use idempotency where specified; concurrent updates and revoked grants are handled safely.
10. Operations expose health/readiness without disclosing secrets or personal data; security-sensitive events are audited.

## Non-functional requirements

- **Security/privacy:** TLS in transit, least privilege, backend authorization, protected secrets, minimized personal data, privacy-aware logging, abuse controls, backup protection, incident response. Detailed acceptance criteria live in `security-and-privacy.md`.
- **Reliability:** Define service objectives and recovery targets before launch; dependency failures must fail explicitly and safely. Numerical SLO/RTO/RPO targets remain undecided.
- **Performance:** Establish realistic mobile/low-bandwidth budgets and measure API, model, retrieval, and provider latency before choosing thresholds. No measured baseline is available.
- **Accessibility:** Target an agreed accessibility standard, including keyboard and screen-reader testing in both languages; the specific conformance target requires product confirmation.
- **Maintainability:** Modular monolith, versioned contracts, reproducible dependencies, schema migrations, automated tests, and documented operational ownership.
- **Observability:** Correlation IDs, sanitized structured logs, metrics and traces with bounded-cardinality labels; no secrets or unnecessary personal content.
- **Data governance:** Record source provenance, license/terms status, freshness, coverage, transformations, and version for material data and knowledge assets.
- **Localization:** No user-visible English-only error or consent flow in the public MVP.
- **Portability:** Containerized application services and managed PostgreSQL are locked goals; providers and deployment topology are undecided.

## Assumptions and open decisions

Feature-specific coverage and model acceptance are unknown until separately verified. Expert qualification/verification, supported Indian languages beyond Hindi/English, accessibility target, numerical service objectives, precise retention periods, source refresh schedules, and public-launch support arrangements require review/decision. Do not interpret this proposed scope as product validation or existing functionality.
