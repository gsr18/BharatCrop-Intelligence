# BharatCrop Intelligence: P0 Resolution Plan

**Status:** Proposed technical disposition for backlog review. This document does not modify the existing specifications, prove the data/model evidence, or authorize implementation. P0 findings remain open until the exit criteria below are evidenced and reviewed.

## 1. P0 findings and disposition

Descriptions, evidence paths, impacts, and recommended resolutions below are reproduced from the actual finding rows in `docs/architecture/consistency-review.md`.

| ID / severity | Original description | Evidence paths | Original impact | Original recommended resolution | Disposition in this plan |
|---|---|---|---|---|---|
| **F-01 / P0** | The yield API cannot yet have a validated request/response contract. The proposed endpoint leaves the source of model inputs ambiguous (`farm_id` or explicit fields), leaves several fields conditional, and correctly states that the target unit is unknown. Repository feature engineering explicitly records `yield_area_production_units_verified: False`. The model's `Season` feature includes `Total` as well as Kharif/Rabi/Summer; other analysis excludes `Total` to avoid double counting, and no serving policy for `Total` is specified. | `docs/architecture/api-contracts.md`; `models/yield_prediction/individual_crop_hgb_location_metadata.json`; `notebooks/15_feature_engineering.ipynb`; `notebooks/07_apy_eda_analysis.ipynb`; `models/model_explainability_and_scenarios/feature_category_audit.json` | Clients could submit semantically invalid inputs or display a yield estimate with a false unit/season interpretation. A farm record does not currently define a complete, verified model input. | Keep `/predictions/yield` disabled. Have data/domain owners verify target unit and season semantics, exact feature/eligibility contract, supported period/category scope, and farm-to-model mapping; then specify schemas and invalid/out-of-scope responses before implementation. | **Partially resolved with a restriction; model endpoint remains blocked.** This plan fixes the safe backlog boundary: no yield inference or crop ranking until unit, target/season meaning, candidate population, feature mapping, and evaluation scope have evidence-backed decisions. |
| **F-02 / P0** | The consent and expert-case creation flow is circular. `POST /consents` may reference `case_id`, but `POST /expert/cases` requires a `consent_id` or authorized-basis reference before creating the case. A case-bound consent cannot be created before the case ID exists, while the case cannot be created before its consent exists. | `docs/architecture/api-contracts.md` (`POST /consents`, `POST /expert/cases`); `docs/architecture/data-model.md` (`consent_records`, `expert_cases`); `docs/architecture/security-and-privacy.md` | The expert flow cannot be safely implemented without inventing a sequencing exception or creating a window where farmer data is available before authorization. | Specify an explicit lifecycle that permits a non-sensitive draft/request record, obtains a scoped grant, and activates/share-populates the case only after authorization; alternatively define another reviewed sequence. State transactional and revocation behavior. | **Partially resolved by a proposed lifecycle; implementation remains blocked pending human approval.** Use a farmer-owned, non-sensitive share request, a grant scoped to that request and a named intended expert, and activate/populate the expert case only after a valid grant. MVP uses explicit consent only; alternative legal bases are deferred pending legal/product approval. |
| **F-03 / P0** | The persistence model does not fully support the proposed API lifecycle. The API promises asynchronous export/deletion request IDs/status and idempotency keys, but the entity list has no export/deletion-request or idempotency record. It also exposes case assignment/status changes and supports alternative authorized bases, while assignment history and a durable authorization-basis record are deferred or only loosely referenced. | `docs/architecture/api-contracts.md` (`Idempotency-Key`, export/deletion, case endpoints); `docs/architecture/data-model.md` (`consent_records`, `expert_cases`, optional `case_assignments`) | Retries may duplicate side effects; export/deletion cannot provide durable status; case access and alternative authority may not be reconstructable or auditable. | Before implementing these endpoints, define durable idempotency scope/expiry/result behavior, export/deletion state, assignment history, and evidence for alternative authorized bases. If a capability is not MVP, remove/defer its endpoint rather than promise unsupported persistence. | **Partially resolved by an explicit backlog restriction and proposed persistence contract.** Do not implement asynchronous export/deletion endpoints until retention, exception, and processing rules are approved. Any retained mutating API requires durable idempotency state. Case assignment changes require immutable history. Alternative-basis access is not in the MVP until legally reviewed and specifically approved. |
| **F-04 / P0** | Location-dependent contracts rely on a verified `location_id`/coverage vocabulary that is not present as an approved source. The current crosswalk is explicitly provisional; source identity and boundary vintage are unverified, and unresolved identifiers remain. The API correctly rejects unsupported locations, but its proposed farm/weather/model requests still require a stable reference. | `docs/architecture/api-contracts.md`; `docs/architecture/data-model.md` (`locations` deferred); `metadata/district_boundary_provenance.json`; `reports/data_audit/district_boundary_audit.json`; `metadata/apy_district_coordinate_crosswalk.csv` | An implementation could accidentally promote name matching or provisional coordinates to canonical national coverage; district-level results could be assigned to the wrong geography or vintage. | Keep location-dependent features behind a versioned coverage source. Define the identifier authority/vintage and map/unknown behavior before enabling these routes. Until then, accept only explicitly validated identifiers or do not implement location-dependent operations. | **Blocked by missing evidence and a human data-source decision.** The backlog may define an adapter boundary and tests for unsupported/unknown locations, but must not publish, persist as canonical, or use the current provisional crosswalk as an approved location authority. |
| **F-05 / P0** | Prediction/ranking execution semantics and result provenance are underspecified. The API does not settle synchronous versus asynchronous execution, the meaning of returned `status`, how inputs are resolved from a farm, or which immutable artifact/evidence revision was used. The data model has a registry FK and checksum concept but does not define a prediction's immutable registry revision/artifact checksum reference. | `docs/architecture/api-contracts.md` (`POST /predictions/yield`, `POST /rankings/crops`); `docs/architecture/data-model.md` (`model_registry`, `prediction_runs`); `models/registry/model_registry.csv` | Results may not be reproducible or auditable; client retry/polling behavior and stale-result handling cannot be implemented consistently. | Define execution mode and lifecycle, stable status transitions, timeout/retry behavior, and persist the exact approved registry/evidence revision and artifact checksum with each run. Do not invent a model version; derive it from verified provenance. | **Partially resolved with a proposed backlog restriction; P0 remains open pending approval and evidence.** The proposed minimum contract selects synchronous request/response for any initially approved inference path, with no queued/polling state. A saved result is opt-in. Each saved result must bind immutably to an approved registry revision and verified artifact checksum; no model version is invented. |

