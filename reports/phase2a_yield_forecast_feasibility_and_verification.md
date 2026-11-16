# BharatCrop Intelligence — Yield Prediction Phase 2A: Forecast Feasibility & Model Verification

**Type:** Investigation + technical design. READ-ONLY. No notebook, dataset, model artifact, metadata, backend/frontend source, or environment file was modified. No model was retrained. No dependency was changed. No Git operation was performed. One new report file was written (this file).

**Evidence base:** Notebook 16 (code+markdown, outputs ignored), the saved `.joblib` artifact loaded read-only in the runtime venv, `individual_crop_hgb_location_metadata.json`, the deployment-readiness report, the backend inference module, the yield API route, and the frontend yield form/validation.

---

## 0. Bottom Line Up Front

- **Manual yield estimation (Mode A)** already works end-to-end, is correctly schema-matched, and is safe to ship with better labeling. **READY FOR IMPLEMENTATION.**
- **Genuine 5-year forecasting (Mode B)** is **not supported by current data or the current model.** The saved model is a location/season memorizer with a single linear `FE_YearStart`; gradient-boosted trees cannot extrapolate a year trend, and there are only 12 annual APY years with no future ground truth. **NOT CURRENTLY FEASIBLE / REQUIRES ADDITIONAL DATA** for horizons ≥3 years; at best **READY AFTER MODEL RE-EVALUATION** for short-horizon (1–2 yr) per-series trends on supported combinations.

---

## Part 1 — Existing Model Verification

All values below were verified against the actual artifact, not just its documentation.

| Item | Verified value | Evidence |
|---|---|---|
| Model object | `Pipeline(preprocessor=ColumnTransformer, model=HistGradientBoostingRegressor)` | loaded `individual_crop_hgb_location.joblib` read-only |
| Estimator params | `max_iter=200, learning_rate=0.08, max_leaf_nodes=31, l2_regularization=1.0, random_state=42` | artifact `get_params()`; nb16 Cell 71 (txt:4796) |
| Target | `Yield` | metadata `target`; nb16 `y_train = Yield` |
| Unit | **kg/ha**, `target_conversion_applied=False` | `yield_prediction.py:27,424,428`; route:107–116 |
| Feature order | `Crop, Season, Crop_Category, State, District, FE_YearStart` | artifact `feature_names_in_` == metadata `features` (verified `True`) |
| Categorical encoding | OneHotEncoder, `handle_unknown="ignore"`, `sparse_output=False` | artifact encoder attribute; nb16 txt:466,471 |
| Learned cardinalities | Crop=13, Season=3, Crop_Category=1, State=32, District=622 | artifact `categorical.categories_` |
| Numeric feature | `FE_YearStart` (passthrough, **not scaled**) | nb16 Cell 71 txt:4787 |
| Training period / rows | 2013–2022; 35,784 rows | metadata; nb16 summary |
| Holdout period | 2023–24 (assert `FE_YearStart ⊆ {2023,2024}`) | nb16 txt:3319 |
| Preprocessing/missing | Cohort filtered to positive finite Area/Production/Yield; asserts reject NaN in features; no imputer in the final pipeline (unlike weather models) | nb16 txt:4755–4759; Cell 71 |
| Weather / Area / Production as inputs | **Excluded** from the saved model (nb16 md: "weather features were excluded") | artifact schema has no weather columns |
| Prediction clipping | **None** — raw regression output | grep: no `clip`/`max(0)` in `yield_prediction.py` or route; only a `math.isfinite` check (`yield_prediction.py:519`) |
| Target transform | **None** | route `numerical_conversion_applied=False` |
| Unseen-category handling | Encoder yields an all-zero vector for unknowns (**silent**), but the **backend rejects unsupported combinations** with 422 before inference | nb16 txt:466; `yield_prediction.py:478–505` |
| Metadata ↔ artifact | Feature list matches; `model_version` is **absent** (recorded only as `model_version_not_recorded`) | artifact vs metadata; `YieldMetadata` model_version=None default |
| Backend schema == training schema | `FEATURES`/`CATEGORICAL_FEATURES`/`NUMERIC_FEATURES` equal the artifact exactly | `yield_prediction.py:17–26` |
| Dependency versions | Runtime **sklearn 1.8.0, joblib 1.6.0, numpy 2.5.4, pandas 2.3.3, Python 3.13.5**; pyproject pins `scikit-learn==1.8.0`. Artifact loads without warning. | import check + `pyproject.toml` |
| Integrity | artifact sha256 `dc057a8c…34dce7` matches `DEFAULT_YIELD_ARTIFACT_SHA256` | artifact hash vs `config.py` |

