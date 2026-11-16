from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bharatcrop_foundation.assistant.knowledge import (
    AGRICULTURAL_RISK_CITATION,
    APY_DATASET_CITATION,
    EXPLAINABILITY_CITATION,
    MODEL_REGISTRY_CITATION,
    WEATHER_DATASET_CITATION,
    YIELD_MODEL_CITATION,
    SourceCitation,
)
from bharatcrop_foundation.models.agricultural_risk import AgriculturalRiskService
from bharatcrop_foundation.models.apy_data import APYDataError, APYDataService
from bharatcrop_foundation.models.explainability import ExplainabilityService
from bharatcrop_foundation.models.model_registry import ModelRegistryService
from bharatcrop_foundation.models.weather_data import WeatherDataService
from bharatcrop_foundation.models.yield_prediction import (
    YieldFeatures,
    YieldPredictionService,
)


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    success: bool
    data: dict[str, Any]
    citations: list[SourceCitation]
    summary: str
    limitations: list[str] = field(default_factory=list)
    error_message: str | None = None


class YieldPredictionTool:
    """Tool for querying the real HistGradientBoosting yield prediction model."""

    def __init__(self, service: YieldPredictionService) -> None:
        self.service = service

    def run(
        self,
        *,
        crop: str,
        district: str,
        state: str | None = None,
        season: str = "Kharif",
        year: int = 2020,
        crop_category: str = "Individual Crop Candidate",
    ) -> ToolResult:
        try:
            # Normalize casing
            clean_crop = crop.strip().title()
            clean_season = season.strip().title()
            clean_category = crop_category.strip()
            clean_district = district.strip().title()
            clean_state = state.strip().title() if state else None

            # Infer state if missing
            if not clean_state:
                options = self.service.options()
                districts_by_state = options.get("districts_by_state", {})
                if isinstance(districts_by_state, dict):
                    for st, dists in districts_by_state.items():
                        if any(d.casefold() == clean_district.casefold() for d in dists):
                            clean_state = st
                            # Match exact casing from options
                            for d in dists:
                                if d.casefold() == clean_district.casefold():
                                    clean_district = d
                            break

            if not clean_state:
                return ToolResult(
                    tool_name="yield_prediction",
                    success=False,
                    data={},
                    citations=[YIELD_MODEL_CITATION],
                    summary="Could not determine the state for the specified district.",
                    error_message=f"State is required or district '{district}' is not recognized in training records.",
                )

            features = YieldFeatures(
                Crop=clean_crop,
                Season=clean_season,
                Crop_Category=clean_category,
                State=clean_state,
                District=clean_district,
                FE_YearStart=int(year),
            )

            prediction = self.service.predict(features)
            val = round(prediction.value, 2)
            is_extrapolation = int(year) > 2022

            summary = (
                f"Model estimated yield for {clean_crop} in {clean_district}, {clean_state} "
                f"({clean_season} {year}) is {val} kg/ha. "
                f"{'Notice: year ' + str(year) + ' is outside the 2013-2022 training period (extrapolation).' if is_extrapolation else ''}"
            ).strip()

            return ToolResult(
                tool_name="yield_prediction",
                success=True,
                data={
                    "crop": clean_crop,
                    "season": clean_season,
                    "state": clean_state,
                    "district": clean_district,
                    "year": int(year),
                    "predicted_yield_kg_per_ha": val,
                    "target_unit": "kg/ha",
                    "training_period": "2013-2022",
                    "prediction_period_status": prediction.prediction_period_status,
                    "is_extrapolation": is_extrapolation,
                    "model_name": prediction.provenance.model_name,
                    "quality_status": "experimental",
                    "production_approved": False,
                },
                citations=[YIELD_MODEL_CITATION],
                summary=summary,
                limitations=list(prediction.limitations),
            )
        except Exception as err:
            return ToolResult(
                tool_name="yield_prediction",
                success=False,
                data={"error": str(err)},
                citations=[YIELD_MODEL_CITATION],
                summary=f"Yield prediction could not be computed: {err}",
                error_message=str(err),
            )