### Overall resolution status

No P0 finding is declared fully closed by this document. F-05's ambiguity has a proposed resolution for backlog planning, while its implementation acceptance criteria remain pending. F-01 and F-04 cannot be resolved from current evidence. F-02 and F-03 have safe proposed restrictions/lifecycles but require review before implementation. **Backlog planning is conditionally approved; implementation of the affected flows is not thereby approved.**

## 2. Minimum safe contract for affected components

The following are proposed boundaries for backlog/design work. They deliberately do not define unknown scientific, geographic, legal, or source facts.

### A. Yield inference and derived crop ranking

| Contract aspect | Proposed minimum safe rule |
|---|---|
| Availability | Disabled by default. A request returns a stable `feature_not_approved` or `model_unavailable` error until a specific immutable model release and population are approved. |
| Required inputs | The serving schema is **not yet final**. Evidence currently lists `Crop`, `Season`, `Crop_Category`, `State`, `District`, and `FE_YearStart`; use only after data/domain owners confirm the actual inference contract. Do not assume a `farm_id` supplies every field. Do not accept client values as verified location/crop identifiers merely because a model accepts them. |
| Output | If enabled later, return the target label `Yield`, value, unit, period/year semantics, geography scope, coverage, limitations, and opaque approved-release reference. Unit is **UNKNOWN** and no yield value is contractually available until verified. A ranking returns only ordered eligible candidates and explicitly labels the basis as predicted-yield ranking, not profitability or agronomic suitability. |
| Validation/rejection | Reject absent/malformed required values, unrecognized or unverified geography, unsupported/unseen categories unless release evidence explicitly allows them, unsupported year/season, missing artifact, unapproved registry state, or non-finite/out-of-contract output. `Season = Total` is rejected unless a future reviewed contract explicitly defines its use. Do not silently coerce or impute. |
| Ownership/authorization | Farmer may request only for a farm they own. Direct inputs, if ever retained, are treated as the caller's data and cannot be used to bypass location/coverage/model validation. An expert may request only for a case with active, scoped authorization that covers the necessary farm/result inputs. Backend checks apply on every request and result read. |
| Execution/lifecycle | Synchronous request/response is the initial proposed mode after approval. No `202 Accepted`, job polling, or background queue is promised. A timeout is an explicit failure, not a prediction-shaped fallback. Retries with the same idempotency key/payload return the same completed response/result; a conflicting payload returns `idempotency_conflict`. |
| Persistence | Do not save input/result unless the caller explicitly requests a saved result and the retention policy permits it. If saved, bind it to the exact approved immutable registry revision, artifact checksum, input-schema revision, evidence reference, response status, units, and timestamp. Never infer a model version from a path or filename. |
| Errors | `feature_not_approved`, `model_unavailable`, `coverage_unavailable`, `evidence_insufficient`, `validation_error`, `permission_denied`, `dependency_unavailable`, `dependency_timeout`, or `internal_error` with the common sanitized envelope and request ID. |
| Acceptance tests | Disabled feature cannot invoke model; missing/invalid values reject before inference; no unsupported season/unit is returned; ownership and case-grant checks reject cross-user access; registry status/checksum mismatch blocks; output schema includes scope/evidence/unit; idempotent retry returns same result; timeout/error cannot appear as success; no saved result without explicit save and approved retention. |
| Remaining uncertainty | Yield unit, source measurement comparability, `Total` season semantics, eligible candidate definition, supported location/category/year scope, farm-to-feature mapping, model runtime/provenance, independent validity, and production approval. |