**Target/unit consistency findings:**
- Unit documentation cites **MoSPI Compendium 2024 §4.10.5** (`YIELD_UNIT_SOURCE`, `yield_prediction.py:28–35`). The backend treats this as `target_unit_status="verified"`, but Notebook 16's own audit flags **"official APY measurement units remain unverified"** (`production_readiness_established: False`). This is a **documentation-vs-evidence discrepancy** — treated here as *Potential risk*, not confirmed error.
- Internal consistency (nb16 §6 / `YIELD_CONSISTENCY_CHECK`): reported `Yield` vs `Production/Area×1000` — median ratio ≈ 1.0, ~71.3% within 10%, but **median relative difference ≈ 2.78% and 90th percentile ≈ 29.9%**, with row-level deviations. Units are therefore **not proven consistent across states, districts, crops, and years.** Some APY values appear rounded or reported differently by crop.
- **Cross-year leakage check:** `FE_YearStart` is the only temporal signal; the model uses it as a plain integer with no lags. No feature contains a same-period target (Area/Production/Yield are excluded), so **no direct target leakage in the saved model** — *Verified safe*.

---

## Part 2 — Evaluation-Contamination Investigation

Notebook 16 uses three distinct evaluation concepts that are easy to conflate. The **published metrics (R² 0.798 / 0.693)** come from **rolling-origin temporal validation** (nb16 Cell 57, txt:3948–3954), **not** from the final 2023–24 holdout. Window A trains on `FE_YearStart ≤ 2018` and tests on 2019–20 (R² 0.798, MAE 448.3, RMSE 673.0). Window B trains `≤ 2020` and tests 2021–22 (R² 0.693, MAE 422.9, RMSE 898.2).

| # | Concern | Classification | Evidence |
|---|---|---|---|
| 1 | Preprocessing fit on training-only, before scoring holdout | **Verified safe** | Pipeline fits `core_encoder` on `*_train` (txt:4022, 533); holdout only via `.transform`/`.predict` |
| 2 | Feature selection / hyperparameters tuned on holdout | **Verified safe** | fixed `HGB` params everywhere; no `GridSearchCV`/`RandomizedSearchCV` in any notebook (Phase-1 scan) |
| 3 | Duplicate/overlapping **observations** across train/test | **Verified safe** | `FE_YearStart` disjoint across cohorts (txt:4760–4762); train-year < test-year |
| 4 | Same district/crop/season entity recurring across years | **Potential risk** | entity effects (District 622, State 32, Crop 13) appear in every year; metrics measure in-period interpolation for *known* entities, not generalization to unseen locations. nb16 §8: "unseen-location validation samples were small." |
| 5 | Features unavailable at prediction time | **Confirmed defect for forecasting** | validation models used `weather_features` (txt:3958) — retrospective annual proxies that cannot be produced for a future season |
| 6 | Final holdout (2023–24) repeatedly inspected | **Confirmed defect (scope-limited)** | nb16 md §8 + audit flag; this taints the *untouched-holdout claim for 2023–24*, NOT the 2019–22 rolling metrics |
| 7 | Published metrics describe a **different model spec** than the saved artifact | **Confirmed defect (documentation)** | rolling windows used `Core + Weather + State + District` (txt:4004); the **saved** model is `Crop/Season/Category/State/District + FE_YearStart` **without weather**. So 0.798/0.693 are **not** measured on the served model. |
| 8 | Selection bias (best-of-many variants on the same windows) | **Potential risk** | many models compared on the same 2019–22 windows before selection; reported figures are optimistic relative to a single frozen candidate |
| 9 | Year-based model bias at deployment | **Potential risk** | `FE_YearStart` passthrough + tree model ⇒ out-of-range years (2023+) are extrapolations with unmeasurable bias |

