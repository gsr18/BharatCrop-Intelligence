# BharatCrop Intelligence: Repository Audit

**Audit date:** 2026-11-02  
**Scope:** Static, read-only inspection of the repository as found. No notebooks were run, no model artifacts were loaded, and no data was downloaded or modified.

## 1. Executive summary

The repository is a research and data-workspace baseline, not an existing web application. It contains 22 primary Jupyter notebooks (and 22 notebook checkpoints), agricultural and weather data, geographic/source metadata, analysis reports, one serialized yield-regression model, and several derived analytical/ranking outputs. No Next.js frontend, FastAPI service, PostgreSQL schema or migration, authentication implementation, test suite, dependency lock/manifest, Docker configuration, deployment configuration, or project-level documentation was found.

The strongest ML asset is a saved `HistGradientBoostingRegressor` for yield estimation. Its metadata records temporal validation results and a “CONDITIONALLY READY FOR INTEGRATION” verdict, but explicitly notes holdout reuse, small unseen-location samples, missing-input acceptance, and unverified reliability for unseen categories. This does not establish production readiness. Crop ranking is a derived use of this model, not a separately trained recommender; risk indicators are explicitly exploratory; and the weather low-yield classifier is explicitly not ready, with no corresponding saved model artifact found.

Data lineage is substantial but not fully dependable for application use. The APY files cover 2013–14 through 2024–25; weather integration is marked exploratory and uses a starting-calendar-year proxy, with incomplete coverage. District boundaries and crosswalks have unresolved identifiers and provenance. Source/license/coverage verification is incomplete in the source registries. Notebook code and saved metadata include machine-specific Windows paths. These constraints, along with absent application infrastructure, are blockers to treating current outputs as farmer-facing advice.

## 2. Verified repository structure

The inspected root contains:

| Path | Observed contents |
|---|---|
| `.idea/` | IntelliJ project/module XML, workspace settings, and `.idea/.gitignore`. The module is configured as a Java module and the project SDK entry names JDK 25. |
| `data/raw/` | Historical APY CSVs, NASA POWER weather JSON/CSV files, a district-boundary shapefile set, and a single-day mandi-price extract. |
| `data/processed/` | APY and weather derivatives, exploratory integration outputs, and coverage/validation summaries. `data/processed/mandi_prices/` exists but contains no files. |
| `metadata/` | Source registries, data requirements, acquisition manifests, district geography/crosswalk files, and source/provenance JSON. |
| `models/` | One `.joblib` yield model; model metadata/readiness/evaluation files; derived rankings, weather history, risk indicators, explainability outputs, and registry/policy files. |
| `notebooks/` | 22 numbered notebooks, 22 `.ipynb_checkpoints`, plus notebook-local data and audit reports. |
| `reports/data_audit/` | CSV/JSON audits for APY, weather, geographic mapping, and acquisition. |

The recursive file inventory showed 2,053 `.json`, 88 `.csv`, 44 `.ipynb`, 7 `.xml`, 5 each of `.shp`, `.shx`, `.dbf`, `.sbn`, `.sbx`, `.prj`, and `.CPG`, plus one `.joblib`, one `.txt`, one `.iml`, and one `.gitignore`. These counts include notebook checkpoints and all inspected subdirectories.

There is no `docs/` or `docs/architecture/` directory in the inspected root; this report is the only file created for the audit.

## 3. Existing technology and dependency inventory

| Area | Verified finding |
|---|---|
| Python/research | The primary executable/research surface is Python Jupyter notebooks using the `Python 3 (ipykernel)` kernel metadata. Static imports include pandas, NumPy, scikit-learn, joblib, SciPy, matplotlib, seaborn, GeoPandas, requests, and notebook/IPython utilities. These are observed imports, not a complete or pinned dependency specification. |
| Python environment | No `requirements.txt`, `pyproject.toml`, `setup.py`, `setup.cfg`, `Pipfile`, `poetry.lock`, `uv.lock`, Conda environment file, or other Python environment manifest was found. Notebook 16 refers to a `requirements.txt` path, but no such file exists at the project root. |
| Node.js/TypeScript | No `package.json`, lockfile, `tsconfig.json`, Next.js config, TypeScript source, or frontend application directory was found. |
| API/backend | No Python application source (`.py` files outside notebooks), FastAPI routes, API schemas, server entry point, or service configuration was found. |
| Database | No PostgreSQL configuration, schema, migration, ORM model, Alembic configuration, or database test was found. |
| Authentication/authorization | No login/session/token code, role model, permission policy, or identity-provider configuration was found. |
| Tests/quality | No test directory, test files, `conftest.py`, pytest/tox configuration, or CI workflow was found. Notebook code and saved outputs are not a substitute for application tests. |
| Containers/deployment | No Dockerfile, Compose file, deployment manifest, or CI/CD configuration was found. |
| Documentation/Git | No README, root `.gitignore`, or Git metadata was found at the inspected root; `git status` could not identify a usable repository. The only `.gitignore` is under `.idea/`. |
| IDE metadata | IntelliJ metadata describes a Java module/JDK setup, not the approved Next.js/FastAPI/PostgreSQL stack. This is an IDE configuration fact and does not establish that Java application code exists. |