**Ranking is downstream of yield inference.** It remains a derived component, not a separate trained model. Even after an inference gate, it must not be called an agronomic recommendation or profitability comparison without separate evidence and approved scope.

### B. Location, farm, weather, and coverage

| Contract aspect | Proposed minimum safe rule |
|---|---|
| Required input | A location reference must include an identifier and the exact source/version/vintage that defines it. The canonical source and vocabulary are **not selected**. |
| Validation/rejection | Until a source is approved, location is `unknown` or unsupported for feature use. Reject synthetic placeholders, unresolved crosswalk entries, ambiguous names, and mismatched boundary versions. No silent name matching, coordinate snapping, fallback to state centroid, or inference of nationwide coverage. |
| Output | Coverage result distinguishes `supported`, `unsupported`, `unknown`, and `unavailable`, with evidence/source version, geographic/time scope, and checked-at timestamp only when backed by a real reviewed coverage record. |
| Ownership/authorization | Farm CRUD is owner-only. Experts receive farm/location detail only through an active scoped case authorization. Public coverage lookup must not disclose a farmer's stored farm. |
| Persistence/lifecycle | Do not persist a provisional crosswalk value as canonical farm location. A future location catalog must be versioned and preserve boundary-vintage lineage; update/reconciliation must not silently rewrite historical locations. |
| Weather-specific boundary | No weather API may imply current conditions or crop-season alignment from annual starting-year proxy data. Weather remains disabled until source rights, units, temporal semantics, freshness, coverage, and geographic mapping are verified. |
| Errors and tests | Unknown/unsupported location is explicit; invalid/stale source version rejects; missing coverage never maps to zero risk. Tests cover ambiguous names, synthetic coordinates, unresolved mapping, version mismatch, and owner/expert authorization. |
| Remaining uncertainty | Authoritative geography source, boundaries and vintage, canonical identifiers, district equivalence, support coverage, user-supplied location precision, weather provider, and season mapping. |

### C. Expert share request, consent, case, and review

Proposed sequence to remove the circular dependency without exposing farmer-specific content before authorization:

1. Authenticated farmer creates an opaque `case_share_request` in `pending_grant` state. It contains no farm, location, prediction, assistant conversation, or free-text case summary visible to an expert. The farmer is the owner.
2. The farmer identifies the intended verified expert (how experts are selected/verified remains a product decision); if there is no specific grantee, the share request cannot proceed to data sharing.
3. The farmer grants explicit consent against the request ID, naming that grantee, purpose, exact resource/action scope, notice version, and optional expiry. This avoids consent needing a not-yet-created `case_id`.
4. In one backend transaction, validate the grant and request state, create/activate the expert case, record the case assignment, and bind case access to that consent. Only after commit may the expert read the scoped case data.
5. Farmer may revoke the grant. Revocation/expiry immediately blocks new reads and writes by the expert; it also prevents new data from being attached. Existing review retention/deletion follows a separately approved policy and is disclosed to the farmer.
6. Case closure removes active access. Assignment changes are recorded as immutable events, and a new assignee receives access only if the existing authorization explicitly covers that grantee or a new grant is obtained.

