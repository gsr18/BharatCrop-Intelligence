# BharatCrop Intelligence: Architecture Consistency Review

**Review date:** 2026-11-02  
**Verdict:** **NEEDS LIMITED CORRECTIONS**  
**Scope:** Documentation and static repository evidence only. No notebook execution, model loading, dependency installation, data download, or source/configuration changes were performed.

## 1. Executive verdict

The proposed direction is internally sound at the high level: Next.js/TypeScript, a modular FastAPI monolith, PostgreSQL, backend-enforced authorization, scoped expert access, curated/versioned assistant knowledge, Hindi/English support, evidence-bounded geographic coverage, and a prohibition on presenting exploratory risk indicators as validated warnings.

The documents are suitable for **backlog drafting**, but not yet for implementation of location-dependent, prediction, expert-case, or data-rights-sensitive endpoints. Five P0 contract/model/data-model gaps must be resolved before the affected components can be safely implemented. Five P1 issues need resolution before their features are released. Two P2 decisions may remain deferred if assigned owners and release gates are retained. The architecture itself does not require a stack change or microservices.

This verdict is not a finding that the whole project is blocked: authentication, account/profile foundations, and other provider-independent work may be planned, but Phase 1 approval should require review of the P0 corrections in the affected contracts and lifecycle designs below.

## 2. Review scope and files inspected

### Actual documentation filenames

The current tree contains:

- `docs/architecture/repository-audit.md`
- `docs/architecture/system-architecture.md`
- `docs/architecture/product-requirements.md`
- `docs/architecture/api-contracts.md`
- `docs/architecture/data-model.md`
- `docs/architecture/security-and-privacy.md`
- `docs/architecture/assistant-design.md`
- `docs/architecture/model-coverage-matrix.md`
- `docs/architecture/phase-acceptance-criteria.md`
- `docs/decisions/architecture-decisions.md`

No `docs/architecture/consistency-review.md` existed before this review. These filenames were verified before proceeding.

### Additional evidence inspected

- `models/yield_prediction/individual_crop_hgb_location_metadata.json`
- `models/yield_prediction/yield_model_deployment_readiness_report.json`
- `models/crop_recommendation/crop_recommendation_metadata.json`
- `models/crop_recommendation/crop_recommendation_evaluation.json`
- `models/weather_intelligence/weather_intelligence_metadata.json`
- `models/weather_intelligence/low_yield_model_evaluation.json`
- `models/agricultural_risk_intelligence/agricultural_risk_metadata.json`
- `models/registry/model_registry.csv`
- `models/registry/model_validation_status.csv`
- `models/registry/model_validation_status_summary.json`
- `models/registry/model_policy_rules.json`
- `models/model_artifact_inventory.csv`
- `models/model_explainability_and_scenarios/feature_category_audit.json`
- `metadata/source_registry.csv`
- `metadata/weather_source_registry.csv`
- `metadata/mandi_price_source_registry.json`
- `metadata/mandi_price_acquisition_audit.json`
- `metadata/district_boundary_provenance.json`
- `metadata/data_requirements.csv`
- `reports/data_audit/historical_apy_manifest.json`
- `reports/data_audit/district_boundary_audit.json`
- `reports/data_audit/nasa_power_identical_series_findings.csv`
- `data/processed/weather_regional/crop_weather_integration_validation_summary.csv`
- Static source/markdown inspection of relevant notebooks: `notebooks/02_apy_dataset_acquisition_and_audit.ipynb`, `notebooks/14_crop_weather_integration.ipynb`, `notebooks/15_feature_engineering.ipynb`, `notebooks/16_yield_model_development_and_selection.ipynb`, `notebooks/17_yield_model_deployment_readiness.ipynb`, and `notebooks/18_crop_recommendation.ipynb`.

The docs tree now exists because the audit and specification were created after the audit's initial inspection. The audit's statement that `docs/` was absent is a time-scoped historical observation, not a current repository claim or contradiction. Its assertion that application infrastructure was not found remains consistent with the present inspection.

