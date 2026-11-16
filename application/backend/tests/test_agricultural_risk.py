from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from bharatcrop_foundation.models.agricultural_risk import AgriculturalRiskService
from bharatcrop_foundation.models.apy_data import QUALITY_FLAGS
from bharatcrop_foundation.models.weather_data import (
    INTEGRATION_COLUMNS,
    VALID_DAY_COLUMNS,
    WEATHER_FLAGS,
    WEATHER_METRICS,
    WeatherDataService,
)


def _fixture_service(tmp_path: Path) -> AgriculturalRiskService:
    rows: list[dict[str, object]] = []
    values = [
        ("Test District", 2013, 10.0, 100.0),
        ("Test District", 2014, 20.0, 100.0),
        ("Test District", 2015, 30.0, 100.0),
        ("Test District", 2016, 3.0, 100.0),
        ("Test District", 2017, 200.0, 100.0),
        ("Second District", 2017, 40.0, 60.0),
    ]
    for district, year, crop_yield, area in values:
        row: dict[str, object] = {column: None for column in INTEGRATION_COLUMNS}
        row.update(
            {
                "State": "Test State",
                "District": district,
                "Crop": "Beans",
                "Season": "Kharif",
                "Crop_Category": "Individual Crop Candidate",
                "Year": f"{year}-{str(year + 1)[-2:]}",
                "Area": area,
                "Production": crop_yield * area / 1000,
                "Yield": crop_yield,
                "apy_geography_id": f"APY-{district}",
                "start_year": year,
                "weather_proxy_calendar_year": year,
                "weather_alignment_method": "STARTING_CALENDAR_YEAR_PROXY",
                "weather_full_season_alignment_verified": False,
                "weather_available": district == "Test District",
                "weather_match_status": (
                    "MATCHED" if district == "Test District" else "UNMATCHED"
                ),
                "_merge": "both" if district == "Test District" else "left_only",
                "weather_proxy_available": district == "Test District",
            }
        )
        for metric in WEATHER_METRICS:
            row[metric] = 25.0 if district == "Test District" else None
        for column in VALID_DAY_COLUMNS:
            row[column] = 365 if district == "Test District" else None
        for flag in (*WEATHER_FLAGS, *QUALITY_FLAGS):
            row[flag] = False
        if year == 2016 and district == "Test District":
            row["Area"] = 0.0
            row["QC_AreaZero-ProductionPositive"] = True
            row["QC_PositiveYieldWithoutPositiveAreaProduction"] = True
        rows.append(row)

    rows.extend(
        [
            {
                **rows[0],
                "Year": "2018-19",
                "start_year": 2018,
                "Yield": 0.0,
            },
            {
                **rows[0],
                "Year": "2018-19",
                "start_year": 2018,
                "Crop_Category": "Aggregate Total - Exclude",
                "Crop": "All Crops",
                "Yield": 999.0,
            },
            {
                **rows[0],
                "Year": "2018-19",
                "Season": "Total",
                "start_year": 2018,
                "Yield": 999.0,
            },
            {
                **rows[0],
                "Year": "2018-19",
                "Crop": "Rice",
                "start_year": 2018,
                "Yield": 10.0,
                "Area": 40.0,
            },
            {
                **rows[0],
                "Year": "2018-19",
                "Crop": "Millet",
                "start_year": 2018,
                "Yield": 10.0,
                "Area": 60.0,
            },
            {
                **rows[0],
                "Year": "2018-19",
                "Crop": "Zero area",
                "start_year": 2018,
                "Yield": 10.0,
                "Area": 0.0,
            },
            {
                **rows[0],
                "Year": "2018-19",
                "Crop": "Missing area",
                "start_year": 2018,
                "Yield": 10.0,
                "Area": None,
            },
            {
                **rows[0],
                "Year": "2018-19",
                "Crop": "Negative area",
                "start_year": 2018,
                "Yield": 10.0,
                "Area": -1.0,
            },
            {
                **rows[0],
                "Year": "2018-19",
                "Crop": "Missing yield",
                "start_year": 2018,
                "Yield": None,
                "Area": 10.0,
            },
            {
                **rows[0],
                "Year": "2018-19",
                "Crop": "Infinite yield",
                "start_year": 2018,
                "Yield": float("inf"),
                "Area": 10.0,
            },
        ]
    )
    integration_path = tmp_path / "integration.csv"
    pd.DataFrame(rows, columns=INTEGRATION_COLUMNS).to_csv(
        integration_path, index=False
    )
    metadata_path = tmp_path / "risk-metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "module": "Agricultural Risk Intelligence",
                "risk_definition": {
                    "high_concern": "Current yield < 70% of baseline"
                },
            }
        ),
        encoding="utf-8",
    )
    weather_service = WeatherDataService(
        annual_path=tmp_path / "not-present-weather.csv",
        reference_path=tmp_path / "not-present-reference.csv",
        history_path=tmp_path / "not-present-history.csv",
        unmatched_path=tmp_path / "not-present-unmatched.csv",
        integration_path=integration_path,
        integration_summary_path=tmp_path / "not-present-summary.csv",
        classifier_evaluation_path=tmp_path / "not-present-evaluation.json",
        intelligence_metadata_path=tmp_path / "not-present-intelligence.json",
    )
    return AgriculturalRiskService(weather_service, metadata_path)