| Contract aspect | Proposed minimum safe rule |
|---|---|
| Required inputs | Share request: only intended expert reference and purpose/scope selection; no case content. Consent: request ID, named grantee, permitted purpose/resource/action scope, notice version/acknowledgment, and expiry if chosen. Activation: request ID plus valid consent reference. Exact scope vocabulary and consent text require review. |
| Validation/rejection | Reject unknown/disabled expert, mismatched grantor/grantee/request, expired/revoked/narrow grant, changed scope, invalid transition, or absent authorization. No farmer-specific content is accepted on draft creation. MVP permits explicit consent only; alternative legal bases are blocked pending legal and product approval. |
| Ownership/authorization | Request and case remain farmer-owned. Expert access requires assigned expert identity plus current exact-scope grant. Admin role alone does not permit content access. Case/review reads are audited. |
| Persistence/lifecycle | Persist request state, consent record, activation/case reference, immutable assignment/access events, grant and revocation timestamps, case status, and actor/audit events. Do not hard-delete authorization evidence contrary to reviewed retention rules. |
| Errors | `consent_required`, `consent_expired`, `permission_denied`, `resource_not_found`, `invalid_state_transition`, or `conflict`; never create an active case on partial failure. |
| Acceptance tests | Expert cannot enumerate or read pending request; no farmer content is stored/shared before grant; only intended grantee sees active case; mismatched/revoked/expired grant blocks access; revocation racing with reads is checked transactionally; assignment changes are auditable; admin content access is denied absent separate authorization. |
| Remaining uncertainty | Expert selection/verification, exact consent language/scope, legal retention of cases/reviews after revocation, alternate authorized basis, and applicable notice/withdrawal semantics. |

### D. Durable persistence, idempotency, export, and deletion

| Contract aspect | Proposed minimum safe rule |
|---|---|
| Idempotency inputs | Require an idempotency key for retriable state-changing operations. Scope uniqueness by authenticated principal, operation/method, route/resource, and key; store a canonical request fingerprint, operation state, safe response/result reference, created/expiry timestamps. |
| Idempotency behavior | Same key and same request returns the original outcome; same key with a different fingerprint returns `409 idempotency_conflict`; concurrent duplicate requests must result in one logical side effect. Exact key-retention duration is **UNKNOWN** and must be approved against the client retry horizon before launch. |
| Export/deletion inputs | Keep export/deletion request APIs out of implementation until data categories, identity verification, legal holds, retention, provider propagation, delivery security, and completion semantics are approved. If retained in MVP, create durable request records before exposing the route. |
| Export/deletion outputs | Asynchronous job IDs/status require persisted request entities, status transitions, actor/owner, requested scope, timestamps, failure state, completion evidence, and secure delivery/expiry metadata. Do not return an ID for unpersisted work. |
| Case authorization persistence | Store explicit consent records, request-to-consent-to-case relations, and immutable assignment/access history. MVP denies non-consent alternative basis until approved schema and legal decision exist. |
| Ownership/access | Export only the authenticated subject's allowed data. Deletion requests are owner-only. Expert case data is included only to the extent the subject is entitled to export/delete and policy permits; an expert cannot trigger farmer deletion. |
| Acceptance tests | Duplicate calls cannot duplicate side effects; conflicting idempotency payload rejects; concurrent requests serialize; request status survives service restart; deletion/export respects ownership and authorization; failures are visible and retryable according to state; all transitions audited without logging personal payloads. |
| Remaining uncertainty | Retention duration, deletion exceptions, backup expiry, legal holds, export format/delivery, processing deadlines, idempotency retention, and provider deletion contracts. |

## 3. Mandi-price evidence and decision

### Exact conflict

| Repository-relative file | Fields and recorded claim |
|---|---|
| `metadata/mandi_price_source_registry.json` | `status`: `"Source registered; local file verification pending"`; `raw_directory`: absolute local path ending in `data\raw\mandi_prices`; source URLs and acquisition date are recorded. |
| `metadata/mandi_price_acquisition_audit.json` | `raw_file`: `data\raw\mandi_prices\mandi_prices_2026-10-31.csv`; `sha256`, file size, row/column counts and column names are recorded; `phase_2_status`: `"Downloaded and structurally inspected; historical coverage limitation identified"`; `unique_arrival_dates`: `1`; earliest/latest arrival date both `2026-10-31`; historical coverage assessment says single-day snapshot insufficient for historical trends/time-series forecasting. |
| `metadata/source_registry.csv` | `SRC002` leaves `schema_verified`, `download_verified`, `coverage_verified`, `license_verified`, and `integration_verified` false and marks source `DISCOVERED`; historical depth and missingness not audited. |
| `data/raw/mandi_prices/mandi_prices_2026-10-31.csv` | File path is present in the repository inventory. This review did not independently recompute its hash, parse rows, or confirm source provenance. |

