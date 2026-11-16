# BharatCrop Intelligence: Architecture Decision Record

**Status:** Living decision log. Locked decisions are recorded as approved product constraints; all implementation status remains proposed unless separately implemented and tested. This file is documentation, not a deployment decision.

## Decision status summary

| Decision | Status | Decision / rationale | Consequences and follow-up |
|---|---|---|---|
| Product and geographic target | Locked | BharatCrop Intelligence is a public agricultural decision-support web application targeting India from the beginning. Feature coverage is limited to verified evidence. | “Nationwide” does not establish uniform data/model coverage; each feature must report supported/unknown/unavailable geography. |
| User roles | Locked | Farmer, agricultural expert, administrator. | Backend enforces role plus ownership, assignment, purpose, and consent/authorized-basis scope. Detailed capability mapping requires review. |
| Initial languages | Locked | Hindi and English. | Both languages required for user-visible MVP flows and errors; assistant must disclose limitations rather than silently switch languages. Human review required. |
| Frontend | Locked | Next.js with TypeScript. | Approved target, not present in the audited repository. Framework version, hosting, browser/session approach remain implementation choices. |
| Backend | Locked | Python FastAPI. | Start as a modular monolith; do not introduce microservices without measured justification. Backend is authoritative for authorization. No FastAPI code exists in the audited baseline. |
| Database | Locked | PostgreSQL. | Proposed transactional source for application accounts, farms, consent, cases, results, assistant metadata, and audit events. No schema/migrations currently exist. |
| Assistant | Locked scope | Basic grounded agricultural Q&A in MVP, using curated/versioned sources and no unrestricted web answers. | Requires source review, citations, abstention, prompt-injection controls, privacy review, and evaluation before release. No working assistant exists. |
| Expert access | Locked principle | Farmer-specific expert access requires explicit consent or another documented authorized basis. | Enforce exact scope, assignment, expiry/revocation and audited reads in backend. Legal basis and workflow details require review. |
| Privacy | Locked principle | Minimum necessary data, explicit consent where applicable, retention/deletion rules, and audited access. | Periods, exceptions, data residency and applicable legal obligations are unresolved and require qualified review. |
| Deployment direction | Locked goal | Containerized services, managed PostgreSQL, secrets management, and backups. | Hosting provider, backup/recovery objectives, networking, regions, and numerical operational targets remain undecided. |
| Risk-warning exclusion | Locked | Exploratory agricultural risk indicators must not become farmer-facing future-risk warnings until adequately validated. | No risk-warning route or assistant claim from these outputs; separate evidence/release gate required. |
| Preserve research baseline | Locked | Existing notebooks, datasets, model artifacts, metadata, and research outputs must be preserved. | Treat them as evidence/research inputs, not production-approved assets; no overwrite/move/delete as part of this specification. |

## Proposed architecture decision: modular monolith

**Decision:** Organize the initial FastAPI application as a modular monolith with explicit account/authorization, farm/location, prediction/weather, assistant, expert-case, knowledge-administration, and audit modules.

**Rationale:** The audit found a notebook/data/model workspace but no existing application stack, runtime contract, test suite, or deployable service. One backend deployment minimizes operational overhead while maintaining domain boundaries and directly supporting Python-based inference integration where later approved.

**Consequences:** Modules share one deployment and may share infrastructure, so enforce ownership of data access, transaction boundaries, internal interfaces, and tests. Do not permit arbitrary cross-module table access. A future split requires measured scaling, isolation, reliability, or organizational justification.

## Unresolved decisions

| Decision | Options/criteria to evaluate | Required owner/evidence | Blocks |
|---|---|---|---|
| Authentication provider/standard | Compare established managed providers and standards-based solutions for secure flows, MFA/recovery, Hindi/English accessibility, identity lifecycle, data location/subprocessors, deletion/export, audit, availability, cost, portability and contractual terms. No provider selected. | Product, security and privacy/legal review; threat model and data-processing terms. | Account implementation and public launch. |
| AI provider/model | Compare data retention/training controls, region/subprocessors, deletion, privacy/security terms, Hindi/English quality, grounding/citation behavior, safety controls, latency, cost, rate limits, model changes, auditability and exit. No provider selected. | Product/domain, security and legal/privacy review plus evaluated benchmark. | Assistant implementation/release. |
| Weather/data provider | Verify provenance, official status, schema, units, spatial/seasonal resolution, coverage/freshness, terms/license, stability, attribution, and fit for specific features. Repository contains NASA POWER-derived assets and an IMD discovery record; neither establishes a production provider decision. | Data/domain and legal review; reproducible coverage/quality evidence. | Public weather feature and weather-dependent claims. |
| Hosting provider/region | Compare managed application/container hosting and PostgreSQL, data location, controls, backup/restore, availability, incident support, network/egress, cost, and exit path. No provider/region selected. | Engineering/operations, security, privacy/legal. | Production deployment. |
| Legal/privacy interpretation | Determine applicable Indian privacy law/rules at launch, source redistribution rights, lawful basis, notices/rights, retention, cross-border processing, expert access, breach obligations and sector-specific rules. | Qualified India-specific counsel and privacy owner. | Collection of personal data and public launch. |
| Location identifiers/boundaries | Select authoritative versioned location reference and policy for historical boundary changes. Existing audit records provisional provenance, unresolved identifiers and crosswalk issues. | Data/domain owner plus source/legal evidence. | Reliable location-bound features. |
| Model release policy | Set independent evaluation protocol, acceptance thresholds, responsible approvers, subgroup/geographic scope, units, and monitoring/rollback process for each component. | ML/domain/product owners; reproducible evaluation evidence. | Yield/ranking serving; risk outputs remain blocked. |
| Retention and deletion periods | Define by data class including account, farms, consents, results, cases, conversations, audit, providers, backups and legal holds. No durations chosen. | Privacy/legal and product owners. | Personal-data collection and public launch. |
| Operational objectives | Choose SLO, latency/capacity thresholds, RTO/RPO, support hours, alert thresholds, and incident ownership from launch needs. | Product and operations; measured load/recovery tests. | Production readiness. |
| Expert verification/authority | Determine qualification checks, allowed scope, assignment, conflict handling and role lifecycle. | Domain, product and legal owners. | Expert access/case workflow. |

## Evidence and discrepancy notes

- The prior repository audit states that no architecture documentation directory existed at audit time. This current task creates the architecture and decisions documents; it does not contradict the historical snapshot.
- The audit is a static baseline: the yield `.joblib` path exists, but was not loaded; notebook outputs/metrics were not rerun. Readiness labels and metrics in the model matrix are recorded evidence, not independent validation or production approvals.
- The audit reports a source-registry inconsistency for mandi prices: the source metadata says local verification is pending while a separate acquisition audit says the single-day file was downloaded and structurally inspected. This does not resolve licensing or historical coverage.
- Existing IntelliJ files describe a Java module/JDK setup, while the approved application stack is Next.js, FastAPI, and PostgreSQL. This is IDE metadata, not evidence of Java application code; project tooling conventions remain to be established.
- The audit's `docs/` absence was true when inspected; the audit file itself and this specification are subsequent documentation changes.

## Review and change control

Record future decisions with status, date, owner, alternatives, evidence, consequences, and superseded decision link. A documentation approval must not be interpreted as model validation, provider contract approval, legal advice, or implementation completion. Revisit this log when a previously unresolved choice is made.
