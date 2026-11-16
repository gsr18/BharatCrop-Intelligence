from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bharatcrop_foundation.api import api_router
from bharatcrop_foundation.assistant.orchestrator import AssistantOrchestrator
from bharatcrop_foundation.assistant.provider import create_llm_provider
from bharatcrop_foundation.assistant.tools import (
    AgriculturalRiskTool,
    CropIntelligenceTool,
    ExplainabilityTool,
    ModelRegistryTool,
    ToolRegistry,
    WeatherIntelligenceTool,
    YieldPredictionTool,
)
from bharatcrop_foundation.config import Settings, settings
from bharatcrop_foundation.database import Database
from bharatcrop_foundation.errors import register_error_handlers
from bharatcrop_foundation.middleware import RequestIdMiddleware
from bharatcrop_foundation.models.agricultural_risk import (
    cached_agricultural_risk_service,
)
from bharatcrop_foundation.models.apy_data import cached_apy_data_service
from bharatcrop_foundation.models.experimental_yield_forecast import (
    ExperimentalForecastAdapter,
    ExperimentalYieldForecastService,
)
from bharatcrop_foundation.models.explainability import ExplainabilityService
from bharatcrop_foundation.models.model_registry import ModelRegistryService
from bharatcrop_foundation.models.weather_agriculture import WeatherAgricultureService
from bharatcrop_foundation.models.weather_data import cached_weather_service
from bharatcrop_foundation.models.weather_ml import WeatherMlService
from bharatcrop_foundation.models.yield_prediction import (
    YieldModelAdapter,
    YieldPredictionService,
)
from bharatcrop_foundation.routes.health import router as health_router


def create_app(app_settings: Settings | None = None) -> FastAPI:
    configured_settings = app_settings or settings
    database = Database(configured_settings.database_url)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.database = database
        yield
        database.dispose()

    application = FastAPI(
        title=configured_settings.service_name,
        version=configured_settings.api_version,
        lifespan=lifespan,
        redoc_url=None,
    )
    application.state.settings = configured_settings
    application.state.database = database
    yield_adapter = YieldModelAdapter(
        configured_settings.yield_artifact_path,
        configured_settings.yield_metadata_path,
        configured_settings.yield_artifact_sha256,
        configured_settings.yield_metadata_sha256,
    )
    yield_prediction_service = YieldPredictionService(
        yield_adapter,
        training_data_path=configured_settings.yield_training_data_path,
    )
    application.state.yield_prediction_service = yield_prediction_service
    experimental_forecast_adapter = ExperimentalForecastAdapter(
        configured_settings.experimental_forecast_artifact_path,
        configured_settings.experimental_forecast_metadata_path,
        configured_settings.experimental_forecast_history_path,
        expected_artifact_sha256=configured_settings.experimental_forecast_artifact_sha256,
        expected_metadata_sha256=configured_settings.experimental_forecast_metadata_sha256,
    )
    application.state.experimental_forecast_service = ExperimentalYieldForecastService(
        experimental_forecast_adapter,
        reference_year=configured_settings.experimental_forecast_reference_year,
    )
    application.state.apy_data_service = cached_apy_data_service(
        configured_settings.apy_data_path.resolve(),
        yield_prediction_service,
    )
    application.state.weather_data_service = cached_weather_service(
        configured_settings.weather_data_path.resolve(),
        configured_settings.weather_reference_path.resolve(),
        configured_settings.weather_history_path.resolve(),
        configured_settings.weather_unmatched_path.resolve(),
        configured_settings.weather_integration_path.resolve(),
        configured_settings.weather_integration_summary_path.resolve(),
        configured_settings.weather_classifier_evaluation_path.resolve(),
        configured_settings.weather_intelligence_metadata_path.resolve(),
    )
    application.state.weather_ml_service = WeatherMlService(
        configured_settings.weather_ml_feature_spec_path.resolve(),
        configured_settings.weather_ml_model_dirs,
        configured_settings.weather_ml_dataset_metadata_path.resolve(),
        district_grid_path=configured_settings.weather_ml_district_grid_path.resolve(),
        feature_dataset_dir=configured_settings.weather_ml_feature_dataset_dir.resolve(),
        feature_coverage_path=configured_settings.weather_ml_feature_coverage_path.resolve(),
    )
    application.state.weather_agriculture_service = WeatherAgricultureService(
        application.state.apy_data_service,
        application.state.weather_data_service,
    )
    application.state.agricultural_risk_service = cached_agricultural_risk_service(
        application.state.weather_data_service,
        configured_settings.agricultural_risk_metadata_path.resolve(),
    )
    application.state.explainability_service = ExplainabilityService(
        configured_settings.explainability_summary_path.resolve(),
    )
    application.state.model_registry_service = ModelRegistryService(
        configured_settings.registry_dir.resolve(),
    )

    tool_registry = ToolRegistry(
        yield_tool=YieldPredictionTool(application.state.yield_prediction_service),
        crop_tool=CropIntelligenceTool(application.state.apy_data_service),
        weather_tool=WeatherIntelligenceTool(application.state.weather_data_service),
        risk_tool=AgriculturalRiskTool(application.state.agricultural_risk_service),
        explainability_tool=ExplainabilityTool(application.state.explainability_service),
        registry_tool=ModelRegistryTool(application.state.model_registry_service),
    )
    llm_provider = create_llm_provider(
        provider_name=configured_settings.llm_provider,
        api_key=configured_settings.llm_api_key,
        model=configured_settings.llm_model,
        base_url=configured_settings.llm_base_url,
        timeout_seconds=configured_settings.llm_timeout_seconds,
        max_tokens=configured_settings.llm_max_tokens,
    )
    application.state.assistant_orchestrator = AssistantOrchestrator(
        provider=llm_provider,
        tool_registry=tool_registry,
    )

    application.add_middleware(RequestIdMiddleware)
    register_error_handlers(application)
    application.include_router(api_router, prefix=configured_settings.api_prefix)
    application.include_router(health_router)
    return application


app = create_app()
