from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from bharatcrop_foundation.models.weather_data import (
    REFERENCE_COLUMNS,
    WEATHER_COLUMNS,
    WEATHER_FLAGS,
    WEATHER_METRICS,
    WeatherDataError,
    WeatherDataService,
)


def _service(tmp_path: Path) -> WeatherDataService:
    annual_rows: list[dict[str, object]] = []
    for year, minimum, maximum, precipitation in (
        (2013, 18.0, 30.0, 400.0),
        (2014, 19.0, 31.0, 500.0),
        (2015, 20.0, 32.0, 600.0),
    ):
        row: dict[str, object] = {column: None for column in WEATHER_COLUMNS}
        row.update(
            {
                "apy_geography_id": "APY-GEO-0001",
                "State": "Test State",
                "District": "Test District",
                "district_latitude": 12.0,
                "district_longitude": 77.0,
                "coordinate_source": "test fixture",
                "geography_confidence": "HIGH",
                "nearest_grid_latitude": 12.1,
                "nearest_grid_longitude": 77.1,
                "nearest_grid_elevation_m": 900.0,
                "nearest_grid_distance_km": 10.0,
                "latitude": 12.1,
                "longitude": 77.1,
                "calendar_year": year,
                "tmin_mean_c": minimum,
                "tmin_min_c": minimum - 5,
                "tmax_mean_c": maximum,
                "tmax_max_c": maximum + 8,
                "precipitation_total_mm": precipitation,
                "precipitation_mean_mm_day": precipitation / 365,
                "precipitation_max_mm_day": 20.0,
                "tmin_valid_days": 365,
                "tmax_valid_days": 365,
                "precipitation_valid_days": 365,
            }
        )
        row.update({flag: False for flag in WEATHER_FLAGS})
        annual_rows.append(row)
    annual_path = tmp_path / "weather.csv"
    pd.DataFrame(annual_rows, columns=WEATHER_COLUMNS).to_csv(
        annual_path, index=False
    )

    reference: dict[str, object] = {
        column: None for column in REFERENCE_COLUMNS
    }
    reference.update(
        {
            "State": "Test State",
            "District": "Test District",
            "weather_years": 3,
            "weather_coverage_pct": 100.0,
            "coverage_status": "Good coverage",
        }
    )
    for metric in WEATHER_METRICS:
        reference[f"{metric}_historical_median"] = 31.0
        reference[f"{metric}_historical_p10"] = 19.0
        reference[f"{metric}_historical_p90"] = 31.0
    reference_path = tmp_path / "reference.csv"
    pd.DataFrame([reference], columns=REFERENCE_COLUMNS).to_csv(
        reference_path, index=False
    )
    history_path = tmp_path / "history.csv"
    pd.DataFrame(
        [
            {
                "State": "Test State",
                "District": "Test District",
                "year": 2013,
            }
        ]
    ).to_csv(history_path, index=False)
    unmatched_path = tmp_path / "unmatched.csv"
    pd.DataFrame(columns=["State", "District", "apy_geography_id"]).to_csv(
        unmatched_path, index=False
    )
    return WeatherDataService(
        annual_path=annual_path,
        reference_path=reference_path,
        history_path=history_path,
        unmatched_path=unmatched_path,
        integration_path=tmp_path / "integration.csv",
        integration_summary_path=tmp_path / "integration-summary.csv",
        classifier_evaluation_path=tmp_path / "evaluation.json",
        intelligence_metadata_path=tmp_path / "metadata.json",
    )


def test_fixture_data_supports_temperature_trend_and_historical_anomalies(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)

    result = service.trends(
        metric="tmax_mean_c",
        state="Test State",
        district="Test District",
    )
    assert result["series"][0]["yearly_values"][0]["value"] == 30.0
    assert result["series"][0]["yearly_values"][0]["mean"] == 30.0
    assert result["series"][0]["yearly_values"][0]["median"] == 30.0
    assert result["series"][0]["yearly_values"][0]["maximum"] == 30.0
    assert result["series"][0]["observation_count"] == 3
    assert "not long-term climate trends" in result["trend_method"]

    anomalies = service.anomalies(
        metric="tmin_mean_c",
        state="Test State",
        district="Test District",
        year_start=2013,
        year_end=2013,
    )
    assert anomalies["records"][0]["historical_percentile_status"]["tmin_mean_c"][
        "status"
    ] == "Below historical range"


def test_fixture_data_reports_coverage_and_rejects_unsupported_filters(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    assert service.options(state="Test State")["districts"] == ["Test District"]
    assert service.overview(year=2014)["record_count"] == 1
    assert service.coverage(state="Test State")["coverage_summary"][
        "locations_with_weather"
    ] == 1

    with pytest.raises(ValueError, match="State is not supported"):
        service.options(state="Missing State")
    with pytest.raises(ValueError, match="metric is not supported"):
        service.trends(metric="relative_humidity")
    with pytest.raises(ValueError, match="outside weather dataset coverage"):
        service.overview(year=2012)


def test_missing_required_processed_data_is_not_reported_as_ready(
    tmp_path: Path,
) -> None:
    missing_service = WeatherDataService(
        annual_path=tmp_path / "missing-weather.csv",
        reference_path=tmp_path / "missing-reference.csv",
        history_path=tmp_path / "missing-history.csv",
        unmatched_path=tmp_path / "missing-unmatched.csv",
        integration_path=tmp_path / "missing-integration.csv",
        integration_summary_path=tmp_path / "missing-summary.csv",
        classifier_evaluation_path=tmp_path / "missing-evaluation.json",
        intelligence_metadata_path=tmp_path / "missing-metadata.json",
    )

    assert missing_service.readiness().execution_available is False
    with pytest.raises(WeatherDataError, match="unavailable"):
        missing_service.options()
