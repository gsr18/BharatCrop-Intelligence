# Phase 3B Stage 1 — Weather-Only ML Feasibility Audit

**Status:** Feasibility and implementation plan only. No source code, source datasets, derived datasets, models, or existing backups were changed. No model was trained and no tests were run. This report is the only deliverable created for this audit.

## Executive decision

The raw NASA POWER regional daily archive is structurally suitable for a weather-only research module. A read-only scan of all 2,016 regional JSON files found a complete and consistent 2,520-cell grid for all three variables and all dates from 2013-01-01 through 2024-12-31. The archive supports retrospective anomaly screening, descriptive weather-pattern discovery, and a next-day statistical prediction experiment.

That finding establishes data feasibility, not model skill. No anomaly labels exist in the repository, no weather-only ML benchmark has been run, and the archive is retrospective MERRA-2/POWER output rather than an operational forecast feed. A user-facing prediction should therefore be labelled a research estimate until it beats simple baselines on a locked temporal holdout and is separately assessed for spatial transfer.

The corrected Phase 3B workstream must have no dependency on crop or yield records, APY identifiers, crop calendars, agricultural suitability, or crop-ranking services. The current Weather Intelligence implementation is coupled to those concepts and should not be reused unchanged. Preserve it and its backups as legacy material; build the independent weather module alongside it, then replace the Weather Intelligence primary workflow only in a later, separately authorized implementation phase.

## 1. Scope, evidence labels, and hard boundary

This audit inspected the raw `data/raw/weather_regional` JSON archive, weather-only aggregate and audit assets, and the existing backend, frontend, tests, and Phase 3B scripts. The raw-file audit parsed the source JSON in memory and wrote no intermediate data. APY-linked outputs were excluded from all reported measurements and model-feasibility calculations; they are mentioned only where their presence in existing code affects architecture boundaries.

Statements marked **Measured** describe repository files or the source-level scan. Statements marked **Proposed** are designs for a future implementation and have not been executed or benchmarked.

**Required boundary for all future Phase 3B code:** no imports from APY/yield modules; no crop, yield, crop-suitability, or ranking fields in weather schemas; no join to agricultural records; no weather-derived agricultural recommendation or impact claim. Weather observations, coordinates, dates, source metadata, and weather-only features are the complete domain.

## 2. Dataset inventory and actual statistics

### 2.1 Raw NASA POWER / MERRA-2 archive — measured

The source archive is `data/raw/weather_regional/{PRECTOTCORR,T2M_MAX,T2M_MIN}/{year}/R###_<VARIABLE>_<year>.json`.

| Measure | Scanned result |
|---|---:|
| Source files | 2,016 JSON files; 56 region files × 3 variables × 12 years |
| On-disk size | 596.46 MiB |
| Region identifiers | 56 (`R001`–`R056`) |
| Distinct grid cells | 2,520 |
| Grid layout | 56 latitude values × 45 longitude values |
| Latitude extent and step | 7.0°–34.5° N, 0.5° |
| Longitude extent and step | 69.375°–96.875° E, 0.625° |
| Date coverage | 2013-01-01–2024-12-31, 4,383 UTC dates per cell |
| Measurements | 11,045,160 values per variable; 33,135,480 across the three variables |

Every variable-year has the same 2,520 unique coordinates. The latitude and longitude value sets form the complete 56 × 45 rectangular grid. Feature counts differ among regional files because regions contain different numbers of grid points; the feature counts sum to 2,520 for every variable-year.

Each response identifies the NASA/POWER Daily API v2.10.1, a UTC time standard, and `-999` as its declared fill value. Daily keys are `YYYYMMDD`; response headers cover January 1 through December 31 for each requested year, including leap days. Parameter metadata declares `T2M_MAX` and `T2M_MIN` in `C` and `PRECTOTCORR` in `mm/day`.

Source lineage is not represented by one identical header tag across variables. All 672 files for each temperature variable report `MERRA2` and `POWER` in `header.sources`; all 672 precipitation files report `MERRA2`. The API name, API version, UTC standard, declared fill value, date window, and units are consistent within their respective variables. Preserve the source tag per variable in the canonical dataset and manifest instead of flattening it to a single generic label.

### 2.2 Source-level quality results — measured