class CropIntelligenceTool:
    """Tool for season-based crop ranking and historical evidence from APY data."""

    def __init__(self, apy_service: APYDataService) -> None:
        self.apy_service = apy_service

    def run(
        self,
        *,
        district: str,
        state: str | None = None,
        season: str = "Kharif",
        crop: str | None = None,
        top_n: int = 5,
        ranking_basis: str = "recent_median",
        year: int | None = None,
    ) -> ToolResult:
        try:
            resolved = self.apy_service.resolve_location(district, state)
            if resolved is None:
                return ToolResult(
                    tool_name="crop_intelligence",
                    success=False,
                    data={},
                    citations=[APY_DATASET_CITATION],
                    summary="Could not locate state for the specified district in APY records.",
                    error_message=f"District '{district}' not found in APY dataset.",
                )
            clean_state, clean_district = resolved
            clean_season = season.strip().title()

            if crop:
                clean_crop = crop.strip().title()
                through_year = (
                    int(year)
                    if year is not None
                    else self.apy_service.years[-1]
                )
                evidence_res = self.apy_service.evidence(
                    state=clean_state,
                    district=clean_district,
                    season=clean_season,
                    crop=clean_crop,
                    through_year=through_year,
                )
                stats = evidence_res.get("statistics", {}) or {}
                recent_median = stats.get("recent_median_yield")
                historical_median = stats.get("historical_median_yield")
                recent_text = (
                    f"{round(recent_median, 1)} kg/ha"
                    if recent_median is not None
                    else "n/a"
                )
                historical_text = (
                    f"{round(historical_median, 1)} kg/ha"
                    if historical_median is not None
                    else "n/a"
                )
                summary = (
                    f"Historical yield evidence for {clean_crop} in {clean_district}, "
                    f"{clean_state} ({clean_season}): recent five-year median "
                    f"{recent_text}, historical median {historical_text} across "
                    f"{stats.get('valid_year_count', 0)} recorded years. This is "
                    "historical evidence, not a planting recommendation or a future "
                    "yield forecast."
                )
                return ToolResult(
                    tool_name="crop_intelligence",
                    success=True,
                    data=evidence_res,
                    citations=[APY_DATASET_CITATION],
                    summary=summary,
                    limitations=list(APY_DATASET_CITATION.limitations),
                )

            ranking_res = self.apy_service.rank(
                state=clean_state,
                district=clean_district,
                season=clean_season,
                top_n=top_n,
                ranking_basis=ranking_basis,
            )
            candidates = ranking_res.get("candidates", [])
            top_candidates = [
                (
                    f"{c['crop']} ({round(c['ranking_value'], 1)} kg/ha"
                    + (
                        f"; model estimate {round(c['predicted_yield'], 1)} kg/ha"
                        if c.get("predicted_yield") is not None
                        else ""
                    )
                    + ")"
                )
                for c in candidates[:3]
            ]
            basis_label = (
                "recent five-year median"
                if ranking_res.get("ranking_basis") == "recent_median"
                else "historical median"
            )
            top_text = (
                ", ".join(top_candidates)
                if top_candidates
                else "none with sufficient evidence"
            )
            summary = (
                f"Top yield-based crop candidates for {clean_district}, {clean_state} "
                f"({clean_season}) based on {basis_label} observed yield through "
                f"{ranking_res.get('latest_data_year')} APY year: {top_text}. Ranking "
                "reflects available historical agricultural evidence, not agronomic "
                "suitability, profitability, or future yields."
            )

            return ToolResult(
                tool_name="crop_intelligence",
                success=True,
                data=ranking_res,
                citations=[APY_DATASET_CITATION],
                summary=summary,
                limitations=list(APY_DATASET_CITATION.limitations),
            )

        except APYDataError as err:
            return ToolResult(
                tool_name="crop_intelligence",
                success=False,
                data={},
                citations=[APY_DATASET_CITATION],
                summary="The crop ranking service is not currently available.",
                error_message=str(err),
            )
        except Exception as err:
            return ToolResult(
                tool_name="crop_intelligence",
                success=False,
                data={"error": str(err)},
                citations=[APY_DATASET_CITATION],
                summary=f"Crop intelligence query failed: {err}",
                error_message=str(err),
            )


