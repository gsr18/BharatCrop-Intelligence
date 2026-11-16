from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

import pandas as pd
import pytest

from bharatcrop_foundation.models.apy_data import (
    QUALITY_FLAGS,
    APYDataError,
    APYDataService,
)
from bharatcrop_foundation.models.yield_prediction import (
    CATEGORICAL_FEATURES,
    FEATURES,
    NUMERIC_FEATURES,
    YieldModelAdapter,
    YieldPredictionService,
)


class FixtureModel:
    feature_names_in_: Sequence[str] = FEATURES

    def predict(self, values: pd.DataFrame) -> list[float]:
        yields = {"Rice": 120.0, "Maize": 130.0, "Wheat": 110.0}
        return [yields[str(crop)] for crop in values["Crop"]]


def _row(
    *,
    state: str = "Test State",
    district: str = "Test District",
    crop: str = "Rice",
    season: str = "Kharif",
    category: str = "Individual Crop Candidate",
    year: int = 2021,
    area: float | None = 1.0,
    production: float | None = 2.0,
    yield_value: float | None = 2000.0,
    flags: tuple[str, ...] = (),
) -> dict[str, object]:
    row: dict[str, object] = {
        "State": state,
        "District": district,
        "Crop": crop,
        "Season": season,
        "Crop_Category": category,
        "Year": f"{year}-{str(year + 1)[-2:]}",
        "Area": area,
        "Production": production,
        "Yield": yield_value,
        "start_year": year,
    }
    row.update({flag: flag in flags for flag in QUALITY_FLAGS})
    return row


@pytest.fixture
def fixture_service(tmp_path: Path) -> APYDataService:
    rows = [
        _row(year=2021, yield_value=100.0),
        _row(year=2022, yield_value=110.0),
        _row(year=2023, yield_value=120.0),
        _row(year=2024, yield_value=130.0),
        _row(crop="Maize", year=2021, yield_value=80.0),
        _row(crop="Maize", year=2022, yield_value=90.0),
        _row(crop="Maize", year=2023, yield_value=100.0),
        _row(crop="Maize", year=2024, yield_value=105.0),
        _row(crop="Wheat", year=2024, yield_value=90.0),
        _row(crop="Wheat", year=2023, yield_value=0.0),
        _row(crop="Barley", year=2024, yield_value=70.0),
        _row(crop="Jowar", year=2022, yield_value=85.0),
        _row(crop="Jowar", year=2023, yield_value=85.0),
        _row(crop="Gram", year=2024, area=0.0, yield_value=500.0),
        _row(crop="Urad", year=2024, flags=(QUALITY_FLAGS[0],)),
        _row(crop="Missing", year=2024, yield_value=None),
        _row(crop="Cereals", category="Grouping - Verify Source Definition", year=2024),
        _row(crop="Total", season="Total", year=2024),
        _row(state="Other State", district="Other District", crop="Rice", year=2024),
        _row(state="Other State", district="Other District", crop="Barley", year=2024),
        _row(state="Solo State", district="Solo District", crop="Rice", year=2024, yield_value=60.0),
    ]
    path = tmp_path / "apy.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"fixture-model")
    metadata = tmp_path / "model.json"
    metadata.write_text(
        json.dumps(
            {
                "model_name": "fixture",
                "model_version": "fixture-v1",
                "features": list(FEATURES),
                "categorical_features": list(CATEGORICAL_FEATURES),
                "numeric_features": list(NUMERIC_FEATURES),
                "target": "Yield",
                "training_year_start": 2013,
                "training_year_end": 2022,
            }
        ),
        encoding="utf-8",
    )
    yield_service = YieldPredictionService(
        YieldModelAdapter(
            artifact,
            metadata,
            hashlib.sha256(artifact.read_bytes()).hexdigest(),
            hashlib.sha256(metadata.read_bytes()).hexdigest(),
            loader=lambda _artifact: FixtureModel(),
        ),
        supported_categories={
            "Crop": frozenset({"Rice", "Maize", "Wheat"}),
            "Season": frozenset({"Kharif"}),
            "Crop_Category": frozenset({"Individual Crop Candidate"}),
            "State": frozenset({"Test State"}),
            "District": frozenset({"Test District"}),
        },
    )
    return APYDataService(path, yield_service)


