from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

WEATHER_VALUE_COLUMNS = ("T2M_MAX", "T2M_MIN", "PRECTOTCORR")
BASE_PANEL_COLUMNS = (
    "cell_id",
    "latitude",
    "longitude",
    "date",
    *WEATHER_VALUE_COLUMNS,
)
DEFAULT_LAGS_DAYS_BEFORE_TARGET = (1, 2, 3, 7, 14, 30)
DEFAULT_ROLLING_WINDOWS = (3, 7, 14, 30)
DEFAULT_WET_DAY_THRESHOLD_MM = 1.0
DAY_OF_YEAR_PERIOD_DAYS = 365.2425
SEASON_MONTHS = {
    "winter": (1, 2),
    "pre_monsoon": (3, 4, 5),
    "monsoon": (6, 7, 8, 9),
    "post_monsoon": (10, 11, 12),
}
FORBIDDEN_COLUMN_TOKENS = ("apy", "crop", "yield", "suitability", "production")


class FeatureInputError(ValueError):
    """Raised when a feature request could cross cells or use a non-weather schema."""


def _validate_weather_panel(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in BASE_PANEL_COLUMNS if column not in frame.columns]
    if missing:
        raise FeatureInputError(f"Weather panel is missing columns: {missing}.")
    forbidden = [
        str(column)
        for column in frame.columns
        if any(token in str(column).casefold() for token in FORBIDDEN_COLUMN_TOKENS)
    ]
    if forbidden:
        raise FeatureInputError(f"Non-weather columns are outside this feature module: {forbidden}.")
    if frame.empty:
        raise FeatureInputError("Weather panel is empty.")
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"], utc=True, errors="raise").dt.normalize()
    result = result.sort_values(["cell_id", "date"], kind="mergesort").reset_index(drop=True)
    if result.duplicated(["cell_id", "date"]).any():
        raise FeatureInputError("Weather panel has duplicate (cell_id, date) keys.")
    if result[list(WEATHER_VALUE_COLUMNS)].isna().any(axis=None):
        raise FeatureInputError("Weather panel contains missing source values.")
    if not np.isfinite(result[list(WEATHER_VALUE_COLUMNS)].to_numpy(dtype=np.float64)).all():
        raise FeatureInputError("Weather panel contains non-finite source values.")
    if (result["PRECTOTCORR"] < 0).any():
        raise FeatureInputError("Weather panel contains negative precipitation.")
    if (result["T2M_MIN"] > result["T2M_MAX"]).any():
        raise FeatureInputError("Weather panel contains T2M_MIN greater than T2M_MAX.")
    return result


def _assert_consecutive_daily_rows(frame: pd.DataFrame) -> None:
    for cell_id, group in frame.groupby("cell_id", sort=False):
        differences = group["date"].diff().dropna().dt.days
        if not differences.eq(1).all():
            raise FeatureInputError(
                f"Cell {cell_id} has a date gap; rolling features require consecutive UTC dates."
            )


def add_temperature_range(frame: pd.DataFrame) -> pd.DataFrame:
    """Add same-day max-minus-min temperature in Celsius."""
    result = _validate_weather_panel(frame)
    result["T2M_RANGE"] = result["T2M_MAX"] - result["T2M_MIN"]
    return result


def add_cyclical_day_of_year(
    frame: pd.DataFrame,
    *,
    date_column: str = "date",
    period_days: float = DAY_OF_YEAR_PERIOD_DAYS,
) -> pd.DataFrame:
    """Add sine/cosine calendar features for a known UTC calendar date."""
    if date_column not in frame.columns:
        raise FeatureInputError(f"Date column {date_column!r} is missing.")
    if period_days <= 0:
        raise FeatureInputError("Day-of-year period must be positive.")
    result = frame.copy()
    dates = pd.to_datetime(result[date_column], utc=True, errors="raise")
    phase = 2.0 * np.pi * dates.dt.dayofyear.astype(np.float64) / period_days
    result["day_of_year_sin"] = np.sin(phase)
    result["day_of_year_cos"] = np.cos(phase)
    return result