class WeatherIntelligenceTool:
    """Tool for querying historical NASA POWER annual weather summaries."""

    def __init__(self, service: WeatherDataService) -> None:
        self.service = service

    def run(
        self,
        *,
        district: str,
        state: str | None = None,
        metric: str = "precipitation",
        year: int | None = None,
    ) -> ToolResult:
        try:
            clean_district = district.strip().title()
            clean_state = state.strip().title() if state else None

            # Infer state if missing
            if not clean_state:
                locations_df = self.service.locations()
                matched = locations_df[locations_df["district"].str.casefold() == clean_district.casefold()]
                if not matched.empty:
                    clean_state = matched.iloc[0]["state"]
                    clean_district = matched.iloc[0]["district"]

            if not clean_state:
                return ToolResult(
                    tool_name="weather_intelligence",
                    success=False,
                    data={},
                    citations=[WEATHER_DATASET_CITATION],
                    summary="Could not locate weather data for the specified district.",
                    error_message=f"District '{district}' not found in weather records.",
                )

            # Query trends or series
            trends_res = self.service.trends(state=clean_state, district=clean_district)
            series_res = self.service.series(
                state=clean_state,
                district=clean_district,
                metric=metric,
            )

            annual_series = series_res.get("series", [])
            mean_precip = trends_res.get("metrics", {}).get("precipitation", {}).get("mean")
            precip_trend = trends_res.get("metrics", {}).get("precipitation", {}).get("trend_direction", "stable")

            summary = (
                f"Historical NASA POWER gridded weather estimates for {clean_district}, {clean_state} "
                "(2013-2024 annual summaries): "
                f"Mean annual precipitation is {round(mean_precip, 1) if mean_precip else 'N/A'} mm "
                f"with a {precip_trend} trend. "
                "These are historical observations, not live conditions or future forecasts."
            )

            return ToolResult(
                tool_name="weather_intelligence",
                success=True,
                data={
                    "state": clean_state,
                    "district": clean_district,
                    "metric": metric,
                    "trends": trends_res,
                    "recent_observations": annual_series[-5:] if annual_series else [],
                },
                citations=[WEATHER_DATASET_CITATION],
                summary=summary,
                limitations=list(WEATHER_DATASET_CITATION.limitations),
            )

        except Exception as err:
            return ToolResult(
                tool_name="weather_intelligence",
                success=False,
                data={"error": str(err)},
                citations=[WEATHER_DATASET_CITATION],
                summary=f"Weather query failed: {err}",
                error_message=str(err),
            )


class AgriculturalRiskTool:
    """Tool for querying Notebook 20 exploratory yield anomalies, instability, and diversification."""

    def __init__(self, service: AgriculturalRiskService) -> None:
        self.service = service

    def run(
        self,
        *,
        district: str,
        state: str | None = None,
        crop: str = "Rice",
        season: str = "Kharif",
        aspect: str = "indicators",
    ) -> ToolResult:
        try:
            clean_district = district.strip().title()
            clean_crop = crop.strip().title()
            clean_season = season.strip().title()
            clean_state = state.strip().title() if state else None

            # Infer state if missing
            if not clean_state:
                opts = self.service.options()
                districts_by_state = opts.get("districts_by_state", {})
                if isinstance(districts_by_state, dict):
                    for st, dists in districts_by_state.items():
                        if any(d.casefold() == clean_district.casefold() for d in dists):
                            clean_state = st
                            for d in dists:
                                if d.casefold() == clean_district.casefold():
                                    clean_district = d
                            break

            if not clean_state:
                return ToolResult(
                    tool_name="agricultural_risk",
                    success=False,
                    data={},
                    citations=[AGRICULTURAL_RISK_CITATION],
                    summary="Could not locate risk indicators for the specified district.",
                    error_message=f"District '{district}' not found in risk intelligence dataset.",
                )

            if aspect == "instability":
                res = self.service.instability(
                    state=clean_state,
                    district=clean_district,
                    crop=clean_crop,
                    season=clean_season,
                )
                cv = res.get("coefficient_of_variation_pct")
                summary = (
                    f"Historical yield instability for {clean_crop} in {clean_district}, {clean_state}: "
                    f"Coefficient of Variation (CV) is {round(cv, 2) if cv else 'N/A'}% across "
                    f"{res.get('valid_observation_count', 0)} recorded years."
                )
                return ToolResult(
                    tool_name="agricultural_risk",
                    success=True,
                    data=res,
                    citations=[AGRICULTURAL_RISK_CITATION],
                    summary=summary,
                    limitations=list(AGRICULTURAL_RISK_CITATION.limitations),
                )

            # Default to indicators / anomalies
            res = self.service.indicators(
                state=clean_state,
                district=clean_district,
                crop=clean_crop,
                season=clean_season,
            )
            summary_info = res.get("historical_pattern_summary", {})
            high_concern = summary_info.get("high_concern_count", 0)
            total_obs = summary_info.get("observation_count", 0)

            summary = (
                f"Historical yield anomalies for {clean_crop} in {clean_district}, {clean_state}: "
                f"Found {high_concern} High Concern observations (<80% baseline) out of {total_obs} years. "
                "These are retrospective exploratory indicators, not future crop-failure warnings."
            )

            return ToolResult(
                tool_name="agricultural_risk",
                success=True,
                data=res,
                citations=[AGRICULTURAL_RISK_CITATION],
                summary=summary,
                limitations=list(AGRICULTURAL_RISK_CITATION.limitations),
            )

        except Exception as err:
            return ToolResult(
                tool_name="agricultural_risk",
                success=False,
                data={"error": str(err)},
                citations=[AGRICULTURAL_RISK_CITATION],
                summary=f"Risk intelligence query failed: {err}",
                error_message=str(err),
            )


