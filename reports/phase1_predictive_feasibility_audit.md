# BharatCrop Intelligence — Phase 1: Predictive Feasibility Audit

**Type:** READ-ONLY inspection and reporting. No notebook, dataset, model, backend, frontend, or environment file was modified, renamed, moved, executed, or retrained. All statements below are grounded in files read directly. Where a value is quoted, it is taken verbatim from notebook markdown/code or a saved JSON/CSV artifact.

**Evidence sources inspected:** 22 notebooks under `notebooks/` (code + markdown, outputs ignored), `data/` (headers, row/col counts, distinct-key coverage), `models/` (artifacts + metadata JSON/CSV), `metadata/` (registries), and `application/backend/bharatcrop_foundation/` (which artifacts the backend actually loads).

---

## 1. Executive Summary

The project is a mature **data engineering + governance** pipeline with **one genuine trained model**.

- **What is real and reusable:** A single supervised regressor — `HistGradientBoostingRegressor` — that predicts crop **Yield** from `Crop, Season, Crop_Category, State, District, FE_YearStart`. It is saved as a joblib artifact, has a feature-contract metadata file, has been time-aware validated, and is loaded and served by the backend. **This is the only persisted model artifact in the entire project.**
- **What the four application modules actually do:**
  - **Yield Prediction (nb16/17):** real regression; genuinely reusable as a *feature-based interpolation* predictor, but **not** a validated future-year forecast and **not** production-approved.
  - **Crop Intelligence (nb18):** *reuses* the yield model to rank historically-observed candidate crops by predicted yield. No new model is trained for ranking; no new artifact is saved. Explicitly yield-based, **not** suitability or profitability.
  - **Weather Intelligence (nb19):** mostly descriptive aggregation of **annual** district weather; a genuinely-fit-but-weak low-yield **classifier** was trained and evaluated (ROC-AUC ≈ 0.59–0.62) but its **Brier score was worse than a constant baseline, weather added no predictive value, and no model artifact was saved** → `NOT READY`.
  - **Agricultural Risk (nb20):** **heuristic threshold rules** on `Yield / historical-median`; **no ML model, no classifier, no artifact**. Classified `EXPLORATORY — NOT VALIDATED`.
- **Biggest blockers to *genuine* prediction:** (1) no true feature-based yield drivers (weather excluded from the selected model; no soil/irrigation/Mandi-cost features); (2) weather data is **annual, grid-representative, calendar-year-proxied**, not daily/seasonal — cannot support weather forecasting; (3) the only forecast-style outputs (2025) are **extrapolations** beyond the 2013–2022 training window; (4) the "holdout" was repeatedly inspected, and APY units/target consistency are unverified.
- **INT234 coverage:** regression (Linear, Ridge, Decision Tree, Random Forest, HistGradientBoosting), classification (Logistic, Decision Tree, Random Forest), chronological validation, and model evaluation are **implemented and evaluated**. KNN, Naive Bayes, SVM, KMeans, hierarchical clustering, PCA, MLP/neural nets, polynomial regression, and association-rule mining are **NOT implemented** (verified absent from all notebook imports/code).

---

## 2. Complete 22-Notebook Inventory

Legend for the last two columns — **Artifact:** does it save a reusable model artifact (`.joblib`)? **Repro:** reproducible from files present on disk?