def test_notebook_baseline_uses_only_previous_three_valid_observations(
    tmp_path: Path,
) -> None:
    service = _fixture_service(tmp_path)
    result = service.anomalies(
        state="Test State",
        district="Test District",
        crop="Beans",
        season="Kharif",
        year_start=2013,
        year_end=2017,
    )
    rows = result["records"]

    assert rows[0]["baseline_available"] is False
    assert rows[0]["historical_observation_count"] == 0
    assert rows[1]["baseline_available"] is False
    assert rows[1]["historical_observation_count"] == 1
    assert rows[2]["historical_median_yield"] == 15.0
    assert rows[2]["baseline_observations"] == [
        {"year_start": 2013, "agricultural_year": "2013-14", "yield_value": 10.0},
        {"year_start": 2014, "agricultural_year": "2014-15", "yield_value": 20.0},
    ]
    assert rows[3]["historical_median_yield"] == 20.0
    assert len(rows[3]["baseline_observations"]) == 3
    assert rows[3]["risk_indicator"] == "High Concern"
    assert rows[3]["anomaly_direction"] == "below_baseline"
    assert rows[3]["source_quality_flags"][
        "QC_PositiveYieldWithoutPositiveAreaProduction"
    ] is True
    assert rows[4]["historical_median_yield"] == 20.0
    assert rows[4]["risk_indicator"] == "Extreme Deviation - Review Data"
    assert rows[4]["anomaly_direction"] == "above_baseline"
    assert rows[4]["standardized_deviation"] is None
    available_crops = service.options()["crops"]
    assert "Missing yield" not in available_crops
    assert "Infinite yield" not in available_crops


def test_instability_summary_guards_sample_size_and_zero_denominator(
    tmp_path: Path,
) -> None:
    service = _fixture_service(tmp_path)
    result = service.instability(
        state="Test State",
        district="Test District",
        crop="Beans",
        season="Kharif",
        year_start=2013,
        year_end=2014,
    )
    assert result["valid_observation_count"] == 2
    assert result["mean_yield"] == 15.0
    assert result["median_yield"] == 15.0
    assert result["sample_standard_deviation"] == pytest.approx(7.0710678118654755)
    assert result["coefficient_of_variation_pct"] == pytest.approx(
        47.14045207910317
    )
    assert result["robust_variability"] is None
    assert result["trend_slope"] is None


def test_diversification_hhi_uses_individual_crops_and_positive_area_only(
    tmp_path: Path,
) -> None:
    service = _fixture_service(tmp_path)
    result = service.diversification(
        state="Test State",
        district="Test District",
        season="Kharif",
        year_start=2018,
    )
    assert result["source_record_count"] == 8
    assert result["positive_area_crop_count"] == 5
    assert result["excluded_missing_zero_or_negative_area_record_count"] == 3
    assert result["herfindahl_hirschman_index"] == pytest.approx(0.3181818181818182)
    assert {row["crop"] for row in result["crop_area_shares"]} == {
        "Beans",
        "Rice",
        "Millet",
        "Missing yield",
        "Infinite yield",
    }
    assert "Infinite yield" not in service.options()["crops"]
    assert "not define a diversification indicator" in result["methodology_source"]


def test_benchmark_only_compares_same_year_crop_season_and_state(
    tmp_path: Path,
) -> None:
    service = _fixture_service(tmp_path)
    result = service.benchmarking(
        state="Test State",
        crop="Beans",
        season="Kharif",
        year_start=2017,
        through_year_start=2017,
    )
    assert result["district_count"] == 2
    assert result["districts_ranked"] is False
    assert [row["district"] for row in result["districts"]] == [
        "Second District",
        "Test District",
    ]
    assert all(row["benchmark_year"] == 2017 for row in result["districts"])
    assert all(row["yield_unit"] == "kg/ha" for row in result["districts"])


def test_weather_is_separate_and_missing_weather_does_not_remove_yield_indicator(
    tmp_path: Path,
) -> None:
    service = _fixture_service(tmp_path)
    result = service.indicators(
        state="Test State",
        district="Test District",
        crop="Beans",
        season="Kharif",
        year_start=2016,
        year_end=2016,
    )
    record = result["records"][0]
    assert record["risk_indicator"] == "High Concern"
    assert record["weather_context"]["available"] is True
    assert record["weather_context"]["full_season_alignment_verified"] is False
    assert record["weather_context"]["calendar_year"] == 2016
    assert record["data_quality"][
        "these_flags_do_not_change_notebook_20_eligibility"
    ] is True
    assert result["interpretation"].startswith("Yield indicators and weather")

    unmatched = service.indicators(
        state="Test State",
        district="Second District",
        crop="Beans",
        season="Kharif",
        year_start=2017,
        year_end=2017,
    )
    assert unmatched["records"][0]["weather_context"]["available"] is False
    assert unmatched["records"][0]["risk_indicator"] == "Insufficient History"


def test_invalid_season_and_year_ranges_are_rejected(tmp_path: Path) -> None:
    service = _fixture_service(tmp_path)
    with pytest.raises(ValueError, match="Season is not supported"):
        service.anomalies(
            state="Test State",
            district="Test District",
            crop="Beans",
            season="Total",
        )
    with pytest.raises(ValueError, match="must not exceed"):
        service.instability(
            state="Test State",
            district="Test District",
            crop="Beans",
            season="Kharif",
            year_start=2017,
            year_end=2013,
        )
