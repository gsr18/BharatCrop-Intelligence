# Phase 2C — Future Yield Forecasting Research Report

**Status:** Research & model evaluation only. **No production API, frontend, model artifact,
notebook, or dataset was created or modified by this phase.** All code and outputs live under
`phase2c_future_yield_forecasting/` and are read-only against the source data.

**Final decision: `REQUIRES MORE DATA`.** See §11.

Prepared: 2026-11-05 · Author: Qoder CLI · Sibling to (and independent of) Phase 2B
"Manual Prediction Stabilization".

---

## 1. Dataset & temporal coverage audit (Part 1)

Source of truth: `data/processed/historical_food_grains_apy_long_2013-14_to_2024-25.csv`
(376,272 rows, long format: `State, District, Crop, Season, Crop_Category, Year, Area,
Production, Yield` + four QC flags). Full numbers in `artifacts/data_audit.json`.

| Dimension | Value |
|---|---|
| Temporal coverage | **12 annual frames**, YearStart 2013 → 2024 (`2013-14` … `2024-25`) |
| States / Districts / Crops / Seasons | 34 / 748 / 19 / {Kharif, Rabi, Summer, Total} |
| Crop_Category levels | `Individual Crop Candidate` (real crops), `Grouping — Verify Source Definition`, `Aggregate Total — Exclude…` |
| Rows with Yield present / null | 281,239 / 95,033 |
| Negative yields | 0 |
| Max Yield (all) | 385,540 kg/ha — **physically implausible**, all such rows have Area=0 |
| Median / p99 Yield (all) | 1,436 / 6,551 kg/ha |
| Series (State×District×Crop×Season) with valid yield | 31,116 (median 12 obs, max 12) |
| Series with ≥8 obs | 22,219 · ≥5 obs 24,850 · exactly 1 obs 2,372 · 2 obs 1,549 |
| Series with internal year gaps | 5,361 |

**Critical data-quality finding — positive yield without positive area.** Of 90,893
season-specific (`Kharif/Rabi/Summer`) Individual-Crop rows with Yield>0, **38,502 (42%)
have Area ≤ 0** and 37,867 have Production ≤ 0. These are the QC-flagged rows that generate the
extreme yields. Only **49,645 rows are "well-formed"** (Yield, Area, Production all > 0). Two
evaluation cohorts are therefore defined (§6): *well-formed* and *full*.

**Mandi data is not usable for historical forecasting.**
`data/raw/mandi_prices/mandi_prices_2026-10-31.csv` is a **single-date snapshot** (only
`Arrival_Date = 2026-10-31`; `data/processed/mandi_prices/` is empty). It carries no time series,
so it cannot be lagged into a year-ahead target. Its 221 `Commodity` labels also do not align with
APY `Crop` names (e.g. "Paddy (Common)" vs "Rice"), and only 21/34 states and 307/748 districts
match APY names textually. **Decision: mandi prices are excluded from all models** — including
them would inject an un-joinable, non-temporal, differently-named source. Mandi price features for
forecasting would require a **multi-year** mandi extract reconciled to APY crop/geography names.

**Weather**: pilot/regional weather exists only for 2013–2024 as area-level series and was built
for the manual model's contemporaneous use; the forecasting task here deliberately uses **only
lagged yield + verified historical geography** to avoid assuming future weather availability (§2).

---

## 2. Target & prediction-task definition (Part 2)

**Target:** annual APY `Yield` (kg/ha) for a crop–district–season in a future marketing year.
**Unit caveat (inherited from Phase 2B):** the kg/ha designation is *verification pending*; no
per-row unit consistency is proven and no conversion is applied. Forecast accuracy is therefore
reported in the raw source unit.

**Forecast origin rule.** A forecast for target year **Y** at horizon **h** is generated at origin
**O = Y − h** and may use **only observations from years ≤ O**. A record for the origin year must
exist; the target year's actual is used only at scoring time.

- **T+1 (h=1):** uses yield at year ≤ Y−1. Never touches Y.
- **T+2 (h=2):** uses yield at year ≤ Y−2. Never touches Y−1 or Y.
- **T+3/4/5:** analogous (evaluated in §10 for feasibility only).

**Information never used as a feature:** the target-year actual, any year > O (future yield,
future weather, future prices), or the single-date mandi snapshot. Every feature is available at
the origin: `y_origin`, `y_origin_lag1/2` (years O, O−1, O−2), `hist_median/mean/std/n` over years
≤ O, `lag_dev`, `trend_slope` (fit over years ≤ O), and `origin_year`/`target_year` calendar
indices. Geography (`Crop, Season, State, District`) is known at origin. This is the reason each
feature is admissible.

---

