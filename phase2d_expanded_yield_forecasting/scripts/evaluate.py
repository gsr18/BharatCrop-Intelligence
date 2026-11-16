"""Phase 2D — strategy comparison + chronological expanding-window evaluation.

Strategies
  A. Direct per-horizon : a separate model for each h in {1..5}.
  B. Recursive          : one 1-step model, its output fed back for T+2..T+5.
  C. Pooled panel       : a single model across all horizons (horizon is a feature).

Baselines (origin-only, no training): previous, mean, median, trend, damped AR(1).
For every forecast origin year Y we train only on target_year < Y and score the
target_year == Y rows. Metrics reported per (strategy, model, cohort, horizon),
split cold-start vs recurring, plus by crop and by state.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("features", HERE / "features.py")
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
spec2 = importlib.util.spec_from_file_location("models", HERE / "models.py")
M = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(M)

ROOT = Path(__file__).resolve().parents[2]
ART = Path(__file__).resolve().parents[1] / "artifacts"
REP = Path(__file__).resolve().parents[1] / "reports"
REP.mkdir(parents=True, exist_ok=True)

FIRST_EVAL_YEAR = 2017
LAST_YEAR = 2024
MIN_TRAIN = 200
MODELS = ["ridge", "random_forest", "gradient_boosting", "hgb"]
BASELINES = {"prev": "b_prev", "mean": "b_mean", "median": "b_median",
             "trend": "b_trend", "ar1": "b_ar1"}


def metrics(actual, pred):
    actual = np.asarray(actual, float); pred = np.asarray(pred, float)
    err = pred - actual
    ss_tot = float(np.sum((actual - actual.mean()) ** 2))
    return {
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "bias": float(np.mean(err)),
        "r2": float(1 - np.sum(err ** 2) / ss_tot) if ss_tot > 0 else float("nan"),
        "n": int(len(actual)),
        "negatives": int((pred < 0).sum()),
    }


def detail_frame(sub, strategy, model, pred):
    return pd.DataFrame({
        "strategy": strategy, "model": model, "horizon": sub["horizon"].values,
        "target_year": sub["target_year"].values, "origin_year": sub["origin_year"].values,
        "State": sub["State"].values, "District": sub["District"].values,
        "Crop": sub["Crop"].values, "Season": sub["Season"].values,
        "cold_start": sub["cold_start"].values,
        "actual": sub["target_yield"].values, "pred": pred,
    })


def eval_direct(fx, vocab, cohort):
    rows = []
    skipped = {}
    for h in range(1, 6):
        sub = fx[fx["horizon"] == h]
        for Y in range(FIRST_EVAL_YEAR, LAST_YEAR + 1):
            train = sub[sub["target_year"] < Y]
            test = sub[sub["target_year"] == Y]
            if len(train) < MIN_TRAIN or len(test) == 0:
                skipped[f"h{h}_Y{Y}"] = int(len(train))
                continue
            for name in MODELS:
                m = M.Supervised(name, vocab).fit(train)
                rows.append(detail_frame(test, "direct", name, m.predict(test)))
    return pd.concat(rows, ignore_index=True), skipped


def eval_pooled(fx, vocab, cohort):
    rows = []
    for Y in range(FIRST_EVAL_YEAR, LAST_YEAR + 1):
        train = fx[fx["target_year"] < Y]
        test = fx[fx["target_year"] == Y]
        if len(train) < MIN_TRAIN or len(test) == 0:
            continue
        for name in MODELS:
            m = M.Supervised(name, vocab).fit(train)
            rows.append(detail_frame(test, "pooled_panel", name, m.predict(test)))
    return pd.concat(rows, ignore_index=True)


def eval_recursive(df_cohort, h1, vocab, model_names=("hgb",)):
    """Vectorized recursive multi-step from each start year S."""
    per_series = {}
    for key, grp in df_cohort.groupby(F.KEY, sort=False):
        g = grp.sort_values("YearStart")
        yrs = list(g["YearStart"].astype(int)); vals = list(g["Yield"].astype(float))
        per_series[key] = (yrs, vals, dict(zip(yrs, vals)),
                           {"State": key[0], "District": key[1], "Crop": key[2], "Season": key[3]})

    rows = []
    for S in range(FIRST_EVAL_YEAR, LAST_YEAR + 1):
        train = h1[h1["target_year"] < S]
        if len(train) < MIN_TRAIN:
            continue
        for name in model_names:
            mdl = M.Supervised(name, vocab).fit(train)
            # active series = have an observation exactly at origin S-1 and >=3 prior obs
            actives = []
            for key, (yrs, vals, ymap, ident) in per_series.items():
                if (S - 1) in ymap:
                    hist_y = [y for y in yrs if y <= S - 1]
                    if len(hist_y) >= 3:
                        actives.append((key, hist_y, [ymap[y] for y in hist_y], ident, ymap))
            if not actives:
                continue
            for k in range(1, LAST_YEAR - S + 2):
                origin_year = S - 1 + (k - 1)
                target_year = S - 1 + k
                frame = pd.DataFrame([
                    _one_step(hy, hv, ident, origin_year, target_year)
                    for (_, hy, hv, ident, _) in actives
                ])
                preds = mdl.predict(frame)
                for (key, hy, hv, ident, ymap), pred in zip(actives, preds):
                    hy.append(target_year); hv.append(float(pred))
                    actual = ymap.get(target_year)
                    if actual is not None:
                        rows.append({
                            "strategy": "recursive", "model": name, "horizon": k,
                            "target_year": target_year, "origin_year": S - 1,
                            "State": ident["State"], "District": ident["District"],
                            "Crop": ident["Crop"], "Season": ident["Season"],
                            "cold_start": 0, "actual": float(actual), "pred": float(pred),
                        })
                if target_year >= LAST_YEAR:
                    break
    if not rows:
        return pd.DataFrame(columns=["strategy", "model", "horizon", "target_year",
                                     "origin_year", "State", "District", "Crop", "Season",
                                     "cold_start", "actual", "pred"])
    return pd.DataFrame(rows)


def _one_step(hist_y, hist_v, ident, origin_year, target_year):
    hy = np.asarray(hist_y, float); hv = np.asarray(hist_v, float)
    med = float(np.median(hv)); mean = float(np.mean(hv))
    std = float(np.std(hv)) if hv.size >= 2 else 0.0
    slope, intercept = F._linfit(hy, hv)
    lag1 = float(hv[-1])
    lag2 = float(hv[-2]) if hv.size >= 2 else med
    lag3 = float(hv[-3]) if hv.size >= 3 else med
    row = {
        **ident, "origin_year": origin_year, "target_year": target_year,
        "lag1": lag1, "lag2": lag2, "lag3": lag3,
        "roll3_mean": float(np.mean(hv[-3:])), "roll5_mean": float(np.mean(hv[-5:])),
        "hist_std": std, "hist_median": med, "hist_mean": mean,
        "trend_slope": slope, "hist_n": int(hv.size),
        "has_lag2": float(hv.size >= 2), "has_lag3": float(hv.size >= 3),
        "horizon": 1, "target_yield": 0.0, "cold_start": 0,
    }
    return row


def summarise(detail, baselines_df):
    out = {"overall_by_horizon": {}, "cold_vs_recurring": {}, "by_crop": {}, "by_state": {}}
    for strat in detail["strategy"].unique():
        sd = detail[detail["strategy"] == strat]
        for model, md in sd.groupby("model"):
            key = f"{strat}:{model}"
            per_h = {}
            for h, sub in md.groupby("horizon"):
                per_h[f"T+{h}"] = metrics(sub["actual"], sub["pred"])
            per_h["all"] = metrics(md["actual"], md["pred"])
            out["overall_by_horizon"][key] = per_h
    # cold vs recurring for the strongest direct model (hgb) and pooled hgb
    for strat in ("direct", "pooled_panel", "recursive"):
        for model in ("hgb", "random_forest"):
            md = detail[(detail["strategy"] == strat) & (detail["model"] == model)]
            if len(md) == 0:
                continue
            key = f"{strat}:{model}"
            out["cold_vs_recurring"][key] = {
                "recurring": metrics(md[md.cold_start == 0]["actual"], md[md.cold_start == 0]["pred"]),
                "cold_start": metrics(md[md.cold_start == 1]["actual"], md[md.cold_start == 1]["pred"]),
            }
    # baselines per horizon from held-out rows (use hgb direct test rows as canonical eval set)
    canon = baselines_df
    base_by_h = {}
    for h, sub in canon.groupby("horizon"):
        bh = {}
        for bname, bcol in BASELINES.items():
            bh[bname] = metrics(sub["actual"], sub[bcol].values)
        base_by_h[f"T+{h}"] = bh
    out["baselines_by_horizon"] = base_by_h
    return out


def main():
    all_summary = {}
    for cohort in ("strict", "broad"):
        print(f"[{cohort}] loading + features...", flush=True)
        df = pd.read_csv(ART / f"cohort_{cohort}.csv")
        fx = F.build_forecast_rows(df)
        vocab = M.build_vocab(fx)
        print(f"[{cohort}] forecast_rows={len(fx)} direct...", flush=True)
        d_direct, skipped = eval_direct(fx, vocab, cohort)
        print(f"[{cohort}] pooled...", flush=True)
        d_pooled = eval_pooled(fx, vocab, cohort)
        print(f"[{cohort}] recursive...", flush=True)
        h1 = fx[fx["horizon"] == 1]
        d_rec = eval_recursive(df, h1, vocab)
        detail = pd.concat([x for x in (d_direct, d_pooled, d_rec) if len(x)], ignore_index=True)
        detail.to_csv(ART / f"detail_predictions_{cohort}.csv", index=False)
        print(f"[{cohort}] summarising ({len(detail)} rows)...", flush=True)

        # canonical baseline eval rows = all fx rows in the eval window
        base_rows = fx[fx["target_year"] >= FIRST_EVAL_YEAR].copy()
        base_rows["actual"] = base_rows["target_yield"]
        summary = summarise(detail, base_rows)
        # by crop / by state for direct hgb & random_forest
        for grain, col in (("by_crop", "Crop"), ("by_state", "State")):
            md = detail[(detail["strategy"] == "direct") & (detail["model"] == "hgb")]
            grp = {}
            for name, sub in md.groupby(col):
                if len(sub) < 400:
                    continue
                bm = base_rows[base_rows[col] == name]
                base_mae = min(metrics(bm["actual"], bm[c]).get("mae") for c in BASELINES.values()) if len(bm) else None
                grp[str(name)] = {"n": int(len(sub)), "hgb_mae": metrics(sub["actual"], sub["pred"])["mae"],
                                  "best_baseline_mae": base_mae}
            summary[grain] = grp
        summary["skipped_direct_folds"] = skipped
        summary["n_detail_rows"] = int(len(detail))
        summary["distinct_districts_eval"] = int(detail["District"].nunique())
        summary["distinct_crop_season_groups"] = int(
            detail.groupby(["Crop", "Season"]).ngroups)

        detail.to_csv(ART / f"detail_predictions_{cohort}.csv", index=False)
        all_summary[cohort] = summary

    (REP / "evaluation_summary.json").write_text(
        json.dumps(all_summary, indent=2), encoding="utf-8"
    )
    for cohort in all_summary:
        print(f"=== {cohort}: detail rows {all_summary[cohort]['n_detail_rows']}, "
              f"districts {all_summary[cohort]['distinct_districts_eval']} ===")
    print(json.dumps(all_summary["strict"]["overall_by_horizon"].get("direct:hgb", {}), indent=2))
    print("baselines strict:", json.dumps(all_summary["strict"]["baselines_by_horizon"], indent=2))


if __name__ == "__main__":
    main()
