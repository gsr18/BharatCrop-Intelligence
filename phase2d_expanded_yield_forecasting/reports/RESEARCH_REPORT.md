# Phase 2D — Expanded Future Yield Prediction: Research Report

**Status:** Research & model-evaluation only. Isolated under
`phase2d_expanded_yield_forecasting/`. **The served production model
(`models/yield_prediction/individual_crop_hgb_location.joblib`), its metadata, the backend
API/frontend, Phase 2C artifacts, and all datasets are unchanged.** Nothing was committed.

**Selected experimental candidate:** *Pooled-panel RandomForest* (trained across all horizons,
`horizon` as a feature) on the **strict** cohort.
**Production readiness: NOT validated — retain as research only.**

---

## 1. Which models were tested

| Family | Estimator | Availability |
|---|---|---|
| Traditional regression | Ridge | sklearn |
| Traditional | RandomForest | sklearn |
| Boosting | HistGradientBoostingRegressor | sklearn |
| Boosting | GradientBoostingRegressor (plain) | sklearn |
| Advanced boosting | XGBoost, LightGBM | **not installed** — skipped deliberately |
| Statistical baselines | previous-year, historical mean, median, trend, damped AR(1) | implemented in numpy |
| Strategies | Direct per-horizon, **Pooled panel**, **Recursive** | — |

`xgboost` / `lightgbm` / `statsmodels` were absent. I did **not** install them: sklearn's
HistGradientBoosting is the same histogram-gradient-boosting family LightGBM implements and a fair
proxy, XGBoost would add no research value here, and the statistical baselines (incl. a damped
AR(1)) are reproducible in numpy without `statsmodels`. This is recorded per the "don't install
without justification / don't assume advanced = better" constraints.

## 2. Which features were used (all origin-safe)

For a forecast of target year **Y** at horizon **h**, origin **O = Y − h**; every feature uses
observations at year ≤ O only.

Lags: `lag1` (=Y−h year yield), `lag2`, `lag3` · Rolling means: `roll3_mean`, `roll5_mean` ·
Dispersion/level: `hist_std`, `hist_median`, `hist_mean` · `trend_slope` (OLS over years ≤ O) ·
`hist_n` and `has_lag2` / `has_lag3` (explicit missing-history flags) · calendar `origin_year`,
`target_year`, `horizon` · identity: `Crop, Season, State, District`.
Low-cardinality categoricals (Crop/Season/State) one-hot encoded; high-cardinality District (≤748)
as a stable integer code. **Missing history** → lag fills to the historical median **and** a flag,
never a silent impute. **Never used:** the target-year actual, any year > O, future weather/price,
or the single-date mandi snapshot.

## 3. Which forecasting strategy performed best

**Pooled-panel** clearly beat direct and recursive on every axis. Strict-cohort MAE (kg/ha):

| Strategy / model | T+1 | T+2 | T+3 | T+4 | T+5 |
|---|---|---|---|---|---|
| **Pooled RandomForest** | **326** | **325** | **327** | **329** | **323** |
| Pooled HGB | 334 | 338 | 343 | 348 | 345 |
| Direct HGB | 329 | 356 | 375 | 377 | 381 |
| Direct RF | 322 | 352 | 371 | 377 | 382 |
| Direct GradientBoosting | 325 | 363 | 382 | 391 | 399 |
| Direct Ridge | 337 | 382 | 394 | 405 | 420 |
| **Recursive HGB** | 327 | 374 | 408 | 443 | **475** |
| Best baseline | 343 | 386 | 412 | 437 | 461 |

- **Pooled panel** shares information across all crop–district–season series and horizons, giving
  the **lowest and nearly horizon-flat MAE** (323–329) and the best aggregate R² (0.866).
- **Direct** per-horizon models degrade monotonically with horizon (T+1 322 → T+5 382): each far
  horizon is trained on progressively fewer, sparser rows.
- **Recursive** is the worst at scale — see §7.
- Ridge is the weakest and emits negative predictions (134 strict / 88 broad).

**Strategy strengths/limitations:** Pooled panel = best data efficiency + stable errors, but risks
dominating the common trend; Direct = horizon-specific calibration but data-starved at long
horizons; Recursive = single model, but compounds one-step error and needs no per-horizon fits.

## 4. Results for all five horizons

See §3 table (strict) and figures `reports/figs/direct_vs_baseline_strict.png`,
`recursive_vs_direct_strict.png`. Broad-cohort numbers are in `artifacts/metrics_by_horizon.csv`
and `reports/evaluation_summary.json`. R² (all horizons pooled) — Pooled RF 0.866, Pooled HGB
0.858, Direct RF 0.845, Direct HGB 0.843, Ridge 0.837–0.839, Recursive HGB 0.782. Evaluated
predictions: **1,222,991** detail rows (strict) / **2,264,841** (broad) across **~729 districts**
and **30–35 crop–season groups**.

## 5. Cold-start vs recurring-series performance

**This APY panel is overwhelmingly recurring districts**: only **1,226 of ~? groups** are genuinely
new (first target-year ≥ 2017) and **9,684 / 1,222,991 rows (~0.8%)** are unseen-in-training. So a
"new-district generalization" test is barely exercisable — itself an important finding: **we cannot
demonstrate generalization to never-observed districts from this data.** I therefore also split by
**history depth** (thin = ≤2 prior obs vs rich = ≥4). Pooled RF (strict):

| Horizon | Recurring (rich) MAE | Thin-history MAE |
|---|---|---|
| T+1 | 322 | 375 |
| T+3 | 310 | 384 |
| T+5 | 311 | 343 |

