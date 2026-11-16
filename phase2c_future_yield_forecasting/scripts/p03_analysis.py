"""Phase 2C - Parts 5-7 analysis (reads saved predictions; no retraining).

Produces:
  * skill vs baselines (relative MAE/RMSE reduction) per horizon
  * stability by forecast/target year
  * implausible (negative / extreme) ML prediction counts
  * cold-start vs recurring-group error split (interpolation vs generalization)
  * horizon feasibility for 3/4/5-year forecasts
Writes metrics_markdown.md + feasibility.json in reports/.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys_path_root = HERE
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("p02", HERE / "p02_forecast_pipeline.py")
p02 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p02)  # type: ignore

ART = HERE.parent / "artifacts"
REP = HERE.parent / "reports"
REP.mkdir(parents=True, exist_ok=True)

MODELS = ["wellformed_ridge_pred", "wellformed_random_forest_pred", "wellformed_hgb_pred"]
BASE = {"prev": "b_prev", "median": "b_median", "trend": "b_trend"}


def rel_metrics(actual, pred):
    err = pred - actual
    return {
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "bias": float(np.mean(err)),
    }


def skill_table(cohort_tag):
    df = pd.read_csv(ART / f"merged_predictions_{cohort_tag}.csv")
    prefix = "wellformed_" if cohort_tag == "wellformed" else "full_"
    model_cols = [c for c in df.columns if c.endswith("_pred")]
    out = {}
    for h in (1, 2):
        sub = df[df["horizon"] == h]
        actual = sub["actual"].values
        base_mae = {b: rel_metrics(actual, sub[c].values)["mae"] for b, c in BASE.items()}
        best_base = min(base_mae.values())
        best_base_name = min(base_mae, key=base_mae.get)
        entry = {"baselines_mae": base_mae, "best_baseline": best_base_name}
        for mc in model_cols:
            m = rel_metrics(actual, sub[mc].values)
            m["mae_skill_vs_best_baseline_pct"] = float(100 * (best_base - m["mae"]) / best_base)
            m["mean_actual"] = float(np.mean(actual))
            m["mae_pct_of_mean"] = float(100 * m["mae"] / np.mean(actual))
            m["negatives"] = int((sub[mc].values < 0).sum())
            m["implausible_gt12000"] = int((sub[mc].values > 12000).sum())
            entry[mc.replace(prefix, "").replace("_pred", "")] = m
        out[f"h{h}"] = entry
    return out, df, model_cols


def stability_by_year(df, model_cols):
    rows = []
    for (h, y), sub in df.groupby(["horizon", "target_year"]):
        rec = {"horizon": h, "target_year": int(y), "n": int(len(sub))}
        rec["baseline_median_mae"] = rel_metrics(sub["actual"].values, sub["b_median"].values)["mae"]
        rec["baseline_prev_mae"] = rel_metrics(sub["actual"].values, sub["b_prev"].values)["mae"]
        for mc in model_cols:
            rec[f"{mc}_mae"] = rel_metrics(sub["actual"].values, sub[mc].values)["mae"]
        rows.append(rec)
    return pd.DataFrame(rows).sort_values(["horizon", "target_year"])


def cold_start_split(df, model_cols):
    key = ["State", "District", "Crop", "Season"]
    first = df.groupby(key)["target_year"].transform("min")
    df = df.assign(cold=(df["target_year"] == first))
    out = {}
    for label, sub in [("cold_start_first_seen_year", df[df["cold"]]),
                       ("recurring_group", df[~df["cold"]])]:
        rec = {"n": int(len(sub))}
        rec["baseline_median_mae"] = rel_metrics(sub["actual"].values, sub["b_median"].values)["mae"]
        for mc in model_cols:
            rec[f"{mc}_mae"] = rel_metrics(sub["actual"].values, sub[mc].values)["mae"]
        out[label] = rec
    return out


def feasibility():
    """Can 3/4/5-year horizons be validated at all with available history?"""
    df = p02.load_cohort(robust=True)
    res = {}
    for h in (1, 2, 3, 4, 5):
        fx = p02.build_forecast_rows(df, horizons=(h,))
        if len(fx) == 0:
            res[h] = {"forecast_rows": 0}
            continue
        fx = fx.assign(hist_n=fx["hist_n"])
        trainable = fx[fx["hist_n"] >= 3]
        # number of target-years that would host an expanding-window eval fold
        # (need >=200 trainable rows with target_year < Y to fit, and >=200 at Y)
        yr_counts = trainable.groupby("target_year").size()
        eval_years = [int(y) for y in yr_counts.index if y >= p02.FIRST_EVAL_YEAR]
        # for each candidate eval year, is there >=200 strictly-earlier trainable rows?
        valid_eval_years = [
            y for y in eval_years
            if (trainable["target_year"] < y).sum() >= 200 and yr_counts.get(y, 0) >= 200
        ]
        res[h] = {
            "forecast_rows": int(len(fx)),
            "rows_with_hist_n_ge3": int(len(trainable)),
            "max_hist_n": int(fx["hist_n"].max()),
            "candidate_eval_years": eval_years,
            "valid_rolling_eval_years": valid_eval_years,
            "n_valid_eval_years": len(valid_eval_years),
        }
    return res


def main():
    report = {}
    for cohort in ("wellformed", "full"):
        st, df, model_cols = skill_table(cohort)
        report[cohort] = {
            "skill": st,
            "cold_start": cold_start_split(df, model_cols),
            "by_year": stability_by_year(df, model_cols).to_dict(orient="records"),
        }
        stability_by_year(df, model_cols).to_csv(
            ART / f"stability_by_year_{cohort}.csv", index=False
        )
    report["feasibility"] = feasibility()
    (REP / "metrics_analysis.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report["wellformed"]["skill"], indent=2))
    print("=== FEASIBILITY ===")
    print(json.dumps(report["feasibility"], indent=2))


if __name__ == "__main__":
    main()
