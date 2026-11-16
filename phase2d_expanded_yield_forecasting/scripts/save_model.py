"""Phase 2D — save the strongest experimental candidate as an isolated research artifact.

Trains the selected strategy/model on the FULL strict cohort forecast rows and
dumps it under models/ with a metadata file that records the honest Phase 2D
metrics and an explicit NOT-FOR-PRODUCTION status. This is a research artifact
only: it is not wired into the API and does not touch the served production model.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import joblib
import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("features", HERE / "features.py")
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
spec2 = importlib.util.spec_from_file_location("models", HERE / "models.py")
M = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(M)

BASE = Path(__file__).resolve().parents[1]
ART = BASE / "artifacts"
MODELDIR = BASE / "models"
MODELDIR.mkdir(parents=True, exist_ok=True)
REP = BASE / "reports"

SELECTED_STRATEGY = "pooled_panel"
SELECTED_MODEL = "random_forest"


def main():
    df = pd.read_csv(ART / "cohort_strict.csv")
    fx = F.build_forecast_rows(df)
    vocab = M.build_vocab(fx)
    summary = json.loads((REP / "evaluation_summary.json").read_text(encoding="utf-8"))
    key = f"{SELECTED_STRATEGY}:{SELECTED_MODEL}"
    metrics = summary["strict"]["overall_by_horizon"].get(key, {})

    # One pooled model scores every horizon (horizon is an input feature).
    pooled = M.Supervised(SELECTED_MODEL, vocab).fit(fx)
    per_horizon = {h: pooled for h in range(1, 6)}

    bundle = {
        "strategy": SELECTED_STRATEGY,
        "model_name": SELECTED_MODEL,
        "estimators": {h: per_horizon[h].est for h in per_horizon},
        "vocab": vocab,
        "numeric_features": F.NUMERIC_FEATURES,
        "design": "numeric(incl. horizon) + one-hot(Crop,Season,State) + district_code",
    }
    joblib.dump(bundle, MODELDIR / "phase2d_pooled_rf_research.joblib", compress=3)

    meta = {
        "artifact": "phase2d_pooled_rf_research.joblib",
        "status": "RESEARCH_ONLY — NOT validated for production; do not wire into the API",
        "phase": "2D",
        "production_model_untouched": True,
        "cohort": "strict (clean: positive Area/Production, Yield<=12000)",
        "strategy": SELECTED_STRATEGY,
        "base_model": SELECTED_MODEL,
        "horizons_fit": list(per_horizon.keys()),
        "features": F.NUMERIC_FEATURES,
        "categorical_handling": "one-hot Crop/Season/State + integer District code",
        "leakage_note": "All features use observations <= origin (target_year - horizon).",
        "expanding_window_metrics_strict": metrics,
        "caveats": [
            "R² is interpolation over recurring districts; cold-start generalization is weak.",
            "Target unit kg/ha is verification_pending (inherited from Phase 2B).",
            "No validated future-season weather/prices used; gains vs baseline are modest.",
        ],
    }
    (MODELDIR / "phase2d_pooled_rf_research_metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print("saved artifact + metadata for horizons", list(per_horizon.keys()))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