| Check across the raw archive | Result |
|---|---:|
| Missing expected cell-dates | 0 |
| Unexpected dates | 0 |
| Duplicate JSON object keys | 0 |
| Duplicate coordinates within a file | 0 |
| Duplicate cell records across files for a variable-year | 0 |
| `-999` values actually present | 0 |
| Non-finite or non-numeric values | 0 |
| Negative precipitation values | 0 |
| Dates with `T2M_MIN > T2M_MAX` | 0 of 11,045,160 temperature pairs |

Observed ranges in the archive are `T2M_MAX` −24.19 to 51.51 °C, `T2M_MIN` −42.81 to 37.98 °C, and `PRECTOTCORR` 0 to 1,038.34 mm/day. Negative temperatures are valid observations and are not treated as invalid values. The maximum precipitation value is an extreme that deserves a review flag, not an automatic deletion: the existing weather-only extreme check lists five high values and reports exact matches against point-API queries, but that is an internal source cross-check, not independent station validation.

The source scan therefore supports a one-to-one join on `(latitude, longitude, date)` without duplicate or missing variable records. It does not establish that MERRA-2/POWER estimates equal local station observations, and it does not prove complete administrative coverage of India; the measured coordinate bounding box is the supported coverage statement.

### 2.3 Existing derived weather assets — measured inventory and disposition

| Asset | Measured/known shape | Audit disposition |
|---|---|---|
| `data/processed/weather_regional/nasa_power_grid_annual_summary_2013_2024.csv` | 6,216 rows; 518 unique coordinates × 12 years; no duplicate coordinate-year keys or missing columns; all three valid-day counts are 365/366; no `tmin_mean_c > tmax_mean_c` rows | Weather-only descriptive annual summary. It is about 20.6% of the raw grid and is too sparse in time for the daily ML tasks. Do not use it as the canonical training table. |
| `data/raw/weather_pilot/nasa_power_weather_pilot_2013.csv` and its pilot audit | One 2013 point series, 365 dates; the audit reports no missing values but does not claim end-to-end source verification or national coverage | Small ingestion example only; not the ML training source. |
| `data/raw/weather_regional_pilot` and `data/raw/weather_regional_test` | 12 and 4 JSON files respectively | Partial test/pilot copies; retain for parser fixtures if useful, but do not mix them into the canonical archive. |
| District-year weather tables, model reference/history CSVs, APY-keyed pilot files, and `phase3b_weather_agriculture/data/seasonal_weather_features.csv` | Existing geography-/agriculture-linked derivatives | Excluded from the weather-only data analysis and proposed training pipeline. Preserve them; do not treat them as weather-only evidence or delete them in this phase. |

The existing `reports/data_audit/nasa_power_weather_value_audit.csv` contains 90,720 cell-variable-year audit rows, consistent with 2,520 cells × 3 variables × 12 years. It is useful supporting evidence, but the source-level scan above is the basis for the duplicate/date/value results in this report. Some older request-audit material uses `T###` identifiers while the raw archive files use `R###`; reconcile this naming difference in the new manifest. Existing acquisition metadata also lacks a per-file hash and complete parameter/request record. Add those in the future ingest contract.

## 3. Weather Anomaly Detection — feasibility and proposed definitions

**Feasibility:** high for historical screening. The panel has 12 years per cell and complete daily values, enough for seasonal baselines and rolling comparisons. The limited time span and lack of labelled weather events prevent strong claims about rare-event recall, climate normals, or impact classification.

### Features and methods

1. **Seasonal climatology baseline.** For each cell and variable, estimate the median and 5th/95th percentiles from a 31-day day-of-year window (the target day ±15 days) using training years only. For temperature, calculate robust anomaly score `z = (x − median) / (1.4826 × MAD)`; fall back to IQR/1.349 when MAD is zero, and mark a zero-dispersion case unscored if no stable scale is available. Use a leap-day mapping rule fixed in the dataset contract.
2. **Precipitation treatment.** Work on `log1p(PRECTOTCORR)` for robust daily scores and retain original `mm/day` values in every response. Also calculate 7- and 14-day precipitation totals and compare them with the cell’s historical seasonal distribution. A dry-spell feature may count consecutive days below 1 mm/day; that 1 mm threshold is a proposed analysis convention, not a source-verified impact threshold.
3. **Trailing rolling detector.** At date `t`, compare each temperature value with the preceding 30 days only (robust median/MAD, minimum 14 valid days). For precipitation, score the trailing 7-/14-day totals against prior rolling windows. Shift windows so the value being scored and any future dates are excluded from its baseline.
4. **Isolation Forest.** Fit on weather residuals rather than raw geography-dominated values: seasonal robust residuals for `T2M_MAX`, `T2M_MIN`, diurnal range, `log1p(PRECTOTCORR)`, one-day changes, and 3-/7-day rainfall totals. Do not use crop fields or yield-derived geography. Return a continuous score and ranked percentile; choose any binary alert threshold from validation/review capacity, not a presumed truth label.