def _rolling_by_cell(
    frame: pd.DataFrame,
    values: pd.Series,
    window: int,
    operation: str,
    *,
    min_periods: int | None = None,
) -> pd.Series:
    required = window if min_periods is None else min_periods
    grouped = values.groupby(frame["cell_id"], sort=False)
    rolling = grouped.rolling(window=window, min_periods=required)
    result = getattr(rolling, operation)()
    if isinstance(result.index, pd.MultiIndex):
        result.index = result.index.droplevel(0)
    return result.reindex(frame.index)


def build_prediction_features(
    panel: pd.DataFrame,
    *,
    lags_days_before_target: Iterable[int] = DEFAULT_LAGS_DAYS_BEFORE_TARGET,
    rolling_windows: Iterable[int] = DEFAULT_ROLLING_WINDOWS,
    wet_day_threshold_mm: float = DEFAULT_WET_DAY_THRESHOLD_MM,
) -> pd.DataFrame:
    """Create one-day-ahead rows whose feature window ends at the forecast origin.

    Input rows are observations on the as-of date. ``*_lag_1`` is therefore the
    value observed on the as-of date, one day before ``target_date``. All rolling
    windows include the as-of date and earlier rows only. The next observation is
    copied only into the target columns.
    """
    if wet_day_threshold_mm < 0:
        raise FeatureInputError("Wet-day threshold must be non-negative.")
    result = add_temperature_range(panel)
    _assert_consecutive_daily_rows(result)
    lags = tuple(sorted(set(int(value) for value in lags_days_before_target)))
    windows = tuple(sorted(set(int(value) for value in rolling_windows)))
    if any(value < 1 for value in lags) or any(value < 1 for value in windows):
        raise FeatureInputError("Lag and rolling-window sizes must be positive integers.")

    groups = result.groupby("cell_id", sort=False)
    result["target_date"] = groups["date"].shift(-1)
    result["target_T2M_MAX"] = groups["T2M_MAX"].shift(-1)
    result["target_PRECTOTCORR"] = groups["PRECTOTCORR"].shift(-1)
    result["history_days"] = groups.cumcount() + 1
    for lag in lags:
        source_offset = lag - 1
        for variable in (*WEATHER_VALUE_COLUMNS, "T2M_RANGE"):
            result[f"{variable}_lag_{lag}"] = groups[variable].shift(source_offset)
    for window in windows:
        for variable in (*WEATHER_VALUE_COLUMNS, "T2M_RANGE"):
            result[f"{variable}_roll_mean_{window}"] = _rolling_by_cell(
                result, result[variable], window, "mean"
            )
            result[f"{variable}_roll_std_{window}"] = _rolling_by_cell(
                result, result[variable], window, "std"
            )
        precip = result["PRECTOTCORR"]
        result[f"PRECTOTCORR_roll_sum_{window}"] = _rolling_by_cell(
            result, precip, window, "sum"
        )
        wet_days = precip.ge(wet_day_threshold_mm).astype(np.float64)
        wet_count = _rolling_by_cell(result, wet_days, window, "sum")
        result[f"wet_day_count_{window}"] = wet_count
        result[f"wet_day_fraction_{window}"] = wet_count / float(window)

    result = result.loc[result["target_date"].notna()].copy()
    result["as_of_date"] = result["date"]
    result = result.drop(columns=["date"])
    result = result.rename(
        columns={
            "target_T2M_MAX": "target_T2M_MAX_next_day",
            "target_PRECTOTCORR": "target_PRECTOTCORR_next_day",
        }
    )
    result = add_cyclical_day_of_year(result, date_column="target_date")
    return result.reset_index(drop=True)


def build_daily_pattern_features(
    panel: pd.DataFrame,
    *,
    rolling_windows: Iterable[int] = (3, 7),
    wet_day_threshold_mm: float = DEFAULT_WET_DAY_THRESHOLD_MM,
) -> pd.DataFrame:
    """Build retrospective daily descriptors; same-day values are intentionally used."""
    result = add_temperature_range(panel)
    _assert_consecutive_daily_rows(result)
    if wet_day_threshold_mm < 0:
        raise FeatureInputError("Wet-day threshold must be non-negative.")
    result["PRECTOTCORR_log1p"] = np.log1p(result["PRECTOTCORR"])
    result = add_cyclical_day_of_year(result)
    for window in sorted(set(int(value) for value in rolling_windows)):
        if window < 1:
            raise FeatureInputError("Rolling-window sizes must be positive integers.")
        result[f"PRECTOTCORR_trailing_sum_{window}"] = _rolling_by_cell(
            result, result["PRECTOTCORR"], window, "sum"
        )
        result[f"T2M_MAX_trailing_mean_{window}"] = _rolling_by_cell(
            result, result["T2M_MAX"], window, "mean"
        )
        wet = result["PRECTOTCORR"].ge(wet_day_threshold_mm).astype(np.float64)
        result[f"wet_day_fraction_{window}"] = _rolling_by_cell(
            result, wet, window, "mean"
        )
    return result