## 4. Notebook inventory and workflow map

All 22 numbered notebooks and their notebook-local checkpoint copies were present. Opening/final markdown text and notebook metadata were read statically; code cells and saved outputs were not executed. The sequence below is the apparent dependency order inferred from filenames, notebook narratives, and referenced file paths.

| # | Notebook | Apparent role and key handoff |
|---:|---|---|
| 01 | `01_project_setup_and_source_registry.ipynb` | Defines project scope and source/data requirements; writes or documents source registry and requirements metadata. |
| 02 | `02_apy_dataset_acquisition_and_audit.ipynb` | Acquires and audits four APY batches; feeds merged historical APY and acquisition/missingness reports. |
| 03 | `03_weather_dataset_acquisition_and_audit.ipynb` | Investigates IMD/NASA POWER weather and district-boundary inputs; produces weather/geography audit outputs and supporting mapping files. |
| 04 | `04_apy_data_overview.ipynb` | Profiles the merged APY data before cleaning. |
| 05 | `05_apy_data_cleaning.ipynb` | Investigates APY quality and creates `historical_food_grains_apy_cleaned_flagged.csv`. |
| 06 | `06_apy_data_preprocessing.ipynb` | Reshapes cleaned APY into `historical_food_grains_apy_long_2013-14_to_2024-25.csv`. |
| 07 | `07_apy_eda_analysis.ipynb` | Analyzes long-format APY trends, coverage, and quality. |
| 08 | `08_apy_data_visualization.ipynb` | Visualizes APY findings; primarily analytical outputs. |
| 09 | `09_weather_data_overview.ipynb` | Profiles annual district weather data. |
| 10 | `10_weather_data_cleaning.ipynb` | Cleans/flags annual weather and emits a weather-cleaning report. |
| 11 | `11_weather_data_preprocessing.ipynb` | Produces the preprocessed annual weather dataset for EDA/integration. |
| 12 | `12_weather_eda_analysis.ipynb` | Analyzes preprocessed weather data. |
| 13 | `13_weather_data_visualization.ipynb` | Visualizes annual district-level weather patterns. |
| 14 | `14_crop_weather_integration.ipynb` | Joins APY to weather and geography; outputs `apy_weather_integrated_exploratory.csv`, coverage files, and integration validation summaries. |
| 15 | `15_feature_engineering.ipynb` | Defines eligibility/features and audits yield/area/production consistency; feeds model development and consistency reports. |
| 16 | `16_yield_model_development_and_selection.ipynb` | Compares yield regression candidates with time-aware validation; saves the selected yield model and metadata. |
| 17 | `17_yield_model_deployment_readiness.ipynb` | Performs a documented inference/readiness smoke assessment and writes a readiness report. Its reported checks are static evidence only for this audit. |
| 18 | `18_crop_recommendation.ipynb` | Ranks eligible historical crop candidates using the yield model; outputs retrospective rankings, evaluation, metadata, and a 2025 projection CSV. |
| 19 | `19_weather_intelligence.ipynb` | Builds descriptive district weather history/reference outputs and evaluates an experimental low-yield classification task. |
| 20 | `20_agricultural_risk_intelligence.ipynb` | Produces historical heuristic yield-risk indicators and summaries; explicitly exploratory. |
| 21 | `21_model_explainability_and_scenarios.ipynb` | Produces permutation-importance, error/bias, and scenario-analysis outputs for the yield model. |
| 22 | `22_model_registry_and_policy_outputs.ipynb` | Consolidates artifact/evidence inventories, registry status, policy rules, and validation status summaries. |

