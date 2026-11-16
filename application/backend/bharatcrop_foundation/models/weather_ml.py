from __future__ import annotations

import hashlib
import json
import math
import threading
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

WI05_HORIZONS = tuple(range(1, 8))
WI05_REQUIRED_VARIABLES = ("T2M_MAX", "T2M_MIN", "PRECTOTCORR")
WI05_UNAVAILABLE_REASON = "awaiting_daily_weather_input_pipeline"

WI05_LIMITATIONS = [
    "WI-05 candidate models are research artifacts; final model selection is pending WI-07.",
    "Validation covered target dates 2020-2022 only; the 2023-2024 holdout was not accessed.",
    "T+1 only modestly improved over persistence; T+2 through T+6 improved over climatology; "
    "T+7 had worse aggregate MAE than climatology.",
    "Heavy rainfall (50+ mm/day) is substantially underestimated and must not be treated as "
    "a validated warning model.",
    "The source archive ends on 2024-12-31 and no live daily weather input pipeline is configured.",
    "Weather-only outputs do not establish crop damage, disease occurrence, or yield loss.",
]

WI05_DISTRICT_NOTICE = (
    "These are archive-based demonstration predictions generated using historical weather inputs. "
    "The source archive ends on 31 December 2024. They do not represent current weather conditions "
    "or operational forecasts."
)
WI05_DISTRICT_LIMITATIONS = [
    "District estimates aggregate grid-cell WI-05 candidate predictions and are not "
    "official observed or operational forecasts.",
    "District boundaries are provisional matches; grid cells are 0.5-degree latitude by "
    "0.625-degree longitude rectangles centered on POWER coordinates.",
    "Area-weighted aggregation can hide local rainfall variation within a district.",
    "Forecast dates are calculated from the latest complete archived feature date and may "
    "fall after the archive end date.",
    "WI-05 candidate artifacts await final selection pending WI-07; T+7 performed worse "
    "than climatology and heavy rainfall is underestimated.",
    "Actual rainfall may differ from model estimates; outputs are not verified against "
    "future observations.",
]


class WeatherMlError(Exception):
    """Raised when weather-ML artifacts or inputs cannot be used safely."""