## 3. Findings

Severity meanings follow the review request: **P0** must be resolved before the affected component can be safely implemented; **P1** before the affected feature can be released; **P2** can be deferred with documented risk.

| ID | Severity | Issue | Evidence paths | Impact | Recommended resolution |
|---|---|---|---|---|---|
| F-01 | P0 | The yield API cannot yet have a validated request/response contract. The proposed endpoint leaves the source of model inputs ambiguous (`farm_id` or explicit fields), leaves several fields conditional, and correctly states that the target unit is unknown. Repository feature engineering explicitly records `yield_area_production_units_verified: False`. The model's `Season` feature includes `Total` as well as Kharif/Rabi/Summer; other analysis excludes `Total` to avoid double counting, and no serving policy for `Total` is specified. | `docs/architecture/api-contracts.md`; `models/yield_prediction/individual_crop_hgb_location_metadata.json`; `notebooks/15_feature_engineering.ipynb`; `notebooks/07_apy_eda_analysis.ipynb`; `models/model_explainability_and_scenarios/feature_category_audit.json` | Clients could submit semantically invalid inputs or display a yield estimate with a false unit/season interpretation. A farm record does not currently define a complete, verified model input. | Keep `/predictions/yield` disabled. Have data/domain owners verify target unit and season semantics, exact feature/eligibility contract, supported year/category scope, and farm-to-model mapping; then specify schemas and invalid/out-of-scope responses before implementation. |
| F-02 | P0 | The consent and expert-case creation flow is circular. `POST /consents` may reference `case_id`, but `POST /expert/cases` requires a `consent_id` or authorized-basis reference before creating the case. A case-bound consent cannot be created before the case ID exists, while the case cannot be created before its consent exists. | `docs/architecture/api-contracts.md` (`POST /consents`, `POST /expert/cases`); `docs/architecture/data-model.md` (`consent_records`, `expert_cases`); `docs/architecture/security-and-privacy.md` | The expert flow cannot be safely implemented without inventing a sequencing exception or creating a window where farmer data is available before authorization. | Specify an explicit lifecycle that permits a non-sensitive draft/request record, obtains a scoped grant, and activates/share-populates the case only after authorization; alternatively define another reviewed sequence. State transactional and revocation behavior. |
| F-03 | P0 | The persistence model does not fully support the proposed API lifecycle. The API promises asynchronous export/deletion request IDs/status and idempotency keys, but the entity list has no export/deletion-request or idempotency record. It also exposes case assignment/status changes and supports alternative authorized bases, while assignment history and a durable authorization-basis record are deferred or only loosely referenced. | `docs/architecture/api-contracts.md` (`Idempotency-Key`, export/deletion, case endpoints); `docs/architecture/data-model.md` (`consent_records`, `expert_cases`, optional `case_assignments`) | Retries may duplicate side effects; export/deletion cannot provide durable status; case access and alternative authority may not be reconstructable or auditable. | Before implementing these endpoints, define durable idempotency scope/expiry/result behavior, export/deletion state, assignment history, and authorized-basis provenance. If a capability is not MVP, remove/defer its endpoint rather than promise unsupported persistence. |
| F-04 | P0 | Location-dependent contracts rely on a verified `location_id`/coverage vocabulary that is not present as an approved source. The current crosswalk is explicitly provisional; source identity and boundary vintage are unverified, and unresolved identifiers remain. The API correctly rejects unsupported locations, but its proposed farm/weather/model requests still require a stable reference. | `docs/architecture/api-contracts.md`; `docs/architecture/data-model.md` (`locations` deferred); `metadata/district_boundary_provenance.json`; `reports/data_audit/district_boundary_audit.json`; `metadata/apy_district_coordinate_crosswalk.csv` | An implementation could accidentally promote name matching or provisional coordinates to canonical national coverage; district-level results could be assigned to the wrong geography or vintage. | Keep location-dependent features behind a versioned coverage source. Define the identifier authority/vintage and map/unknown behavior before enabling these routes. Until then, accept only explicitly validated identifiers or do not implement location-dependent operations. |
| F-05 | P0 | Prediction/ranking execution semantics and result provenance are underspecified. The API does not settle synchronous versus asynchronous execution, the meaning of returned `status`, how inputs are resolved from a farm, or which immutable artifact/evidence revision was used. The data model has a registry FK and checksum concept but does not define a prediction's immutable registry revision/artifact checksum reference. | `docs/architecture/api-contracts.md` (`POST /predictions/yield`, `POST /rankings/crops`); `docs/architecture/data-model.md` (`model_registry`, `prediction_runs`); `models/registry/model_registry.csv` | Results may not be reproducible or auditable; client retry/polling behavior and stale-result handling cannot be implemented consistently. | Define execution mode and lifecycle, stable status transitions, timeout/retry behavior, and persist the exact approved registry/evidence revision and artifact checksum with each run. Do not invent a model version; derive it from verified provenance. |
| F-06 | P1 | The weather API returns `as_of` and mentions source/coverage, but does not define freshness/staleness states, stale-data policy, or how source interruption is distinguished from a valid historical observation. The source and coverage remain unverified, and all integrated APY-weather rows use a starting-calendar-year proxy, not verified crop-season alignment. | `docs/architecture/api-contracts.md` (`GET /weather`); `models/weather_intelligence/weather_intelligence_metadata.json`; `data/processed/weather_regional/crop_weather_integration_validation_summary.csv`; `metadata/source_registry.csv`; `metadata/weather_source_registry.csv` | A client could present stale or proxy-aligned weather as current or crop-season-specific. | Before weather release, define source freshness and temporal/geographic semantics, response freshness/missingness states, attribution, and refusal behavior; publish only for evidence-supported periods/locations. |
| F-07 | P1 | Mandi-price metadata conflicts: source registry status says “local file verification pending,” while acquisition audit says “downloaded and structurally inspected.” The audit describes one arrival date only, not a price history; the processed mandi directory is empty. Source registry also leaves license/coverage verification false. The product requirements do not promise a market-price MVP, so this should remain out of scope unless separately approved. | `metadata/mandi_price_source_registry.json`; `metadata/mandi_price_acquisition_audit.json`; `metadata/source_registry.csv`; `docs/architecture/product-requirements.md`; `docs/architecture/repository-audit.md` | Do not claim verified price provenance, historical trends, or a functioning price feature. A single-day local extract cannot support time-series analysis. | Reconcile what “verification pending” refers to (file presence, source identity, or terms) using evidence, record license/attribution, and explicitly exclude market-price APIs/features from MVP until coverage and rights are verified. |
| F-08 | P1 | Assistant design requires claim-level citation support, but the proposed `message_citations` entity links citations to a whole assistant message, not to the individual claim/span they support. The API returns citations but does not specify whether they support all material claims or how validation status is exposed. | `docs/architecture/assistant-design.md`; `docs/architecture/api-contracts.md` (assistant message response); `docs/architecture/data-model.md` (`message_citations`) | Citation presence could be mistaken for claim support; unsupported generated claims may appear properly sourced. | Define citation-to-claim/span mapping or an equivalent verifiable answer structure, store validation outcome/version, and require claim-level evaluation before release. Otherwise narrow the stated guarantee and block unsupported answers. |
| F-09 | P1 | Knowledge administration describes quarantine, ingestion, review, approval, publish, and withdrawal, but the API catalogue provides submit/publish/withdraw without explicit review/approve/reject/status-transition operations or a clear safe content-upload boundary. `content/artifact reference` is not an ingestion protocol. | `docs/architecture/api-contracts.md` (admin knowledge endpoints); `docs/architecture/assistant-design.md` (source lifecycle); `docs/architecture/data-model.md` (`knowledge_sources`, `knowledge_documents`) | Unreviewed material might be published through an ambiguous workflow; uploaded content handling and provenance cannot be implemented consistently. | Specify submit/quarantine, review decision, publish, withdraw, and rollback transitions with reviewer authority/separation, content limits, artifact-reference ownership, checksum, and immutable version semantics before enabling knowledge administration. |
| F-10 | P1 | Model provenance is described but no approved operational artifact/version is established. The registry row records a path/existence and readiness status, but production approval is not established; readiness notes missing-input acceptance and unverified unseen-category reliability. The deployment API can change status but does not define the evidence schema or independent approval gate. | `models/registry/model_registry.csv`; `models/registry/model_validation_status.csv`; `models/yield_prediction/yield_model_deployment_readiness_report.json`; `models/yield_prediction/individual_crop_hgb_location_metadata.json`; `docs/architecture/api-contracts.md` (`/admin/models`); `docs/architecture/phase-acceptance-criteria.md` | Artifact existence or a smoke report could be operationally misread as deployment authorization. | Keep inference disabled. Define model-card/evidence requirements, independent approval workflow, approved population/coverage, artifact provenance/checksum, and release/rollback authority. Do not load or serve until the model gate passes. |
| F-11 | P2 | Accessibility conformance target and quantitative latency/availability/recovery objectives are explicitly undecided. Current documents require measurement and later SLO/RTO/RPO selection but do not assign owners or a decision date. | `docs/architecture/product-requirements.md`; `docs/architecture/phase-acceptance-criteria.md`; `docs/decisions/architecture-decisions.md` | Backlog sizing and public-service readiness estimates remain uncertain; this does not block architecture planning or a provider-independent foundation. | Assign product/operations owners during backlog planning; set measurable targets before performance/recovery testing and public-launch approval. |
| F-12 | P2 | The audit's historical statement that the root had no `docs/` is now false if read as a current inventory, though it is explicitly dated/scoped to the initial static audit and the decision log explains the chronology. | `docs/architecture/repository-audit.md` (audit date and structure); current `docs/` tree; `docs/decisions/architecture-decisions.md` | A reader skimming only the audit may confuse historical baseline with present state. No substantive architecture evidence is contradicted. | Preserve the audit as an immutable historical snapshot; reference this review/current file inventory for present documentation status. No audit rewrite is required for this task. |