### Expected output and evaluation

Each flagged record should report `cell_id`, coordinates, UTC date, variable(s), observed value and unit, baseline, residual/robust z or Isolation Forest score, threshold/method version, source provenance, and an explicit label such as “statistical outlier for this cell and period.” Do not call it a disaster, hazard impact, or crop risk.

No ground-truth event labels are present in the weather-only source. Evaluate detector behaviour with (a) injected synthetic shifts/spikes to test sensitivity to known perturbations, (b) false-positive burden and method-agreement summaries on untouched data, (c) seasonal/location-stratified spot review of top-ranked records, and (d) consistency with the independent source QA checks. Synthetic tests measure response to the injected pattern only; they do not estimate real-event recall or precision. Future validation with independent station/event labels is an unresolved data requirement.

For retrospective plots, a baseline may use a declared historical training interval. For any “as-of” monitor, recompute it walk-forward using only observations available before the scored date. Report those two modes separately.

## 4. Weather Pattern Discovery — feasibility and proposed definitions

**Feasibility:** high for monthly and seasonal patterns; feasible but more compute-intensive for daily patterns. Patterns are descriptive groupings, not weather forecasts or causal regimes.

### Feature tables

Create independent weather-only rows at three grains:

| Grain | Row key | Proposed weather features |
|---|---|---|
| Daily | cell × UTC date | `T2M_MAX`, `T2M_MIN`, diurnal range (`T2M_MAX − T2M_MIN`), precipitation, `log1p(precipitation)`, 3-/7-day precipitation sums, 3-/7-day temperature means, and sine/cosine day-of-year. Every rolling feature ends on the stated date and is clearly marked as retrospective for pattern analysis. |
| Monthly | cell × year × month | mean and standard deviation of daily max/min temperature; mean diurnal range; total and mean daily precipitation; 95th percentile daily precipitation; precipitation wet-day fraction (`PRECTOTCORR ≥ 1 mm/day`); valid-day count. |
| Seasonal | cell × year × defined season | The same summary family as monthly. Proposed fixed bins: Jan–Feb winter, Mar–May pre-monsoon, Jun–Sep monsoon, Oct–Dec post-monsoon. These are reproducible analysis bins, not crop seasons or official local impact categories. |

Keep latitude/longitude out of the weather-value feature vector for the first clustering experiment so clusters reflect weather rather than spatial separation. Retain coordinates for maps and geographic evaluation. A separate experiment may add coordinates if the question is explicitly spatial typology.

### Clustering, scaling, and stability

- Fit `StandardScaler` on training rows only; persist it with the model. Examine a robust-scaling sensitivity run because precipitation is skewed.
- Evaluate K-Means for `k=2..12` using inertia, silhouette, Calinski–Harabasz, and Davies–Bouldin scores, followed by bootstrap/sample stability using adjusted Rand index (ARI) after label alignment. Choose `k` using stability plus interpretability, not one index alone.
- Use PCA fitted on training data for two-dimensional visualization only; transform held-out rows through the same fitted PCA. PCA axes are not physical explanations.
- Evaluate Agglomerative/Hierarchical clustering on a stratified sample or a small set of prototypes. Avoid an all-daily or all-monthly pairwise-distance matrix. Use the same scaled features and compare sample cluster assignments with K-Means results.
- Fit on earlier years and assign later years to frozen centroids; separately fit on geographic training blocks and assign held-out blocks. Report cluster occupancy and centroid changes over time and space. Name clusters from their measured weather centroids, with no severity or agricultural interpretation.

## 5. Weather Prediction Lab — feasibility, features, and validation

**Targets:** next UTC day’s `T2M_MAX` in °C and next UTC day’s `PRECTOTCORR` in mm/day, independently. These experiments predict the retrospective archive values from past archive values; they do not replace an operational numerical weather prediction feed.

