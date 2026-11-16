"""Phase 2D — data preparation: build strict-clean and broad cohorts.

Reads the APY long table read-only, applies *documented, non-silent* quality
filters, and writes two cohort CSVs plus a coverage/QC report. Nothing here
modifies source data or production artifacts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LONG = ROOT / "data" / "processed" / "historical_food_grains_apy_long_2013-14_to_2024-25.csv"
OUT = Path(__file__).resolve().parents[1] / "artifacts"
OUT.mkdir(parents=True, exist_ok=True)

SEASONS = ("Kharif", "Rabi", "Summer")
STRICT_MAX_YIELD = 12000.0
BROAD_MAX_YIELD = 30000.0


def load_base() -> pd.DataFrame:
    df = pd.read_csv(LONG)
    df["YearStart"] = (
        df["Year"].astype(str).str.extract(r"^(\d{4})")[0].astype("float64")
    )
    for c in ("Yield", "Area", "Production"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def individual_season(df: pd.DataFrame) -> pd.DataFrame:
    out = df[df["Crop_Category"] == "Individual Crop Candidate"].copy()
    out = out[out["Season"].isin(SEASONS)]
    out = out.dropna(subset=["State", "District", "Crop", "Season", "YearStart"])
    # exact duplicate check on the natural series key
    key = ["State", "District", "Crop", "Season", "YearStart"]
    dup_count = int(out.duplicated(subset=key, keep=False).sum())
    out = out.drop_duplicates(subset=key, keep="first")
    out.attrs["dropped_duplicates"] = dup_count
    return out.reset_index(drop=True)


def build_cohorts() -> dict:
    base = load_base()
    cand = individual_season(base)
    report: dict = {
        "source_rows_total": int(len(base)),
        "individual_season_rows": int(len(cand)),
        "dropped_exact_duplicates": int(cand.attrs.get("dropped_duplicates", 0)),
        "seasons_excluded": ["Total (aggregate season)"],
    }

    # ---- strict / clean cohort ---------------------------------------------
    strict = cand[
        (cand["Yield"] > 0)
        & (cand["Area"] > 0)
        & (cand["Production"] > 0)
        & (cand["Yield"] <= STRICT_MAX_YIELD)
    ].reset_index(drop=True)

    # ---- broad cohort -----------------------------------------------------
    # keeps positive-yield rows even with zero/absent area or production
    # (the 'yield without area' population), removing only gross unit errors.
    broad = cand[
        (cand["Yield"] > 0) & (cand["Yield"] <= BROAD_MAX_YIELD)
    ].reset_index(drop=True)

    for name, c in (("strict", strict), ("broad", broad)):
        report[f"{name}_rows"] = int(len(c))
        report[f"{name}_states"] = int(c["State"].nunique())
        report[f"{name}_districts"] = int(c["District"].nunique())
        report[f"{name}_crops"] = int(c["Crop"].nunique())
        report[f"{name}_series"] = int(
            c.groupby(["State", "District", "Crop", "Season"]).ngroups
        )
        report[f"{name}_year_min"] = int(c["YearStart"].min())
        report[f"{name}_year_max"] = int(c["YearStart"].max())
        report[f"{name}_yield_median"] = float(c["Yield"].median())
        report[f"{name}_yield_p99"] = float(c["Yield"].quantile(0.99))
        report[f"{name}_yield_max"] = float(c["Yield"].max())

    # documented discards (non-silent)
    report["discarded_zero_area_positive_yield"] = int(
        ((cand["Yield"] > 0) & (cand["Area"] <= 0)).sum()
    )
    report["discarded_gross_unit_error_gt30000"] = int((cand["Yield"] > BROAD_MAX_YIELD).sum())
    report["discarded_null_yield"] = int(cand["Yield"].isna().sum())

    cols = ["State", "District", "Crop", "Season", "YearStart",
            "Area", "Production", "Yield"]
    strict[cols].to_csv(OUT / "cohort_strict.csv", index=False)
    broad[cols].to_csv(OUT / "cohort_broad.csv", index=False)

    # missing-year matrix (per series count of present years)
    for name, c in (("strict", strict), ("broad", broad)):
        g = c.groupby(["State", "District", "Crop", "Season"]).size()
        report[f"{name}_series_len_hist"] = {
            str(b): int(((g >= lo) & (g <= hi)).sum())
            for b, lo, hi in [("1", 1, 1), ("2", 2, 2), ("3-4", 3, 4),
                              ("5-7", 5, 7), ("8-10", 8, 10), ("11-12", 11, 12)]
        }

    (OUT / "data_prep_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    build_cohorts()
