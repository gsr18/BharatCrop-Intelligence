from __future__ import annotations

import hashlib
import importlib
import json
import logging
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Protocol, cast

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, ValidationError, field_validator

FEATURES = (
    "Crop",
    "Season",
    "Crop_Category",
    "State",
    "District",
    "FE_YearStart",
)
CATEGORICAL_FEATURES = ("Crop", "Season", "Crop_Category", "State", "District")
NUMERIC_FEATURES = ("FE_YearStart",)
YIELD_UNIT = "kg/ha"
YIELD_TARGET_UNIT_STATUS = "verification_pending"
YIELD_TARGET_UNIT_DISPLAY = "Yield (kg/ha; unit verification pending)"
YIELD_TARGET_SEMANTICS = (
    "APY Yield field, documented by MoSPI as kilograms per hectare (kg/ha). "
    "A static consistency check supports kg/ha as the likely unit, but unit "
    "consistency is not proven for every source row, so the unit is reported "
    "as pending verification and no conversion is applied to predictions."
)
logger = logging.getLogger(__name__)
YIELD_UNIT_SOURCE = (
    "Ministry of Statistics and Programme Implementation, Compendium of Datasets "
    "and Registries in India 2024, section 4.10.5, Agricultural Productivity"
)
YIELD_UNIT_SOURCE_URL = (
    "https://mospi.gov.in/sites/default/files/publication_reports/"
    "Compendium_of_Datasets_and_Registries_in_India_2024_0.pdf"
)
YIELD_TARGET_CONSTRUCTION = (
    "The APY annual Yield field is the training target. Notebook 06 reshapes the "
    "source Yield columns without recalculating or scaling them; notebook 16 "
    "coerces Yield to numeric and uses it directly as y."
)
YIELD_CONSISTENCY_CHECK = (
    "Notebook 16 checks Yield against Production / Area. A static check of the "
    "41,212 positive individual-crop primary-cohort APY rows from 2013-2022 "
    "found a median Yield / ((Production / Area) * 1000) ratio of 1.0, with "
    "71.3% of rows within 10% of that ratio. Row-level deviations remain and "
    "no conversion is applied to predictions."
)


class ModelNotReadyError(Exception):
    def __init__(self, reason_codes: Sequence[str]) -> None:
        self.reason_codes = tuple(reason_codes)
        super().__init__("Yield model is not ready.")


class ModelArtifactError(Exception):
    pass


class YieldFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    Crop: StrictStr
    Season: StrictStr
    Crop_Category: StrictStr
    State: StrictStr
    District: StrictStr
    FE_YearStart: StrictInt

    @field_validator(*CATEGORICAL_FEATURES)
    @classmethod
    def non_empty_category(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("Categorical features must be non-empty and unpadded.")
        return value

    @field_validator("Season")
    @classmethod
    def reject_aggregate_season(cls, value: str) -> str:
        if value.casefold() == "total":
            raise ValueError("Aggregate Total season is not accepted.")
        return value


class YieldMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    model_name: StrictStr
    model_version: StrictStr | None = None
    features: list[StrictStr]
    categorical_features: list[StrictStr]
    numeric_features: list[StrictStr]
    target: StrictStr
    training_year_start: StrictInt
    training_year_end: StrictInt


@dataclass(frozen=True)
class Readiness:
    execution_available: bool
    reason_codes: tuple[str, ...]
    availability: str
    quality_status: str
    production_approved: bool
    artifact_sha256: str | None
    model_name: str | None
    model_version: str | None
    target: str | None
    target_unit: str | None
    training_year_start: int | None
    training_year_end: int | None
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class YieldProvenance:
    model_version: str | None
    artifact_sha256: str
    metadata_sha256: str
    model_name: str
    target: str
    target_unit: str
    target_unit_status: str
    target_unit_source: str
    target_unit_source_url: str
    target_construction: str
    target_consistency_check: str
    target_conversion_applied: bool
    training_year_start: int
    training_year_end: int
    validation_metrics: Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class YieldPrediction:
    value: float
    provenance: YieldProvenance
    limitations: tuple[str, ...]
    prediction_period_status: str


class Predictor(Protocol):
    feature_names_in_: Sequence[str]

    def predict(self, values: pd.DataFrame) -> Sequence[float]: ...


ModelLoader = Callable[[bytes], Predictor]


class YieldModelAdapter:
    def __init__(
        self,
        artifact_path: Path,
        metadata_path: Path,
        expected_artifact_sha256: str | None,
        expected_metadata_sha256: str | None,
        *,
        loader: ModelLoader | None = None,
    ) -> None:
        self.artifact_path = artifact_path
        self.metadata_path = metadata_path
        self.expected_artifact_sha256 = expected_artifact_sha256
        self.expected_metadata_sha256 = expected_metadata_sha256
        self._loader = loader or self._joblib_loader
        self._model: Predictor | None = None
        self._metadata: YieldMetadata | None = None
        self._artifact_sha256: str | None = None
        self._metadata_sha256: str | None = None

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _joblib_loader(artifact_bytes: bytes) -> Predictor:
        joblib = importlib.import_module("joblib")
        model = joblib.load(BytesIO(artifact_bytes))
        if not callable(getattr(model, "predict", None)):
            raise ModelArtifactError("Artifact does not provide prediction.")
        return cast(Predictor, model)

    def inspect(self) -> tuple[YieldMetadata | None, tuple[str, ...]]:
        reasons: list[str] = []
        if self.metadata_path.suffix.casefold() != ".json":
            reasons.append("metadata_path_invalid")
        if not self.metadata_path.is_file():
            return None, tuple([*reasons, "metadata_unavailable"])
        try:
            raw_metadata = self.metadata_path.read_bytes()
            payload = json.loads(raw_metadata)
            metadata = YieldMetadata.model_validate(payload)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError):
            return None, ("metadata_invalid",)

        if tuple(metadata.features) != FEATURES:
            reasons.append("feature_contract_mismatch")
        if tuple(metadata.categorical_features) != CATEGORICAL_FEATURES:
            reasons.append("categorical_feature_contract_mismatch")
        if tuple(metadata.numeric_features) != NUMERIC_FEATURES:
            reasons.append("numeric_feature_contract_mismatch")
        if metadata.target != "Yield":
            reasons.append("target_contract_mismatch")
        if metadata.model_version is None or not metadata.model_version.strip():
            reasons.append("model_version_not_recorded")
        if (
            metadata.training_year_start > metadata.training_year_end
            or metadata.training_year_start < 1
        ):
            reasons.append("training_year_range_invalid")
        self._metadata = metadata
        self._metadata_sha256 = hashlib.sha256(raw_metadata).hexdigest()
        if self.expected_metadata_sha256 is None:
            reasons.append("metadata_checksum_not_approved")
        elif self._metadata_sha256 != self.expected_metadata_sha256:
            reasons.append("metadata_checksum_mismatch")

        if self.artifact_path.suffix.casefold() != ".joblib":
            reasons.append("artifact_path_invalid")
        if not self.artifact_path.is_file():
            reasons.append("artifact_unavailable")
        else:
            try:
                self._artifact_sha256 = self._sha256(self.artifact_path)
            except OSError:
                reasons.append("artifact_unavailable")
            else:
                if self.expected_artifact_sha256 is None:
                    reasons.append("artifact_checksum_not_approved")
                elif self._artifact_sha256 != self.expected_artifact_sha256:
                    reasons.append("artifact_checksum_mismatch")
        return metadata, tuple(dict.fromkeys(reasons))

    def load(self) -> Predictor:
        if self._model is not None:
            return self._model
        metadata, reasons = self.inspect()
        # A missing model version blocks readiness, but does not affect deserialization.
        blocking_reasons = tuple(
            reason for reason in reasons if reason != "model_version_not_recorded"
        )
        if blocking_reasons:
            raise ModelArtifactError("Model artifact or metadata failed validation.")
        if metadata is None or self._artifact_sha256 is None:
            raise ModelArtifactError("Model artifacts are unavailable.")
        try:
            artifact_bytes = self.artifact_path.read_bytes()
            if hashlib.sha256(artifact_bytes).hexdigest() != self._artifact_sha256:
                raise ModelArtifactError("Artifact changed during integrity validation.")
            model = self._loader(artifact_bytes)
            feature_names = tuple(model.feature_names_in_)
        except Exception as error:
            raise ModelArtifactError("Model artifact could not be loaded.") from error
        if feature_names != tuple(metadata.features):
            raise ModelArtifactError("Artifact feature contract does not match metadata.")
        self._model = model
        return model