class ExplainabilityTool:
    """Tool for querying Notebook 21 permutation importance, evaluation metrics, and uncertainty status."""

    def __init__(self, service: ExplainabilityService) -> None:
        self.service = service

    def run(self, *, query_type: str = "global_importance") -> ToolResult:
        try:
            if query_type in {"global_importance", "importance", "features"}:
                importances = self.service.global_importance()
                top_features = [
                    f"{item.feature} (mean MAE increase: {round(item.importance_mean_mae_increase, 1)} kg/ha)"
                    for item in importances
                ]
                summary = (
                    "Model feature reliance based on permutation importance: "
                    + ", ".join(top_features)
                    + ". Crop is the most influential feature, followed by State, District, and Year. "
                    "Notice: permutation importance measures predictive reliance, not agronomic causation."
                )
                return ToolResult(
                    tool_name="explainability",
                    success=True,
                    data={"importance": [item.__dict__ for item in importances]},
                    citations=[EXPLAINABILITY_CITATION],
                    summary=summary,
                    limitations=list(EXPLAINABILITY_CITATION.limitations),
                )

            if query_type in {"evaluation", "metrics"}:
                metrics = self.service.evaluation_metrics()
                eval_metrics = metrics.get("evaluation_metrics", {})
                mae = round(eval_metrics.get("MAE", 0.0), 2)
                rmse = round(eval_metrics.get("RMSE", 0.0), 2)
                r2 = round(eval_metrics.get("R2", 0.0), 4)
                summary = (
                    f"Yield model holdout evaluation (2021-2022 test sample): "
                    f"MAE = {mae} kg/ha, RMSE = {rmse} kg/ha, R² = {r2}."
                )
                return ToolResult(
                    tool_name="explainability",
                    success=True,
                    data=metrics,
                    citations=[EXPLAINABILITY_CITATION],
                    summary=summary,
                    limitations=list(EXPLAINABILITY_CITATION.limitations),
                )

            if query_type in {"uncertainty", "confidence"}:
                uncertainty = self.service.uncertainty_status()
                summary = (
                    "Prediction uncertainty status: Prediction intervals and confidence calibration "
                    "are NOT implemented in the research. The model does not provide calibrated error margins."
                )
                return ToolResult(
                    tool_name="explainability",
                    success=True,
                    data=uncertainty,
                    citations=[EXPLAINABILITY_CITATION],
                    summary=summary,
                    limitations=list(EXPLAINABILITY_CITATION.limitations),
                )

            return ToolResult(
                tool_name="explainability",
                success=False,
                data={},
                citations=[EXPLAINABILITY_CITATION],
                summary="Unsupported explainability query type.",
                error_message=f"Unknown query_type: '{query_type}'",
            )

        except Exception as err:
            return ToolResult(
                tool_name="explainability",
                success=False,
                data={"error": str(err)},
                citations=[EXPLAINABILITY_CITATION],
                summary=f"Explainability query failed: {err}",
                error_message=str(err),
            )