| # | Notebook | Type | Key objective | Target | Algorithms actually implemented | Evaluation | Saved artifact | Repro |
|---|---|---|---|---|---|---|---|---|
| 01 | project_setup_and_source_registry | Setup/governance | Define scope, register official sources | none | none (pandas only) | column asserts | CSV registry (`metadata/source_registry.csv`) | Yes |
| 02 | apy_dataset_acquisition_and_audit | Acquisition/audit | Merge APY DES files, audit zero/missing | none | none (the `classification_report` is a pandas DataFrame of zero-area/positive-yield QC — **not** ML) | coverage/missingness audit | CSVs under `reports/data_audit` | Yes |
| 03 | weather_dataset_acquisition_and_audit | Acquisition/audit | Acquire NASA POWER weather; grid mapping | none | none (no sklearn) | coverage/distance QC | many CSVs (`data/raw/weather_pilot_2013_2024/*.csv`) | Yes (10 pilot geographies) |
| 04 | apy_data_overview | EDA | Dimensions, dtypes, zero vs missing | none | none | describe/missingness | none | Yes |
| 05 | apy_data_cleaning | Cleaning | Flag QC issues, preserve source | none | none | QC flag counts | `historical_food_grains_apy_cleaned_flagged.csv` | Yes |
| 06 | apy_data_preprocessing | Preprocess | Wide→long reshape, preserve flags | none | none | row/mismatch asserts | `historical_food_grains_apy_long_2013-14_to_2024-25.csv` | Yes |
| 07 | apy_eda_analysis | EDA | Distributions, trends by year/crop | none | none | descriptive stats/plots | none | Yes |
| 08 | apy_data_visualization | Visualization | Charts of APY | none | none | plots only | none | Yes |
| 09 | weather_data_overview | EDA | Weather schema/coverage | none | none | describe | none | Yes |
| 10 | weather_data_cleaning | Cleaning | Flag extreme/missing weather | none | none | QC flags | `district_weather_annual_cleaned_flagged_2013_2024.csv` | Yes |
| 11 | weather_data_preprocessing | Preprocess | Annual aggregation of daily grids | none | none | asserts | `district_weather_annual_preprocessed_2013_2024.csv` | Yes |
| 12 | weather_eda_analysis | EDA | Weather distributions, correlations | none | descriptive stats (no PCA/clustering) | describe/correlation | none | Yes |
| 13 | weather_data_visualization | Visualization | Weather charts | none | none | plots only | none | Yes |
| 14 | crop_weather_integration | Integration | Join APY↔weather via `apy_geography_id`, calendar-year proxy | none | none | `weather_match_status`, alignment flags | `apy_weather_integrated_exploratory.csv` (376,272×39) | Yes |
| 15 | feature_engineering | Feature engineering | Build `FE_*` modeling columns | Yield (carried) | none (no model fit) | completeness checks | engineered CSVs (feeds modeling) | Yes |
| 16 | yield_model_development_and_selection | **ML — regression** | Predict Yield; select best model | `Yield` | LinearRegression, Ridge, DecisionTreeRegressor, RandomForestRegressor, **HistGradientBoostingRegressor**, + global-median & crop-season-median baselines | **MAE, RMSE, R²** on chronological windows | **`individual_crop_hgb_location.joblib`** + metadata | Yes |
| 17 | yield_model_deployment_readiness | Governance/QA | Load artifact, smoke-test contract | — | none (loads nb16 model) | 12-point readiness checklist | readiness report JSON | Yes |
| 18 | crop_recommendation | **ML-adjacent — ranking** | Rank candidate crops by predicted yield | `Yield` (predicted) | Reuses nb16 HGB; classifier imports (Logistic, DT, RF, Dummy) exercised as auxiliary experiments | **Top-1 79.20%, Top-3 99.83%, Spearman 0.792** on 2,365 groups (2023–24) | CSV/JSON only — **no new model artifact** | Yes |
| 19 | weather_intelligence | Descriptive + **weak classifier** | Weather summaries; test if weather predicts low yield | binary low-yield (<80% of prior median) | **HistGradientBoostingClassifier, LogisticRegression, RandomForestClassifier**, `TimeSeriesSplit` | **ROC-AUC 0.595/0.617; PR-AUC ~0.16–0.18; Brier worse than constant baseline** | evaluation JSON + reference CSVs — **classifier NOT saved** | Inputs yes; model artifact absent |
| 20 | agricultural_risk_intelligence | Descriptive/rule-based | Flag historical yield anomalies | risk categories | **none** (thresholds on Yield/historical-median) | counts only | `yield_risk_indicators.csv` + metadata (no model) | Yes |
| 21 | model_explainability_and_scenarios | Explainability | Explain the nb16 model | — | `permutation_importance` on loaded HGB (no retraining) | MAE 424.03 / RMSE 601.16 / **R² 0.7775** (3,000-row 2021–22 sample) | explainability JSON/CSVs | Yes |
| 22 | model_registry_and_policy_outputs | Governance | Registry + policy of all components | — | none | status consolidation | `model_registry.csv`, policy/validation JSONs | Yes |