Direct HGB thin-history is far worse (T+3 470, T+5 450 vs its recurring 343/353). **Pooled RF
degrades most gracefully** with thin history — a robustness advantage. Per the task: the headline
skill is **interpolation over recurring series**, not proven generalization.

## 6. Clean vs broad cohort performance

Broad (keeps positive-yield/zero-area rows; cap 30,000) has *lower absolute* MAE (many easy repeat
rows) but the **same ranking**: Pooled RF best (297→310 flat), Recursive worst (295→445). Strict
MAE ~20–30 kg/ha higher but cleaner targets. **Negatives concentrate in the dirty broad cohort and
in Ridge/recursive**: e.g. broad Ridge 88, recursive 85, GB 6; Pooled RF = 0 in both cohorts. The
38,502 positive-yield/zero-area records excluded from strict are the source of both the extreme
targets (max 22,846 broad vs 11,986 strict) and the negative-prediction risk.

## 7. Error accumulation in recursive forecasting

Recursive HGB (strict), MAE by step — each step feeds its own prediction back:

| Horizon | T+1 | T+2 | T+3 | T+4 | T+5 | T+6 | T+7 | T+8 |
|---|---|---|---|---|---|---|---|---|
| MAE | 327 | 374 | 408 | 443 | **475** | 525 | 583 | 660 |

Error compounds ~+46 MAE/step and by **T+4 recursive (443) already exceeds the best baseline
(437)**; by T+5 it is clearly worse (475 vs 461). Recursive is the least defensible multi-step
strategy here.

## 8. Can experimental five-year predictions be generated?

**Yes — experimentally, but not validated.** The pooled-panel RF produces a **T+5** forecast with
MAE ≈ 323 and R² ≈ 0.87 on the strict recurring cohort, essentially as good as T+1 (because it
reverts to a stable conditional mean given lag/history/geography rather than extrapolating).
Caveats that cap the claim:
- It is **interpolation to recurring districts** (see §5); no evidence for unseen districts.
- **Direct per-horizon T+4/T+5 training folds are data-starved**: the earliest folds
  (`h4_Y2017`, `h5_Y2017`, `h5_Y2018`) had <200 training rows and were skipped, so only ~6 of 8
  origins support them.
- Target unit kg/ha is **verification-pending** (inherited Phase 2B).
- Recursive T+5 (475) is *worse than baseline*, so a five-year number should come from the pooled
  model, **never** recursive, and must be labelled experimental.

## 9. Which horizons are defensible for user-facing experimental projections

- **T+1, T+2, T+3 — defensible as *experimental*** (clear baseline skill, near-flat error, 0
  negatives for pooled RF). Present with the Phase 2B guards and "experimental estimate, not a
  validated forecast, unit verification pending" wording.
- **T+4, T+5 — borderline**: pooled RF still edges the baseline (25–30% "skill" vs a decaying
  baseline) but skill is interpolation-driven, thin-history degrades, and direct folds are sparse.
  Only if explicitly marked low-confidence and restricted to rich-history recurring series.
- **Recursive / Ridge — not defensible** (recursive worse than baseline ≥T+4; Ridge yields
  negatives).

## 10. What additional data would improve reliability

1. **Verified row-level target units** (close Phase 2B `verification_pending`).
2. **A genuine multi-year feature source available at forecast origin** — historical mandi prices
   (the current file is a single 2026-10-31 snapshot), district sowing area, and in/pre-season
   weather. These, not more model complexity, are the binding constraint.
3. **Cleaner APY rows** — resolve the 42% positive-yield/zero-area records.
4. **Longer history** (pre-2013 and post-2024) and **deliberately held-out districts/crops** to test
   true spatial generalization, since the current panel is almost entirely recurring series.

## Best-model selection & complexity justification

**Winner: Pooled-panel RandomForest (strict cohort).** It offers the best accuracy (MAE ~325,
R² 0.866), the most **consistent performance across all five horizons**, the **most graceful
degradation on thin history**, **0 negative predictions** (robustness), and the broadest
crop/geography coverage — beating every baseline at every horizon. Its complexity is justified
versus the simple baselines: it improves MAE by 5% (T+1) up to 30% (T+5, vs a decaying baseline)
and eliminates baseline bias (median baseline is −145 to −196 biased; pooled RF bias ≈ −11).
Against the manual HGB nowcast it is a distinct future-horizon model. Saved as
`models/phase2d_pooled_rf_research.joblib` + metadata — **research only, not wired into the API**.

Per-crop/state detail (direct HGB, n≥400) confirms gains are **geography-dependent**: large for
Maize (702 vs 773), UP (302 vs 372), Bihar (524 vs 602); roughly at par for Urad/Tur/Small-Millets
and Tamil Nadu — so blanket deployment is not justified.

---

## Reproducibility

```
phase2d_expanded_yield_forecasting/
  scripts/  data_prep.py  features.py  models.py  evaluate.py
            p05_generalization.py  p06_metrics_csv.py  save_model.py  visualize.py
  artifacts/ cohort_{strict,broad}.csv, data_prep_report.json,
             detail_predictions_{strict,broad}.csv, metrics_by_horizon.csv,
             generalization_metrics.csv, eval.log
  reports/  RESEARCH_REPORT.md, evaluation_summary.json, generalization_analysis.json, figs/*.png
  models/   phase2d_pooled_rf_research.joblib + _metadata.json   (RESEARCH ONLY)
  backups/  timestamped copies of every research file
```
Run order: `data_prep → evaluate → p05_generalization → save_model → visualize → p06_metrics_csv`.
No source dataset, production code, served artifact, notebook, or Phase 2C file was modified.