class ModelRegistryTool:
    """Tool for querying Notebook 22 model registry, model cards, and governance policy rules."""

    def __init__(self, service: ModelRegistryService) -> None:
        self.service = service

    def run(self, *, query_type: str = "portfolio", registry_id: str | None = None) -> ToolResult:
        try:
            if query_type == "portfolio":
                cards = self.service.portfolio()
                component_summaries = [
                    f"{c.registry_id} ({c.component_type}: {c.recorded_status})"
                    for c in cards
                ]
                summary = (
                    f"Model Registry portfolio records {len(cards)} components: "
                    + "; ".join(component_summaries)
                    + ". Production approval is NOT ESTABLISHED for any component."
                )
                return ToolResult(
                    tool_name="model_registry",
                    success=True,
                    data={"total_components": len(cards), "components": [c.__dict__ for c in cards]},
                    citations=[MODEL_REGISTRY_CITATION],
                    summary=summary,
                    limitations=list(MODEL_REGISTRY_CITATION.limitations),
                )

            if query_type == "governance":
                rules = self.service.policy_rules()
                val_status = self.service.validation_status()
                summary = (
                    f"Governance status: {len(rules)} policy rules registered. "
                    f"Production approval: {val_status.get('production_approval', 'NOT ESTABLISHED')}. "
                    "Registry records artifact availability and documented evidence without authorizing production use."
                )
                return ToolResult(
                    tool_name="model_registry",
                    success=True,
                    data={"policy_rules_count": len(rules), "validation_status": val_status},
                    citations=[MODEL_REGISTRY_CITATION],
                    summary=summary,
                    limitations=list(MODEL_REGISTRY_CITATION.limitations),
                )

            if registry_id:
                card = self.service.model_card(registry_id)
                if not card:
                    return ToolResult(
                        tool_name="model_registry",
                        success=False,
                        data={},
                        citations=[MODEL_REGISTRY_CITATION],
                        summary=f"No model card found for registry ID '{registry_id}'.",
                        error_message=f"Registry ID not found: {registry_id}",
                    )
                summary = (
                    f"Model card for {card.registry_id}: Type={card.component_type}, "
                    f"Status={card.recorded_status}, Artifact Exists={card.artifact_exists}, "
                    f"Restrictions='{card.restrictions}'."
                )
                return ToolResult(
                    tool_name="model_registry",
                    success=True,
                    data=card.__dict__,
                    citations=[MODEL_REGISTRY_CITATION],
                    summary=summary,
                    limitations=list(MODEL_REGISTRY_CITATION.limitations),
                )

            return ToolResult(
                tool_name="model_registry",
                success=False,
                data={},
                citations=[MODEL_REGISTRY_CITATION],
                summary="Invalid model registry query parameters.",
                error_message="Specify valid query_type ('portfolio', 'governance') or registry_id.",
            )

        except Exception as err:
            return ToolResult(
                tool_name="model_registry",
                success=False,
                data={"error": str(err)},
                citations=[MODEL_REGISTRY_CITATION],
                summary=f"Model registry query failed: {err}",
                error_message=str(err),
            )


class ToolRegistry:
    """Allowlisted registry holding all typed agricultural intelligence tools."""

    def __init__(
        self,
        yield_tool: YieldPredictionTool,
        crop_tool: CropIntelligenceTool,
        weather_tool: WeatherIntelligenceTool,
        risk_tool: AgriculturalRiskTool,
        explainability_tool: ExplainabilityTool,
        registry_tool: ModelRegistryTool,
    ) -> None:
        self.yield_prediction = yield_tool
        self.crop_intelligence = crop_tool
        self.weather_intelligence = weather_tool
        self.agricultural_risk = risk_tool
        self.explainability = explainability_tool
        self.model_registry = registry_tool

    def list_tool_names(self) -> list[str]:
        return [
            "yield_prediction",
            "crop_intelligence",
            "weather_intelligence",
            "agricultural_risk",
            "explainability",
            "model_registry",
        ]