**Are R² 0.798 / 0.693 trustworthy?**
- **Yes, but narrowly:** as **within-training-period, chronological, interpolation performance for a weather-inclusive model on known districts/crops.** The split methodology is legitimate (temporal, train-only preprocessing).
- **No, for two uses that matter to this product:** (a) they are **not** performance of the served (weather-free) artifact; (b) they are **not** future-forecast accuracy and must not be presented as such. Do not recalculate or republish them as forecast quality.

---

## Part 3 — Manual Prediction Mode (Design)

This mode **already exists and is preserved.** Verified path: frontend `yield-page.tsx` (form + client guard replicating `isYieldOptions`) → `POST /api/v1/predictions/yield` → `YieldPredictionService.predict` → `Pipeline.predict` → kg/ha, with `prediction_period_status` = `in_training_range` vs `out_of_training_range_extrapolation`.

**Exactly-supported fields (do not add soil/irrigation/rainfall/fertilizer/price — the model has none):**

| Control | Source of options | Validation | Default |
|---|---|---|---|
| Crop | 13 model categories | must be in supported set | none |
| Season | 3 categories | `total` rejected (`yield_prediction.py:77–82`) | none |
| Crop_Category | **1 value** (`Individual Crop Candidate`) | fixed | auto-select, hide or grey out |
| State | model categories (32) ∩ training pairs | cascading parent | none |
| District | `districts_by_state[state]` | cascading child; reject cross-state | none |
| Year | `FE_YearStart: StrictInt ≥ 1` | integer; **no max enforced** | training `year_end` (2022) |

**Recommendations:**
- Keep **cascading state→district** and **combination-level validation** (already implemented via `supported_combinations`, `yield_prediction.py:498–505`) — this is what prevents the silent all-zero-encode failure mode of `handle_unknown="ignore"`.
- Because the served model has **only one** crop-category and **13** crops, restrict inputs to those; anything else should return 422, not a number.
- **Label the result as a model estimate**, explicitly: "not a guarantee of actual yield; experimental; years beyond 2013–2022 are extrapolations." The API already returns `quality_status="experimental"`, `production_approved=false`, and `limitations[]` — surface all of them.
- Consider a **non-negative sanity floor with a visible warning** (not a silent clip): since predictions are unclipped, a negative or implausibly large value should be flagged to the user as out-of-support rather than displayed as-is.

---

## Part 4 — Five-Year Projection Feasibility

Data reality that constrains everything: APY has **12 annual years (2013–2024)**, 34 states / 748 district labels (622 with usable model categories), target = reported Yield, and **no** soil/irrigation/price/future-weather features. Weather on disk is **annual, nearest-grid, calendar-year-proxied** (`weather_full_season_alignment_verified=false`) — i.e. **retrospective**, not forecastable ahead.

### Approach A — Existing HGB with future `FE_YearStart`
- **Inputs:** the 6 existing features; set Year = now+1…+5.
- **Data exists?** Yes — it runs today.
- **Candidates:** the current pipeline (no change).
- **Validation:** would require future ground truth we do not have.
- **Leakage:** none at inference, but **`FE_YearStart` is a monotone index the trees cannot extrapolate** — beyond 2022 predictions flatten toward leaf means; any apparent trend is spurious.
- **Strength:** zero new engineering. **Limitation:** not a forecast; **cannot credibly support any horizon** beyond the training range without revalidation. The backend already correctly labels these as `out_of_training_range_extrapolation`.
- **5-year support:** **No.**