**Finding count:** P0: **5**; P1: **5**; P2: **2**.

## 4. Confirmed facts, assumptions, and unknowns

### Confirmed by static repository evidence

- The current documentation filenames are those listed in Section 2; the architecture and decision documents were added after the initial audit. Their proposed status is explicit.
- No application source or database migration was found in the prior audit; this review did not identify contradictory application implementation. `.git` is absent at the inspected root.
- The saved yield artifact path `models/yield_prediction/individual_crop_hgb_location.joblib` exists. Metadata lists target `Yield` and features `Crop`, `Season`, `Crop_Category`, `State`, `District`, and `FE_YearStart`. Evaluation/readiness values are recorded in metadata, not reproduced here.
- `notebooks/15_feature_engineering.ipynb` records `yield_area_production_units_verified: False`. Notebook 02's yield conversion is explicitly phrased as an assumption, not verified units. Therefore the application-facing target unit is **UNKNOWN**.
- Season evidence includes Kharif, Rabi, Summer, and `Total`. Existing EDA excludes `Total` to avoid double counting; model feature audits include `Total`. No evidence establishes the correct application treatment for `Total`.
- Crop ranking uses the yield model to rank eligible historical candidates. Registry metadata calls it a derived ranking, not a separate trained model; 2025 is beyond the documented training period. Evaluation is retrospective, not agronomic suitability/profitability.
- Registry status for the low-yield classifier is `NOT READY`, and no classifier artifact path is recorded. Its evaluation report says the weather-added predictive value is false and trained model Brier scores are worse than the constant baseline.
- Weather integration is marked exploratory and uses APY starting-calendar-year proxy alignment; full crop-season alignment is unverified. It records 320,124 matches and 56,148 unmatched APY rows in the validation summary.
- Risk outputs are heuristic analytical artifacts, with thresholds not agronomically validated and explicit prohibition on farmer-facing calibrated future-risk claims.
- Mandi source status conflicts with the acquisition audit. The acquisition audit describes a structurally inspected single-day snapshot, not historical price coverage; licensing remains unverified.
- District-boundary source identity/vintage remain unverified, with unresolved identifiers and a provisional crosswalk. The crosswalk also contains synthetic placeholder coordinates marked low confidence and held for review.
- The architecture consistently chooses a modular monolith and does not require microservices. Authentication, AI, weather, hosting providers, legal interpretation, model units, and operational objectives are not decided.