def _period_summary(
    frame: pd.DataFrame,
    period_columns: list[str],
    *,
    wet_day_threshold_mm: float = DEFAULT_WET_DAY_THRESHOLD_MM,
) -> pd.DataFrame:
    result = add_temperature_range(frame)
    result["wet_day"] = result["PRECTOTCORR"].ge(wet_day_threshold_mm)
    keys = ["cell_id", "latitude", "longitude", *period_columns]
    summary = (
        result.groupby(keys, as_index=False, sort=True, observed=True)
        .agg(
            valid_days=("date", "count"),
            T2M_MAX_mean=("T2M_MAX", "mean"),
            T2M_MAX_std=("T2M_MAX", "std"),
            T2M_MIN_mean=("T2M_MIN", "mean"),
            T2M_MIN_std=("T2M_MIN", "std"),
            T2M_RANGE_mean=("T2M_RANGE", "mean"),
            T2M_RANGE_std=("T2M_RANGE", "std"),
            PRECTOTCORR_total_mm=("PRECTOTCORR", "sum"),
            PRECTOTCORR_mean_mm_day=("PRECTOTCORR", "mean"),
            PRECTOTCORR_p95_mm_day=("PRECTOTCORR", lambda values: values.quantile(0.95)),
            wet_day_count=("wet_day", "sum"),
        )
        .sort_values(keys, kind="mergesort")
        .reset_index(drop=True)
    )
    summary["wet_day_fraction"] = summary["wet_day_count"] / summary["valid_days"]
    summary["wet_day_threshold_mm_day"] = wet_day_threshold_mm
    return summary


def build_monthly_summaries(
    panel: pd.DataFrame,
    *,
    wet_day_threshold_mm: float = DEFAULT_WET_DAY_THRESHOLD_MM,
) -> pd.DataFrame:
    """Retrospective cell-year-month summaries from all observed days in each month."""
    if wet_day_threshold_mm < 0:
        raise FeatureInputError("Wet-day threshold must be non-negative.")
    result = _validate_weather_panel(panel)
    result["year"] = result["date"].dt.year.astype(np.int16)
    result["month"] = result["date"].dt.month.astype(np.int8)
    return _period_summary(
        result, ["year", "month"], wet_day_threshold_mm=wet_day_threshold_mm
    )


def build_seasonal_summaries(
    panel: pd.DataFrame,
    *,
    wet_day_threshold_mm: float = DEFAULT_WET_DAY_THRESHOLD_MM,
) -> pd.DataFrame:
    """Retrospective fixed weather seasons; bins are not agricultural seasons."""
    if wet_day_threshold_mm < 0:
        raise FeatureInputError("Wet-day threshold must be non-negative.")
    result = _validate_weather_panel(panel)
    result["year"] = result["date"].dt.year.astype(np.int16)
    result["month"] = result["date"].dt.month.astype(np.int8)
    month_to_season = {
        month: season for season, months in SEASON_MONTHS.items() for month in months
    }
    result["season"] = result["month"].map(month_to_season)
    if result["season"].isna().any():
        raise FeatureInputError("A date could not be assigned to a fixed weather season.")
    summary = _period_summary(
        result, ["year", "season"], wet_day_threshold_mm=wet_day_threshold_mm
    )
    summary["season"] = pd.Categorical(
        summary["season"], categories=list(SEASON_MONTHS), ordered=True
    )
    return summary.sort_values(
        ["cell_id", "latitude", "longitude", "year", "season"], kind="mergesort"
    ).reset_index(drop=True)