## 3. Baseline models (Part 3 — mandatory)

1. **Previous / carry-forward (`b_prev`)** — last observed yield at the origin (y_origin).
2. **Historical group median (`b_median`)** — median of the series' yields over years ≤ O.
3. **Trend (`b_trend`)** — least-squares line over years ≤ O, extrapolated to Y (needs ≥3 pts,
   else falls back to the historical mean).

Baselines are strong and interpretable; any ML model must beat them to justify deployment.

---

## 4. Candidate ML models (Part 4)

Pooled panel regressors sharing the **identical origin-safe feature set**, trained once per
expanding-window fold:

- **Ridge** — standardized numeric lags + one-hot (Crop, Season).
- **Random Forest** — numeric lags + ordinal codes of Crop/Season/State/District.
- **HistGradientBoostingRegressor (HGB)** — numeric lags + native categoricals (Crop, Season,
  State) with District carried as an integer code (native categorical exceeds the 255-cardinality
  limit at 648 districts).

The existing manual `individual_crop_hgb_location` model is **not** reused; it is a
*nowcast* on `FE_YearStart` with no lagged-yield memory and is explicitly out of scope.

---

## 5. Leakage-free validation (Part 5)

**Expanding-window rolling-origin.** For each evaluation target-year *Y* (2017→2024), the model is
trained only on forecast rows with `target_year < Y` and scored on rows with `target_year == Y`;
the window then expands. Horizons are evaluated **independently**. No random split; no tuning on
the final window. Code: `scripts/p02_forecast_pipeline.py`, `scripts/p03_analysis.py`.

**Well-formed cohort — headline results** (60,271 evaluated rows, 5,070 distinct
crop–district–season groups):

| Horizon | Best baseline | Ridge MAE (skill) | RF MAE (skill) | HGB MAE (skill) |
|---|---|---|---|---|
| **T+1** | prev 343 | 338 (1.4%) | **327 (4.7%)** | 330 (4.0%) |
| **T+2** | median 391 | 395 (−1.1%) | 359 (8.0%) | **353 (9.6%)** |

RMSE (T+1): Ridge 534 (best), RF 549, HGB 556 vs baseline prev 599 / median 586.
Mean actual yield ≈ 2,050 kg/ha; **MAE is 15.5–18.8% of the target level**. Bias is near zero for
RF/HGB; Ridge is positively biased (+50/+86); the median baseline is strongly negatively biased
(−145/−172) because it under-predicts upward trends.

**Interpolation vs generalization (decisive).** Splitting the well-formed evaluation into a series'
**first-seen year (cold start)** vs **recurring years**:

| Split | n | median baseline | Ridge | RF | HGB |
|---|---|---|---|---|---|
| Recurring groups | 51,739 | 371 | 351 | **332** | **328** |
| **Cold start (new series)** | 8,532 | **392** | 457 | 411 | 420 |

On recurring crop–district–season series ML beats the baseline by ~10%. On series at their
first-seen year **every ML model loses to a trivial historical median.** The demonstrated skill is
therefore **interpolation to already-observed locations over time, not generalization to unseen
locations.** The evaluation cohorts repeat the same districts across years, which is exactly the
condition the task flagged.

---

## 6. Data quality & robustness (Part 6)

Full (un-filtered, includes positive-yield-zero-area rows) cohort, 112,485 rows, 9,596 groups:

| Horizon | Best baseline | Ridge | RF | HGB |
|---|---|---|---|---|
| T+1 | prev 318 | **−2.6%** | 2.9% | 1.6% |
| T+2 | median | ~−4% | ~+2% | ~+2% |

On the dirtier full cohort the ML advantage **collapses to ~1–3% and Ridge goes negative**;
**HGB emitted 11 negative predictions**, confirming the Phase 2B need for output sanity guards
(never silently clamp; reject and log). Negative predictions were 0 on the well-formed cohort and
0 for Ridge/RF everywhere.

- **Extremes:** all implausible yields (>12,000; max 385,540) coincide with Area=0. The 12,000
  kg/ha robustness cap removes 9 well-formed rows — negligible coverage impact.
- **Missing / gaps:** 5,361 series have internal year gaps; the origin rule handles them (a row is
  only built when a true origin observation exists). No fabricated points.
- **Imbalance:** `Individual Crop Candidate` = 18,663 series; `Grouping` 8,951; `Aggregate` 3,502.
  Aggregates/Total seasons are excluded (double counting). Rice/Wheat dominate the crop mix.
- **Filtering impact, disclosed:** well-formed filtering drops ~45% of positive-yield rows
  (90,893 → 49,645 obs; 31,116 → 5,070 evaluable recurring groups). Difficult (thin/dirty) groups
  are **not silently deleted to flatter metrics** — they are reported separately as the *full*
  cohort above, where models fail to add value.