### Assumptions/inferences

- Workflow order among notebooks and handoff relationships are inferred from filenames, static references, and notebook narrative; they are not a reproducible pipeline guarantee.
- The proposed schema/API could support the product after the listed gaps are resolved; no implementation behavior or runtime compatibility is implied.
- Backlog drafting can begin for provider-independent foundation work, but implementation of affected sensitive or evidence-dependent components should wait for their P0 decisions.

### Unknowns

- Yield unit and comparable unit semantics across all APY records; validated treatment of `Season = Total`; supported crop/state/district/year population and model performance outside recorded evaluation.
- Legal rights, source freshness and refresh guarantees for APY, weather, geography, and mandi data.
- Authoritative location IDs and historical boundary mapping.
- How consent and alternative legal bases should be sequenced and persisted; retention periods, deletion exceptions, backup expiry, and expert verification.
- Authentication/session details, AI provider/model, weather provider, hosting/region, content upload/index technology, and numerical SLO/RTO/RPO.
- No independent verification that notebooks execute, artifacts load, inference succeeds, or recorded metrics represent valid production performance was performed.

## 5. Model and data blockers

### Yield prediction

The model is a trained `HistGradientBoostingRegressor`, not a validated nationwide service. Artifact presence is verified by file listing only. Its recorded temporal validation results are MAE 448.306/RMSE 672.961/R² 0.798 for 2019–2020 and MAE 422.856/RMSE 898.177/R² 0.693 for 2021–2022, based on `models/yield_prediction/individual_crop_hgb_location_metadata.json`. The final holdout was repeatedly inspected during diagnostics. The readiness report records that missing crop/year values were not rejected and unseen-category reliability was not verified. These records do not establish units, generalization, or production readiness.