def test_options_exclude_aggregate_rows_and_filter_districts_by_state(
    fixture_service: APYDataService,
) -> None:
    options = fixture_service.options()

    assert "Cereals" not in options["crops"]
    assert "Total" not in options["crops"]
    assert "Gram" not in options["crops"]
    assert "Urad" not in options["crops"]
    assert "Missing" not in options["crops"]
    assert "Total" not in options["seasons"]
    assert fixture_service.options(state="Test State")["districts"] == ["Test District"]
    assert fixture_service.options(state="Other State")["districts"] == ["Other District"]
    assert fixture_service.options(state="Test State", year_start=2021)["crops"] == [
        "Maize",
        "Rice",
    ]


def test_rank_discovers_candidates_by_recent_median_without_a_year_input(
    fixture_service: APYDataService,
) -> None:
    result = fixture_service.rank(
        state="Test State",
        district="Test District",
        season="Kharif",
    )

    assert result["ranking_available"] is True
    assert result["ranking_basis"] == "recent_median"
    assert result["latest_data_year"] == 2024
    assert result["data_period_start"] == 2021
    assert result["top_n"] == 5
    assert result["reference_year"] == 2022
    assert result["eligible_candidate_count"] == 5
    assert [(item["crop"], item["rank"], item["ranking_value"]) for item in result["candidates"]] == [
        ("Rice", 1, 115.0),
        ("Maize", 2, 95.0),
        ("Wheat", 3, 90.0),
        ("Jowar", 4, 85.0),
        ("Barley", 5, 70.0),
    ]
    rice = next(item for item in result["candidates"] if item["crop"] == "Rice")
    assert rice["predicted_yield"] == 120.0
    assert rice["observed_yield"] == 130.0
    assert rice["has_observation_in_latest_year"] is True
    assert rice["model_reference_year"] == 2022
    assert rice["model_prediction_period_status"] == "in_training_range"
    assert rice["model_difference_from_median"] == pytest.approx(5.0)
    assert rice["candidate_eligibility"]["reason_code"] == (
        "historical_evidence_and_model_supported"
    )
    assert rice["historical_statistics"]["historical_mean_yield"] == pytest.approx(115.0)
    assert rice["historical_statistics"]["latest_observation_year"] == 2024
    assert "not a guarantee of agronomic suitability" in result["ranking_methodology"]
    assert "not planting recommendations" in " ".join(result["limitations"])


def test_model_unsupported_crop_is_still_ranked_by_historical_evidence(
    fixture_service: APYDataService,
) -> None:
    result = fixture_service.rank(
        state="Test State",
        district="Test District",
        season="Kharif",
    )
    barley = next(item for item in result["candidates"] if item["crop"] == "Barley")

    assert barley["rank"] == 5
    assert barley["predicted_yield"] is None
    assert barley["model_reference_year"] is None
    assert barley["candidate_eligibility"]["eligible"] is True
    assert barley["candidate_eligibility"]["reason_code"] == (
        "historical_evidence_only_model_unsupported"
    )
    assert any("does not support" in warning for warning in barley["warnings"])


def test_crop_without_latest_year_observation_is_ranked_and_evidence_order_diverges(
    fixture_service: APYDataService,
) -> None:
    result = fixture_service.rank(
        state="Test State",
        district="Test District",
        season="Kharif",
    )
    by_crop = {item["crop"]: item for item in result["candidates"]}

    jowar = by_crop["Jowar"]
    assert jowar["has_observation_in_latest_year"] is False
    assert jowar["observed_yield"] is None
    assert jowar["rank"] == 4
    assert jowar["evidence_rank"] == 3
    wheat = by_crop["Wheat"]
    assert wheat["rank"] == 3
    assert wheat["evidence_rank"] == 4
    assert [
        item["crop"]
        for item in sorted(result["candidates"], key=lambda item: item["evidence_rank"])
    ] == ["Rice", "Maize", "Jowar", "Wheat", "Barley"]


def test_historical_median_basis_orders_by_historical_medians(
    fixture_service: APYDataService,
) -> None:
    result = fixture_service.rank(
        state="Test State",
        district="Test District",
        season="Kharif",
        ranking_basis="historical_median",
    )
    rice = next(item for item in result["candidates"] if item["crop"] == "Rice")

    assert result["ranking_basis"] == "historical_median"
    assert rice["ranking_basis"] == "historical_median"
    assert rice["ranking_value"] == pytest.approx(115.0)


