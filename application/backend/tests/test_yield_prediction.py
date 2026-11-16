from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

import pandas as pd
import pytest

from bharatcrop_foundation.models.yield_prediction import (
    FEATURES,
    ModelArtifactError,
    ModelLoader,
    Predictor,
    YieldFeatures,
    YieldModelAdapter,
    YieldPredictionService,
)

METADATA = {
    "model_name": "HistGradientBoostingRegressor",
    "model_version": "test-model-v1",
    "features": list(FEATURES),
    "categorical_features": ["Crop", "Season", "Crop_Category", "State", "District"],
    "numeric_features": ["FE_YearStart"],
    "target": "Yield",
    "training_year_start": 2013,
    "training_year_end": 2022,
    "validation_metrics": {
        "2019-2020": {"MAE": 448.306, "RMSE": 672.961, "R2": 0.798},
        "2021-2022": {"MAE": 422.856, "RMSE": 898.177, "R2": 0.693},
    },
}
CATEGORIES = {
    "Crop": frozenset({"Rice", "Wheat"}),
    "Season": frozenset({"Kharif", "Rabi"}),
    "Crop_Category": frozenset({"Individual Crop Candidate"}),
    "State": frozenset({"Test State"}),
    "District": frozenset({"Test District"}),
}


class FakeModel:
    feature_names_in_: Sequence[str] = FEATURES

    def __init__(self, value: float = 123.5, error: Exception | None = None) -> None:
        self.value = value
        self.error = error
        self.calls = 0

    def predict(self, values: pd.DataFrame) -> Sequence[float]:
        self.calls += 1
        assert tuple(values.columns) == FEATURES
        if self.error is not None:
            raise self.error
        return [self.value]


def _adapter(
    tmp_path: Path,
    *,
    metadata: dict[str, object] | None = None,
    loader: ModelLoader | None = None,
    expected_hash: str | None = None,
    expected_metadata_hash: str | None = "actual",
) -> YieldModelAdapter:
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"fixture-artifact")
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata or METADATA), encoding="utf-8")
    if expected_hash == "actual":
        expected_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if expected_metadata_hash == "actual":
        expected_metadata_hash = hashlib.sha256(metadata_path.read_bytes()).hexdigest()
    return YieldModelAdapter(
        artifact,
        metadata_path,
        expected_hash,
        expected_metadata_hash,
        loader=loader,
    )


def _enabled_service(
    adapter: YieldModelAdapter,
    categories: dict[str, frozenset[str]] | None = None,
) -> YieldPredictionService:
    return YieldPredictionService(
        adapter,
        total_season_semantics_verified=True,
        geographic_coverage_verified=True,
        category_coverage_verified=True,
        artifact_runtime_verified=True,
        release_approved=True,
        supported_categories=categories or CATEGORIES,
    )


def _features(**overrides: object) -> YieldFeatures:
    fields: dict[str, object] = {
        "Crop": "Rice",
        "Season": "Kharif",
        "Crop_Category": "Individual Crop Candidate",
        "State": "Test State",
        "District": "Test District",
        "FE_YearStart": 2020,
    }
    fields.update(overrides)
    return YieldFeatures.model_validate(fields)


def test_valid_metadata_matches_exact_feature_and_target_contract(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path, expected_hash="actual")

    metadata, reasons = adapter.inspect()

    assert metadata is not None
    assert metadata.features == list(FEATURES)
    assert metadata.target == "Yield"
    assert reasons == ()


def test_missing_model_version_allows_deserialization_but_not_readiness(
    tmp_path: Path,
) -> None:
    metadata = dict(METADATA)
    metadata.pop("model_version")
    model = FakeModel()
    adapter = _adapter(
        tmp_path,
        metadata=metadata,
        loader=lambda _artifact: model,
        expected_hash="actual",
        expected_metadata_hash="actual",
    )

    assert adapter.load() is model
    assert "model_version_not_recorded" in YieldPredictionService(adapter).readiness().reason_codes


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("features", ["Season", *FEATURES[1:]], "feature_contract_mismatch"),
        ("target", "Production", "target_contract_mismatch"),
        ("training_year_end", 2010, "training_year_range_invalid"),
        ("numeric_features", ["Year"], "numeric_feature_contract_mismatch"),
    ],
)
def test_incompatible_metadata_is_not_ready(
    tmp_path: Path,
    field: str,
    value: object,
    reason: str,
) -> None:
    metadata = dict(METADATA)
    metadata[field] = value
    adapter = _adapter(tmp_path, metadata=metadata, expected_hash="actual")

    _, reasons = adapter.inspect()

    assert reason in reasons


