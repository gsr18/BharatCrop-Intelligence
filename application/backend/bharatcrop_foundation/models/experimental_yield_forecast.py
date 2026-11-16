"""Phase 2E — isolated experimental future-yield forecasting service.

Wraps the Phase 2D pooled-panel RandomForest research artifact
(``phase2d_pooled_rf_research.joblib``) behind a strictly guarded, clearly
labelled capability. It is completely independent of the served manual
HistGradientBoosting model in :mod:`bharatcrop_foundation.models.yield_prediction`
— that path, its artifact, and its schema are untouched.

Design guarantees enforced here:

* The inference contract is explicit and validated against the artifact:
  pooled ``random_forest`` strategy, exact 15-feature order, one-hot
  Crop/Season/State over the training vocabulary, stable district integer code.
* Origin-only features are rebuilt by the shared
  :mod:`experimental_forecast_features` module (no logic duplication of a
  *different* implementation; parity is asserted against the research code in
  tests).
* The forecast origin is never fabricated: it is the most recent observed
  marketing year for that exact series. A target year that is already in the
  past relative to the data or to today is reported as such and never labelled
  a future projection.
* Non-finite and negative model outputs are rejected; nothing is clamped.
* Every response carries model id/version, training cutoff, origin/target years,
  horizon, history depth, eligibility status, experimental status, and
  limitations/warnings.
"""
from __future__ import annotations

import datetime as _datetime
import hashlib
import importlib
import json
import logging
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from bharatcrop_foundation.models import experimental_forecast_features as EFF
from bharatcrop_foundation.models.yield_prediction import (
    YIELD_TARGET_UNIT_STATUS,
    YIELD_UNIT,
    YIELD_UNIT_SOURCE,
    YIELD_UNIT_SOURCE_URL,
    ModelArtifactError,
    ModelNotReadyError,
)

logger = logging.getLogger(__name__)

MODEL_ID = "phase2d_pooled_rf_research"
MODEL_NAME = "pooled_panel random_forest (research)"
MODEL_VERSION = "phase2d-pooled-rf-v1"
VALID_HORIZONS = (1, 2, 3, 4, 5)
MIN_HISTORY_EXPERIMENTAL = 1
MIN_HISTORY_HIGH_HORIZON = 4
HIGH_HORIZONS = (4, 5)

# Data-freshness / projection-status codes surfaced to callers.
STATUS_OBSERVED_TARGET = "target_already_observed"
STATUS_PAST_OR_PRESENT_TARGET = "target_in_past_or_present"
STATUS_FUTURE_TARGET = "future_target_beyond_latest_data"
FUTURE_STATUSES = (
    STATUS_OBSERVED_TARGET,
    STATUS_PAST_OR_PRESENT_TARGET,
    STATUS_FUTURE_TARGET,
)

HISTORICAL_COLUMNS = [
    "State",
    "District",
    "Crop",
    "Season",
    "YearStart",
    "Yield",
]


class ForecastContractError(ModelArtifactError):
    """Raised when the research artifact violates the inference contract."""


@dataclass(frozen=True)
class ForecastProvenance:
    model_id: str
    model_name: str
    model_version: str
    strategy: str
    base_model: str
    cohort: str
    artifact_sha256: str
    metadata_sha256: str
    training_cutoff_year: int
    latest_observation_year: int
    reference_year: int
    target: str
    target_unit: str
    target_unit_status: str
    target_unit_source: str
    target_unit_source_url: str
    design_width: int
    numeric_features: tuple[str, ...]
    research_expanding_window_mae: Mapping[str, float]
    research_expanding_window_r2: Mapping[str, float]


@dataclass(frozen=True)
class ForecastResult:
    crop: str
    season: str
    state: str
    district: str
    horizon: int
    origin_year: int
    target_year: int
    predicted_yield: float
    unit: str
    unit_status: str
    history_count: int
    eligibility_status: str
    future_projection: bool
    target_year_status: str
    experimental_status: str
    provenance: ForecastProvenance
    limitations: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