The ordering is an inferred workflow, not a reproducible pipeline contract. The notebook files do not establish that a clean checkout can rerun sequentially or that all referenced inputs are the current versions. Notebook 01 and 02 have no distinct trailing markdown cell in the inspected cell structure; the others include closing Markdown narrative. Notebook checkpoints are present but were not compared for content equivalence.

## 5. Model and artifact evidence table

“Artifact exists” means the named path was found in the repository inventory. Serialized model files were not opened or loaded. Readiness is quoted from repository metadata and is not an independent approval.

| Component/model | Actual artifact path | Metadata path | Intended task and target | Recorded evaluation evidence | Recorded readiness | Known limitations | Artifact exists? | Outstanding validation requirements |
|---|---|---|---|---|---|---|---|---|
| Yield prediction — `HistGradientBoostingRegressor` | `models/yield_prediction/individual_crop_hgb_location.joblib` | `models/yield_prediction/individual_crop_hgb_location_metadata.json`; `models/yield_prediction/yield_model_deployment_readiness_report.json` | Predict `Yield` for an individual crop candidate using `Crop`, `Season`, `Crop_Category`, `State`, `District`, and `FE_YearStart`. | Metadata records 35,784 training rows (2013–2022); validation windows 2019–2020 (MAE 448.306, RMSE 672.961, R² 0.798) and 2021–2022 (MAE 422.856, RMSE 898.177, R² 0.693). Readiness report records two synthetic sample rows and an initial non-representative latency measurement. | `CONDITIONALLY READY FOR INTEGRATION`; production approval `NOT ESTABLISHED`. | Final holdout was repeatedly inspected during diagnostics; unseen-location samples were small; weather features excluded; missing Crop/year values currently produce predictions; unseen-category prediction reliability is unverified; no evidence-based agronomic bounds. | **Yes** — file found; not loaded. | Re-establish an untouched evaluation; validate geographic/categorical generalization and required-field behavior; define output bounds and operational/monitoring/security criteria; validate artifact provenance and runtime/dependency compatibility. |
| Crop recommendation — derived ranking component, not a separate trained model | `models/crop_recommendation/crop_recommendations_ranked.csv`; `models/crop_recommendation/crop_recommendations_projection_2025.csv`. Upstream estimator: `models/yield_prediction/individual_crop_hgb_location.joblib`. | `models/crop_recommendation/crop_recommendation_metadata.json`; `models/crop_recommendation/crop_recommendation_evaluation.json`; `models/registry/crop_recommendation_evaluation_evidence.json` | Rank historically observed eligible candidates within State–District–Season–Year groups by predicted yield. Target used for ranking: predicted `Yield`; not profitability or suitability. | Retrospective 2023–2024 evaluation records 8,433 eligible prediction rows and 2,365 groups; top-1 hit rate 0.792, top-3 hit rate 0.998, mean Spearman 0.792. Evidence explicitly limits interpretation to observed yield among eligible historical candidates. Configured 2025 predictions are beyond model training years. | `EVALUATED RETROSPECTIVELY — NOT PRODUCTION-APPROVED`; research/historical ranking only. | Not a standalone recommendation model; historically observed candidates only; no soil, NPK, soil moisture, irrigation, or profitability features; weather alignment unverified; 2025 is extrapolation beyond training years 2013–2022. | **Yes** — both CSVs found; upstream model file found. | Define agronomic eligibility and candidate coverage; assess temporal/geographic generalization independently; validate season and data contracts; determine how recommendations should account for profitability, soil, irrigation, and uncertainty. |
| Weather low-yield classifier — experimental model evaluation | **No saved classifier artifact path is recorded or found.** Evaluation report: `models/weather_intelligence/low_yield_model_evaluation.json`. | `models/weather_intelligence/low_yield_model_evaluation.json`; `models/weather_intelligence/weather_intelligence_metadata.json` | Classify whether current yield is below 80% of the median of the previous 2–3 available positive-yield observations for the same state, district, crop, and named season. | Train 2015–2022 (47,309 rows), test 2023–2024 (12,692 rows). Constant baseline Brier 0.113; logistic baseline 0.176; logistic with weather 0.184; random forest baseline 0.202; with weather 0.205. Weather-added predictive value recorded `false`. | `NOT READY`. | Starting-calendar-year weather proxy; full crop-season alignment unverified; trained model Brier scores worse than constant baseline; probabilities are not validated farmer risk estimates. | **No** saved classifier model found; evaluation JSON exists. | Do not operationalize without a verified saved artifact, stronger evaluation/calibration evidence, correct crop-season alignment, explicit label rationale, and farmer-risk validation. |
| Agricultural risk indicators — analytical output, not a trained classifier | `models/agricultural_risk_intelligence/yield_risk_indicators.csv`; `models/agricultural_risk_intelligence/district_crop_risk_summary.csv`; review file `models/agricultural_risk_intelligence/extreme_yield_deviations_review.csv` | `models/agricultural_risk_intelligence/agricultural_risk_metadata.json` | Historical heuristic classifications using yield relative to prior observations; not calibrated future-risk probabilities. | Metadata records 90,893 prepared observations, 69,693 with historical baseline, and 9,236 district–crop–season groups. Thresholds include high concern below 70% and moderate concern from 70% to below 85% of historical median; extreme ratios require review. | `EXPLORATORY — NOT VALIDATED FOR FARMER-FACING RISK WARNINGS`. | Heuristic thresholds are not agronomically validated; extreme deviations need source/unit review; weather associations descriptive, not causal; starting-year proxy; missing weather means unavailable, not low risk. | **Yes** — analytical CSVs found; not model weights. | Validate measures and units with domain experts; establish prospective/temporal evaluation and calibration if future risk is intended; keep exploratory status and missingness visible. |
| Weather intelligence — descriptive outputs | `models/weather_intelligence/district_weather_history.csv`; `models/weather_intelligence/district_weather_reference.csv` | `models/weather_intelligence/weather_intelligence_metadata.json` | Historical district weather context and percentile/reference flags; not a forecast. | Metadata records 2013–2024, 7,680 district-year records with weather, 640 districts with good coverage, and 111 districts without weather data (751 districts in the reported coverage scope). | Descriptive/exploratory; no production approval recorded. | Starting-calendar-year proxy; full crop-season alignment not verified; historical percentile flags are not forecasts; missing data must remain unavailable, not imply low risk. | **Yes** — CSV and metadata paths found. | Verify coverage and seasonal mapping; define freshness/source/units and missing-data behavior before application use. |
| Explainability and scenario outputs — analytical evidence, not a model artifact | `models/model_explainability_and_scenarios/` (including `explainability_summary.json`, `feature_category_audit.json`, `permutation_feature_importance.csv`, error/bias/group CSVs, and `year_scenario_comparison.csv`). Upstream estimator is the yield model above. | `models/model_explainability_and_scenarios/explainability_summary.json`; `models/model_explainability_and_scenarios/feature_category_audit.json` | Explain model behavior and summarize scenario/error patterns; target is yield prediction. | Summary records a 3,000-row sample from 2021–2022 (MAE 424.03, RMSE 601.16, R² 0.778). Permutation importance identifies Crop and State as the largest predictive-reliance measures. | Analytical outputs only; no separate deployment-readiness status. | Permutation importance is not causation; sampled evaluation; group metrics can be unstable for small groups; repeated holdout inspection is noted; years beyond 2022 are unvalidated; scenario baseline appeared only twice. | **Yes** — outputs found; no separate model weights. | Retain sample/population/evaluation context; validate group stability and interpretation; do not surface scenarios as forecasts without independent validation. |