### Candidate baselines and estimators

| Candidate | Definition |
|---|---|
| Persistence | `ŷ(D) = y(D−1)` for the target variable. |
| Historical climatology | For a cell and target day-of-year, mean and median over a ±15-day window from training years only. For rainfall, report both training mean rainfall and a two-part climatology summary (wet-day frequency and mean on wet days); any amount prediction remains in mm/day. |
| Ridge Regression | Standardized numeric lag/rolling/calendar/coordinate features; scaler fit within the training fold. Clip negative precipitation output at zero only as a declared post-processing variant and report its effect. |
| Random Forest Regressor | Nonlinear tabular benchmark on the same feature contract; fixed seed, bounded tree depth/leaf size and a deterministic stratified training sample if the full panel exceeds memory/runtime limits. |
| HistGradientBoostingRegressor | Nonlinear boosting benchmark on the same features; tune leaf count, learning rate, iterations, and regularization only inside chronological validation folds. |

### Exact prediction-time feature contract

For a row whose target date is `D`, the latest permitted observation is `D−1`. For each of `T2M_MAX`, `T2M_MIN`, and `PRECTOTCORR`, define `lag_1/2/3/7/14/30` as the observation at `D−1`, `D−2`, `D−3`, `D−7`, `D−14`, and `D−30`. Define trailing `mean_3/7/14/30`, temperature min/max/std over 7/14/30 days, and precipitation `sum_3/7/14/30`, wet-day count and wet-day fraction over windows ending at `D−1`. Add diurnal range lags/means, latitude, longitude, target month, and cyclical day-of-year sine/cosine. Missing early lags must stay missing with an explicit history-depth flag, not be filled using future values.

Any learned scaler or imputer is fit within a fold. If a learned climatology feature is later added to estimator inputs, construct it from years before each training row’s target year; do not calculate an all-years normal once and feed it to earlier training examples. Do not use target-day weather, centered rolling windows, future MERRA-2 data, crop/price data, or post-target summaries.

### Chronological validation and locked holdout

Use an expanding-window one-day-ahead backtest across all cells:

| Fold | Fit years | Validation year |
|---|---|---:|
| 1 | 2013–2017 | 2018 |
| 2 | 2013–2018 | 2019 |
| 3 | 2013–2019 | 2020 |
| 4 | 2013–2020 | 2021 |
| 5 | 2013–2021 | 2022 |

Keep 2023–2024 locked until model, feature, and hyperparameter choices are complete. Fit the final research candidate through 2022, then evaluate once on 2023–2024. For daily one-step evaluation, the prior day’s observed weather may be used after each forecast origin; label this explicitly as rolling one-step evaluation. Random row splits are prohibited because adjacent dates and locations are dependent.

Report MAE and RMSE in native units, R² as a secondary statistic, and MAE skill relative to persistence and climatology by year, variable, and cell. Include both micro-averaged results and a macro-average over cells so dense/easy groups do not dominate. If precipitation uses a transformed target, inverse-transform before computing public-facing mm/day metrics. Do not claim prediction skill unless the candidate consistently beats baselines across validation folds and the locked holdout.

### Separate-location holdouts

They are feasible: the archive contains 2,520 cells, each with 12 years of daily data. Use contiguous latitude/longitude blocks (with an optional buffer around held-out cells) rather than random cells or adjacent grid points, and report this as a separate spatial-generalization test. The primary temporal test should remain “future dates at known cells”; a spatial holdout asks “new cells.” A cell-specific climatology is unavailable for a never-seen cell, so the spatial test must compare against a training-only regional/grid-neighbour climatology. Spatial correlation and the shared gridded source mean this is a challenging but still not station-independent external test.

## 6. Data size and computational limits

The raw compressed-on-disk footprint is about 596 MiB, but parsing JSON into Python objects or a long pandas table costs substantially more. The full daily panel is 11.05 million cell-days; an in-memory three-variable `float32` tensor alone is about 126 MiB, before date indexes, feature arrays, DataFrame objects, models, and temporary copies. A 20-feature `float32` feature matrix at full size is roughly 0.8 GiB before overhead.

