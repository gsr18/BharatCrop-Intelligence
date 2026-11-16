from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from weather_intelligence.features import (
    FeatureInputError,
    add_cyclical_day_of_year,
    add_temperature_range,
    build_daily_pattern_features,
    build_monthly_summaries,
    build_prediction_features,
    build_seasonal_summaries,
    describe_feature_schema,
)


def _panel(*, days: int = 45, cells: tuple[str, ...] = ("A", "B")) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    start = datetime(2020, 1, 1, tzinfo=UTC)
    for cell_index, cell_id in enumerate(cells):
        for offset in range(days):
            rows.append(
                {
                    "cell_id": cell_id,
                    "latitude": 10.0 + cell_index,
                    "longitude": 80.0 + cell_index,
                    "date": start + timedelta(days=offset),
                    "T2M_MAX": 20.0 + offset + cell_index * 100,
                    "T2M_MIN": 10.0 + offset + cell_index * 100,
                    "PRECTOTCORR": float(cell_index * 10 + (offset % 4)),
                }
            )
    return pd.DataFrame(rows)


def test_temperature_range_and_cyclical_date_features() -> None:
    panel = _panel(days=3, cells=("A",))
    with_range = add_temperature_range(panel)
    assert with_range["T2M_RANGE"].tolist() == [10.0, 10.0, 10.0]
    cyclical = add_cyclical_day_of_year(panel)
    assert np.isfinite(cyclical[["day_of_year_sin", "day_of_year_cos"]].to_numpy()).all()


def test_prediction_lag_and_rolling_features_use_only_prior_rows() -> None:
    panel = _panel(days=40, cells=("A",))
    features = build_prediction_features(
        panel,
        lags_days_before_target=(1, 2),
        rolling_windows=(3,),
    )
    row = features.loc[features["as_of_date"] == pd.Timestamp("2020-01-10", tz="UTC")].iloc[0]
    assert row["T2M_MAX_lag_1"] == 29.0
    assert row["T2M_MAX_lag_2"] == 28.0
    assert row["T2M_MAX_roll_mean_3"] == 28.0
    assert row["target_date"] == pd.Timestamp("2020-01-11", tz="UTC")
    assert row["target_T2M_MAX_next_day"] == 30.0
    assert "date" not in features.columns
    assert "as_of_date" in features.columns


def test_rolling_windows_are_isolated_by_cell() -> None:
    features = build_prediction_features(
        _panel(days=5), lags_days_before_target=(1,), rolling_windows=(3,)
    )
    b_rows = features.loc[features["cell_id"] == "B"].reset_index(drop=True)
    assert np.isnan(b_rows.loc[0, "PRECTOTCORR_roll_sum_3"])
    assert b_rows.loc[2, "PRECTOTCORR_roll_sum_3"] == 33.0
    assert b_rows.loc[2, "wet_day_count_3"] == 3.0
    assert b_rows.loc[2, "wet_day_fraction_3"] == 1.0


def test_prediction_features_do_not_change_when_future_weather_changes() -> None:
    original = _panel(days=40, cells=("A",))
    changed = original.copy()
    origin = pd.Timestamp("2020-01-20", tz="UTC")
    future = changed["date"] > origin
    changed.loc[future, "T2M_MAX"] += 1000.0
    changed.loc[future, "T2M_MIN"] += 1000.0
    changed.loc[future, "PRECTOTCORR"] += 1000.0
    baseline_features = build_prediction_features(original)
    changed_features = build_prediction_features(changed)
    base_row = baseline_features.loc[baseline_features["as_of_date"] == origin].iloc[0]
    changed_row = changed_features.loc[changed_features["as_of_date"] == origin].iloc[0]
    target_columns = {"target_T2M_MAX_next_day", "target_PRECTOTCORR_next_day"}
    feature_columns = [column for column in baseline_features if column not in target_columns]
    pdt.assert_series_equal(base_row[feature_columns], changed_row[feature_columns])
    assert changed_row["target_T2M_MAX_next_day"] != base_row["target_T2M_MAX_next_day"]
    assert changed_row["target_PRECTOTCORR_next_day"] != base_row["target_PRECTOTCORR_next_day"]


def test_missing_daily_observation_is_rejected_before_rolling() -> None:
    panel = _panel(days=8, cells=("A",))
    panel = panel.loc[panel["date"] != pd.Timestamp("2020-01-04", tz="UTC")]
    with pytest.raises(FeatureInputError, match="date gap"):
        build_prediction_features(panel, rolling_windows=(3,))


def test_monthly_seasonal_and_daily_pattern_summaries() -> None:
    panel = _panel(days=45, cells=("A",))
    daily = build_daily_pattern_features(panel, rolling_windows=(3,))
    assert {"T2M_RANGE", "PRECTOTCORR_log1p", "wet_day_fraction_3"}.issubset(daily.columns)
    monthly = build_monthly_summaries(panel, wet_day_threshold_mm=2.0)
    assert monthly[["year", "month"]].drop_duplicates().values.tolist() == [[2020, 1], [2020, 2]]
    assert monthly["wet_day_threshold_mm_day"].eq(2.0).all()
    seasonal = build_seasonal_summaries(panel)
    assert set(seasonal["season"].astype(str)) == {"winter"}


def test_feature_outputs_are_reproducible_and_weather_only(config: dict[str, object]) -> None:
    panel = _panel(days=40, cells=("A",))
    first = build_prediction_features(panel)
    second = build_prediction_features(panel)
    pdt.assert_frame_equal(first, second, check_exact=True)
    schema = describe_feature_schema(config)
    assert schema["prediction_time"]["target_date"] == "the immediately following UTC calendar day"
    assert "PRECTOTCORR_roll_sum_30" in schema["features"]["precipitation_rolling"]["columns"]


@pytest.mark.parametrize("mutation", ["nan", "missing", "duplicate", "negative_precip", "invalid_range"])
def test_invalid_weather_panel_is_rejected(mutation: str) -> None:
    panel = _panel(days=5, cells=("A",))
    if mutation == "nan":
        panel.loc[0, "T2M_MAX"] = float("nan")
    elif mutation == "missing":
        panel.loc[0, "PRECTOTCORR"] = None
    elif mutation == "duplicate":
        panel = pd.concat([panel, panel.iloc[[0]]], ignore_index=True)
    elif mutation == "negative_precip":
        panel.loc[0, "PRECTOTCORR"] = -1.0
    else:
        panel.loc[0, "T2M_MIN"] = panel.loc[0, "T2M_MAX"] + 1.0
    with pytest.raises(FeatureInputError):
        add_temperature_range(panel)