class WeatherMlService:
    """Loads WI-05 rainfall candidate artifacts and reports input readiness."""

    def __init__(
        self,
        feature_spec_path: Path,
        model_dirs: tuple[Path, ...],
        dataset_metadata_path: Path,
        *,
        district_grid_path: Path | None = None,
        feature_dataset_dir: Path | None = None,
        feature_coverage_path: Path | None = None,
    ) -> None:
        self.feature_spec_path = feature_spec_path
        self.model_dirs = tuple(Path(path) for path in model_dirs)
        self.dataset_metadata_path = dataset_metadata_path
        self.district_grid_path = district_grid_path
        self.feature_dataset_dir = feature_dataset_dir
        self.feature_coverage_path = feature_coverage_path
        self._lock = threading.Lock()
        self._predictors: list[str] | None = None
        self._feature_spec: dict[str, Any] | None = None
        self._models: dict[int, dict[str, Any]] | None = None
        self._horizon_status: list[dict[str, Any]] | None = None
        self._dataset_metadata: dict[str, Any] | None = None
        self._district_grid: pd.DataFrame | None = None
        self._feature_coverage: dict[str, dict[str, Any]] | None = None
        self._forecast_origin: date | None = None
        self._district_forecast_cache: dict[tuple[Any, ...], dict[str, Any]] = {}

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise WeatherMlError(f"Could not read weather-ML metadata: {path}") from error
        if not isinstance(payload, dict):
            raise WeatherMlError(f"Weather-ML metadata is not an object: {path}")
        return payload

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _load_feature_contract(self) -> tuple[list[str], dict[str, Any]]:
        if self._predictors is not None and self._feature_spec is not None:
            return self._predictors, self._feature_spec
        spec = self._read_json(self.feature_spec_path)
        predictors = spec.get("predictors")
        if not isinstance(predictors, list) or not all(isinstance(v, str) for v in predictors):
            raise WeatherMlError("WI-05 feature specification does not define predictors.")
        predictors = list(predictors)
        required = {
            "latitude",
            "longitude",
            "PRECTOTCORR_current",
            "T2M_MAX_current",
            "T2M_MIN_current",
        }
        missing = sorted(required.difference(predictors))
        if missing:
            raise WeatherMlError(f"WI-05 feature specification is missing predictors: {missing}.")
        self._predictors = predictors
        self._feature_spec = {
            "path": str(self.feature_spec_path),
            "target_variable": spec.get("target_variable"),
            "predictor_count": int(spec.get("predictor_count", len(predictors))),
            "predictors": predictors,
            "feature_selection": spec.get("feature_selection"),
            "final_holdout_accessed": spec.get("final_holdout_accessed"),
        }
        return predictors, self._feature_spec

    def _artifact_path(self, horizon: int, kind: str) -> Path | None:
        token = "wet_classifier" if kind == "classifier" else "wet_amount_regressor"
        filename = f"WI_05_hgb_{token}_t{horizon}_candidate.joblib"
        for directory in self.model_dirs:
            candidate = directory / filename
            if candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _artifact_info(path: Path | None) -> dict[str, Any] | None:
        if path is None:
            return None
        return {
            "path": str(path),
            "name": path.name,
            "sha256": WeatherMlService._sha256(path),
            "size_bytes": path.stat().st_size,
        }

    def _load_models(self) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
        if self._models is not None and self._horizon_status is not None:
            return self._models, self._horizon_status
        with self._lock:
            if self._models is not None and self._horizon_status is not None:
                return self._models, self._horizon_status
            try:
                predictors, _ = self._load_feature_contract()
            except WeatherMlError:
                predictors = []
            models: dict[int, dict[str, Any]] = {}
            status_rows: list[dict[str, Any]] = []
            for horizon in WI05_HORIZONS:
                classifier_path = self._artifact_path(horizon, "classifier")
                regressor_path = self._artifact_path(horizon, "amount_regressor")
                row = {
                    "horizon": horizon,
                    "label": f"T+{horizon}",
                    "status": "missing_artifacts",
                    "classifier_artifact": None,
                    "amount_regressor_artifact": None,
                    "reason_code": "model_artifacts_missing",
                }
                if classifier_path is None or regressor_path is None:
                    status_rows.append(row)
                    continue
                try:
                    classifier = joblib.load(classifier_path)
                    regressor = joblib.load(regressor_path)
                    for model in (classifier, regressor):
                        names = list(getattr(model, "feature_names_in_", []))
                        if names != predictors:
                            raise WeatherMlError(
                                "WI-05 feature order does not match the specification."
                            )
                    models[horizon] = {
                        "classifier": classifier,
                        "amount_regressor": regressor,
                        "classifier_artifact": self._artifact_info(classifier_path),
                        "amount_regressor_artifact": self._artifact_info(regressor_path),
                    }
                    row.update(
                        {
                            "status": "loaded",
                            "classifier_artifact": classifier_path.name,
                            "amount_regressor_artifact": regressor_path.name,
                            "reason_code": None,
                        }
                    )
                except Exception as error:  # noqa: BLE001 - artifact loading must fail closed per horizon.
                    row.update(
                        {
                            "status": "artifact_error",
                            "reason_code": "model_artifact_load_failed",
                        }
                    )
                    row["error"] = str(error)
                status_rows.append(row)
            self._models = models
            self._horizon_status = status_rows
            return models, status_rows

    def _dataset_info(self) -> dict[str, Any]:
        if self._dataset_metadata is not None:
            return self._dataset_metadata
        if self.dataset_metadata_path.is_file():
            metadata = self._read_json(self.dataset_metadata_path)
            self._dataset_metadata = {
                "dataset_version": metadata.get("dataset_version"),
                "date_start": metadata.get("date_start"),
                "date_end": metadata.get("date_end"),
                "cell_count": metadata.get("cell_count"),
                "canonical_rows": metadata.get("canonical_rows"),
                "row_key": metadata.get("row_key"),
            }
        else:
            self._dataset_metadata = {"dataset_version": None, "date_end": None}
        return self._dataset_metadata

    @property
    def feature_predictors(self) -> list[str]:
        predictors, _ = self._load_feature_contract()
        return predictors

    def status(self) -> dict[str, Any]:
        _, horizon_status = self._load_models()
        dataset = self._dataset_info()
        input_status = {
            "provider": "none_configured",
            "forecast_available": False,
            "latest_available_input_date": dataset.get("date_end"),
            "required_variables": list(WI05_REQUIRED_VARIABLES),
            "frequency": "consecutive UTC daily observations through the as-of date",
            "reason_code": WI05_UNAVAILABLE_REASON,
            "message": (
                "Live rainfall forecasting is awaiting a daily weather input pipeline. "
                "The audited archive ends on 2024-12-31 and cannot supply current inputs."
            ),
        }
        return {
            "task": "wi05_rainfall_forecast",
            "status": "awaiting_input_pipeline",
            "forecast_available": False,
            "reason_code": WI05_UNAVAILABLE_REASON,
            "production_approved": False,
            "model_directories": [str(path) for path in self.model_dirs],
            "feature_specification": self._feature_spec or {},
            "predictor_count": len(self._predictors or []),
            "horizons": horizon_status,
            "input": input_status,
            "dataset": dataset,
            "limitations": list(WI05_LIMITATIONS),
        }

    def _parse_as_of_date(self, value: str | None) -> date:
        if value is None:
            return date.today()
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as error:
            raise WeatherMlError("as_of_date must use YYYY-MM-DD format.") from error

    def rainfall_forecast(
        self,
        *,
        latitude: float,
        longitude: float,
        as_of_date: str | None = None,
        horizons: list[int] | None = None,
    ) -> dict[str, Any]:
        if not 7.0 <= latitude <= 34.5:
            raise WeatherMlError("latitude must be within the audited grid range 7.0-34.5.")
        if not 69.375 <= longitude <= 96.875:
            raise WeatherMlError("longitude must be within the audited grid range 69.375-96.875.")
        requested_as_of = self._parse_as_of_date(as_of_date)
        requested_horizons = WI05_HORIZONS if horizons is None else tuple(sorted(set(horizons)))
        invalid = [h for h in requested_horizons if h not in WI05_HORIZONS]
        if invalid:
            raise WeatherMlError(f"Unsupported forecast horizons: {invalid}.")
        _, horizon_status = self._load_models()
        by_horizon = {int(row["horizon"]): row for row in horizon_status}
        dataset = self._dataset_info()
        latest = dataset.get("date_end")
        return {
            "task": "wi05_rainfall_forecast",
            "forecast_available": False,
            "status": "awaiting_input_pipeline",
            "reason_code": WI05_UNAVAILABLE_REASON,
            "message": (
                "No forecast is emitted because the backend does not have a configured "
                "daily weather input provider for the required lag and rolling-window features."
            ),
            "latitude": latitude,
            "longitude": longitude,
            "as_of_date": requested_as_of.isoformat(),
            "latest_available_input_date": latest,
            "required_input_variables": list(WI05_REQUIRED_VARIABLES),
            "horizons": [by_horizon[h] for h in requested_horizons],
            "dataset": dataset,
            "limitations": list(WI05_LIMITATIONS),
        }

    def predict_feature_row(
        self,
        feature_row: Mapping[str, float],
        *,
        as_of_date: date,
        horizons: tuple[int, ...] = WI05_HORIZONS,
    ) -> list[dict[str, Any]]:
        """Run already-prepared WI-05 features through the loaded candidate models."""
        models, _ = self._load_models()
        missing_models = [h for h in horizons if h not in models]
        if missing_models:
            raise WeatherMlError(
                f"WI-05 model artifacts are unavailable for horizons: {missing_models}."
            )
        predictors = self.feature_predictors
        missing_features = [name for name in predictors if name not in feature_row]
        if missing_features:
            raise WeatherMlError(
                f"Prepared features are missing WI-05 predictors: {missing_features[:5]}"
            )
        frame = pd.DataFrame([{name: float(feature_row[name]) for name in predictors}])
        predictions: list[dict[str, Any]] = []
        for horizon in horizons:
            bundle = models[horizon]
            classifier = bundle["classifier"]
            regressor = bundle["amount_regressor"]
            probabilities = classifier.predict_proba(frame)[0]
            classes = [int(value) for value in classifier.classes_]
            wet_probability = (
                float(probabilities[classes.index(1)])
                if 1 in classes
                else float(probabilities[-1])
            )
            conditional_amount = float(regressor.predict(frame)[0])
            expected = wet_probability * conditional_amount
            predictions.append(
                {
                    "horizon": horizon,
                    "label": f"T+{horizon}",
                    "target_date": (as_of_date + timedelta(days=horizon)).isoformat(),
                    "wet_probability": wet_probability,
                    "conditional_wet_amount_mm_day": conditional_amount,
                    "expected_precipitation_mm_day": expected,
                }
            )
        return predictions

    def _require_district_inputs(self) -> None:
        if (
            self.district_grid_path is None
            or self.feature_dataset_dir is None
            or self.feature_coverage_path is None
        ):
            raise WeatherMlError("District archive rainfall forecasting is not configured.")

    def _load_district_grid(self) -> pd.DataFrame:
        self._require_district_inputs()
        if self._district_grid is not None:
            return self._district_grid
        path = self.district_grid_path
        if path is None or not path.is_file():
            raise WeatherMlError("District-to-grid mapping artifact is unavailable.")
        frame = pd.read_csv(path)
        required = {
            "state",
            "district",
            "apy_geography_id",
            "matched_boundary_name",
            "cell_id",
            "cell_latitude",
            "cell_longitude",
            "intersection_area_m2",
            "intersection_area_km2",
        }
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise WeatherMlError(f"District grid mapping is missing columns: {missing}.")
        self._district_grid = frame
        return frame

    def _load_feature_coverage(self) -> dict[str, dict[str, Any]]:
        self._require_district_inputs()
        if self._feature_coverage is not None and self._forecast_origin is not None:
            return self._feature_coverage
        path = self.feature_coverage_path
        if path is None or not path.is_file():
            raise WeatherMlError("Archived feature coverage artifact is unavailable.")
        frame = pd.read_csv(path)
        required = {"cell_id", "feature_date", "complete_predictors"}
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise WeatherMlError(f"Feature coverage artifact is missing columns: {missing}.")
        coverage: dict[str, dict[str, Any]] = {}
        origin_candidates: list[date] = []
        for row in frame.itertuples(index=False):
            cell_id = str(row.cell_id)
            raw_date = row.feature_date
            parsed = pd.to_datetime(raw_date, errors="coerce")
            feature_date = parsed.date() if pd.notna(parsed) else None
            complete = bool(row.complete_predictors) and feature_date is not None
            coverage[cell_id] = {"feature_date": feature_date, "complete_predictors": complete}
            if complete and feature_date is not None:
                origin_candidates.append(feature_date)
        if not origin_candidates:
            raise WeatherMlError("No archived cells have complete WI-05 predictors.")
        self._forecast_origin = max(origin_candidates)
        self._feature_coverage = coverage
        return coverage

    def district_options(self) -> dict[str, Any]:
        grid = self._load_district_grid()
        coverage = self._load_feature_coverage()
        origin = self._forecast_origin
        if origin is None:
            raise WeatherMlError("Forecast origin could not be determined.")
        supported: list[dict[str, Any]] = []
        for (state, district), group in grid.groupby(["state", "district"], sort=True):
            cells = group["cell_id"].astype(str).tolist()
            valid = [cell for cell in cells if coverage.get(cell, {}).get("complete_predictors")]
            if not valid:
                continue
            supported.append(
                {
                    "state": str(state),
                    "district": str(district),
                    "apy_geography_id": str(group.iloc[0]["apy_geography_id"]),
                    "matched_boundary_name": str(group.iloc[0]["matched_boundary_name"]),
                    "intersecting_cell_count": len(cells),
                    "valid_cell_count": len(valid),
                }
            )
        states = sorted({row["state"] for row in supported})
        districts_by_state: dict[str, list[str]] = {}
        for row in supported:
            districts_by_state.setdefault(row["state"], []).append(row["district"])
        for items in districts_by_state.values():
            items.sort()
        return {
            "task": "wi05_rainfall_forecast_district_archive",
            "forecast_origin_date": origin.isoformat(),
            "archive_end_date": self._dataset_info().get("date_end"),
            "supported_district_count": len(supported),
            "states": states,
            "districts_by_state": districts_by_state,
            "districts": supported,
            "aggregation_method": "area_weighted_mean",
            "weight_field": "intersection_area_m2",
            "limitations": list(WI05_DISTRICT_LIMITATIONS),
        }

    def _district_cells(self, state: str, district: str) -> tuple[pd.DataFrame, date]:
        grid = self._load_district_grid()
        coverage = self._load_feature_coverage()
        origin = self._forecast_origin
        if origin is None:
            raise WeatherMlError("Forecast origin could not be determined.")
        mask = (grid["state"].astype(str) == state) & (grid["district"].astype(str) == district)
        cells = grid.loc[mask].copy()
        if cells.empty:
            raise WeatherMlError("District is not supported for archive rainfall forecasting.")
        def complete_at_origin(cell_id: object) -> bool:
            info = coverage.get(str(cell_id), {})
            return bool(info.get("complete_predictors")) and info.get("feature_date") == origin
        cells["valid_at_origin"] = cells["cell_id"].map(complete_at_origin)
        return cells, origin

    def _read_origin_features(
        self,
        cells: pd.DataFrame,
        origin: date,
        predictors: list[str],
    ) -> dict[str, dict[str, float]]:
        if self.feature_dataset_dir is None:
            raise WeatherMlError("Archived feature dataset directory is not configured.")
        needed = set(cells["cell_id"].astype(str))
        by_batch: dict[int, set[str]] = {}
        for cell_id in needed:
            try:
                number = int(str(cell_id).rsplit("_", 1)[1])
            except (IndexError, ValueError) as error:
                raise WeatherMlError(f"Invalid archived cell identifier: {cell_id}.") from error
            by_batch.setdefault(number // 10, set()).add(str(cell_id))
        rows: dict[str, dict[str, float]] = {}
        timestamp = pd.Timestamp(origin)
        for batch_index in sorted(by_batch):
            path = self.feature_dataset_dir / f"batch_{batch_index:04d}.parquet"
            if not path.is_file():
                continue
            frame = pd.read_parquet(
                path,
                columns=["cell_id", "date", *predictors],
                filters=[("date", "=", timestamp)],
            )
            frame = frame[frame["cell_id"].astype(str).isin(by_batch[batch_index])]
            for record in frame.itertuples(index=False):
                cell_id = str(record.cell_id)
                values: dict[str, float] = {}
                valid = True
                for name in predictors:
                    try:
                        value = float(getattr(record, name))
                    except (TypeError, ValueError):
                        valid = False
                        break
                    if not math.isfinite(value):
                        valid = False
                        break
                    values[name] = value
                if valid:
                    rows[cell_id] = values
        return rows

    def district_forecast(
        self,
        *,
        state: str,
        district: str,
        horizons: list[int] | None = None,
    ) -> dict[str, Any]:
        cells, origin = self._district_cells(state, district)
        requested_horizons = WI05_HORIZONS if horizons is None else tuple(sorted(set(horizons)))
        invalid = [h for h in requested_horizons if h not in WI05_HORIZONS]
        if invalid:
            raise WeatherMlError(f"Unsupported forecast horizons: {invalid}.")
        cache_key = (state, district, origin.isoformat(), tuple(requested_horizons))
        if cache_key in self._district_forecast_cache:
            return self._district_forecast_cache[cache_key]
        models, horizon_status = self._load_models()
        missing_models = [h for h in requested_horizons if h not in models]
        if missing_models:
            raise WeatherMlError(
                f"WI-05 model artifacts are unavailable for horizons: {missing_models}."
            )
        valid_cells = cells.loc[cells["valid_at_origin"]].copy()
        predictors = self.feature_predictors
        feature_rows = self._read_origin_features(valid_cells, origin, predictors)
        used: list[dict[str, Any]] = []
        for _, cell in valid_cells.iterrows():
            cell_id = str(cell["cell_id"])
            feature_row = feature_rows.get(cell_id)
            if feature_row is None:
                continue
            weight = float(cell["intersection_area_m2"])
            if not math.isfinite(weight) or weight <= 0:
                continue
            predictions = self.predict_feature_row(
                feature_row,
                as_of_date=origin,
                horizons=requested_horizons,
            )
            used.append(
                {
                    "cell_id": cell_id,
                    "latitude": float(cell["cell_latitude"]),
                    "longitude": float(cell["cell_longitude"]),
                    "intersection_area_m2": weight,
                    "intersection_area_km2": float(cell["intersection_area_km2"]),
                    "predictions": {int(item["horizon"]): item for item in predictions},
                }
            )
        total_cells = int(len(cells))
        valid_count = int(len(used))
        first_valid = valid_cells.iloc[0] if len(valid_cells) else None
        apy_geography_id = (
            str(first_valid["apy_geography_id"]) if first_valid is not None else None
        )
        matched_boundary_name = (
            str(first_valid["matched_boundary_name"]) if first_valid is not None else None
        )
        base = {
            "task": "wi05_rainfall_forecast_district_archive",
            "state": state,
            "district": district,
            "apy_geography_id": apy_geography_id,
            "matched_boundary_name": matched_boundary_name,
            "forecast_origin_date": origin.isoformat(),
            "archive_end_date": self._dataset_info().get("date_end"),
            "spatial": {
                "total_intersecting_cell_count": total_cells,
                "valid_cell_count": valid_count,
                "aggregation_method": "area_weighted_mean",
                "weight_field": "intersection_area_m2",
                "grid_cell_rectangle": (
                    "0.5-degree latitude by 0.625-degree longitude centered on POWER coordinate"
                ),
            },
            "grid_cells": [
                {
                    "cell_id": cell["cell_id"],
                    "latitude": cell["latitude"],
                    "longitude": cell["longitude"],
                    "intersection_area_km2": cell["intersection_area_km2"],
                }
                for cell in used
            ],
            "model": {
                "candidate_status": "pending_wi07",
                "classifier_artifacts": "WI_05_hgb_wet_classifier_t{horizon}_candidate.joblib",
                "amount_regressor_artifacts": (
                    "WI_05_hgb_wet_amount_regressor_t{horizon}_candidate.joblib"
                ),
            },
            "limitations": list(WI05_DISTRICT_LIMITATIONS),
            "notice": WI05_DISTRICT_NOTICE,
        }
        if not used:
            result = {
                **base,
                "forecast_available": False,
                "status": "insufficient_archived_feature_coverage",
                "reason_code": "insufficient_archived_feature_coverage",
                "message": (
                    "No intersecting grid cells have complete archived WI-05 features "
                    "at the forecast origin."
                ),
                "forecast_dates": [],
                "horizons": [],
            }
            self._district_forecast_cache[cache_key] = result
            return result
        total_weight = sum(cell["intersection_area_m2"] for cell in used)
        horizon_rows: list[dict[str, Any]] = []
        for horizon in requested_horizons:
            expected_values: list[float] = []
            wet_values: list[float] = []
            amount_values: list[float] = []
            weighted_expected = 0.0
            weighted_wet = 0.0
            weighted_amount = 0.0
            target_date = None
            for cell in used:
                prediction = cell["predictions"][horizon]
                expected = float(prediction["expected_precipitation_mm_day"])
                wet = float(prediction["wet_probability"])
                amount = float(prediction["conditional_wet_amount_mm_day"])
                if not all(math.isfinite(v) for v in (expected, wet, amount)):
                    continue
                weight = cell["intersection_area_m2"]
                expected_values.append(max(0.0, expected))
                wet_values.append(min(1.0, max(0.0, wet)))
                amount_values.append(max(0.0, amount))
                weighted_expected += weight * max(0.0, expected)
                weighted_wet += weight * min(1.0, max(0.0, wet))
                weighted_amount += weight * max(0.0, amount)
                target_date = prediction["target_date"]
            if not expected_values:
                continue
            horizon_rows.append(
                {
                    "horizon": horizon,
                    "label": f"T+{horizon}",
                    "target_date": target_date,
                    "expected_precipitation_mm_day": weighted_expected / total_weight,
                    "wet_probability": weighted_wet / total_weight,
                    "conditional_wet_amount_mm_day": weighted_amount / total_weight,
                    "min_cell_expected_mm_day": min(expected_values),
                    "max_cell_expected_mm_day": max(expected_values),
                    "cell_count": len(expected_values),
                }
            )
        result = {
            **base,
            "forecast_available": bool(horizon_rows),
            "status": (
                "archive_demonstration" if horizon_rows else "insufficient_model_outputs"
            ),
            "reason_code": (
                "archive_demonstration" if horizon_rows else "insufficient_model_outputs"
            ),
            "message": (
                WI05_DISTRICT_NOTICE
                if horizon_rows
                else "Model outputs were unavailable for the valid archived cells."
            ),
            "forecast_dates": [row["target_date"] for row in horizon_rows],
            "horizons": horizon_rows,
        }
        self._district_forecast_cache[cache_key] = result
        return result