Build in chunks by year and store a canonical wide table with `(cell_id, latitude, longitude, date, T2M_MAX, T2M_MIN, PRECTOTCORR, source tags, units, quality flags)`. Partitioned Parquet is a good candidate for daily and feature tables; the current backend dependency manifest does not declare a Parquet engine, so either add and pin one during implementation or choose another documented columnar format. Keep raw JSON immutable.

Monthly features are about 362,880 rows; four seasonal bins give about 120,960 rows; daily modeling stays near 11 million rows per target. Begin Isolation Forest and Random Forest with fixed, stratified samples across cell, year, and season, then score in batches. Record the sampling seed and inclusion rule. HGB may use larger samples but still needs a memory/time benchmark. Limit full hierarchical clustering to a stratified sample (initially a few thousand rows) or prototypes; use K-Means for larger feature tables. No such benchmark or model fit was performed in this audit.

## 7. Existing application architecture and reuse/retirement plan

### Reuse as patterns, not as weather-only data dependencies

- FastAPI routers use typed Pydantic response models, query validation, pagination, explicit 422/503 errors, and a shared `application.state` service object.
- `WeatherDataService` demonstrates cached read-only table loading, dataset hashes, source/provenance responses, and unavailable states. Reuse these service qualities, but not its current data contract or dataframe.
- Frontend `ObservationChart`, `MetricGrid`, `ProvenanceDetails`, loading/error states, and unit-labelled scales can support the descriptive weather page and lab views. The frontend currently has no charting dependency; use the existing SVG-oriented components or add a visualization library only with a clear need.
- Existing project dependencies include pandas, scikit-learn 1.8.0, and joblib. The requested Ridge, Random Forest, HistGradientBoosting, Isolation Forest, K-Means, AgglomerativeClustering, and PCA algorithms are available from scikit-learn. No weather-only trained model artifact was identified under `models/weather_intelligence`.

### Existing coupling and retirement from the primary workflow

- `WeatherDataService` imports APY quality flags and yield units, and its schemas contain APY geography/district identifiers. It loads annual district weather/reference/history assets and an integration source; it is not an independent grid-cell daily service.
- Its current `/api/v1/weather/anomalies` is an annual historical percentile comparison (p10/p90), not a validated daily detector. Its `/classifier` endpoint reports saved low-yield research metadata and no executable artifact; it is not a weather-only classifier.
- `application/backend/bharatcrop_foundation/app.py` constructs a `WeatherAgricultureService` from APY and weather services. `api.py` registers `/api/v1/weather-agriculture/options` and `/api/v1/weather-agriculture/regions`; the weather router also includes `/api/v1/weather/crop-context`.
- The Weather Intelligence page calls the annual history, coverage, anomaly, and classifier routes, and embeds the weather-agriculture explorer. The explorer presents APY historical ranking and crop-calendar weather context.
- `phase3b_weather_agriculture/scripts/build_seasonal_weather_features.py` reads the district grid-reference/calendar inputs and writes `seasonal_weather_features.csv`; it is not a generic daily weather panel builder.

For the new primary workflow, retain a simple descriptive historical view over the weather-only canonical grid dataset. Rebuild that view from daily observations or full-grid monthly/annual aggregates, showing cell coordinates, UTC dates, units, source, and coverage. Do not back it with district or agricultural joins. Retire the crop-context and weather-agriculture explorer from the Weather Intelligence primary page and retire the low-yield classifier panel from that page. Preserve all source files, prior reports, derived assets, and backups; this audit does not delete, rename, or rewrite any of them.

Create a separate `WeatherMLService` for anomaly, clustering, and prediction inference. It should load versioned weather-only artifacts/metrics lazily, check hashes and feature schema, reject unknown cells/targets, and fail closed when an artifact or required coverage is unavailable. Keep model fitting offline; do not expose a training endpoint. Existing artifact conventions in the application use separate artifact/metadata paths and SHA-256 checks; apply that pattern in a separate weather-only artifact namespace so existing files are not overwritten.

Existing weather tests cover historical data loading, aggregations, percentile anomalies, routes, and integration behaviour. Other existing tests explicitly cover the old agriculture-ranking flow. No dedicated weather-only anomaly-model, clustering, or prediction-lab test suite was found. Frontend tests cover the old explorer/API client, not a complete independent weather-lab page.

## 8. Proposed artifact and reproducibility structure