The registries also contain eight model-policy rules. They explicitly call for verifying artifacts/metadata, rejecting incomplete inputs, treating unseen categories as unverified, blocking the not-ready classifier and unvalidated risk warnings, retaining evaluation context, and separating registry presence from production approval.

## 6. Data lineage observations

### Observed data flow

1. **Crop statistics:** Four raw Department of Agriculture and Farmers Welfare/UPAg APY CSV batches are present under `data/raw/`, covering 2013–14 through 2024–25. The recorded acquisition manifest reports 31,356 merged rows and 40 columns, with 284,246 missing cells. Processed wide, cleaned/flagged, and long APY files are present. The long-format row count cited by notebook outputs is 376,272.
2. **Weather:** NASA POWER pilot and regional raw JSON/CSV assets are present; raw regional files are organized by variable (`PRECTOTCORR`, `T2M_MAX`, `T2M_MIN`) and year. Processed annual, cleaned/flagged, and preprocessed weather CSVs are present. Notebook/report metadata reports 7,680 district-year records for 640 districts with good coverage and 111 districts without coverage in a 751-district scope.
3. **Geography:** A district-boundary shapefile and APY coordinate/geographic reference and crosswalk files exist. Boundary provenance says source identity, original archive, and boundary vintage are unverified. The boundary audit records 810 features, 36 state labels, 780 unique district labels, 28 features with unavailable state/district identifiers, 31 unavailable district LGD identifiers, and 31 unresolved records. It also notes suspicious district names.
4. **Integration and features:** Notebook 14 emits an exploratory APY-weather integration and coverage summaries. Its validation summary records 376,272 original/integrated rows, 320,124 weather matches and 56,148 unmatched records; row preservation and key uniqueness are not evidence of measurement validity. All matched weather rows use APY starting-calendar-year mapping; full-season weather alignment is recorded as unverified.
5. **Model/risk products:** Notebook 15 reviews yield/area/production consistency and feature readiness; Notebook 16 trains/evaluates the yield model; later notebooks derive rankings, weather/risk summaries, explainability outputs, and registry evidence. These derived products do not add source verification or production approval by themselves.
6. **Market prices:** A local raw mandi CSV exists and the acquisition audit describes 12,556 records, 10 columns, 26 states, 396 districts, 1,240 markets, 221 commodities, all for one arrival date (2026-10-31). The audit identifies it as insufficient for historical trends/forecasting. The processed mandi directory is empty. The source-registry JSON still says local file verification is pending, while its separate audit says downloaded and structurally inspected; this is a metadata inconsistency.