**Verified negatives (no ML fitting):** 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 20, 22.
**The only notebook that saves a loadable model artifact:** **16**.
**The only notebook that trains additional models for evaluation (artifact not saved):** **19** (and 18's auxiliary classifier experiments).

---

## 3. Dataset Inventory

All row counts are data rows (excluding header), measured without full loads.

| Dataset | Format | Rows × Cols | Temporal | Geographic | Target / features | Quality notes | Task support |
|---|---|---|---|---|---|---|---|
| `data/processed/historical_food_grains_apy_long_2013-14_to_2024-25.csv` | CSV (long) | 376,272 × 13 | 12 ag-yr 2013-14→2024-25 | 34 states, 748 districts, 19 crop categories | Target `Yield`; Area/Production; QC flags | Missingness ~33%→~19% over years; zeros ≠ missing; aggregate-vs-individual crops must be separated | Regression, ranking, descriptive |
| `data/processed/weather_regional/apy_weather_integrated_exploratory.csv` | CSV | 376,272 × 39 | same 12 ag-yrs | 34 states / 748 districts; weather present for 640 geographies | `Yield` + 10 weather columns (`tmin/tmax mean/min/max`, `precipitation_total/mean/max`, `*_valid_days`) | Weather is **annual proxy** (`weather_proxy_calendar_year`, `weather_alignment_method`, `weather_full_season_alignment_verified=false`); grid-representative, not station | The modeling frame for nb16/18/19/20 |
| `data/processed/weather_regional/district_weather_annual_cleaned_flagged_2013_2024.csv` | CSV | 7,680 × 29 | **annual** 2013–2024 | **640 geographies** (1 row each × 12 yr) | Weather vars + lat/lon + nearest-grid distance | Only 640 districts × 12 yr; annual resolution | Time series (n≈640), descriptive |
| `models/weather_intelligence/district_weather_reference.csv` | CSV | 751 × 14 | historical percentiles | 751 districts | Median/p10/p90 of tmin/tmax/precip + coverage | 640 with data, 111 without | Lookup/reference only |
| `models/agricultural_risk_intelligence/yield_risk_indicators.csv` | CSV | 69,693 × 46 | 2013–2024 | district×crop×season | Integrated frame + `historical_median_yield`, `yield_to_baseline_ratio`, `yield_risk_indicator` | Derived, not raw | Descriptive risk |
| Raw APY DES files (`data/raw/DES-District-Data-*`), raw weather pilot (10 geographies), mandi prices, district boundaries | CSV/geo | — | 2013-14→2024-25 | India-wide | source for nb02/03 | Mandi prices present but **not used** in any model | — |

**Data NOT present (gaps limiting prediction):** soil pH/NPK/moisture, irrigation, farm-gate input costs (profitability), true seasonal (Kharif/Rabi-window) weather, daily weather at district level. Mandi prices exist on disk but were never integrated into any model.

---

## 4. Model Artifact Inventory

| Artifact | Type / algorithm | Training | Schema | Saved metrics | Loaded by backend? | Classification |
|---|---|---|---|---|---|---|
| `models/yield_prediction/individual_crop_hgb_location.joblib` | HistGradientBoostingRegressor pipeline (OneHot categorical + `FE_YearStart` numeric) | 35,784 rows, **2013–2022**, target `Yield` | `Crop, Season, Crop_Category, State, District, FE_YearStart` | `validation_metrics`: 2019-20 MAE 448.3 / RMSE 673.0 / R² 0.798 ; 2021-22 MAE 422.9 / RMSE 898.2 / R² 0.693 | **Yes** — `yield_prediction.py` joblib.load | **READY FOR REUSE** (with caveats) |
| `.../individual_crop_hgb_location_metadata.json` | feature contract + limitations | — | 5 categorical + 1 numeric | same as above | Yes (contract check) | Governance |
| `.../yield_model_deployment_readiness_report.json` | QA report | — | — | verdict **CONDITIONALLY READY FOR INTEGRATION**; missing Crop/Year not rejected; unseen-category reliability unverified | registry | Governance |
| `models/crop_recommendation/*` | **No model file** — ranking CSV/JSON produced by reusing the yield HGB | 2023–24 eval | — | Top-1 79.2%, Top-3 99.8%, Spearman 0.792 | ranking recomputed live by backend | **FEASIBLE WITH ADDITIONAL WORK** |
| Weather low-yield classifier | HistGradientBoosting/Logistic/RandomForest **Classifier** (fit in nb19) | 2015–2022 train, 2023–24 test | weather + location | ROC-AUC 0.595–0.617; PR-AUC 0.165–0.180; **Brier worse than constant**; `weather_added_predictive_value=false`; `deployment_status=NOT READY` | **Only the evaluation JSON is read** (`weather_data.py:1145`) — **classifier itself was never saved** | **RESEARCH ONLY** |
| Risk indicators (`yield_risk_indicators.csv`) | Heuristic thresholds (not a model) | — | — | counts only | metadata read by `agricultural_risk.py` | **RESEARCH ONLY** |

**Loading compatibility:** the only `.joblib` is the yield HGB. Reproducible reload was verified in nb16/nb17 (artifact loads, produces finite deterministic predictions). **Prediction equivalence vs the original in-memory model was NOT verified** (nb16 audit flag) and the training scikit-learn version pin is not documented — a real compatibility risk for reuse.

**API-key note:** the backend `.env` contained an LLM provider key. It is intentionally **not reproduced** here.

---

## 5. Four-Module Predictive Feasibility Assessment

### A. Yield Prediction — `READY FOR REUSE` (as interpolation) / `FEASIBLE WITH ADDITIONAL WORK` (as forecast)
- **Reusable?** Yes — one loadable HGB artifact, valid feature contract, served by the backend.
- **What it predicts / from what:** expected `Yield` for a `Crop×Season×Category×State×District×Year` row.
- **Feature-based or forecast?** **Feature-based interpolation** over observed district-crop-season combos. The temporal signal is only a single `FE_YearStart` integer, so out-of-2013–2022 years are **extrapolations, not validated forecasts**. Weather features were **excluded** from the selected model because they didn't consistently help once location was included.
- **Work needed for credible future prediction:** true lagged/agronomic features (seasonal weather, sowing dates, soil/irrigation), a pristine untouched holdout on later years, unit/target validation vs the Production÷Area ratio (median discrepancy 2.78%, 90th-pct 29.9%), unseen-category reliability, and a pinned scikit-learn version.

### B. Crop Intelligence — `FEASIBLE WITH ADDITIONAL WORK`
- **Can it rank top-5 yield candidates per district-season?** **Yes, as a yield-ranking** — exactly what nb18 does by scoring eligible historical candidates with the yield model (retrospective Top-1 79.2% / Spearman 0.792). Only 13 crops are represented in projections and Rice/Maize/Wheat ≈ 92.4% of top ranks, so real candidate diversity is thin.
- **Exact features/target:** same 6 features as A; target `Yield`.
- **Modeling approach:** current **shared/unified regressor + per-croup ranking** is reasonable and already implemented. Crop-wise models would need more per-crop data; the bigger change is adding a suitability/economic objective.
- **Critical distinction:** this is **yield ranking, not crop suitability and not profitability** (stated explicitly in evaluation JSON). Profitability would require input-cost/price data (Mandi prices exist but are unused). A genuine "top-5 recommendation" must be reframed as "top-5 expected-yield among historically-grown candidates."

### C. Weather Intelligence — `NOT CURRENTLY FEASIBLE` (forecasting) / `RESEARCH ONLY` (classification)
- **Actual resolution:** **annual**, district = **nearest weather grid-point representative** (lat/lon distance + `geography_confidence`), joined to APY by a **calendar-year proxy** (`weather_full_season_alignment_verified=false`). Only **640 districts × 12 years**.
- **Forecasting feasibility:** **No.** 12 annual points per geography (n≈640 series, 12 steps each) cannot support daily, monthly, or even reliable seasonal forecasting. **Do not build daily forecasting** — the data cannot support it.
- **The trained classifier** (low-yield binary) is real but **weak and not saved**: ROC-AUC ≈ 0.60, PR-AUC ≈ 0.17, Brier worse than constant baseline, and weather **did not improve** held-out metrics. Class balance: event rate ~14.5% train / ~13.0% test (imbalanced). Leakage risk: target uses prior-season median (must never leak current yield).
- **To make weather genuinely predictive:** obtain **seasonal-window, district-level** weather (or daily gridded aggregated per season), align to actual Kharif/Rabi windows, then evaluate forecasting/risk models with strict chronological CV.

### D. Agricultural Risk — `RESEARCH ONLY` (transparent index) / `REQUIRES ADDITIONAL DATA` (supervised risk model)
- **Available indicators:** heuristic categories from `Yield vs historical median` (high <70%, moderate 70–85%, within 85–115%, above >115–5×, extreme outside 0.1–5×) with persistence counts. High-concern obs: 5,877; combos ≥3 high-concern years: 488.
- **Transparent risk index?** Yes — a **rule-based index is constructible and defensible** (already largely exists). It is descriptive, not a calibrated probability.
- **Supervised risk classifier?** Weak with current data: the only such attempt (nb19) underperformed a constant baseline; labels are self-derived from yield (leakage-prone), imbalanced, and the "risk" definition has no external disaster/loss ground truth.
- **Leakage/imbalance/validation problems:** target derived from the same yield distribution used to build features; no true-outcome (crop-insurance payout, declared loss) labels; ~13% positive rate; annual calendar-year weather proxy misaligned to seasons; holdout contamination risk.

---

## 6. INT234 Syllabus Coverage Matrix

Labels: **IE** = Implemented & Evaluated · **IP** = Implemented but not adequately evaluated · **NI** = Not implemented · **NV** = Not verifiable.

| Syllabus topic | Status | Evidence |
|---|---|---|
| Data preprocessing & EDA | **IE** | nb02–15 (wide→long, QC flags, missingness, integration, correlation) |
| Linear regression | **IE** | nb16 `LinearRegression`, MAE/RMSE/R² |
| Multiple regression | **IE** | nb16 features >1 (linear/Ridge are multivariate) |
| Polynomial regression | **NI** | no `PolynomialFeatures` anywhere |
| Logistic regression | **IE** | nb19 Logistic classifier w/ ROC-AUC/PR-AUC/Brier; nb18 auxiliary |
| KNN | **NI** | no `KNeighbors*` |
| Naive Bayes | **NI** | no `*NB` |
| Decision trees | **IE** | nb16 Regressor + nb18/19 Classifier |
| SVM | **NI** | no `SVC/SVR` |
| KMeans | **NI** | no `KMeans` |
| Hierarchical clustering | **NI** | no `Agglomerative*/Silhouette` |
| Association rule mining | **NI** | no `mlxtend/apriori/fpgrowth` |
| PCA | **NI** | no `sklearn.decomposition/PCA` |
| Feedforward NN / MLP | **NI** | no `MLPRegressor/MLPClassifier` or any NN framework |
| Model evaluation | **IE** | MAE/RMSE/R², ROC-AUC/PR-AUC/Brier/confusion, Top-k/Spearman, `TimeSeriesSplit`, baselines |
| Bagging | **IE** | `RandomForestRegressor/Classifier` (nb16/18/19) |
| Boosting | **IE** | `HistGradientBoostingRegressor` (chosen) + `HistGradientBoostingClassifier` (nb16/19) |
| Random Forest | **IE** | nb16 regression, nb18/19 classification |

No algorithms were added to satisfy the syllabus; the NI rows are genuine absences verified across all 22 notebooks.

---

## 7. Data Gaps and Technical Risks

1. **Only one persisted model.** Everything else is recomputed, heuristic, or unsaved — losing nb16 would lose the project's sole artifact.
2. **No feature-based yield drivers.** Selected yield model excludes weather; no soil/irrigation/cost inputs. Predictions are essentially "learned historical averages by crop×place (+year trend)."
3. **Weather granularity mismatch.** Annual, grid-representative, calendar-year-proxied, 640/748 districts. Blocks seasonal/daily modeling and causal weather-yield claims.
4. **Forecast ≠ interpolation.** "2025" outputs are extrapolations beyond 2013–2022 training; not validated future forecasts.
5. **Target integrity.** APY `Yield` vs `Production÷Area×1000` median discrepancy 2.78% (90th pct 29.9%); official units unverified; zero-vs-missing and aggregate-crop double-count risks.
6. **Evaluation hygiene.** Final holdout repeatedly inspected (nb16); some metrics (nb21) are sample-specific, not independent validation.
7. **Weak/absent classification signal.** Weather classifier worse-than-baseline on Brier and not saved; risk "classification" is thresholded, not learned.
8. **Reproducibility/version risk.** No pinned scikit-learn version in metadata; in-memory↔saved prediction equivalence unverified; unseen-category reliability unverified.
9. **Unused available data.** Mandi prices present but never modeled; district boundaries unused.

---

## 8. Recommended Model Development Roadmap

| Priority | Action | Data/evidence basis | Classification |
|---|---|---|---|
| 1 | **Consolidate yield model as reusable service artifact** (pin sklearn version, add unit bounds, required-field rejection, persist training snapshot) | nb16/17 artifacts + readiness report gaps (`missing_crop_rejected=false`) | READY FOR REUSE |
| 2 | **Add real feature-based yield predictors**: season-aligned weather (from raw daily grids), and integrate the **unused Mandi prices** for an economic target | nb03 daily pilot exists; integrated file is only annual; `data/raw/mandi_prices/*` unused | FEASIBLE WITH ADDITIONAL WORK |
| 3 | **Rebuild weather data to seasonal/daily district aggregates** (aggregate daily grids into Kharif/Rabi windows; extend 640→748 coverage) | annual frame + `weather_full_season_alignment_verified=false` | REQUIRES ADDITIONAL DATA |
| 4 | **Crop recommendation → explicit yield-only product wording**, or add profitability model once cost/price features land | nb18 eval interpretation ("not profitability/suitability") | FEASIBLE WITH ADDITIONAL WORK |
| 5 | **Risk: keep transparent rule-based index** now; pursue supervised risk only after external loss/payout labels exist | nb20 metadata + nb19 NOT READY | RESEARCH ONLY → REQUIRES ADDITIONAL DATA |
| 6 | **Establish a pristine chronological holdout** (e.g., train ≤2022, test 2023–25 once) and re-benchmark all yield models against it | nb16 holdout-contamination limitation | FEASIBLE WITH ADDITIONAL WORK |
| 7 | **Fill syllabus breadth only if academically required** (KNN/NB/SVM/KMeans/PCA/MLP/association) on the integrated frame — do not claim them as existing work | Section 6 NI rows | FEASIBLE WITH ADDITIONAL WORK |

**Weather forecasting specifically:** **NOT CURRENTLY FEASIBLE** at daily/monthly resolution with present data. Reassess only after step 3 delivers finer temporal data.

---

## 9. Recommended Implementation Order

1. **Yield (stabilize first)** — persist, version-pin, and add input-contract validation + agronomic output bounds. It is the only working model and everything downstream reuses it.
2. **Crop Intelligence (reframe + extend)** — lock it as a yield-ranking product now; layer profitability only after price/cost features are added.
3. **Weather data upgrade (enabler)** — build seasonal/daily district weather and coverage backfill; this is the single highest-leverage data investment because it unlocks credible yield features, honest risk, and any future forecasting.
4. **Risk (index now, learn later)** — ship the transparent heuristic index; defer supervised risk until true outcome labels exist.
5. **Re-evaluate forecasting** — only after (3), decide whether any weather forecast is defensible.

---

### Final Response

- **Report location:** `C:\Users\gsr58\Desktop\Projects\BharatCrop-Intelligence\reports\phase1_predictive_feasibility_audit.md`
- **Strongest existing ML work:** the notebook-16 `HistGradientBoostingRegressor` yield model — time-aware validated (R² 0.798 / 0.693 across 2019–22 windows; explainability sample R² 0.778), saved as a joblib artifact with a documented feature contract, and the only model the backend actually loads.
- **Biggest gaps preventing genuine prediction:** no true feature-based yield drivers (weather excluded; no soil/irrigation/costs); weather is annual + calendar-year-proxied over only 640 districts, so forecasting is unsupported; "future" outputs are extrapolations; the holdout was contaminated and APY units/target consistency are unverified.
- **Proposed development order (4 modules):** Yield → Crop Intelligence → Weather (data upgrade first) → Risk (transparent index now, supervised later).
- **No project files were modified.** This task was read-only inspection plus a single new report file at the path above; no notebooks/datasets/models/code/env were changed, executed, retrained, or moved, and no Git operations were performed.