---

## 7. Longer-horizon feasibility (Part 7)

Rolling-origin origins were computed honestly (`reports/longer_horizon_evaluation.json`,
`reports/metrics_analysis.json` → `feasibility`):

| Horizon | valid eval years | max series history | best ML MAE | best-baseline MAE | apparent "skill" |
|---|---|---|---|---|---|
| T+1 | 8 | 11 | 327 | 343 | 4.7% |
| T+2 | 7 | 10 | 353 | 391 | 9.6% |
| T+3 | 6 | 9 | 368 | 417 | 11.7% |
| T+4 | 5 | 8 | 369 | 439 | 15.9% |
| T+5 | 4 | 7 | 372 | 466 | 20.3% |

**The rising "skill" at T+3…T+5 is an artifact of baseline decay, not better forecasts.** Absolute
ML MAE stays ~368–372 kg/ha across every horizon; the naive/median baselines simply deteriorate
faster the further ahead they extrapolate. Underneath, the forecast itself does not get more
accurate, series histories shrink (max 7 obs for T+5), and only **4–6 real evaluation years** exist.
Generalization to unseen locations is unproven at any horizon (§5). **T+3/4/5 cannot yet be
trusted**; the horizon where any value is even marginally demonstrated is **T+1, restricted to
well-formed recurring series**.

---

## 8. Error analysis

- Dominant residual source: genuine year-to-year yield variability at a fixed location that lagged
  yield + geography cannot resolve (no joinable in-season weather/area/price at forecast time).
- Systematic baseline bias (median under-shoots trends) is what ML partly recovers — a modest,
  trend-correcting effect rather than a predictive breakthrough.
- Cold-start and full-cohort error bands exceed the best baseline, i.e. deploying ML there would be
  *worse than the simple median* and would need a baseline fallback.

---

## 9. Recommended model

**None for production deployment.** If and only if a future-year estimate is required now, ship the
**historical group median + trend-corrected carry-forward baseline** as an explicitly *experimental,
one-year, recurring-series-only* indicator — **not** an ML model and **not** a forecast promise.
HGB/RF would be the ML candidates *if* re-validated with the additional data below and only with a
baseline fallback for cold-start/low-history inputs and the Phase 2B negative/non-finite guards.

## 10. Implementation recommendation

Do **not** integrate an ML forecaster into the production API or frontend yet. If revisited, gate
behind: minimum historical depth (`hist_n ≥ 3`), recurring (non-cold) series, well-formed inputs,
output sanity guards, and an on-page "experimental estimate — not a validated forecast, unit
verification pending" label consistent with Phase 2B.

---

## 11. Final decision

### `REQUIRES MORE DATA`

The models produce future numbers, but on this dataset they do **not** reliably demonstrate value:
improvement over a trivial baseline is only ~5–10% MAE, exists **exclusively for already-observed
recurring series**, vanishes on cold-start groups and on the full (unfiltered) cohort, and is
mirrored by strong naive baselines. The gains do not reflect genuine forecasting skill at longer
horizons — just slower baseline decay. Two structural data gaps make this verdict a *more-data*
issue rather than a permanent *no-value* verdict.

To move to `READY FOR ONE-YEAR … INTEGRATION`, the project would need:

1. **Verified target units** at row level (close the Phase 2B `verification_pending` status).
2. **Cleaner APY rows** — resolve the 42% positive-yield/zero-area records.
3. **A real multi-year feature source** available at the forecast origin — joinable historical
   mandi prices, district-level sowing area, and in-season/pre-season weather — none of which the
   current snapshot data provides.
4. **Longer history and/or unseen-location splits** to test generalization beyond interpolation to
   recurring districts.

Until then, the honest product position is that **no forecasting model adds validated value over
baselines**, and this phase is recorded as research, not a deployable capability.

---

### Reproducibility & preservation

```
phase2c_future_yield_forecasting/
  scripts/  p01_data_audit.py  p02_forecast_pipeline.py  p03_analysis.py  p04_longer_horizons.py
  artifacts/ data_audit.json, forecast_evaluation_summary.json, merged_predictions_{wellformed,full}.csv,
             predictions_*.csv, series_observation_counts.csv, stability_by_year_*.csv
  reports/  metrics_analysis.json, longer_horizon_evaluation.json, RESEARCH_REPORT.md
  backups/  timestamped copies of every research file
```

This phase read the source datasets and did not modify: the served `.joblib` artifact, its
metadata, `models/yield_prediction.py`, any schema/route/config, `Notebook 16`, the frontend, or
any raw/processed dataset. Production behavior is unchanged. Nothing was committed.
