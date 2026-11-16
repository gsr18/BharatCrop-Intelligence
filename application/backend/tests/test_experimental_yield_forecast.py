"""Phase 2E — tests for the isolated experimental future-yield forecast.

Covers: artifact load + inference contract, checksum gating, feature/design
parity against the preserved Phase 2D research code, eligibility rules,
data-freshness / past-target labelling, non-finite and negative rejection
(no clamping), response metadata labels, and a manual-model regression check to
prove the served HistGradientBoosting path is untouched.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from bharatcrop_foundation.config import Settings, settings
from bharatcrop_foundation.models import experimental_forecast_features as EFF
from bharatcrop_foundation.models.experimental_yield_forecast import (
    ExperimentalForecastAdapter,
    ExperimentalYieldForecastService,
    ForecastResult,
    ModelArtifactError,
    ModelNotReadyError,
)

REFERENCE_YEAR = 2026
RESEARCH_SCRIPTS = (
    Path(settings.experimental_forecast_artifact_path).parents[1] / "scripts"
)


def build_adapter(
    *,
    artifact_sha: str | None = None,
    metadata_sha: str | None = None,
) -> ExperimentalForecastAdapter:
    return ExperimentalForecastAdapter(
        settings.experimental_forecast_artifact_path,
        settings.experimental_forecast_metadata_path,
        settings.experimental_forecast_history_path,
        expected_artifact_sha256=(
            artifact_sha
            if artifact_sha is not None
            else str(settings.experimental_forecast_artifact_sha256)
        ),
        expected_metadata_sha256=(
            metadata_sha
            if metadata_sha is not None
            else str(settings.experimental_forecast_metadata_sha256)
        ),
    )


@pytest.fixture(scope="module")
def adapter() -> ExperimentalForecastAdapter:
    return build_adapter()


@pytest.fixture(scope="module")
def service(adapter: ExperimentalForecastAdapter) -> ExperimentalYieldForecastService:
    return ExperimentalYieldForecastService(adapter, reference_year=REFERENCE_YEAR)


@pytest.fixture(scope="module")
def history(adapter: ExperimentalForecastAdapter) -> pd.DataFrame:
    return adapter.load_history()


@pytest.fixture(scope="module")
def vocab(adapter: ExperimentalForecastAdapter) -> dict[str, list[str]]:
    return adapter.vocab()


def richest_series(history: pd.DataFrame) -> tuple[str, str, str, str]:
    grouped = history.groupby(["State", "District", "Crop", "Season"])
    sizes = grouped.size().sort_values(ascending=False)
    for key in sizes.index:
        state, district, crop, season = (str(v) for v in key)
        sub = history[
            history["State"].eq(state)
            & history["District"].eq(district)
            & history["Crop"].eq(crop)
            & history["Season"].eq(season)
        ]
        if int(sub["YearStart"].max()) < 2024:
            continue
        if len(sub) >= 8:
            return state, district, crop, season
    raise AssertionError("no rich recurring series found")


def short_history_series(
    history: pd.DataFrame, vocab: dict[str, list[str]]
) -> tuple[str, str, str, str]:
    grouped = history.groupby(["State", "District", "Crop", "Season"])
    for key, size in grouped.size().items():
        state, district, crop, season = (str(v) for v in key)
        if 2 <= int(size) <= 3 and district in vocab["districts"]:
            sub = history[
                history["State"].eq(state)
                & history["District"].eq(district)
                & history["Crop"].eq(crop)
                & history["Season"].eq(season)
            ]
            years = sorted(int(y) for y in sub["YearStart"])
            if years and max(years) >= 2018:
                return state, district, crop, season
    raise AssertionError("no short-history series found")


def lapsed_series(
    history: pd.DataFrame, vocab: dict[str, list[str]]
) -> tuple[str, str, str, int]:
    """A series whose last observation is a few years behind the global latest."""
    grouped = history.groupby(["State", "District", "Crop", "Season"])
    for key, sub in grouped:
        state, district, crop, season = (str(v) for v in key)
        if district not in vocab["districts"]:
            continue
        years = [int(y) for y in sub["YearStart"]]
        origin = max(years)
        if len(years) >= 4 and origin <= 2021:
            return state, district, crop, origin
    raise AssertionError("no lapsed series found")


# --------------------------------------------------------------------------- #
# Part 1 — artifact load + explicit inference contract
# --------------------------------------------------------------------------- #
def test_artifact_loads_and_contract_validates(adapter: ExperimentalForecastAdapter) -> None:
    bundle = adapter.validate_contract()
    assert bundle["strategy"] == "pooled_panel"
    assert bundle["model_name"] == "random_forest"
    assert tuple(bundle["numeric_features"]) == tuple(EFF.NUMERIC_FEATURES)
    estimator = adapter.predict_estimator()
    assert estimator.n_features_in_ == EFF.design_width(bundle["vocab"]) == 66


def test_contract_rejects_mismatched_feature_order(adapter: ExperimentalForecastAdapter) -> None:
    from bharatcrop_foundation.models import experimental_yield_forecast as mod

    bundle = adapter.validate_contract()
    tampered = dict(bundle)
    tampered["numeric_features"] = list(bundle["numeric_features"])[::-1]
    original = adapter._bundle
    adapter._bundle = tampered
    try:
        with pytest.raises(mod.ForecastContractError):
            adapter.validate_contract()
    finally:
        adapter._bundle = original


def test_checksum_mismatch_blocks_forecast(
    history: pd.DataFrame, vocab: dict[str, list[str]]
) -> None:
    bad = build_adapter(artifact_sha="0" * 64)
    reasons = bad.inspect()
    assert "forecast_artifact_checksum_mismatch" in reasons
    svc = ExperimentalYieldForecastService(bad, reference_year=REFERENCE_YEAR)
    availability, _ = svc.availability()
    assert availability == "unavailable"
    state, district, crop, season = richest_series(history)
    with pytest.raises(ModelNotReadyError):
        svc.forecast(crop=crop, season=season, state=state, district=district, horizon=1)


# --------------------------------------------------------------------------- #
# Part 3 — shared feature implementation parity with research code
# --------------------------------------------------------------------------- #
def test_feature_and_prediction_parity_with_research_code(
    adapter: ExperimentalForecastAdapter,
    history: pd.DataFrame,
    vocab: dict[str, list[str]],
) -> None:
    sys.path.insert(0, str(RESEARCH_SCRIPTS))
    try:
        fx_spec = importlib.util.spec_from_file_location(
            "phase2d_features", RESEARCH_SCRIPTS / "features.py"
        )
        md_spec = importlib.util.spec_from_file_location(
            "phase2d_models", RESEARCH_SCRIPTS / "models.py"
        )
        assert fx_spec and fx_spec.loader and md_spec and md_spec.loader
        rfeatures = importlib.util.module_from_spec(fx_spec)
        fx_spec.loader.exec_module(rfeatures)
        rmodels = importlib.util.module_from_spec(md_spec)
        md_spec.loader.exec_module(rmodels)
    finally:
        sys.path.remove(str(RESEARCH_SCRIPTS))

    research_fx = rfeatures.build_forecast_rows(history)
    sample = research_fx[research_fx["target_year"] >= 2018].sample(
        200, random_state=0
    )
    estimator = adapter.predict_estimator()
    max_diff = 0.0
    for index, row in sample.iterrows():
        observations = EFF.series_observations(
            history,
            state=str(row["State"]),
            district=str(row["District"]),
            crop=str(row["Crop"]),
            season=str(row["Season"]),
        )
        features = EFF.origin_feature_row(
            observations,
            origin_year=int(row["origin_year"]),
            horizon=int(row["horizon"]),
        )
        mine = EFF.make_design_row(
            features,
            crop=str(row["Crop"]),
            season=str(row["Season"]),
            state=str(row["State"]),
            district=str(row["District"]),
            vocab=vocab,
        )
        assert mine.shape == (1, 66)
        theirs = rmodels.make_design(research_fx.loc[[index]], vocab)
        assert np.allclose(mine, theirs, atol=1e-9, equal_nan=True)
        max_diff = max(
            max_diff,
            abs(float(estimator.predict(mine)[0]) - float(estimator.predict(theirs)[0])),
        )
    assert max_diff < 1e-6


def test_origin_features_use_only_history_up_to_origin(service, history) -> None:
    state, district, crop, season = richest_series(history)
    observations = EFF.series_observations(
        history, state=state, district=district, crop=crop, season=season
    )
    origin = int(observations["YearStart"].max())
    features = EFF.origin_feature_row(observations, origin_year=origin, horizon=2)
    assert features["lag1"] == float(observations["Yield"].iloc[-1])
    assert features["hist_n"] == len(observations)
    assert features["origin_year"] == float(origin)
    assert features["target_year"] == float(origin + 2)


# --------------------------------------------------------------------------- #
# Part 4 — eligibility rules + Part 3/5 provenance + honesty
# --------------------------------------------------------------------------- #
def test_valid_forecast_carries_labels_and_provenance(service) -> None:
    adapter = service.adapter
    history = adapter.load_history()
    state, district, crop, season = richest_series(history)
    result = service.forecast(
        crop=crop, season=season, state=state, district=district, horizon=3
    )
    assert isinstance(result, ForecastResult)
    assert result.predicted_yield > 0
    assert result.unit == "kg/ha"
    assert result.unit_status == "verification_pending"
    assert result.history_count >= 1
    assert result.eligibility_status == "eligible_experimental"
    assert result.experimental_status == "experimental_research_not_validated"
    assert result.provenance.model_version == "phase2d-pooled-rf-v1"
    assert result.provenance.latest_observation_year == 2024
    assert result.provenance.artifact_sha256 and len(result.provenance.artifact_sha256) == 64
    assert result.provenance.design_width == 66
    # stale-data limitation must be surfaced
    assert any("behind the current reference year" in w for w in result.warnings)


def test_high_horizon_requires_rich_history(service, history, vocab) -> None:
    state, district, crop, season = short_history_series(history, vocab)
    result = service.forecast(
        crop=crop, season=season, state=state, district=district, horizon=1
    )
    assert result.history_count < 4
    assert any("Thin history" in w for w in result.warnings)
    with pytest.raises(ValueError):
        service.forecast(
            crop=crop, season=season, state=state, district=district, horizon=4
        )


def test_rich_series_allows_high_horizon_and_restricted_label(service) -> None:
    history = service.adapter.load_history()
    state, district, crop, season = richest_series(history)
    result = service.forecast(
        crop=crop, season=season, state=state, district=district, horizon=5
    )
    assert result.eligibility_status == "eligible_high_horizon_restricted"
    assert any("T+4/T+5" in w or "High-horizon" in w for w in result.warnings)


def test_unseen_district_is_rejected(service, vocab) -> None:
    history = service.adapter.load_history()
    state, _district, crop, season = richest_series(history)
    with pytest.raises(ValueError):
        service.forecast(
            crop=crop, season=season, state=state, district="Zzz Not A District", horizon=1
        )


def test_unknown_category_is_rejected(service) -> None:
    history = service.adapter.load_history()
    state, district, crop, season = richest_series(history)
    with pytest.raises(ValueError):
        service.forecast(
            crop="NotACrop", season=season, state=state, district=district, horizon=1
        )


def test_missing_series_insufficient_history(service, vocab) -> None:
    with pytest.raises(ValueError):
        service.forecast(
            crop=vocab["Crop"][0],
            season=vocab["Season"][0],
            state=vocab["State"][0],
            district=vocab["districts"][0],
            horizon=1,
        )


def test_horizon_out_of_range(service) -> None:
    history = service.adapter.load_history()
    state, district, crop, season = richest_series(history)
    for horizon in (0, 6):
        with pytest.raises(ValueError):
            service.forecast(
                crop=crop, season=season, state=state, district=district, horizon=horizon
            )


# --------------------------------------------------------------------------- #
# Data-freshness: never label a past target as future
# --------------------------------------------------------------------------- #
def test_observed_target_is_not_future(service, history, vocab) -> None:
    state, district, crop, origin = lapsed_series(history, vocab)
    season_row = history[
        history["State"].eq(state)
        & history["District"].eq(district)
        & history["Crop"].eq(crop)
    ]
    season = str(season_row["Season"].iloc[0])
    result = service.forecast(
        crop=crop, season=season, state=state, district=district, horizon=1
    )
    assert result.origin_year == origin
    assert result.target_year == origin + 1
    # target at/below the latest observation is explicitly not a future projection
    assert result.future_projection is False
    assert result.target_year_status in {
        "target_already_observed",
        "target_in_past_or_present",
    }
    assert any(
        phrase in w
        for w in result.warnings
        for phrase in ("not a future", "hindcast", "at or before")
    )


def test_far_future_target_flagged(service, history) -> None:
    state, district, crop, season = richest_series(history)
    result = service.forecast(
        crop=crop, season=season, state=state, district=district, horizon=5
    )
    assert result.target_year == 2029
    assert result.future_projection is True
    assert result.target_year_status == "future_target_beyond_latest_data"


# --------------------------------------------------------------------------- #
# Output safety — non-finite and negative are rejected, never clamped
# --------------------------------------------------------------------------- #
class _FakeEstimator:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, _design: np.ndarray) -> np.ndarray:
        return np.asarray([self.value])


def test_non_finite_output_rejected(service) -> None:
    history = service.adapter.load_history()
    state, district, crop, season = richest_series(history)
    service.adapter.predict_estimator = lambda: _FakeEstimator(float("nan"))  # type: ignore[method-assign]
    try:
        with pytest.raises(ModelArtifactError):
            service.forecast(
                crop=crop, season=season, state=state, district=district, horizon=1
            )
    finally:
        del service.adapter.predict_estimator  # type: ignore[attr-defined]


def test_negative_output_rejected_not_clamped(service) -> None:
    history = service.adapter.load_history()
    state, district, crop, season = richest_series(history)
    service.adapter.predict_estimator = lambda: _FakeEstimator(-5.0)  # type: ignore[method-assign]
    try:
        with pytest.raises(ModelArtifactError):
            service.forecast(
                crop=crop, season=season, state=state, district=district, horizon=1
            )
    finally:
        del service.adapter.predict_estimator  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# Options + endpoint integration
# --------------------------------------------------------------------------- #
def test_options_shape(service) -> None:
    options = service.options()
    assert options["unit"] == "kg/ha"
    assert options["unit_status"] == "verification_pending"
    assert options["latest_observation_year"] == 2024
    assert options["reference_year"] == REFERENCE_YEAR
    assert set(options["valid_horizons"]) == {1, 2, 3, 4, 5}
    assert options["crops"] and options["states"]
    assert "1" in options["research_mae_by_horizon"]


def test_experimental_endpoint_forecast(client) -> None:
    history = build_adapter().load_history()
    state, district, crop, season = richest_series(history)
    response = client.post(
        "/api/v1/predictions/yield/forecast",
        json={"crop": crop, "season": season, "state": state, "district": district, "horizon": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["quality_status"] == "experimental"
    assert body["production_approved"] is False
    assert body["predicted_yield"] > 0
    assert body["provenance"]["model_id"] == "phase2d_pooled_rf_research"


def test_experimental_endpoint_invalid_district_422(client) -> None:
    history = build_adapter().load_history()
    state, _d, crop, season = richest_series(history)
    response = client.post(
        "/api/v1/predictions/yield/forecast",
        json={
            "crop": crop,
            "season": season,
            "state": state,
            "district": "Unknown District",
            "horizon": 1,
        },
    )
    assert response.status_code == 422


def test_experimental_endpoint_bad_horizon_422(client) -> None:
    response = client.post(
        "/api/v1/predictions/yield/forecast",
        json={
            "crop": "Rice",
            "season": "Kharif",
            "state": "West Bengal",
            "district": "Uttar Dinajpur",
            "horizon": 9,
        },
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Manual-model regression: the served HGB path is untouched by Phase 2E
# --------------------------------------------------------------------------- #
def test_manual_hgb_endpoint_still_works(client) -> None:
    options = client.get("/api/v1/predictions/yield/options")
    assert options.status_code == 200
    manual = client.post(
        "/api/v1/predictions/yield",
        json={
            "crop": "Rice",
            "season": "Kharif",
            "crop_category": "Individual Crop Candidate",
            "state": "Andaman And Nicobar Islands",
            "district": "North And Middle Andaman",
            "year_start": 2019,
        },
    )
    assert manual.status_code == 200
    assert manual.json()["model_name"] == "HistGradientBoostingRegressor"
    assert np.isfinite(manual.json()["prediction"])


def test_settings_do_not_mutate_manual_paths() -> None:
    base = Settings()
    assert base.yield_artifact_sha256 == settings.yield_artifact_sha256
    assert base.yield_metadata_sha256 == settings.yield_metadata_sha256
    assert base.yield_artifact_path == settings.yield_artifact_path
    exp_path = str(base.experimental_forecast_artifact_path).lower()
    assert "phase2d_pooled_rf_research" in exp_path
    assert base.experimental_forecast_artifact_path != base.yield_artifact_path
    assert (
        base.experimental_forecast_metadata_path != base.yield_metadata_path
    )


def test_artifact_bundle_is_joblib_and_reproducible(adapter) -> None:
    first = joblib.load(settings.experimental_forecast_artifact_path)["estimators"][1]
    second = adapter.predict_estimator()
    probe = np.zeros((1, 66))
    probe[0, 0] = 2000.0
    assert np.allclose(first.predict(probe), second.predict(probe))