Keep the old Phase 3B folder and `backups/phase3b/{pre_implementation_20261108,runtime_repair_20261108_020353}` intact. For implementation, use a new isolated research directory such as:

```text
phase3b_weather_intelligence/
  manifests/          # per-source file hash, source header, request, size, coverage
  config/             # immutable dataset and feature contracts
  scripts/            # audit, panel build, anomaly, pattern, prediction, evaluate
  data/processed/     # weather-only partitioned daily panel and feature tables
  artifacts/metrics/  # fold/holdout metrics, split IDs, stability diagnostics
  artifacts/predictions/ # holdout prediction rows and anomaly/cluster assignments
  reports/            # methods, data quality, model cards, limitations
```

Store serialized estimators separately from the current weather artifacts, for example under `models/weather_only_ml/{anomaly,patterns,prediction_tmax,prediction_precipitation}/<version>/`. Each version should include the model file, metadata JSON, feature schema/order, training cutoff, exact split/sample IDs, configuration, random seeds, package versions, source-manifest hash, and artifact SHA-256. Keep the locked holdout predictions and metrics as immutable evaluation evidence. Do not point this work at an existing model path.

## 9. Proposed backend API contracts

Use a weather-only namespace such as `/api/v1/weather-ml`; retain ordinary descriptive routes separately until the frontend cutover. Responses should contain weather fields only.

| Route | Contract |
|---|---|
| `GET /api/v1/weather-ml/metadata` | Dataset date range, UTC convention, grid extent/cell count, variables/units, source lineage, manifest hash, model availability/version, and explicit research status. |
| `GET /api/v1/weather-ml/anomalies` | Query `start_date`, `end_date`, `cell_id` or coordinate bounds, `variable`, `method` (`climatology`, `rolling`, `isolation_forest`), optional score/severity threshold, and bounded pagination. Return observed value/unit, baseline, score, method, UTC date, cell coordinates, quality/provenance, and total count. |
| `GET /api/v1/weather-ml/patterns` | Query `granularity` (`daily`, `monthly`, `seasonal`), date range, frozen `model_version`/`k`, and optional cell/bounds filter. Return cluster assignment, centroid summary, feature definitions, scaler/model version, and provenance. Never fit clusters in a request. |
| `GET /api/v1/weather-ml/prediction-lab/metrics` | Query target and evaluation protocol; return baseline/model metrics by fold, year, and spatial summary, with locked-holdout status and training cutoff. |
| `POST /api/v1/weather-ml/prediction-lab/predict` | Body: `target` (`T2M_MAX` or `PRECTOTCORR`), cell ID or coordinate, `as_of_date`, and optional registered model version. Return target date `as_of_date + 1 day`, prediction/unit, baselines, model version, training cutoff, feature-availability flags, and limitations. Return intervals only after they are calibrated and evaluated. |

Validate dates, known grid cells, supported targets, and pagination. Return 422 for invalid inputs and 503 for unavailable data/artifacts, matching current API error conventions. Training, parameter search, and artifact creation stay offline and are not API actions. No route accepts crop, season, yield, suitability, or ranking parameters.

## 10. Proposed frontend experience

Replace the Weather Intelligence primary experience with four weather-only areas:

1. **Observed Weather:** searchable grid-cell map/list, coordinate and source details, date range, daily series, monthly/seasonal summaries, and data coverage. Label the data as NASA POWER/MERRA-2 gridded estimates, not local station observations.
2. **Anomaly Detection:** choose method, variable, period, and cell/region; show ranked observations with observed value, baseline, deviation/score, method, and an explanation that the result is statistical screening without event labels.
3. **Pattern Discovery:** choose daily/monthly/seasonal features and a validated cluster solution; visualize a grid map, cluster centroids, season profiles, and a PCA projection. State fit interval, scaler, `k`, and stability evidence.
4. **Prediction Lab:** select next-day maximum temperature or precipitation, cell/date, and registered benchmark; show persistence/climatology alongside Ridge, Random Forest, and HistGradientBoosting results, plus fold metrics and the 2023–2024 locked holdout summary. Mark every prediction “research estimate from historical gridded data,” not an operational weather forecast.

Do not render crop ranking, crop calendar, yield, suitability, agricultural risk, or crop-weather context in these views. Keep the historic page’s unit-aware charts and provenance/error patterns where suitable. No browser interaction or UI change was performed for this audit.