class ExperimentalForecastAdapter:
    """Loads and verifies the research artifact against an explicit contract."""

    def __init__(
        self,
        artifact_path: Path,
        metadata_path: Path,
        historical_data_path: Path,
        *,
        expected_artifact_sha256: str | None = None,
        expected_metadata_sha256: str | None = None,
    ) -> None:
        self.artifact_path = artifact_path
        self.metadata_path = metadata_path
        self.historical_data_path = historical_data_path
        self.expected_artifact_sha256 = (
            expected_artifact_sha256.lower() if expected_artifact_sha256 else None
        )
        self.expected_metadata_sha256 = (
            expected_metadata_sha256.lower() if expected_metadata_sha256 else None
        )
        self._bundle: dict[str, Any] | None = None
        self._metadata: dict[str, Any] | None = None
        self._artifact_sha256: str | None = None
        self._metadata_sha256: str | None = None

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def inspect(self) -> tuple[str, ...]:
        """Return non-empty reason codes when the artifact is not usable."""
        reasons: list[str] = []
        if not self.metadata_path.is_file():
            return ("forecast_metadata_unavailable",)
        if not self.artifact_path.is_file():
            return ("forecast_artifact_unavailable",)
        try:
            raw_meta = self.metadata_path.read_bytes()
            self._metadata = json.loads(raw_meta)
        except (OSError, json.JSONDecodeError):
            return ("forecast_metadata_invalid",)
        self._metadata_sha256 = hashlib.sha256(raw_meta).hexdigest()

        self._artifact_sha256 = self._sha256(self.artifact_path)
        if self.expected_metadata_sha256 is None:
            reasons.append("forecast_metadata_checksum_not_approved")
        elif self._metadata_sha256 != self.expected_metadata_sha256:
            reasons.append("forecast_metadata_checksum_mismatch")
        if self.expected_artifact_sha256 is None:
            reasons.append("forecast_artifact_checksum_not_approved")
        elif self._artifact_sha256 != self.expected_artifact_sha256:
            reasons.append("forecast_artifact_checksum_mismatch")
        if not self.historical_data_path.is_file():
            reasons.append("forecast_history_source_unavailable")
        return tuple(dict.fromkeys(reasons))

    def _load_bundle(self) -> dict[str, Any]:
        if self._bundle is not None:
            return self._bundle
        joblib = importlib.import_module("joblib")
        try:
            bundle = joblib.load(BytesIO(self.artifact_path.read_bytes()))
        except Exception as error:  # pragma: no cover - defensive
            raise ForecastContractError("research artifact could not be loaded") from error
        if not isinstance(bundle, dict):
            raise ForecastContractError("research artifact bundle is malformed")
        self._bundle = bundle
        return bundle

    def validate_contract(self) -> dict[str, Any]:
        """Verify strategy, model, feature order, encodings, and estimator parity."""
        bundle = self._load_bundle()
        if bundle.get("strategy") != "pooled_panel":
            raise ForecastContractError("artifact strategy is not pooled_panel")
        if bundle.get("model_name") != "random_forest":
            raise ForecastContractError("artifact base model is not random_forest")
        if tuple(bundle.get("numeric_features", ())) != tuple(EFF.NUMERIC_FEATURES):
            raise ForecastContractError("artifact numeric feature order mismatch")
        vocab = bundle.get("vocab")
        if not isinstance(vocab, dict):
            raise ForecastContractError("artifact vocabulary is missing")
        for column in EFF.LOW_CARDINALITY:
            if column not in vocab or not vocab[column]:
                raise ForecastContractError(f"artifact vocabulary missing {column}")
        if not vocab.get("districts"):
            raise ForecastContractError("artifact district vocabulary is missing")
        estimators = bundle.get("estimators")
        if not isinstance(estimators, Mapping) or not estimators:
            raise ForecastContractError("artifact has no horizon estimators")
        signatures = set()
        for horizon, estimator in estimators.items():
            if horizon not in VALID_HORIZONS:
                raise ForecastContractError(f"unexpected horizon key {horizon}")
            n_features = getattr(estimator, "n_features_in_", None)
            if n_features != EFF.design_width(vocab):
                raise ForecastContractError(
                    "estimator feature width does not match the encoded design"
                )
            first = estimator.estimators_[0]
            signatures.add(
                (
                    n_features,
                    int(first.tree_.node_count),
                    int(np.argmax(first.tree_.threshold)),
                )
            )
        # pooled_panel: a single model replicated per horizon key.
        if len(signatures) != 1:
            raise ForecastContractError("per-horizon estimators are not a pooled model")
        return bundle

    def predict_estimator(self) -> Any:
        bundle = self.validate_contract()
        # All horizon keys reference the identical pooled estimator.
        return bundle["estimators"][min(bundle["estimators"])]

    def vocab(self) -> dict[str, list[str]]:
        return cast(dict[str, list[str]], self._load_bundle()["vocab"])

    def load_history(self) -> pd.DataFrame:
        try:
            frame = pd.read_csv(
                self.historical_data_path,
                usecols=HISTORICAL_COLUMNS,
                low_memory=False,
            )
        except (OSError, ValueError) as error:
            raise ForecastContractError("forecast history source is unreadable") from error
        frame["YearStart"] = pd.to_numeric(frame["YearStart"], errors="coerce")
        frame["Yield"] = pd.to_numeric(frame["Yield"], errors="coerce")
        return frame.dropna(subset=["YearStart", "Yield"])