### Approach B — Time-series forecasting of Yield by Crop×District×Season
- **Inputs:** historical Yield panel (exists); per-series targets.
- **Data exists?** Partially. Per district-crop-season series are at most **12 points** and often sparse/gappy due to the 33%→19% missingness; many combinations have < 5 usable years.
- **Candidates:** ETS/ARIMA (`statsmodels`), seasonal-naive, linear trend, Prophet.
- **Validation:** rolling-origin backtest per series; must aggregate and report by crop/state/district/horizon.
- **Leakage:** risk of using same-year or revised APY values; must lag inputs strictly behind the forecast origin.
- **Strength:** gives an honest trend + uncertainty for well-populated series. **Limitation:** short series, no strong covariates, unreliable at long horizon.
- **5-year support:** **1–2 years plausible for supported, data-rich combinations; 3–5 years NOT feasible.**

### Approach C — Hybrid (historical yield + weather + verified predictors)
- **Inputs:** would need **season-aligned, district-level** weather that is itself forecastable, plus soil/irrigation/price features.
- **Data exists?** **No.** Weather is annual retrospective proxy only; soil/irrigation/price are absent from the model (and Mandi prices, though present on disk, were never integrated/validated).
- **Candidates:** gradient boosting / two-stage (climate-downscale → yield), or hierarchical Bayesian.
- **Validation:** requires future weather covariates that don't exist.
- **5-year support:** **REQUIRES ADDITIONAL DATA — not currently feasible.**

**Verdict across the four modules:** A = not real forecasting; B = feasible only for short horizons on rich series after re-evaluation; C = blocked on data. No current approach credibly delivers 3–5-year validated forecasts.

---

## Part 5 — Required Forecasting Evaluation (Backtest Design)

**Framework: expanding-window rolling-origin backtest** that simulates true production forecasts.
1. For each **forecast origin** `T`, fit **only** on years `< T − h` … predict year `T` at horizon `h` (h = 1..5). Never fit on ≥ `T`.
2. Repeat for every origin where the training history reaches a minimum (recommend ≥ 5 prior years).
3. **Score each horizon separately** (do not average horizons).

**Metrics:** MAE, RMSE, **Bias (mean signed error)**, and R² (R² can be negative — report it honestly). **Baselines required for every cell:** (a) previous-year yield, (b) trailing-3-year mean of the series, (c) global/crop×season median. A forecast earns the label "validated" only if it **beats these baselines out-of-sample by a clear margin**.

**Breakouts:** per horizon, per crop, per state, per district-cluster (avoid tiny cells), and seen-vs-unseen district.

