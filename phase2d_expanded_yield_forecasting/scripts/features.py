"""Phase 2D — origin-safe feature engineering.

All lag/rolling/median/std/trend features use ONLY observations at or before
the forecast origin O = target_year - h. Future values are never referenced.
Missing history is handled with an explicit fallback (historical median) plus
boolean availability flags, so nothing is silently imputed away.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

KEY = ["State", "District", "Crop", "Season"]

NUMERIC_FEATURES = [
    "lag1", "lag2", "lag3",
    "roll3_mean", "roll5_mean",
    "hist_std", "hist_median", "hist_mean",
    "trend_slope", "hist_n", "has_lag2", "has_lag3",
    "origin_year", "target_year", "horizon",
]
CATEGORICAL_FEATURES = ["Crop", "Season", "State", "District"]


def _linfit(years: np.ndarray, vals: np.ndarray):
    """Return (slope, intercept) from an ordinary least-squares line."""
    if len(vals) < 2:
        return 0.0, float(vals[-1]) if len(vals) else 0.0
    slope = float(np.polyfit(years, vals, 1)[0])
    intercept = float(np.mean(vals) - slope * np.mean(years))
    return slope, intercept


def series_arrays(df: pd.DataFrame) -> dict:
    """Return {key_tuple: (sorted_years:int[], yields:float[])} per series."""
    out = {}
    for key, grp in df.groupby(KEY, sort=False):
        g = grp.sort_values("YearStart")
        yrs = g["YearStart"].astype(int).to_numpy()
        out[tuple(key)] = (yrs, g["Yield"].astype(float).to_numpy(),
                           {str(key[i]): grp.iloc[0][KEY[i]] for i in range(4)})
    return out


def build_forecast_rows(df: pd.DataFrame, horizons=(1, 2, 3, 4, 5)) -> pd.DataFrame:
    """One row per (series, target_year, horizon) with only past-available features."""
    rows: list[dict] = []
    for key, grp in df.groupby(KEY, sort=False):
        g = grp.sort_values("YearStart")
        yrs = g["YearStart"].astype(int).to_numpy()
        vals = g["Yield"].astype(float).to_numpy()
        ymap = dict(zip(yrs, vals))
        ident = {"State": key[0], "District": key[1], "Crop": key[2], "Season": key[3]}
        min_target = min(yrs)
        for target_year, target_yield in ymap.items():
            for h in horizons:
                origin = target_year - h
                if origin not in ymap:
                    continue
                hist_y = np.asarray([y for y in yrs if y <= origin], dtype=float)
                hist_v = np.asarray([ymap[int(y)] for y in hist_y], dtype=float)
                if hist_v.size == 0:
                    continue
                h_median = float(np.median(hist_v))
                h_mean = float(np.mean(hist_v))
                h_std = float(np.std(hist_v)) if hist_v.size >= 2 else 0.0
                slope, intercept = _linfit(hist_y, hist_v)
                lag1 = float(ymap[origin])
                l2 = ymap.get(origin - 1)
                l3 = ymap.get(origin - 2)
                has_lag2 = l2 is not None
                has_lag3 = l3 is not None
                lag2 = float(l2) if has_lag2 else h_median
                lag3 = float(l3) if has_lag3 else h_median
                r3 = hist_v[-3:] if hist_v.size >= 1 else hist_v
                r5 = hist_v[-5:] if hist_v.size >= 1 else hist_v
                rows.append({
                    **ident,
                    "horizon": h,
                    "origin_year": origin,
                    "target_year": target_year,
                    "lag1": lag1, "lag2": lag2, "lag3": lag3,
                    "roll3_mean": float(np.mean(r3)),
                    "roll5_mean": float(np.mean(r5)),
                    "hist_std": h_std, "hist_median": h_median, "hist_mean": h_mean,
                    "trend_slope": slope, "hist_n": int(hist_v.size),
                    "has_lag2": float(has_lag2), "has_lag3": float(has_lag3),
                    "target_yield": float(target_yield),
                    # origin-only baselines
                    "b_prev": lag1,
                    "b_mean": h_mean,
                    "b_median": h_median,
                    "b_trend": float(slope * target_year + intercept),
                    "b_ar1": _ar1_forecast(hist_v, hist_y, target_year),
                    "_cold_ref": min_target,
                })
    fx = pd.DataFrame(rows)
    if len(fx):
        fx["cold_start"] = (fx["target_year"] == fx["_cold_ref"]).astype(int)
        fx = fx.drop(columns=["_cold_ref"])
    return fx


def _ar1_forecast(hist_v: np.ndarray, hist_y: np.ndarray, target_year: int) -> float:
    """Damped AR(1)-style forecast: last value plus a shrunk first difference."""
    if hist_v.size < 2:
        return float(hist_v[-1])
    diffs = np.diff(hist_v)
    last = float(hist_v[-1])
    step = float(np.mean(diffs)) * 0.5  # damping factor 0.5
    steps = max(1, target_year - int(hist_y[-1]))
    return float(last + step * steps)