class YieldPredictionService:
    LIMITATIONS = (
        "Predictions are experimental model estimates, not production-approved advice.",
        "Predictions are feature-based estimates, not validated forecasts of future yield.",
        "Season Total semantics are unresolved and aggregate Total inputs are rejected.",
        "Geographic coverage and unseen-category reliability are unverified.",
        "No validated performance metric (MAE, RMSE, or R-squared) is available for this "
        "served artifact; the recorded R-squared values describe a different "
        "weather-inclusive candidate and are reference context only.",
        "The kg/ha target unit is documented by MoSPI and supported by a static consistency "
        "check, but row-level unit consistency is unverified; the unit is reported as pending.",
        "Some APY target values do not match the simple Production / Area ratio; source "
        "measurement and crop-specific reporting differences remain possible.",
    )
    RELEASE_GATES = (
        "total_season_semantics_unverified",
        "geographic_coverage_unverified",
        "category_coverage_unverified",
        "artifact_runtime_compatibility_unverified",
        "independent_model_release_not_approved",
    )

    def __init__(
        self,
        adapter: YieldModelAdapter,
        *,
        training_data_path: Path | None = None,
        total_season_semantics_verified: bool = False,
        geographic_coverage_verified: bool = False,
        category_coverage_verified: bool = False,
        artifact_runtime_verified: bool = False,
        release_approved: bool = False,
        supported_categories: Mapping[str, frozenset[str]] | None = None,
    ) -> None:
        self.adapter = adapter
        self.training_data_path = training_data_path
        self._gates = {
            "total_season_semantics_unverified": total_season_semantics_verified,
            "geographic_coverage_unverified": geographic_coverage_verified,
            "category_coverage_unverified": category_coverage_verified,
            "artifact_runtime_compatibility_unverified": artifact_runtime_verified,
            "independent_model_release_not_approved": release_approved,
        }
        self.supported_categories = supported_categories
        self._districts_by_state: dict[str, frozenset[str]] | None = None
        self.supported_combinations: frozenset[tuple[str, ...]] | None = None

    @classmethod
    def _limitations(cls, metadata: YieldMetadata | None) -> tuple[str, ...]:
        recorded = (metadata.model_extra or {}).get("limitations", []) if metadata else []
        recorded_limitations = (
            tuple(item for item in recorded if isinstance(item, str))
            if isinstance(recorded, list)
            else ()
        )
        version_limitation = (
            ("Model version is not recorded.",)
            if metadata is not None and not metadata.model_version
            else ()
        )
        return tuple(
            dict.fromkeys((*cls.LIMITATIONS, *version_limitation, *recorded_limitations))
        )

    @staticmethod
    def _model_categories(model: Predictor) -> dict[str, frozenset[str]]:
        steps = getattr(model, "named_steps", None)
        if not isinstance(steps, Mapping):
            raise ModelArtifactError("Model preprocessing is unavailable.")
        preprocessor = steps.get("preprocessor")
        named_transformers = getattr(preprocessor, "named_transformers_", None)
        if not isinstance(named_transformers, Mapping):
            raise ModelArtifactError("Model preprocessing is unavailable.")
        categorical = named_transformers.get("categorical")
        categories = getattr(categorical, "categories_", None)
        if not isinstance(categories, Sequence) or len(categories) != len(CATEGORICAL_FEATURES):
            raise ModelArtifactError("Model category metadata is unavailable.")
        result: dict[str, frozenset[str]] = {}
        for field, values in zip(CATEGORICAL_FEATURES, categories, strict=True):
            try:
                labels = frozenset(str(value) for value in values)
            except TypeError as error:
                raise ModelArtifactError("Model category metadata is invalid.") from error
            if not labels:
                raise ModelArtifactError("Model category metadata is empty.")
            result[field] = labels
        return result

    def options(self) -> dict[str, object]:
        model = self.adapter.load()
        categories = self._model_categories(model)
        if self.training_data_path is None:
            raise ModelArtifactError("Training category source is unavailable.")
        if self._districts_by_state is None:
            try:
                frame = pd.read_csv(
                    self.training_data_path,
                    usecols=[
                        "State",
                        "District",
                        "Crop",
                        "Season",
                        "Crop_Category",
                        "Year",
                        "Area",
                        "Production",
                        "Yield",
                    ],
                    low_memory=False,
                )
            except (OSError, ValueError, pd.errors.ParserError) as error:
                raise ModelArtifactError("Training category source is unavailable.") from error
            year_start = pd.to_numeric(
                frame["Year"].astype("string").str.extract(r"^(\d{4})", expand=False),
                errors="coerce",
            )
            numeric = frame[["Area", "Production", "Yield"]].apply(
                pd.to_numeric,
                errors="coerce",
            )
            valid = (
                frame["Crop_Category"].eq("Individual Crop Candidate")
                & frame["Crop"].astype("string").str.casefold().ne("total")
                & frame["Season"].astype("string").str.casefold().ne("total")
                & year_start.between(2013, 2022)
                & numeric["Area"].gt(0)
                & numeric["Production"].gt(0)
                & numeric["Yield"].gt(0)
            )
            training_pairs = frame.loc[valid, ["State", "District"]].drop_duplicates()
            training_pairs = training_pairs[
                training_pairs["State"].isin(categories["State"])
                & training_pairs["District"].isin(categories["District"])
            ]
            districts_by_state: dict[str, frozenset[str]] = {}
            for state, group in training_pairs.groupby("State", sort=True):
                if isinstance(state, str):
                    districts_by_state[state] = frozenset(
                        district
                        for district in group["District"].tolist()
                        if isinstance(district, str)
                    )
            self._districts_by_state = districts_by_state
            supported_rows = frame.loc[valid, list(CATEGORICAL_FEATURES)].drop_duplicates()
            self.supported_combinations = frozenset(
                tuple(row)
                for row in supported_rows.itertuples(index=False, name=None)
                if all(isinstance(value, str) for value in row)
            )
        metadata, _ = self.adapter.inspect()
        if metadata is None:
            raise ModelArtifactError("Model metadata is unavailable.")
        return {
            "crops": sorted(categories["Crop"]),
            "seasons": sorted(categories["Season"]),
            "crop_categories": sorted(categories["Crop_Category"]),
            "states": sorted(self._districts_by_state),
            "districts_by_state": {
                state: sorted(districts) for state, districts in self._districts_by_state.items()
            },
            "year_start": metadata.training_year_start,
            "year_end": metadata.training_year_end,
            "year_range_type": "training_with_extrapolation",
            "category_label_basis": "model_training_encoder",
            "location_pair_basis": "positive_primary_training_cohort_source",
            "target_unit": YIELD_UNIT,
            "target_unit_status": YIELD_TARGET_UNIT_STATUS,
            "target_semantics": YIELD_TARGET_SEMANTICS,
            "target_unit_source": YIELD_UNIT_SOURCE,
            "target_unit_source_url": YIELD_UNIT_SOURCE_URL,
            "target_conversion_applied": False,
            "limitations": [
                "Model-supported labels are not verified official administrative records.",
                "District/state pairs are derived from the recorded training-source rows.",
                "Predictions are accepted only for crop, season, and location combinations "
                "present in the positive primary training cohort.",
                "Years after the training period are extrapolations, not validated forecasts.",
                "The kg/ha target unit is pending verification; no conversion is applied.",
                "Predictions are feature-based experimental estimates, not validated forecasts.",
                "Predictions are experimental and not production-approved.",
            ],
        }

    def availability(self) -> tuple[str, tuple[str, ...]]:
        metadata, reasons = self.adapter.inspect()
        blocking_reasons = tuple(
            reason for reason in reasons if reason != "model_version_not_recorded"
        )
        if blocking_reasons or metadata is None:
            return "unavailable", blocking_reasons or ("metadata_unavailable",)
        try:
            self.adapter.load()
        except ModelArtifactError:
            return "unavailable", ("model_runtime_unavailable",)
        self._gates["artifact_runtime_compatibility_unverified"] = True
        return "available", ()

    def readiness(self) -> Readiness:
        metadata, adapter_reasons = self.adapter.inspect()
        availability, availability_reasons = self.availability()
        reasons = [reason for reason in self.RELEASE_GATES if not self._gates[reason]]
        reasons.extend(adapter_reasons)
        if availability != "available":
            reasons.extend(availability_reasons)
        # Executable model availability is independent of certification or output units.
        production_approved = False
        return Readiness(
            execution_available=availability == "available",
            reason_codes=tuple(dict.fromkeys(reasons)),
            availability=availability,
            quality_status="experimental" if availability == "available" else "unavailable",
            production_approved=production_approved,
            artifact_sha256=self.adapter._artifact_sha256,
            model_name=metadata.model_name if metadata else None,
            model_version=metadata.model_version if metadata else None,
            target=metadata.target if metadata else None,
            target_unit=YIELD_UNIT,
            training_year_start=metadata.training_year_start if metadata else None,
            training_year_end=metadata.training_year_end if metadata else None,
            limitations=self._limitations(metadata),
        )

    def validate(self, features: YieldFeatures) -> None:
        readiness = self.readiness()
        if not readiness.execution_available:
            raise ModelNotReadyError(readiness.reason_codes)
        metadata, _ = self.adapter.inspect()
        if metadata is None:
            raise ModelNotReadyError(("metadata_unavailable",))
        if self.supported_categories is None or (
            self.training_data_path is not None and self._districts_by_state is None
        ):
            self.options()
        if self.supported_categories is None:
            self.supported_categories = self._model_categories(self.adapter.load())
        for field in CATEGORICAL_FEATURES:
            allowed = self.supported_categories.get(field)
            if allowed is None or getattr(features, field) not in allowed:
                raise ValueError(f"Unsupported category for {field}.")
        if self._districts_by_state is not None:
            if features.District not in self._districts_by_state.get(features.State, frozenset()):
                raise ValueError("Unsupported state and district combination.")
        if self.supported_combinations is not None and (
            features.Crop,
            features.Season,
            features.Crop_Category,
            features.State,
            features.District,
        ) not in self.supported_combinations:
            raise ValueError("Unsupported crop, season, and location combination.")

    def predict(self, features: YieldFeatures) -> YieldPrediction:
        self.validate(features)
        try:
            model = self.adapter.load()
            frame = pd.DataFrame(
                [[getattr(features, feature) for feature in FEATURES]],
                columns=FEATURES,
            )
            predictions = np.asarray(model.predict(frame))
            if predictions.shape != (1,):
                raise ModelArtifactError("Model returned an invalid prediction count.")
            value = float(predictions[0])
            if not math.isfinite(value):
                logger.warning(
                    "Yield inference rejected a non-finite value for inputs "
                    "crop=%r season=%r state=%r district=%r year=%r.",
                    features.Crop,
                    features.Season,
                    features.State,
                    features.District,
                    features.FE_YearStart,
                )
                raise ModelArtifactError("Model returned a non-finite value.")
            if value < 0:
                logger.warning(
                    "Yield inference rejected a negative estimate (value=%r) for inputs "
                    "crop=%r season=%r state=%r district=%r year=%r; no clamping applied.",
                    value,
                    features.Crop,
                    features.Season,
                    features.State,
                    features.District,
                    features.FE_YearStart,
                )
                raise ModelArtifactError("Model returned an implausible negative estimate.")
        except ModelNotReadyError:
            raise
        except Exception as error:
            raise ModelArtifactError("Yield inference failed.") from error

        metadata, _ = self.adapter.inspect()
        artifact_hash = self.adapter._artifact_sha256
        metadata_hash = self.adapter._metadata_sha256
        if metadata is None or artifact_hash is None or metadata_hash is None:
            raise ModelArtifactError("Model provenance is unavailable.")
        raw_metrics = metadata.model_extra or {}
        raw_windows = raw_metrics.get("served_artifact_validation_metrics", {})
        validation_metrics = {
            window: {
                metric: float(metric_value)
                for metric, metric_value in metrics.items()
                if isinstance(metric_value, int | float)
            }
            for window, metrics in raw_windows.items()
            if isinstance(metrics, dict)
        }
        prediction_period_status = (
            "in_training_range"
            if metadata.training_year_start
            <= features.FE_YearStart
            <= metadata.training_year_end
            else "out_of_training_range_extrapolation"
        )
        limitations = self._limitations(metadata)
        if prediction_period_status != "in_training_range":
            limitations = (
                *limitations,
                "The requested year is outside the training period; this is an "
                "out-of-training-range model extrapolation, not a validated "
                "forecast of future yield.",
            )
        return YieldPrediction(
            value=value,
            provenance=YieldProvenance(
                model_version=metadata.model_version,
                artifact_sha256=artifact_hash,
                metadata_sha256=metadata_hash,
                model_name=metadata.model_name,
                target=metadata.target,
                target_unit=YIELD_UNIT,
                target_unit_status=YIELD_TARGET_UNIT_STATUS,
                target_unit_source=YIELD_UNIT_SOURCE,
                target_unit_source_url=YIELD_UNIT_SOURCE_URL,
                target_construction=YIELD_TARGET_CONSTRUCTION,
                target_consistency_check=YIELD_CONSISTENCY_CHECK,
                target_conversion_applied=False,
                training_year_start=metadata.training_year_start,
                training_year_end=metadata.training_year_end,
                validation_metrics=validation_metrics,
            ),
            limitations=limitations,
            prediction_period_status=prediction_period_status,
        )