**Coverage-driven horizon cap:** with only 12 years and 2013–2022 training, a **5-year-ahead** point has essentially no clean held-out future: an origin `T` needs training through `T−5`, so with the latest ground truth 2024 there is ~**1 observable origin** for h=5. **Therefore 5-year-ahead validation is impossible with current history** — the maximum honestly-backtestable horizon today is roughly **1–2 years**, and even that must be qualified by the weather-vs-saved-spec gap (Part 2 #7) and the fact that a genuine retrain would be needed.

**Minimum evidence before calling a forecast "validated":**
- Backtest MAE/RMSE/Bias vs baselines on **strictly earlier** data, per horizon;
- documented, version-pinned artifact;
- no use of retrospective/unavailable features at inference;
- uncertainty produced by a validated method (residual quantiles or conformal intervals), not hand-drawn bands.

---

## Part 6 — Product Design Recommendation

Single Yield page, **two clearly separated modes** (radio/tab switch). Both reuse the existing `/options` + `/predictions/yield` contract already served by the backend and mirrored in `yield-page.tsx`.

**Mode A — Manual Yield Estimation** *(READY — implement/label)*
- Selectors: Crop, Season, State → District (cascading, as today), Crop_Category fixed to the single supported value, Year.
- Output: estimated yield **kg/ha**, plus **model version** (`not_recorded` until a version is stored), **supported data range (2013–2022)**, and caveats.
- If Year > 2022 → show the returned `out_of_training_range_extrapolation` label inline.
- Guard: reject/flag negative or out-of-range outputs (do not silently clip).

**Mode B — Future Yield Projection** *(gate behind re-evaluation; cap at supported horizons)*
- Selectors: Crop, Season, State, District; horizon selector 1–5.
- Display a **combined chart**: **historical observations as points/line (2013–2024 actual)**; **projections as a dashed continuation**; **unsupported horizons and unsupported district-crop-season combinations clearly greyed with a reason** ("insufficient series length", "combination not in model support", "horizon beyond validated range").
- Show **uncertainty bands only when** they come from the Part-5 backtest (residual/conformal). Until then, show point estimates labelled *indicative, not validated*.
- Never imply a guarantee; carry `experimental / production_approved=false`.

**Recommended visual:** one time-series panel — solid line + markers = APY actual; dashed line = projection; shaded band = validated uncertainty (if any); a vertical "training cutoff" marker separating observed from extrapolated region.

**Interim product stance:** launch **Mode A now**. For Mode B, present only the **1–2-year per-series trend** (Approach B) clearly marked *indicative*, and **explicitly withhold** 3–5-year projections until re-evaluation and data upgrades. Do **not** expose Approach A (HGB with future year) as a "forecast."

---

## Part 7 — Technical Findings & Decision

**9. Exact implementation sequence (design — not yet executed):**
1. **Freeze Mode A.** Verify the served model equals the artifact (done); add a stored `model_version` to metadata and a non-negative/plausibility guard on outputs.
2. **Retitle current extrapolation behavior** as "indicative estimate," never "forecast."
3. **Build a backtest harness** (Part 5) on `apy_weather_integrated_exploratory.csv` for Approach B baselines; publish per-horizon MAE/RMSE/Bias vs baselines for supported series only.
4. **Ship Mode B at h=1–2** for combinations passing the baseline-beat test; keep h=3–5 disabled with a stated reason.
5. **Request data upgrades** (below) before any 3–5-year or feature-based forecast claim.

**8. Required data upgrades:** season-aligned **forecastable** weather (or daily gridded → seasonal aggregates over Kharif/Rabi windows) and coverage backfill 622→748; soil/irrigation features; validated input-cost/price (Mandi) for profitability; a longer APY history (target ≥ 8–10 prior years per series) to make multi-horizon backtesting meaningful.

**10. Risks / unresolved questions:**
- Published R² 0.798/0.693 are **not** the served model's numbers (weather-inclusive spec) — do not reuse them as forecast accuracy. (Confirmed defect #7.)
- APY **units/target consistency unverified** across states/crops/years; backend label `target_unit_status="verified"` conflicts with nb16's own "units unverified."
- `handle_unknown="ignore"` is safe **only** because the backend rejects unsupported combinations — any future relaxation re-enables silent zero-encode failures.
- `Crop_Category` is a single constant → contributes nothing (permutation importance 0); candidate diversity is thin (13 crops; Rice/Maize/Wheat dominate recommendations).
- No `model_version`, no output clipping, and a minor year-range mismatch (backend builds `supported_combinations` from a 2013–**2024** frame while the model trained through 2022) remain to be tightened.

### Final Decision
- **Mode A — Manual Yield Estimation:** **READY FOR IMPLEMENTATION** (preserve current behavior; add labeling, a stored model version, and an output sanity guard).
- **Mode B — Future Yield Projection:**
  - h = 1–2 years, supported data-rich combinations: **READY AFTER MODEL RE-EVALUATION** (requires the Part-5 backtest and an Approach-B retrain; must beat baselines).
  - h = 3–5 years: **NOT CURRENTLY FEASIBLE** with existing history, and a covariate-based version is **REQUIRES ADDITIONAL DATA**.

Overall phase verdict: **READY FOR IMPLEMENTATION of Mode A; NOT CURRENTLY FEASIBLE for credible 5-year forecasting (Mode B) without the stated re-evaluation and data upgrades.**