### Verified versus unknown

- **Verified in this static review:** the metadata files exist and make the claims above; the referenced raw CSV path is present. The written audit and source registry disagree in status wording.
- **Recorded but not independently reproduced:** the acquisition audit's hash, file size, row count, schema, unique-date count, and structural-inspection result.
- **Unknown:** whether the pending status means local file presence, file integrity, verified upstream origin, rights/terms, schema, coverage, or successful integration; whether the hash matches the current file; source rights and allowed redistribution; historical coverage beyond the recorded single date; data refresh reliability.
- The two statuses may describe different verification scopes, but the files do not explicitly say so. That is a possible reconciliation, **not an established resolution**.

### Evidence needed to resolve

1. Record a defined verification checklist/status vocabulary that separates file existence/integrity from source provenance, schema, coverage, license/terms, and integration.
2. Verify the raw file checksum against the audit record and preserve the original; document the upstream acquisition record/source identifier and retrieval method without exposing credentials.
3. Review current source terms/license, attribution, redistribution and derived-use permissions with the responsible owner/legal reviewer.
4. Establish whether the product needs prices; if so, verify dates, historical depth, update cadence, missingness, units, market/commodity identifiers, and API/source coverage against intended use.
5. Update the metadata only in a separately authorized task after evidence review; this task leaves it unchanged.

**MVP decision:** Yes. Mandi-price endpoints, price history/trends, and price-based crop/profitability claims remain excluded from the MVP unless the evidence and rights gates above pass and product explicitly adds the feature. This follows the current product requirements, which do not include mandi prices as an MVP feature; it is not a claim that the source is invalid.

## 4. Human decisions and remaining blockers

- Data/domain owner: verify yield unit and source measurement meaning; decide use/exclusion of `Season = Total`; define eligible crop candidate and farm-to-feature mapping.
- Data steward: choose an authoritative, versioned geography source and approve boundary vintage/crosswalk policy.
- Product and privacy/legal owners: approve the proposed two-stage expert-share lifecycle, named-grantee consent scope, consent notice, retention/deletion behavior, and whether non-consent authorized bases are in MVP.
- Product/privacy/operations: decide which export/deletion endpoints are MVP, retention schedules, legal holds, secure delivery, backup expiry, and idempotency key retention.
- Product/data/domain: set required weather and mandi features, if any; resolve source rights, scope, freshness, units, and API needs.
- Model owner: produce independent validation and immutable artifact/release provenance before inference is enabled.

## 5. P0 closure criteria

| Finding | Required evidence to mark resolved |
|---|---|
| F-01 | Verified target unit and season semantics; approved feature/input and candidate eligibility schema; documented farm-to-feature mapping; supported population/coverage; reviewed API validation/error contract; independent model approval evidence. Until then the inference/ranking route remains disabled and F-01 is open. |
| F-02 | Product/privacy review accepts a non-sensitive request → explicit scoped grant → atomic case activation lifecycle; expert selection and scope are defined; retention/withdrawal rules are recorded; state-transition and authorization tests are specified. Until review, only backlog planning may use the proposed flow; case implementation remains blocked. |
| F-03 | Final endpoint scope is approved; every retained async export/deletion workflow has durable request/status persistence and reviewed retention/exception semantics; every retriable mutation has a persisted idempotency contract and approved retention; assignment history and any allowed authorization basis are auditable. Deferred endpoints are removed from the implementation scope until then. |
| F-04 | Authoritative location reference, source rights, version/vintage, stable IDs, unresolved/synthetic-entry policy, coverage states, and historical mapping have owner-approved evidence; location contract and rejection tests are accepted. Until then location-dependent farm/weather/model features remain blocked. |
| F-05 | Execution mode/status/error behavior and retry semantics are approved; each saved result immutably references an approved registry/evidence revision, artifact checksum, input schema and scope; persistence opt-in/retention is defined; integration and replay/provenance tests pass. Inference still also requires F-01 closure. |

**No finding is marked fully resolved in this plan.** These criteria state what must be true before closure; they are not claims that the criteria have already been met.
