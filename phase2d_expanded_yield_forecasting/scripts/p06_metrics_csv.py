"""Phase 2D — export tidy metrics tables (CSV) from the JSON summaries."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
ART = BASE / "artifacts"
REP = BASE / "reports"

summary = json.loads((REP / "evaluation_summary.json").read_text(encoding="utf-8"))
gen = json.loads((REP / "generalization_analysis.json").read_text(encoding="utf-8"))

rows = []
for cohort, c in summary.items():
    for key, per in c["overall_by_horizon"].items():
        strat, model = key.split(":", 1)
        for h, m in per.items():
            if not h.startswith("T+"):
                continue
            rows.append({"cohort": cohort, "strategy": strat, "model": model,
                         "horizon": h, **{k: m[k] for k in
                         ("mae", "rmse", "bias", "r2", "n", "negatives")}})
    for h, bmap in c["baselines_by_horizon"].items():
        for b, m in bmap.items():
            rows.append({"cohort": cohort, "strategy": "baseline", "model": b,
                         "horizon": h, **{k: m[k] for k in
                         ("mae", "rmse", "bias", "r2", "n", "negatives")}})
pd.DataFrame(rows).sort_values(["cohort", "strategy", "model", "horizon"]).to_csv(
    ART / "metrics_by_horizon.csv", index=False)

# generalization (recurring vs thin-history) per horizon for key candidates
grows = []
for cohort, o in gen.items():
    for key, per in o.items():
        if key in ("cohort", "counts") or not isinstance(per, dict):
            continue
        for h, split in per.items():
            if not h.startswith("T+"):
                continue
            for label, m in split.items():
                if m["n"]:
                    grows.append({"cohort": cohort, "model": key, "horizon": h,
                                  "split": label, **{k: m[k] for k in ("mae", "rmse", "r2", "n")}})
pd.DataFrame(grows).to_csv(ART / "generalization_metrics.csv", index=False)
print("metrics_by_horizon rows:", len(rows), "| generalization rows:", len(grows))