def describe_feature_schema(config: dict[str, object]) -> dict[str, object]:
    """Return a deterministic, explicit feature definition for versioned metadata."""
    feature_config = config["features"]
    lags = tuple(int(value) for value in feature_config["prediction_lags_days_before_target"])
    windows = tuple(int(value) for value in feature_config["rolling_windows_days"])
    threshold = float(feature_config["wet_day_threshold_mm_day"])
    seasons = {
        str(name): [int(month) for month in months]
        for name, months in feature_config["season_bins"].items()
    }
    history_variables = (*WEATHER_VALUE_COLUMNS, "T2M_RANGE")
    return {
        "feature_schema_version": "1.0.0",
        "input_contract": {
            "row_key": ["cell_id", "date"],
            "weather_columns": list(WEATHER_VALUE_COLUMNS),
            "sort_order": ["cell_id", "date"],
            "frequency": "one consecutive UTC calendar day per cell",
        },
        "prediction_time": {
            "origin": "as_of_date, after that UTC day's weather observations are available",
            "target_date": "the immediately following UTC calendar day",
            "target_columns": ["target_T2M_MAX_next_day", "target_PRECTOTCORR_next_day"],
            "availability_rule": "All feature source dates are less than or equal to as_of_date; targets are shifted from target_date and never enter features.",
            "lag_definition": "lag_k uses the observation k-1 calendar days before target_date, so lag_1 equals the as_of_date observation.",
            "rolling_definition": "Trailing windows include as_of_date and only preceding observations; min_periods equals the full window; standard deviation uses sample ddof=1.",
        },
        "features": {
            "temperature_range": {
                "name": "T2M_RANGE",
                "formula": "T2M_MAX - T2M_MIN",
                "unit": "C",
            },
            "cyclical_day_of_year": {
                "columns": ["day_of_year_sin", "day_of_year_cos"],
                "formula": "sin/cos(2*pi*day_of_year/period_days)",
                "period_days": float(feature_config["day_of_year_period_days"]),
                "prediction_date": "target_date",
            },
            "lagged_weather": {
                "source_columns": list(history_variables),
                "lags_days_before_target": list(lags),
                "columns": [f"{name}_lag_{lag}" for lag in lags for name in history_variables],
            },
            "trailing_rolling": {
                "source_columns": list(history_variables),
                "window_days": list(windows),
                "statistics": ["mean", "sample_std_ddof_1"],
                "columns": [
                    f"{name}_roll_{stat}_{window}"
                    for window in windows
                    for name in history_variables
                    for stat in ("mean", "std")
                ],
            },
            "precipitation_rolling": {
                "window_days": list(windows),
                "wet_day_threshold_mm_day": threshold,
                "columns": [
                    column
                    for window in windows
                    for column in (
                        f"PRECTOTCORR_roll_sum_{window}",
                        f"wet_day_count_{window}",
                        f"wet_day_fraction_{window}",
                    )
                ],
                "wet_day_definition": "PRECTOTCORR >= wet_day_threshold_mm_day",
            },
            "daily_pattern_analysis": {
                "semantics": "Retrospective descriptive features; same-day observations may be included.",
                "columns": [
                    "T2M_RANGE",
                    "PRECTOTCORR_log1p",
                    "day_of_year_sin",
                    "day_of_year_cos",
                    *[
                        column
                        for window in (3, 7)
                        for column in (
                            f"PRECTOTCORR_trailing_sum_{window}",
                            f"T2M_MAX_trailing_mean_{window}",
                            f"wet_day_fraction_{window}",
                        )
                    ],
                ],
            },
            "monthly_summary": {
                "group_key": ["cell_id", "year", "month"],
                "statistics": ["valid_days", "mean", "sample_std", "precip_sum", "precip_mean", "precip_p95", "wet_day_count", "wet_day_fraction"],
                "semantics": "Retrospective; uses every observation in the completed calendar month.",
            },
            "seasonal_summary": {
                "group_key": ["cell_id", "year", "season"],
                "month_bins": seasons,
                "statistics": ["valid_days", "mean", "sample_std", "precip_sum", "precip_mean", "precip_p95", "wet_day_count", "wet_day_fraction"],
                "semantics": "Retrospective fixed weather month bins; not agricultural seasons and not prediction-time features.",
            },
        },
        "weather_value_columns": list(WEATHER_VALUE_COLUMNS),
        "forbidden_input_domains": ["APY", "crop", "yield", "agricultural suitability", "production"],
    }