### Crop ranking

The ranking is a derived component over predicted yield among historically observed eligible candidates, not a separate trained recommendation model. Its recorded 2023–2024 evaluation is retrospective and explicitly says it is not a measure of agronomic suitability or profitability. The model omits weather, and 2025 projections extrapolate beyond 2013–2022 training. Any API/UI called a crop recommendation would overstate the evidence unless renamed/restricted and independently gated.

### Weather and risk

Descriptive weather history is not a forecast. Crop-weather joins use a starting-year proxy; the report records no rows with verified full-season alignment. Coverage gaps and questionable repeated daily series remain. The low-yield classifier has no verified saved artifact and is `NOT READY`; heuristic risk CSVs are explicitly not calibrated future-risk probabilities. None can currently support farmer-facing risk warnings.

### Geography and seasons

Boundary metadata records unverified source/vintage, missing identifiers, and unresolved crosswalk records. Some coordinates are synthetic placeholders and explicitly ineligible for weather acquisition. APY seasons include `Total`; existing analysis excludes it in some contexts, while model evaluation includes it. Location IDs, versioning, historical boundary equivalence, and season semantics must be resolved for affected features.

### Mandi-price conflict

`metadata/mandi_price_source_registry.json` says local file verification is pending. `metadata/mandi_price_acquisition_audit.json` identifies a raw CSV, hash, 12,556 rows, and one unique arrival date, and calls it downloaded/structurally inspected. This supports a distinction between **local file inspection** and **source/provenance/license/coverage verification**, but the documents do not explicitly reconcile that distinction. Do not guess which status is intended. Market price features should remain outside the MVP until the status is clarified and historical coverage/rights are evidenced.

## 6. API, database, security, and assistant gaps

