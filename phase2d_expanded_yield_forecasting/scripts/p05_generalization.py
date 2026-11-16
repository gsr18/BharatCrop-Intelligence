"""Phase 2D — cold-start / generalization analysis (no retraining).

Redefines the recurring-vs-cold split correctly for a chronological eval:
  * unseen_in_train : for the fold testing target-year Y, the group's earliest
    available target_year is >= Y, i.e. it has NO earlier target the model trained on.
  * rich vs thin history: hist_n (observations at or before the origin).
This measures generalization to series/origins the model has not previously scored,
beyond the recurring-district interpolation the pooled metrics hide.
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

BASE = Path(__file__).resolve().parents[1]
ART = BASE / "artifacts"
REP = BASE / "reports"


def metrics(actual, pred):
    actual = np.asarray(actual, float); pred = np.asarray(pred, float)
    err = pred - actual
    ss = float(np.sum((actual - actual.mean()) ** 2))
    return {"mae": float(np.mean(np.abs(err))),
            "rmse": float(np.sqrt(np.mean(err ** 2))),
            "bias": float(np.mean(err)),
            "r2": float(1 - np.sum(err ** 2) / ss) if ss > 0 else None,
            "n": int(len(actual))}


def cohort_analysis(cohort):
    df = pd.read_csv(ART / f"cohort_{cohort}.csv")
    fx = F.build_forecast_rows(df)
    gkey = ["State", "District", "Crop", "Season"]
    first_target = fx.groupby(gkey)["target_year"].min()
    fx["group_first_target"] = fx.set_index(gkey).index.map(first_target)

    det = pd.read_csv(ART / f"detail_predictions_{cohort}.csv")
    # attach hist_n + unseen for direct/pooled via exact feature-row key
    fxs = fx[gkey + ["horizon", "origin_year", "target_year", "hist_n", "group_first_target"]]
    merged = det.merge(fxs, on=gkey + ["horizon", "origin_year", "target_year"],
                       how="left")
    merged["unseen_in_train"] = merged["target_year"] <= merged["group_first_target"]
    # depth-based split (well-populated)
    merged["generalize"] = merged["hist_n"] <= 2
    merged["recurring"] = merged["hist_n"] >= 4
    new_groups = int((first_target >= 2017).sum())

    out = {"cohort": cohort}
    for strat, model in [("direct", "hgb"), ("direct", "random_forest"),
                         ("pooled_panel", "random_forest"), ("pooled_panel", "hgb"),
                         ("recursive", "hgb")]:
        md = merged[(merged.strategy == strat) & (merged.model == model)]
        if len(md) == 0:
            continue
        per_h = {}
        for h, sub in md.groupby("horizon"):
            per_h[f"T+{h}"] = {
                "recurring": metrics(sub[sub.recurring]["actual"], sub[sub.recurring]["pred"]),
                "generalize": metrics(sub[sub.generalize]["actual"], sub[sub.generalize]["pred"]),
            }
        out[f"{strat}:{model}"] = per_h
    # aggregate split counts
    out["counts"] = {
        "n_detail": int(len(merged)),
        "n_short_history_rows": int((merged["hist_n"] <= 2).sum()),
        "n_rich_history_rows": int((merged["hist_n"] >= 4).sum()),
        "n_new_groups_first_target_ge_2017": new_groups,
        "n_unseen_in_train_rows": int(merged["unseen_in_train"].sum()),
    }
    return out, merged


def main():
    summary = json.loads((REP / "evaluation_summary.json").read_text(encoding="utf-8"))
    report = {}
    for cohort in ("strict", "broad"):
        out, merged = cohort_analysis(cohort)
        report[cohort] = out
        # build simple aggregate recurring vs generalize per model
        cvr = {}
        for (strat, model), grp in merged.groupby(["strategy", "model"]):
            cvr[f"{strat}:{model}"] = {
                "recurring": metrics(grp[grp.recurring]["actual"], grp[grp.recurring]["pred"]),
                "cold_start": metrics(grp[grp.generalize]["actual"], grp[grp.generalize]["pred"]),
            }
        summary[cohort]["cold_vs_recurring"] = cvr
    (REP / "generalization_analysis.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    (REP / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")

    # print concise
    for cohort in ("strict", "broad"):
        print("=" * 30, cohort)
        o = report[cohort]
        print("counts:", o["counts"])
        for key in ["direct:hgb", "pooled_panel:random_forest", "recursive:hgb"]:
            if key not in o:
                continue
            for h in sorted(o[key]):
                r = o[key][h]["recurring"]; g = o[key][h]["generalize"]
                gr2 = g["r2"] if g["r2"] is not None else float("nan")
                print(f"  {key:26s} {h} recur_MAE={r['mae']:.0f}(n={r['n']}) "
                      f"gen_MAE={(g['mae'] if g['n'] else float('nan')):.0f}(n={g['n']}) "
                      f"gen_r2={gr2:.3f}")


if __name__ == "__main__":
    main()
