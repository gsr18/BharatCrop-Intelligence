"""Phase 2C - Part 7: evaluate longer horizons (T+3, T+4, T+5) for evidence."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p02", HERE / "p02_forecast_pipeline.py")
p02 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p02)  # type: ignore

ART = HERE.parent / "artifacts"
REP = HERE.parent / "reports"


def mae(actual, pred):
    return float(np.mean(np.abs(np.asarray(actual) - np.asarray(pred))))


def rmse(actual, pred):
    e = np.asarray(actual) - np.asarray(pred)
    return float(np.sqrt(np.mean(e ** 2)))


def r2(actual, pred):
    actual = np.asarray(actual)
    err = np.asarray(pred) - actual
    ssr = float(np.sum(err ** 2))
    sst = float(np.sum((actual - actual.mean()) ** 2))
    return float(1 - ssr / sst) if sst > 0 else float("nan")


def run_horizon(df, h):
    all_fx = p02.build_forecast_rows(df, horizons=(h,))
    for c in p02.CATEGORICAL:
        vocab = sorted(all_fx[c].astype(str).unique())
        all_fx[f"{c}__code"] = all_fx[c].astype(str).map({v: i for i, v in enumerate(vocab)}).astype(float)
    acc = []
    for y in range(p02.FIRST_EVAL_YEAR, int(all_fx["target_year"].max()) + 1):
        train = all_fx[all_fx["target_year"] < y]
        test = all_fx[all_fx["target_year"] == y]
        if len(train) < 200 or len(test) == 0:
            continue
        for name, fitter in p02.MODELS.items():
            m = fitter().fit(train)
            p = m.predict(test)
            acc.append(pd.DataFrame({
                "horizon": h, "eval_year": y, "model": name,
                "actual": test["target_yield"].values, "pred": p,
                "b_prev": test["b_prev"].values, "b_median": test["b_median"].values,
                "b_trend": test["b_trend"].values,
            }))
    d = pd.concat(acc, ignore_index=True)
    out = {"h": h, "n_eval_years": int(d["eval_year"].nunique()) if len(d) else 0,
           "n_rows": int(len(d) / max(1, len(p02.MODELS)))}
    base = d.groupby("eval_year").agg(b_prev=("b_prev", "size")).reset_index()
    best_base = min(mae(d["actual"], d["b_prev"]), mae(d["actual"], d["b_median"]))
    for name in p02.MODELS:
        sub = d[d["model"] == name]
        out[name] = {"mae": mae(sub["actual"], sub["pred"]),
                     "rmse": rmse(sub["actual"], sub["pred"]),
                     "r2": r2(sub["actual"], sub["pred"]),
                     "negatives": int((sub["pred"] < 0).sum())}
    out["best_baseline_mae"] = best_base
    out["baseline_median_mae"] = mae(d["actual"], d["b_median"])
    for name in p02.MODELS:
        out[f"{name}_skill_vs_best_baseline_pct"] = float(
            100 * (best_base - out[name]["mae"]) / best_base)
    return out


def main():
    df = p02.load_cohort(robust=True)
    res = {f"h{h}": run_horizon(df, h) for h in (3, 4, 5)}
    (REP / "longer_horizon_evaluation.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