- **API:** Shared conventions for timestamps, units, errors, pagination, correlation IDs, and idempotency are a strong baseline. Implementation detail is still missing for prediction input resolution, sync/async behavior, status lifecycle, exact model/evidence provenance, and freshness/stale-data responses. The expert-consent sequence is circular. Proposed fields whose source contracts are unknown must remain disabled.
- **Database:** Core ownership, consent, model evidence, cases, conversations, citations, and audit concepts are represented. Durable export/deletion jobs, idempotency outcomes, assignment history, and alternative-authority evidence are not sufficiently specified to support the corresponding API promises. Location registry/version and weather storage are appropriately deferred pending evidence, but prevent those APIs from being enabled now.
- **Security/privacy:** Backend-enforced authorization, least privilege, secret-safe logging, and provider/legal review are consistent. Identity/session transport, expert qualification, consent/authorized-basis lifecycle, retention periods, deletion propagation, and operational recovery objectives remain open. No legal compliance conclusion is possible from the repository.
- **Assistant:** Source curation, versioning, retrieval, attribution, abstention, language behavior, injection defense, data minimization, and evaluation scope are well covered at the design level. The missing claim-to-citation relation and incomplete admin state/upload contract prevent a testable end-to-end implementation/release contract. Provider and corpus evidence are absent.
- **Architecture/build sequence:** The modular FastAPI monolith aligns with existing Python research assets while avoiding unsupported distributed-system complexity. The approved web stack is not present in the repository. No contradiction requires changing the stack; actual toolchain/dependency choices must be established during implementation planning without assuming the existing IntelliJ Java metadata is the product stack.

## 7. Prioritized resolution list

### P0 — resolve before affected component implementation

1. **Close the model-serving contract:** confirm yield unit, season/`Total` treatment, exact input/eligibility schema, supported period/categories, farm-to-feature mapping, response status semantics, execution mode, and immutable model/evidence provenance. Keep prediction and ranking routes disabled until then.
2. **Redesign the expert-case/consent sequence:** define draft/request, grant, activation, revocation, and deletion states so case-specific data is not accessible before a valid scoped grant or documented alternative basis.
3. **Align API lifecycle with persistence:** decide whether export/deletion requests and idempotency are MVP; if yes, define durable state/entities. Specify case assignments/history and evidence for alternative authorized bases. Remove promises that are deferred.
4. **Gate location-dependent work on a versioned authority:** choose or defer an authoritative location reference and historical-boundary strategy; reject provisional/synthetic/unresolved mappings rather than treating them as coverage.
5. **Specify prediction/ranking execution and provenance:** define synchronous/asynchronous lifecycle, retries/polling, exact registry/artifact revision reference, and stored result provenance before serving or history APIs are implemented.

### P1 — resolve before affected feature release

1. Define weather source rights, freshness, `as_of` interpretation, stale/unavailable states, temporal alignment, units, attribution, and coverage; until then weather endpoints remain disabled or strictly limited to evidence-backed historical data.
2. Reconcile mandi local-file versus source-verification status and establish rights/coverage; exclude the price feature from the MVP unless that gate passes.
3. Represent/validate citation support at claim level (or weaken the claim guarantee) and add tests for citation accuracy, not just citation existence.
4. Specify full knowledge submission/review/approve/reject/publish/withdraw/rollback state machine and safe content ingestion boundary.
5. Define an independent model evidence and approval process; recorded registry labels and artifact presence must not serve as approval.

### P2 — assign and resolve before the corresponding release gate

1. Product/operations to set measurable accessibility target, performance/SLO, RTO/RPO, and operational ownership before public launch tests.
2. Keep the audit as a historical baseline; reviewers should use the current docs inventory rather than interpret its initial no-`docs/` observation as present state.

## 8. Proposed implementation backlog and dependencies

Backlog is proposed, not started. Ordering shows dependency constraints without selecting providers or technologies beyond the locked stack.

