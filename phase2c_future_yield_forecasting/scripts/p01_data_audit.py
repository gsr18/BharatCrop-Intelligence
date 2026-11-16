"""Phase 2C - Part 1: Data & temporal coverage audit.

Reads the long-format APY dataset and the mandi price snapshot.
Writes a JSON audit + a CSV of per-series observation counts.
Read-only on source data. No production code touched.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LONG = ROOT / "data" / "processed" / "historical_food_grains_apy_long_2013-14_to_2024-25.csv"
MANDI = ROOT / "data" / "raw" / "mandi_prices" / "mandi_prices_2026-10-31.csv"
OUT = Path(__file__).resolve().parents[1] / "artifacts"
OUT.mkdir(parents=True, exist_ok=True)

KEY = ["State", "District", "Crop", "Season"]


def profile_long() -> dict:
    df = pd.read_csv(LONG)
    audit: dict = {"n_rows": int(len(df)), "columns": list(df.columns)}

    # Year is a marketing-year string like "2013-14"; derive a 4-digit YearStart.
    df["YearStart"] = (
        df["Year"].astype(str).str.extract(r"^(\d{4})")[0].astype("Int64")
    )
    years = sorted(int(y) for y in df["YearStart"].dropna().unique())
    audit["year_start"] = years[0]
    audit["year_end"] = years[-1]
    audit["distinct_years"] = years
    audit["n_years"] = len(years)

    # Yield numeric coverage
    df["Yield"] = pd.to_numeric(df["Yield"], errors="coerce")
    audit["yield_nonnull"] = int(df["Yield"].notna().sum())
    audit["yield_null"] = int(df["Yield"].isna().sum())
    audit["yield_negative"] = int((df["Yield"] < 0).sum())
    audit["yield_zero"] = int((df["Yield"] == 0).sum())
    audit["yield_min"] = float(df["Yield"].min())
    audit["yield_max"] = float(df["Yield"].max())
    audit["yield_median"] = float(df["Yield"].median())
    audit["yield_p99"] = float(df["Yield"].quantile(0.99))

    # Distinct groups
    audit["n_states"] = int(df["State"].nunique())
    audit["n_districts"] = int(df["District"].nunique())
    audit["n_crops"] = int(df["Crop"].nunique())
    audit["n_seasons"] = int(df["Season"].nunique())
    audit["n_crop_categories"] = int(df["Crop_Category"].nunique())
    audit["crops"] = sorted(df["Crop"].dropna().unique().tolist())
    audit["seasons"] = sorted(df["Season"].dropna().unique().tolist())
    audit["crop_categories"] = sorted(df["Crop_Category"].dropna().unique().tolist())

    # Per crop-district-season series: usable annual observations (yield notna)
    valid = df[df["Yield"].notna() & (df["Yield"] > 0)].copy()
    grp = valid.groupby(KEY)
    counts = grp.size().rename("obs_count")
    span = grp["YearStart"].agg(["min", "max"])
    span["span"] = span["max"] - span["min"] + 1
    series = counts.to_frame().join(span)
    series = series.reset_index()
    series.to_csv(OUT / "series_observation_counts.csv", index=False)

    audit["n_series_with_valid_yield"] = int(len(series))
    obs = series["obs_count"]
    audit["obs_count_min"] = int(obs.min())
    audit["obs_count_median"] = float(obs.median())
    audit["obs_count_mean"] = float(obs.mean())
    audit["obs_count_max"] = int(obs.max())
    # distribution of series length
    audit["series_len_histogram"] = {
        str(bucket): int(((obs >= lo) & (obs <= hi)).sum())
        for bucket, lo, hi in [
            ("1", 1, 1), ("2", 2, 2), ("3-4", 3, 4), ("5-7", 5, 7),
            ("8-10", 8, 10), ("11-12", 11, 12),
        ]
    }
    # series with >=3 (needed for T+2 expanding-window) and >=8
    audit["n_series_ge3"] = int((obs >= 3).sum())
    audit["n_series_ge5"] = int((obs >= 5).sum())
    audit["n_series_ge8"] = int((obs >= 8).sum())
    audit["n_series_ge10"] = int((obs >= 10).sum())

    # Gap analysis: obs_count vs span (irregular / missing years)
    gaps = (series["span"] - series["obs_count"])
    audit["series_with_gaps"] = int((gaps > 0).sum())
    audit["median_gap_years"] = float(gaps.median())

    # Crop-category balance
    audit["rows_by_crop_category"] = {
        str(k): int(v) for k, v in df["Crop_Category"].value_counts().items()
    }
    # count series per category (a series has one Crop_Category)
    cat_counts = (
        valid.groupby(KEY)["Crop_Category"].first().reset_index()
        .groupby("Crop_Category").size()
    )
    audit["series_by_crop_category"] = {
        str(k): int(v) for k, v in cat_counts.items()
    }

    return audit


def profile_mandi() -> dict:
    m = pd.read_csv(MANDI)
    audit: dict = {
        "n_rows": int(len(m)),
        "columns": list(m.columns),
        "n_states": int(m["State"].nunique()),
        "n_districts": int(m["District"].nunique()),
        "n_commodities": int(m["Commodity"].nunique()),
    }
    dates = pd.to_datetime(m["Arrival_Date"], errors="coerce", dayfirst=True)
    audit["distinct_arrival_dates"] = sorted(
        d.strftime("%Y-%m-%d") for d in dates.dropna().dt.normalize().unique()
    )
    audit["arrival_date_min"] = str(dates.min())
    audit["arrival_date_max"] = str(dates.max())
    # overlap of mandi State/District names with APY
    apy = pd.read_csv(LONG, usecols=["State", "District", "Crop"])
    audit["mandi_states_matching_apy"] = int(
        len(set(m["State"].str.strip()) & set(apy["State"].str.strip()))
    )
    audit["mandi_districts_matching_apy"] = int(
        len(set(m["District"].str.strip()) & set(apy["District"].str.strip()))
    )
    audit["mandi_commodities_sample"] = sorted(
        m["Commodity"].dropna().unique().tolist()
    )[:40]
    return audit


def main() -> None:
    result = {"apy_long": profile_long(), "mandi_snapshot": profile_mandi()}
    (OUT / "data_audit.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result["apy_long"], indent=2)[:4000])
    print("=== MANDI ===")
    print(json.dumps(result["mandi_snapshot"], indent=2)[:1500])


if __name__ == "__main__":
    main()