## 11. Test and acceptance criteria for a later implementation

### Data contract

- The immutable source manifest accounts for all expected region-variable-year files, records per-file SHA-256, API/source/unit metadata, and makes the `R###` naming explicit.
- Parser tests cover normal and leap years, duplicate JSON keys, duplicate coordinates, missing dates, unexpected dates, `-999`, non-finite/non-numeric values, source-tag variation, and malformed JSON.
- Full-corpus acceptance reproduces 2,520 cells, the 4,383-day window, matching cell/date/variable keys, and zero missing/sentinel/non-finite/negative-precipitation/Tmin-above-Tmax records. Any changed result blocks model training pending investigation.
- The canonical weather table contains no APY/crop/yield fields, imports, joins, or identifiers.

### ML and validation

- Unit tests prove every prediction feature at date `D` uses observations no later than `D−1`; a synthetic future spike cannot alter earlier features or fold climatology.
- Scaling, imputation, clustering, anomaly thresholds, and hyperparameter selection fit on the training portion of each fold only. The 2023–2024 holdout is not used for feature, threshold, or model choice.
- Candidate predictions are finite; precipitation outputs and clipping policy are explicit. Metrics include both baselines and exact units.
- Fixed seeds reproduce samples, model artifacts, and cluster assignments within documented tolerance. Spatial holdouts use contiguous coordinate blocks and report buffers.
- Pattern acceptance includes stability across seeds/bootstrap samples and held-out period/location assignment; silhouette alone is insufficient.
- Anomaly acceptance reports injection sensitivity and review burden while explicitly omitting real-event precision/recall claims in the absence of labels.
- Prediction acceptance requires consistent baseline skill in rolling validation and the locked holdout. Otherwise the lab reports “no demonstrated skill” and does not promote the candidate.

### API and UI

- API contract and integration tests use a weather-only fixture; every response carries units, UTC date semantics, source, model/evaluation version, and limitations where applicable.
- Static/schema checks ensure the new service and routes do not import APY/yield modules or expose agricultural fields.
- Frontend tests cover loading, unavailable data/model, empty results, units, period filters, method/model switches, and correct research disclaimers. No crop-ranking or yield-related content appears on the Weather Intelligence primary route.
- Existing legacy tests/backups remain preserved; any later routing change is reviewed independently from this Stage 1 audit.

## 12. Risks, assumptions, and unresolved questions

1. **Retrospective source versus operational forecast:** the proposed next-day task predicts another MERRA-2/POWER daily estimate from previous estimates. A real operational forecast needs a forecast product or live provider and its own validation.
2. **Short climatology:** 2013–2024 is only 12 years and ends in 2024. Call it the historical baseline, not a standard climate normal; test non-stationarity and report year slices.
3. **Spatial meaning:** a 0.5° × 0.625° grid point is not a district station. The coordinate bounding box is measured; administrative coverage and local representativeness are not.
4. **Extreme precipitation:** 1,038.34 mm/day is source-consistent in the existing point/regional comparison but has no independent station verification. Preserve it, flag it, and inspect it before using tail-sensitive training or alert thresholds.
5. **No event labels:** anomaly rankings cannot support event detection precision/recall or impact claims without independent labels.
6. **Metadata drift:** per-variable `header.sources` differs, and older request logs use a different region prefix. Add a manifest and keep raw headers before combining variables.
7. **Derived data coverage:** the existing annual grid summary covers 518 coordinates rather than all 2,520 and cannot substitute for the daily archive.
8. **Leakage and dependence:** temporal neighbours and nearby grid cells are correlated; random row/cell splits will overstate generalization.
9. **Compute:** full daily feature matrices, Isolation Forest, Random Forest, and hierarchical clustering can consume substantial memory/time. Benchmark deterministic samples and batch inference before committing to UI latency.
10. **Unresolved product decisions:** whether the Prediction Lab is research-only or eventually user-facing; whether its normal use is historical replay or live “as-of” prediction; the desired anomaly review burden; and whether future validation may add independent station or event-label data.

## Recommended next phase

Proceed first with a source manifest and weather-only daily panel builder under a new isolated workspace. Re-run the raw acceptance checks as automated tests, then create baselines and chronological benchmarks. Do not begin frontend cutover or promote any model until the locked 2023–2024 evaluation and spatial holdout are complete and the above boundary checks pass.