| Order | Work item | Depends on | Completion evidence |
|---:|---|---|---|
| 1 | Resolve P0 contract and lifecycle decisions above; update affected API/data-model documents after human review. | Product, domain, data, privacy, and engineering owners. | Approved versioned contracts for location, yield/ranking, consent/case, idempotency, exports/deletion, and result provenance. |
| 2 | Compare authentication options and approve provider/session design. | Threat model, privacy/legal criteria, account-role policy. | Recorded decision and security-tested auth flow; no vendor assumed here. |
| 3 | Define minimal account/role/consent/deletion and audit data schema; plan migrations. | Work item 1; retention/legal review; identity mapping decision. | Reviewed schema constraints and ownership tests; migration plan only after implementation authorization. |
| 4 | Build provider-independent application foundation and versioned API shell. | Locked stack; account/session decision for protected routes; API conventions. | Reproducible service baseline, health/error/correlation contracts and targeted API tests. |
| 5 | Implement ownership/access-control primitives and farmer account/farm flows. | Work items 2–4; authoritative location policy before location-dependent fields. | Cross-user/role/IDOR tests, consent state tests, localization/accessibility tests. |
| 6 | Establish source/location/season/units evidence and coverage service. | Data/domain/legal review; source provenance and boundary decisions. | Versioned coverage records, explicit unknown/unavailable behavior, reproducible source contract. |
| 7 | Evaluate each model component and define release cards; do not wire inference before approval. | Work items 1 and 6; model/data owners. | Independent evaluation, artifact provenance/checksum, input/output contract, approval record. |
| 8 | Implement model adapter/API only for individually approved components. | Work item 7; P0 model contract; authorization and persistence. | Model contract tests, out-of-scope rejection, provenance in results, rollback and performance evidence. |
| 9 | Select/approve AI provider and curated-source governance; build knowledge ingestion/review and citation schema. | Legal/privacy review, P1 assistant requirements, source-rights decisions. | Approved source versions, claim-level citation validation, injection/abstention/language test suite. |
| 10 | Implement assistant and expert workflow. | Work items 2, 3, 5, and 9; resolved consent/case lifecycle. | Grounding/citation, Hindi/English, privacy, assignment, expiry/revocation, and audit integration tests. |
| 11 | Select hosting/region and finalize production operations. | Provider/legal decisions; measured service objectives; deployment and threat model. | Container deployment, managed DB, secrets, backups/restore, monitoring, incident exercise and release sign-off. |

## 9. Explicit criteria for approving Phase 1

Phase 1 may be approved for **application-foundation implementation** when:

1. The five P0 findings are resolved in reviewed contracts/designs, or affected capabilities are explicitly removed from Phase 1 scope. The model-serving, location and expert-case routes may remain disabled while unrelated foundation work proceeds.
2. Authentication provider comparison criteria, owner, decision process, and session integration boundary are approved; actual provider selection must precede protected production authentication implementation.
3. Ownership and role matrix is accepted by product/security; consent and documented alternative-basis records have a non-circular lifecycle.
4. The database design supports any API promises retained for Phase 1, including idempotency, deletion/export state if included, audit requirements, and account/role lifecycle.
5. Existing assets are treated as static evidence only; no model is approved by artifact presence, registry row, or prior smoke report.
6. Phase 1 backlog has measurable acceptance tests for API validation/errors, correlation IDs, pagination, ownership and authorization, Hindi/English behavior, and secret-safe logging.
7. Work items that require unresolved data rights, location definitions, units, provider contracts, or legal interpretation are marked blocked rather than silently assumed.

Approval of Phase 1 foundation does **not** approve public release, model serving, market-price functionality, weather claims, assistant answers, or farmer-specific expert access. Each remains subject to its own evidence and release gates.

## 10. Inspection limitations

This review inspected filenames and static documentation/metadata/report contents. It did not execute notebooks, inspect model internals by loading serialized files, recompute metrics, validate hashes, test APIs, inspect an application service (none was found in the baseline), verify upstream data sources, or obtain legal advice. Repository-recorded metrics, statuses, paths, and audit conclusions are reported as recorded evidence, not independently established truth. No existing architecture document was modified.