def test_top_n_is_capped_at_five_and_honours_smaller_requests(
    fixture_service: APYDataService,
) -> None:
    capped = fixture_service.rank(
        state="Test State",
        district="Test District",
        season="Kharif",
        top_n=99,
    )
    smaller = fixture_service.rank(
        state="Test State",
        district="Test District",
        season="Kharif",
        top_n=2,
    )

    assert capped["top_n"] == 5
    assert len(capped["candidates"]) == 5
    assert smaller["top_n"] == 2
    assert [item["crop"] for item in smaller["candidates"]] == ["Rice", "Maize"]


def test_single_rankable_crop_disables_ranking(fixture_service: APYDataService) -> None:
    result = fixture_service.rank(
        state="Solo State",
        district="Solo District",
        season="Kharif",
    )

    assert result["ranking_available"] is False
    assert result["ranked_candidate_count"] == 0
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["rank"] is None


def test_ranking_model_documents_single_common_reference_year(
    fixture_service: APYDataService,
) -> None:
    result = fixture_service.rank(
        state="Test State",
        district="Test District",
        season="Kharif",
    )
    model = result["ranking_model"]

    assert model["reference_year"] == 2022
    assert model["prediction_period_status"] == "in_training_range"
    assert model["quality_status"] == "experimental"
    assert model["production_approved"] is False
    assert "not a multi-year average" in model["reference_year_policy"]


def test_rank_rejects_unknown_basis_and_unsupported_location(
    fixture_service: APYDataService,
) -> None:
    with pytest.raises(ValueError, match="Ranking basis"):
        fixture_service.rank(
            state="Test State",
            district="Test District",
            season="Kharif",
            ranking_basis="model_estimate",
        )
    with pytest.raises(ValueError, match="selected state"):
        fixture_service.rank(
            state="Test State",
            district="Other District",
            season="Kharif",
        )


def test_statistics_use_historical_and_recent_medians(
    fixture_service: APYDataService,
) -> None:
    stats = fixture_service.comparison(
        state="Test State",
        district="Test District",
        season="Kharif",
        through_year=2024,
    )
    rice = next(item for item in stats if item["crop"] == "Rice")

    assert rice["historical_median_yield"] == 115.0
    assert rice["historical_mean_yield"] == pytest.approx(115.0)
    assert rice["latest_observation_year"] == 2024
    assert rice["recent_median_yield"] == 115.0
    assert rice["valid_observation_count"] == 4
    assert rice["valid_year_count"] == 4
    assert rice["historical_trend_yield_per_year"] == pytest.approx(10.0)
    assert rice["yield_standard_deviation"] == pytest.approx(12.909944)


def test_evidence_reports_excluded_source_records(
    fixture_service: APYDataService,
) -> None:
    evidence = fixture_service.evidence(
        state="Test State",
        district="Test District",
        season="Kharif",
        crop="Wheat",
        through_year=2024,
    )

    assert evidence["source_observation_count"] == 2
    assert evidence["valid_observation_count"] == 1
    assert evidence["excluded_observation_count"] == 1


def test_season_and_year_validation_reject_unsupported_values(
    fixture_service: APYDataService,
) -> None:
    with pytest.raises(ValueError, match="Kharif, Rabi, or Summer"):
        fixture_service.options(season="Total")
    with pytest.raises(ValueError, match="Agricultural year"):
        fixture_service.comparison(
            state="Test State",
            district="Test District",
            season="Kharif",
            through_year=2025,
        )


def test_invalid_state_district_pair_is_rejected(
    fixture_service: APYDataService,
) -> None:
    with pytest.raises(ValueError, match="selected state"):
        fixture_service.options(state="Test State", district="Other District")


def test_dataset_loading_failures_are_explicit(tmp_path: Path) -> None:
    with pytest.raises(APYDataError, match="unavailable"):
        APYDataService(tmp_path / "missing.csv").options()

    invalid_path = tmp_path / "invalid.csv"
    pd.DataFrame([{"State": "Test State"}]).to_csv(invalid_path, index=False)
    with pytest.raises(APYDataError, match="could not be read"):
        APYDataService(invalid_path).options()