### Quality, leakage, lineage, and reproducibility observations

- The source registries mark APY and proposed IMD sources as not verified for schema/download/coverage/license/integration. An IMD rainfall entry is marked `DISCOVERED_NOT_DOWNLOADED`; available NASA POWER data does not establish nationwide source verification or license/terms approval.
- The APY manifest records substantial missingness. The zero-area/positive-yield classification includes many records across years. A separate yield consistency summary reports 18,218 of 186,587 tested positive finite observations with more than 25% deviation from implied yield; the report says these require investigation, not automatic rejection.
- The weather audit flags identical daily precipitation and temperature series for two geography IDs across 4,383 dates; a shared grid-cell assignment is plausible but unverified. The audit explicitly says retain both records pending investigation.
- The district crosswalk/provenance is provisional and not approved for a final crosswalk. Historical district-name matches do not establish boundary equivalence.
- Yield-model metadata reports the final holdout was repeatedly inspected during diagnostics. This weakens claims of an untouched final test; it is not, by itself, proof of a specific leakage path. The current feature list does not include contemporaneous yield, but the complete training/evaluation implementation was not independently reproduced.
- The low-yield label is built from prior observed yields and weather is aligned by starting calendar year, not verified crop season. This creates a construct/temporal-alignment concern for any farmer-facing risk interpretation.
- Multiple notebooks and metadata contain absolute Windows paths tied to a specific local user/workspace; notebook 03 also contains a placeholder path for a downloaded boundary archive. These are environment assumptions and portability risks. No environment-variable values were read or reported.
- Notebook outputs and report files include prior execution results and warnings, but they were not treated as fresh verification. The audit did not execute notebooks, inspect serialized model internals, validate hashes, or independently recompute metrics.
- The available contents do not prove all historical notebook inputs/outputs are current, reproducible, licensed for redistribution, or consistent with the metadata inventories.

## 7. Existing application infrastructure

**None was found in the inspected repository.** The verified code surface is notebooks and static/data artifacts. There is no existing frontend, backend/API, database schema or migration, authentication/authorization, test suite, application configuration, or deployment stack to extend. The approved Next.js/TypeScript, FastAPI, and PostgreSQL stack remains a product decision, not an existing repository implementation.

## 8. Risks, blockers, and unresolved questions

### Blockers and material risks

