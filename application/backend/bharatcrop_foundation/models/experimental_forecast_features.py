"""Phase 2E — shared origin-only feature builder for the experimental forecast.

This module is the single source of truth for reconstructing the Phase 2D
pooled-panel RandomForest design matrix at inference time. The windowing maths
mirrors ``phase2d_expanded_yield_forecasting/scripts/features.py`` and
``models.py`` exactly so that a feature row built here is byte-for-byte equal to
the row the research model was trained on. A dedicated parity test imports the
research modules and compares outputs row-by-row; nothing here recomputes the
logic differently.

Every lag / rolling / median / std / trend statistic is derived ONLY from
observations at or before the forecast origin ``O = target_year - horizon``.
Future values are never referenced.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

# Series identity key (matches Phase 2D features.KEY).
KEY = ("State", "District", "Crop", "Season")

# Exact numeric feature order the pooled estimator was fit on (15 columns).
NUMERIC_FEATURES: tuple[str, ...] = (
    "lag1",
    "lag2",
    "lag3",
    "roll3_mean",
    "roll5_mean",
    "hist_std",
    "hist_median",
    "hist_mean",
    "trend_slope",
    "hist_n",
    "has_lag2",
    "has_lag3",
    "origin_year",
    "target_year",
    "horizon",
)

# Low-cardinality categoricals are one-hot encoded; District is an integer code.
LOW_CARDINALITY: tuple[str, ...] = ("Crop", "Season", "State")

DESIGN_NUMERIC_WIDTH = len(NUMERIC_FEATURES)  # 15


def linfit(years: np.ndarray, values: np.ndarray) -> float:
    """OLS slope of value on year (mirrors features._linfit slope branch)."""
    if len(values) < 2:
        return 0.0
    return float(np.polyfit(years, values, 1)[0])


def build_vocab(frame: pd.DataFrame) -> dict[str, list[str]]:
    """Sorted category vocabularies + district codes (mirrors models.build_vocab)."""
    return {
        "districts": sorted(frame["District"].astype(str).unique()),
        **{c: sorted(frame[c].astype(str).unique()) for c in LOW_CARDINALITY},
    }


def series_observations(
    frame: pd.DataFrame,
    *,
    state: str,
    district: str,
    crop: str,
    season: str,
) -> pd.DataFrame:
    """Return the observed rows for one series, sorted by marketing year."""
    mask = (
        frame["State"].astype(str).eq(state)
        & frame["District"].astype(str).eq(district)
        & frame["Crop"].astype(str).eq(crop)
        & frame["Season"].astype(str).eq(season)
    )
    sub = frame.loc[mask].copy()
    sub["YearStart"] = sub["YearStart"].astype(float).astype(int)
    return sub.sort_values("YearStart").reset_index(drop=True)


def origin_feature_row(
    observations: pd.DataFrame,
    *,
    origin_year: int,
    horizon: int,
) -> dict[str, Any]:
    """Build the 15 origin-only numeric features for one (origin, horizon).

    ``observations`` holds the series rows sorted by ``YearStart`` with a
    ``Yield`` column. Only rows with ``YearStart <= origin_year`` are consulted;
    the target year itself may be unobserved (a genuine projection).
    """
    years = observations["YearStart"].to_numpy(dtype=int)
    yields = observations["Yield"].to_numpy(dtype=float)
    ymap: dict[int, float] = dict(zip(years.tolist(), yields.tolist(), strict=True))
    if origin_year not in ymap:
        raise ValueError("origin year is not an observed value for this series.")

    hist_years = np.asarray([y for y in years if y <= origin_year], dtype=float)
    hist_values = np.asarray([ymap[int(y)] for y in hist_years], dtype=float)
    if hist_values.size == 0:
        raise ValueError("no history available at or before the origin.")

    hist_median = float(np.median(hist_values))
    hist_mean = float(np.mean(hist_values))
    hist_std = float(np.std(hist_values)) if hist_values.size >= 2 else 0.0
    trend_slope = linfit(hist_years, hist_values)

    lag1 = float(ymap[origin_year])
    lag2_raw = ymap.get(origin_year - 1)
    lag3_raw = ymap.get(origin_year - 2)
    has_lag2 = lag2_raw is not None
    has_lag3 = lag3_raw is not None
    lag2 = lag2_raw if lag2_raw is not None else hist_median
    lag3 = lag3_raw if lag3_raw is not None else hist_median

    roll3 = hist_values[-3:]
    roll5 = hist_values[-5:]

    return {
        "lag1": lag1,
        "lag2": lag2,
        "lag3": lag3,
        "roll3_mean": float(np.mean(roll3)),
        "roll5_mean": float(np.mean(roll5)),
        "hist_std": hist_std,
        "hist_median": hist_median,
        "hist_mean": hist_mean,
        "trend_slope": trend_slope,
        "hist_n": int(hist_values.size),
        "has_lag2": float(has_lag2),
        "has_lag3": float(has_lag3),
        "origin_year": float(origin_year),
        "target_year": float(origin_year + horizon),
        "horizon": float(horizon),
    }


def make_design_row(
    feature_row: dict[str, Any],
    *,
    crop: str,
    season: str,
    state: str,
    district: str,
    vocab: dict[str, list[str]],
) -> np.ndarray:
    """Turn one identity + numeric feature row into the 66-wide design vector.

    Column order matches models.make_design: numeric(15) then one-hot(Crop),
    one-hot(Season), one-hot(State) over the sorted vocab, then district_code.
    """
    numeric = np.asarray(
        [[float(feature_row[name]) for name in NUMERIC_FEATURES]], dtype=float
    )
    blocks = [numeric]
    for column in LOW_CARDINALITY:
        categories = vocab[column]
        value = {"Crop": crop, "Season": season, "State": state}[column]
        onehot = np.asarray([[1.0 if value == cat else 0.0 for cat in categories]])
        blocks.append(onehot)
    district_map = {v: i for i, v in enumerate(vocab["districts"])}
    district_code = float(district_map.get(district, -1))
    blocks.append(np.asarray([[district_code]]))
    return np.hstack(blocks)


def design_width(vocab: dict[str, list[str]]) -> int:
    return (
        DESIGN_NUMERIC_WIDTH
        + len(vocab["Crop"])
        + len(vocab["Season"])
        + len(vocab["State"])
        + 1
    )