def test_invalid_metadata_json_reports_safe_reason(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    adapter.metadata_path.write_text("{", encoding="utf-8")

    _, reasons = adapter.inspect()

    assert reasons == ("metadata_invalid",)


def test_missing_artifact_is_not_ready(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    adapter.artifact_path.unlink()

    _, reasons = adapter.inspect()

    assert "artifact_unavailable" in reasons


def test_unexpected_artifact_extension_is_rejected(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    adapter.artifact_path.rename(tmp_path / "model.bin")
    adapter.artifact_path = tmp_path / "model.bin"

    _, reasons = adapter.inspect()

    assert "artifact_path_invalid" in reasons


def test_missing_artifact_checksum_prevents_loading(tmp_path: Path) -> None:
    calls = 0

    def loader(_artifact: bytes) -> Predictor:
        nonlocal calls
        calls += 1
        return FakeModel()

    adapter = _adapter(tmp_path, loader=loader)

    with pytest.raises(ModelArtifactError):
        adapter.load()

    assert calls == 0


def test_artifact_checksum_mismatch_prevents_loading(tmp_path: Path) -> None:
    calls = 0

    def loader(_artifact: bytes) -> Predictor:
        nonlocal calls
        calls += 1
        return FakeModel()

    adapter = _adapter(tmp_path, loader=loader, expected_hash="0" * 64)

    with pytest.raises(ModelArtifactError):
        adapter.load()

    assert calls == 0


def test_metadata_checksum_mismatch_prevents_loading(tmp_path: Path) -> None:
    calls = 0

    def loader(_artifact: bytes) -> Predictor:
        nonlocal calls
        calls += 1
        return FakeModel()

    adapter = _adapter(
        tmp_path,
        loader=loader,
        expected_hash="actual",
        expected_metadata_hash="0" * 64,
    )

    with pytest.raises(ModelArtifactError):
        adapter.load()

    assert calls == 0


def test_corrupt_artifact_loader_error_is_sanitized(tmp_path: Path) -> None:
    def loader(_artifact: bytes) -> Predictor:
        raise RuntimeError("private path in broken artifact")

    adapter = _adapter(
        tmp_path,
        loader=loader,
        expected_hash="actual",
        expected_metadata_hash="actual",
    )

    with pytest.raises(ModelArtifactError) as error:
        adapter.load()

    assert str(error.value) == "Model artifact could not be loaded."
    assert "private path" not in str(error.value)


def test_artifact_feature_order_mismatch_is_rejected(tmp_path: Path) -> None:
    model = FakeModel()
    model.feature_names_in_ = tuple(reversed(FEATURES))
    adapter = _adapter(
        tmp_path,
        loader=lambda _artifact: model,
        expected_hash="actual",
        expected_metadata_hash="actual",
    )

    with pytest.raises(ModelArtifactError):
        adapter.load()


@pytest.mark.parametrize(
    "fields",
    [
        {"Crop": "Rice", "Season": "Kharif"},
        {
            "Crop": "Rice",
            "Season": "Kharif",
            "Crop_Category": "Individual Crop Candidate",
            "State": "Test State",
            "District": "Test District",
            "FE_YearStart": "2020",
        },
        {
            "Crop": "",
            "Season": "Kharif",
            "Crop_Category": "Individual Crop Candidate",
            "State": "Test State",
            "District": "Test District",
            "FE_YearStart": 2020,
        },
    ],
)
def test_missing_or_malformed_features_are_rejected(fields: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        YieldFeatures.model_validate(fields)


def test_aggregate_total_season_is_rejected() -> None:
    with pytest.raises(ValueError, match="Aggregate Total"):
        _features(Season="Total")


def test_readiness_lists_unresolved_release_reasons(tmp_path: Path) -> None:
    metadata = dict(METADATA)
    metadata.pop("model_version")
    service = YieldPredictionService(
        _adapter(tmp_path, metadata=metadata, expected_metadata_hash=None)
    )

    readiness = service.readiness()

    assert readiness.execution_available is False
    assert {
        "model_version_not_recorded",
        "total_season_semantics_unverified",
        "geographic_coverage_unverified",
        "category_coverage_unverified",
        "artifact_runtime_compatibility_unverified",
        "independent_model_release_not_approved",
        "artifact_checksum_not_approved",
        "metadata_checksum_not_approved",
    } <= set(readiness.reason_codes)
    assert readiness.target_unit == "kg/ha"


def test_experimental_inference_is_separate_from_release_readiness(tmp_path: Path) -> None:
    model = FakeModel()
    service = YieldPredictionService(
        _adapter(
            tmp_path,
            loader=lambda _artifact: model,
            expected_hash="actual",
            expected_metadata_hash="actual",
        ),
        supported_categories=CATEGORIES,
    )

    result = service.predict(_features())

    assert service.readiness().execution_available
    assert service.readiness().production_approved is False
    assert result.provenance.target_unit == "kg/ha"
    assert model.calls == 1


def test_enabled_internal_service_returns_provenance_without_invented_units(
    tmp_path: Path,
) -> None:
    model = FakeModel()
    service = _enabled_service(
        _adapter(
            tmp_path,
            loader=lambda _artifact: model,
            expected_hash="actual",
            expected_metadata_hash="actual",
        )
    )

    result = service.predict(_features())

    assert result.value == 123.5
    assert result.provenance.target_unit == "kg/ha"
    assert result.provenance.artifact_sha256
    assert result.provenance.target_conversion_applied is False
    assert result.provenance.model_version == "test-model-v1"
    assert result.provenance.metadata_sha256
    assert result.provenance.training_year_end == 2022
    assert model.calls == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("Crop", "Unverified Crop"),
        ("Season", "Unverified Season"),
        ("State", "Unverified State"),
        ("District", "Unverified District"),
        ("Crop_Category", "Unverified Category"),
    ],
)
def test_unknown_category_rejects_and_out_of_range_year_is_extrapolation(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    service = _enabled_service(
        _adapter(
            tmp_path,
            loader=lambda _artifact: FakeModel(),
            expected_hash="actual",
            expected_metadata_hash="actual",
        )
    )

    with pytest.raises(ValueError, match="Unsupported category"):
        service.predict(_features(**{field: value}))
    result = service.predict(_features(FE_YearStart=2023))
    assert result.prediction_period_status == "out_of_training_range_extrapolation"


def test_inference_exception_is_sanitized(tmp_path: Path) -> None:
    service = _enabled_service(
        _adapter(
            tmp_path,
            loader=lambda _artifact: FakeModel(error=RuntimeError("private path")),
            expected_hash="actual",
            expected_metadata_hash="actual",
        )
    )

    with pytest.raises(ModelArtifactError) as error:
        service.predict(_features())

    assert str(error.value) == "Yield inference failed."
    assert "private path" not in str(error.value)


def test_non_finite_prediction_is_rejected(tmp_path: Path) -> None:
    service = _enabled_service(
        _adapter(
            tmp_path,
            loader=lambda _artifact: FakeModel(value=float("nan")),
            expected_hash="actual",
            expected_metadata_hash="actual",
        )
    )

    with pytest.raises(ModelArtifactError, match="Yield inference failed"):
        service.predict(_features())


def test_unseen_crop_season_location_combination_is_rejected(tmp_path: Path) -> None:
    service = _enabled_service(
        _adapter(
            tmp_path,
            loader=lambda _artifact: FakeModel(),
            expected_hash="actual",
            expected_metadata_hash="actual",
        )
    )
    service.supported_combinations = frozenset(
        {
            (
                "Wheat",
                "Rabi",
                "Individual Crop Candidate",
                "Test State",
                "Test District",
            )
        }
    )

    with pytest.raises(ValueError, match="Unsupported crop, season, and location"):
        service.predict(_features())


def test_prediction_reports_pending_unit_status_and_recorded_version(
    tmp_path: Path,
) -> None:
    service = _enabled_service(
        _adapter(
            tmp_path,
            loader=lambda _artifact: FakeModel(),
            expected_hash="actual",
            expected_metadata_hash="actual",
        )
    )

    result = service.predict(_features())

    assert result.provenance.target_unit == "kg/ha"
    assert result.provenance.target_unit_status == "verification_pending"
    assert result.provenance.model_version == "test-model-v1"


def test_foreign_validation_metrics_are_not_attributed_to_the_served_artifact(
    tmp_path: Path,
) -> None:
    assert "validation_metrics" in METADATA
    service = _enabled_service(
        _adapter(
            tmp_path,
            loader=lambda _artifact: FakeModel(),
            expected_hash="actual",
            expected_metadata_hash="actual",
        )
    )

    result = service.predict(_features())

    assert result.provenance.validation_metrics == {}


def test_negative_prediction_is_rejected_without_clamping(tmp_path: Path) -> None:
    model = FakeModel(value=-5.0)
    service = _enabled_service(
        _adapter(
            tmp_path,
            loader=lambda _artifact: model,
            expected_hash="actual",
            expected_metadata_hash="actual",
        )
    )

    with pytest.raises(ModelArtifactError, match="Yield inference failed"):
        service.predict(_features())

    assert model.calls == 1


def test_out_of_range_prediction_adds_not_a_forecast_warning(tmp_path: Path) -> None:
    service = _enabled_service(
        _adapter(
            tmp_path,
            loader=lambda _artifact: FakeModel(),
            expected_hash="actual",
            expected_metadata_hash="actual",
        )
    )

    result = service.predict(_features(FE_YearStart=2023))

    assert result.prediction_period_status == "out_of_training_range_extrapolation"
    assert any(
        "not a validated" in limitation and "forecast" in limitation
        for limitation in result.limitations
    )