- **Application baseline:** No product code or reproducible dependency environment exists. The first implementation cannot safely assume import paths, pinned versions, API contracts, deployment conventions, or tested behavior.
- **Model serving:** Only one saved trained model was found. Its readiness report identifies missing-field acceptance and unverified unseen-category reliability; model format/runtime compatibility and artifact provenance were not tested. No farmer-facing model output should be treated as approved.
- **Recommendation semantics:** Current crop ranking optimizes predicted historical yield among observed eligible candidates. It has no evidence of profitability, input availability, soil/irrigation suitability, or causal agronomic benefit.
- **Risk interpretation:** The classifier is not ready and its trained artifact was not found. The risk indicators are heuristic historical summaries, not calibrated forecasts.
- **Data quality and coverage:** APY missingness/measurement anomalies, unresolved district mapping, weather coverage gaps, identical weather series, and seasonal alignment create material geographic and temporal uncertainty.
- **Source rights and reliability:** The registries leave schema, download, coverage, license/terms, or integration verification open. The repository’s presence of a dataset is not proof of permission, freshness, completeness, or official provenance.
- **Security and operations:** No secrets/configuration were assessed from environment values; no service exists to audit. Any future model-serving path needs controlled artifact provenance and dependency management. Serialized joblib/pickle-style artifacts must only be loaded from trusted, integrity-checked sources in a controlled runtime.
- **Privacy and governance:** The product will handle farmer identity, precise location, farm/crop details, and potentially assistant conversations. Consent, minimization, retention/deletion, access, sharing, and storage jurisdiction are not documented in this repository.
- **Assistant grounding and safety:** No retrieval corpus, source-citation mechanism, prompt/model configuration, assistant API, conversation storage policy, or expert escalation behavior was found. A grounded assistant cannot be verified from the current assets.
- **Authorization and localization:** Farmer, agricultural expert, and administrator roles have no implementation or policy mapping. No Hindi/English translation catalog or localization infrastructure was found.
- **Portability and project hygiene:** Absolute workstation paths and a Java-oriented IntelliJ configuration conflict with portable Python/web workflows. No root Git metadata/configuration or dependency lock was available at this location.

### Unresolved questions requiring product/domain decisions

- Which data sources may legally be stored, transformed, redistributed, or exposed, and what are the required source attribution and refresh expectations?
- What location precision is necessary, and what consent, retention, deletion, and data-residency rules apply to farmer and chat data?
- What output is acceptable for crop recommendations: yield ranking only, or an actionable agronomic recommendation with inputs, confidence, and expert review?
- What evidence threshold and responsible domain owner are required before predictive yield/risk outputs can be shown to farmers?
- Which trusted sources and citation standards ground the agricultural assistant, and when should it abstain or route to an agricultural expert?
- What are the detailed capabilities and separation-of-duty rules for farmer, expert, and administrator accounts?
- What languages, scripts, and fallback behavior are required beyond the initial Hindi/English scope?
- What deployment, availability, observability, incident response, and model-update expectations apply to the public launch?

## 9. Recommended next steps for Phase 0

1. Resolve data-source ownership, terms/licenses, provenance, update cadence, and geographic/temporal coverage; maintain explicit evidence rather than treating local files as verified sources.
2. Establish a reproducible baseline for the notebook/model assets: dependency versions, data contracts, stable relative paths, artifact checksums/provenance, and a clean-run validation plan that preserves all existing research outputs.
3. Have domain and evaluation owners review APY measurement anomalies, district crosswalk/boundary vintage, weather grid mapping, missing coverage, and crop-season alignment before fixing any data contract.
4. Define model-use gates separately for yield prediction, retrospective crop ranking, descriptive weather intelligence, and risk warnings. Revisit evaluation design/holdout integrity and required-field/unseen-category behavior before serving.
5. Agree on the grounded-assistant corpus, citation/freshness rules, abstention/escalation policy, privacy controls, and Hindi/English quality expectations.
6. Specify the application security and authorization model for the three approved roles, along with farmer-data minimization, retention, and audit requirements.
7. After those decisions, baseline the approved Next.js/TypeScript, FastAPI, and PostgreSQL stack with explicit dependency, testing, migration, deployment, and configuration practices. Preserve the current notebooks, datasets, model artifacts, metadata, and research outputs unchanged.

These are recommendations for completing Phase 0, not implementation work performed by this audit.

## 10. Evidence classification and audit limits

- **Verified facts** are direct observations from filenames/directories and static contents of notebooks, CSV/JSON metadata, and reports. Examples include the existence of the `.joblib` path, recorded evaluation metrics, absent application/configuration files, and repository-recorded readiness labels.
- **Inferences** are explicitly described as apparent/inferred: notebook order and handoffs, product integration implications, and risk assessments based on recorded limitations. They are not independent experimental results.
- **Unverified assumptions/unknowns** include the validity of notebook outputs, ability to reproduce metrics, successful model loading/inference, source licensing, freshness, nationwide completeness, true geospatial equivalence, production behavior, and application-stack suitability beyond the approved decisions.

No tests, notebook execution, model loading, predictions, retraining, dependency installation, network access, or secret-value inspection were performed. The audit is complete as a static baseline for the repository contents accessible at the inspected root; it does not certify data correctness, model performance, legal rights, or production readiness.
