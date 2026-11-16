"""Phase 2D — forecast comparison visualizations (matplotlib, headless PNGs)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
ART = BASE / "artifacts"
FIG = BASE / "reports" / "figs"
FIG.mkdir(parents=True, exist_ok=True)
summary = json.loads((BASE / "reports" / "evaluation_summary.json").read_text(encoding="utf-8"))
HORIZONS = [1, 2, 3, 4, 5]
HZ = [f"T+{h}" for h in HORIZONS]
ML = ["ridge", "random_forest", "gradient_boosting", "hgb"]
COLORS = {"ridge": "#94a3b8", "random_forest": "#0ea5e9",
          "gradient_boosting": "#22c55e", "hgb": "#f97316"}


def _mae_series(cohort, strat, model):
    d = summary[cohort]["overall_by_horizon"].get(f"{strat}:{model}", {})
    return [d.get(f"T+{h}", {}).get("mae", np.nan) for h in HORIZONS]


def _baseline_best(cohort):
    base = summary[cohort]["baselines_by_horizon"]
    out = []
    for h in HORIZONS:
        vals = [base[f"T+{h}"][b]["mae"] for b in base[f"T+{h}"]]
        out.append(min(vals))
    return out


def fig_direct_vs_baseline(cohort):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(HORIZONS))
    for m in ML:
        ax.plot(x, _mae_series(cohort, "direct", m), marker="o",
                color=COLORS[m], label=f"direct {m}")
    ax.plot(x, _baseline_best(cohort), marker="s", ls="--", color="#111",
            label="best baseline")
    ax.set_xticks(x); ax.set_xticklabels(HZ)
    ax.set_ylabel("MAE (kg/ha)"); ax.set_title(f"Direct models vs best baseline — {cohort} cohort")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / f"direct_vs_baseline_{cohort}.png", dpi=130); plt.close(fig)


def fig_recursive_vs_direct(cohort):
    if f"recursive:hgb" not in summary[cohort]["overall_by_horizon"]:
        return
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(HORIZONS))
    ax.plot(x, _mae_series(cohort, "direct", "hgb"), marker="o", color=COLORS["hgb"], label="direct hgb")
    ax.plot(x, _mae_series(cohort, "recursive", "hgb"), marker="^", color="#dc2626", label="recursive hgb")
    ax.plot(x, _mae_series(cohort, "pooled_panel", "hgb"), marker="v", color="#7c3aed", label="pooled hgb")
    ax.plot(x, _baseline_best(cohort), marker="s", ls="--", color="#111", label="best baseline")
    ax.set_xticks(x); ax.set_xticklabels(HZ); ax.set_ylabel("MAE (kg/ha)")
    ax.set_title(f"Recursive vs direct vs pooled — error growth with horizon ({cohort})")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / f"recursive_vs_direct_{cohort}.png", dpi=130); plt.close(fig)


def fig_cold_vs_recurring(cohort):
    cvr = summary[cohort].get("cold_vs_recurring", {})
    keys = [k for k in cvr if k.endswith("hgb")]
    if not keys:
        return
    fig, ax = plt.subplots(figsize=(8, 4.5))
    # metrics per horizon are stored under overall; cold/recurring are aggregated.
    labels = list(keys)
    rec_mae = [cvr[k]["recurring"]["mae"] for k in labels]
    cold_mae = [cvr[k]["cold_start"]["mae"] for k in labels]
    xx = np.arange(len(labels))
    ax.bar(xx - 0.18, rec_mae, 0.36, label="recurring series", color="#0ea5e9")
    ax.bar(xx + 0.18, cold_mae, 0.36, label="cold-start series", color="#dc2626")
    ax.set_xticks(xx); ax.set_xticklabels([l.replace(":", "\n") for l in labels], fontsize=8)
    ax.set_ylabel("MAE (kg/ha)")
    ax.set_title(f"Cold-start vs recurring — {cohort} cohort")
    ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / f"cold_vs_recurring_{cohort}.png", dpi=130); plt.close(fig)


def fig_cohort_compare():
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(HORIZONS))
    for cohort, col in (("strict", "#22c55e"), ("broad", "#eab308")):
        ax.plot(x, _mae_series(cohort, "direct", "hgb"), marker="o", color=col, label=f"{cohort} direct hgb")
    ax.set_xticks(x); ax.set_xticklabels(HZ); ax.set_ylabel("MAE (kg/ha)")
    ax.set_title("Clean (strict) vs broad cohort — direct HGB")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "cohort_compare.png", dpi=130); plt.close(fig)


def main():
    for cohort in ("strict", "broad"):
        fig_direct_vs_baseline(cohort)
        fig_recursive_vs_direct(cohort)
        fig_cold_vs_recurring(cohort)
    fig_cohort_compare()
    print("figures:", sorted(p.name for p in FIG.glob("*.png")))


if __name__ == "__main__":
    main()