class ExperimentalYieldForecastService:
    BASE_LIMITATIONS = (
        "This is an experimental research model, not validated for production.",
        "It is independent of the served HistGradientBoosting yield model.",
        "The pooled-panel R-squared reflects interpolation over recurring "
        "districts; generalization to unseen districts is not established.",
        "No validated future-season weather or price signal is used; gains over "
        "simple historical baselines are modest.",
        f"The {YIELD_UNIT} target unit is {YIELD_TARGET_UNIT_STATUS.replace('_', ' ')}; "
        "no unit conversion is applied.",
    )

    def __init__(
        self,
        adapter: ExperimentalForecastAdapter,
        *,
        reference_year: int | None = None,
    ) -> None:
        self.adapter = adapter
        self._reference_year = reference_year
        self._history: pd.DataFrame | None = None
        self._latest_observation_year: int | None = None

    @property
    def reference_year(self) -> int:
        if self._reference_year is not None:
            return self._reference_year
        return _datetime.datetime.now().year

    # -- readiness ----------------------------------------------------------
    def availability(self) -> tuple[str, tuple[str, ...]]:
        reasons = self.adapter.inspect()
        if reasons:
            return "unavailable", reasons
        try:
            self.adapter.validate_contract()
            self._ensure_history()
        except (ForecastContractError, ModelArtifactError):
            return "unavailable", ("forecast_artifact_contract_invalid",)
        return "available", ()

    def _ensure_history(self) -> pd.DataFrame:
        if self._history is None:
            self._history = self.adapter.load_history()
            if self._history.empty:
                raise ForecastContractError("forecast history source is empty")
            self._latest_observation_year = int(self._history["YearStart"].max())
        assert self._history is not None
        return self._history

    def latest_observation_year(self) -> int:
        self._ensure_history()
        assert self._latest_observation_year is not None
        return self._latest_observation_year

    # -- options ------------------------------------------------------------
    def options(self) -> dict[str, Any]:
        availability, reasons = self.availability()
        if availability != "available":
            raise ModelNotReadyError(reasons)
        history = self._ensure_history()
        vocab = self.adapter.vocab()
        districts_by_state: dict[str, list[str]] = {}
        pairs = history[["State", "District"]].dropna().drop_duplicates()
        for state, group in pairs.groupby("State", sort=True):
            districts_by_state[str(state)] = sorted(
                str(d) for d in group["District"].tolist()
            )
        metrics = (self.adapter._metadata or {}).get(
            "expanding_window_metrics_strict", {}
        )
        return {
            "model_id": MODEL_ID,
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "experimental_status": "experimental_research_not_validated",
            "crops": sorted(vocab["Crop"]),
            "seasons": sorted(vocab["Season"]),
            "states": sorted(districts_by_state),
            "districts_by_state": districts_by_state,
            "valid_horizons": list(VALID_HORIZONS),
            "latest_observation_year": self.latest_observation_year(),
            "training_cutoff_year": self.latest_observation_year(),
            "reference_year": self.reference_year,
            "eligibility_rules": {
                "T+1..T+3": "experimental, requires a valid observed origin",
                "T+4,T+5": "restricted to rich-history recurring series "
                f"(>= {MIN_HISTORY_HIGH_HORIZON} prior observations)",
                "unseen_district": "rejected; generalization is not claimed",
            },
            "unit": YIELD_UNIT,
            "unit_status": YIELD_TARGET_UNIT_STATUS,
            "research_mae_by_horizon": {
                str(h): metrics.get(f"T+{h}", {}).get("mae")
                for h in VALID_HORIZONS
                if isinstance(metrics.get(f"T+{h}"), dict)
            },
            "limitations": list(self.BASE_LIMITATIONS),
        }

    # -- forecasting --------------------------------------------------------
    def forecast(
        self,
        *,
        crop: str,
        season: str,
        state: str,
        district: str,
        horizon: int,
    ) -> ForecastResult:
        availability, reasons = self.availability()
        if availability != "available":
            raise ModelNotReadyError(reasons)

        if horizon not in VALID_HORIZONS:
            raise ValueError("Horizon must be an integer from 1 to 5.")
        for label, text in (
            ("Crop", crop),
            ("Season", season),
            ("State", state),
            ("District", district),
        ):
            if not isinstance(text, str) or not text.strip() or text != text.strip():
                raise ValueError(f"{label} must be a non-empty, unpadded value.")

        vocab = self.adapter.vocab()
        if season.casefold() == "total":
            raise ValueError("Aggregate Total season is not accepted.")
        if crop not in vocab["Crop"]:
            raise ValueError("Unsupported crop for this experimental model.")
        if season not in vocab["Season"]:
            raise ValueError("Unsupported season for this experimental model.")
        if state not in vocab["State"]:
            raise ValueError("Unsupported state for this experimental model.")
        # Never run the model on an unseen district: encoding collapses to -1.
        if district not in vocab["districts"]:
            raise ValueError("Unsupported district: unseen-district generalization is not claimed.")

        history = self._ensure_history()
        observations = EFF.series_observations(
            history, state=state, district=district, crop=crop, season=season
        )
        if observations.empty:
            raise ValueError(
                "No historical observations for this crop/season/state/district series."
            )

        origin_year = int(observations["YearStart"].max())
        latest = self.latest_observation_year()
        feature_row = EFF.origin_feature_row(
            observations, origin_year=origin_year, horizon=horizon
        )
        hist_n = int(feature_row["hist_n"])
        target_year = origin_year + horizon

        self._check_eligibility(horizon, hist_n, origin_year, latest)

        design = EFF.make_design_row(
            feature_row,
            crop=crop,
            season=season,
            state=state,
            district=district,
            vocab=vocab,
        )
        estimator = self.adapter.predict_estimator()
        try:
            predictions = np.asarray(estimator.predict(design))
        except Exception as error:
            raise ModelArtifactError("Experimental forecast inference failed.") from error
        if predictions.shape != (1,):
            raise ModelArtifactError("Model returned an invalid prediction count.")
        value = float(predictions[0])
        if not math.isfinite(value):
            logger.warning(
                "Experimental forecast rejected a non-finite value "
                "crop=%r season=%r state=%r district=%r horizon=%r.",
                crop,
                season,
                state,
                district,
                horizon,
            )
            raise ModelArtifactError("Model returned a non-finite value.")
        if value < 0:
            logger.warning(
                "Experimental forecast rejected a negative estimate (value=%r) "
                "for crop=%r season=%r state=%r district=%r horizon=%r; no clamping applied.",
                value,
                crop,
                season,
                state,
                district,
                horizon,
            )
            raise ModelArtifactError("Model returned an implausible negative estimate.")

        target_status, future_projection = self._classify_target(target_year, latest)
        warnings = self._warnings(horizon, hist_n, origin_year, latest, target_status)
        limitations = self._limitations(horizon, hist_n, target_status)
        eligibility_status = (
            "eligible_high_horizon_restricted"
            if horizon in HIGH_HORIZONS
            else "eligible_experimental"
        )

        return ForecastResult(
            crop=crop,
            season=season,
            state=state,
            district=district,
            horizon=horizon,
            origin_year=origin_year,
            target_year=target_year,
            predicted_yield=value,
            unit=YIELD_UNIT,
            unit_status=YIELD_TARGET_UNIT_STATUS,
            history_count=hist_n,
            eligibility_status=eligibility_status,
            future_projection=future_projection,
            target_year_status=target_status,
            experimental_status="experimental_research_not_validated",
            provenance=self._provenance(design.shape[1]),
            limitations=limitations,
            warnings=warnings,
        )

    @staticmethod
    def _check_eligibility(
        horizon: int, hist_n: int, origin_year: int, latest: int
    ) -> None:
        if origin_year > latest:
            raise ValueError("Forecast origin cannot be later than the latest observed year.")
        if hist_n < MIN_HISTORY_EXPERIMENTAL:
            raise ValueError("Insufficient history to build a valid origin feature.")
        if horizon in HIGH_HORIZONS and hist_n < MIN_HISTORY_HIGH_HORIZON:
            raise ValueError(
                "T+4 and T+5 projections are restricted to rich-history recurring "
                f"series with at least {MIN_HISTORY_HIGH_HORIZON} prior observations."
            )

    def _classify_target(self, target_year: int, latest: int) -> tuple[str, bool]:
        reference = self.reference_year
        if target_year <= latest:
            return STATUS_OBSERVED_TARGET, False
        if target_year <= reference:
            return STATUS_PAST_OR_PRESENT_TARGET, False
        return STATUS_FUTURE_TARGET, True

    def _warnings(
        self,
        horizon: int,
        hist_n: int,
        origin_year: int,
        latest: int,
        target_status: str,
    ) -> tuple[str, ...]:
        reference = self.reference_year
        warnings: list[str] = [
            "Experimental research projection; not validated for operational use.",
            f"Model trained through {latest} (APY observation cutoff); the "
            "forecast origin for this series is {0}.".format(origin_year),
        ]
        staleness = reference - latest
        if staleness > 0:
            warnings.append(
                f"Source data is {staleness} year(s) behind the current reference "
                f"year {reference}; the most recent actual APY observation is {latest}."
            )
        if target_status == STATUS_OBSERVED_TARGET:
            warnings.append(
                "Requested target year is already within the observed data; this is "
                "a hindcast, not a future projection."
            )
        elif target_status == STATUS_PAST_OR_PRESENT_TARGET:
            warnings.append(
                f"Target year is at or before the current year {reference}; it is not "
                "a future year. Do not treat this as a forward-looking projection."
            )
        if horizon in HIGH_HORIZONS:
            warnings.append(
                "High-horizon (T+4/T+5) projection: low evidence, restricted to "
                "rich-history recurring series only."
            )
        if hist_n < MIN_HISTORY_HIGH_HORIZON:
            warnings.append(
                f"Thin history ({hist_n} prior observations); feature reliability is reduced."
            )
        return tuple(warnings)

    def _limitations(
        self, horizon: int, hist_n: int, target_status: str
    ) -> tuple[str, ...]:
        extra: list[str] = list(self.BASE_LIMITATIONS)
        if target_status != STATUS_FUTURE_TARGET:
            extra.append(
                "This request does not target a genuinely future year relative to "
                "the available data and today; it cannot be presented as a forecast."
            )
        if horizon in HIGH_HORIZONS:
            extra.append(
                "T+4/T+5 support is limited to deep, recurring histories and is the "
                "weakest-evidence tier of this experimental capability."
            )
        if hist_n < MIN_HISTORY_HIGH_HORIZON:
            extra.append(
                "Short observed history reduces confidence in lag/rolling features."
            )
        return tuple(dict.fromkeys(extra))

    def _provenance(self, design_width: int) -> ForecastProvenance:
        metadata = self.adapter._metadata or {}
        metrics = metadata.get("expanding_window_metrics_strict", {})
        mae = {
            str(h): metrics.get(f"T+{h}", {}).get("mae")
            for h in VALID_HORIZONS
            if isinstance(metrics.get(f"T+{h}"), dict)
        }
        r2 = {
            str(h): metrics.get(f"T+{h}", {}).get("r2")
            for h in VALID_HORIZONS
            if isinstance(metrics.get(f"T+{h}"), dict)
        }
        latest = self.latest_observation_year()
        assert self.adapter._artifact_sha256 is not None
        assert self.adapter._metadata_sha256 is not None
        return ForecastProvenance(
            model_id=MODEL_ID,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            strategy=metadata.get("strategy", "pooled_panel"),
            base_model=metadata.get("base_model", "random_forest"),
            cohort=metadata.get("cohort", "strict"),
            artifact_sha256=self.adapter._artifact_sha256,
            metadata_sha256=self.adapter._metadata_sha256,
            training_cutoff_year=latest,
            latest_observation_year=latest,
            reference_year=self.reference_year,
            target="Yield",
            target_unit=YIELD_UNIT,
            target_unit_status=YIELD_TARGET_UNIT_STATUS,
            target_unit_source=YIELD_UNIT_SOURCE,
            target_unit_source_url=YIELD_UNIT_SOURCE_URL,
            design_width=design_width,
            numeric_features=EFF.NUMERIC_FEATURES,
            research_expanding_window_mae={
                k: float(v) for k, v in mae.items() if isinstance(v, (int, float))
            },
            research_expanding_window_r2={
                k: float(v) for k, v in r2.items() if isinstance(v, (int, float))
            },
        )


__all__ = [
    "ExperimentalForecastAdapter",
    "ExperimentalYieldForecastService",
    "ForecastContractError",
    "ForecastResult",
    "ForecastProvenance",
    "MODEL_ID",
    "MODEL_VERSION",
    "VALID_HORIZONS",
    "STATUS_FUTURE_TARGET",
    "STATUS_OBSERVED_TARGET",
    "STATUS_PAST_OR_PRESENT_TARGET",
]
