from fastapi import APIRouter

from bharatcrop_foundation.routes.agricultural_intelligence import (
    router as agricultural_intelligence_router,
)
from bharatcrop_foundation.routes.agricultural_risk import (
    router as agricultural_risk_router,
)
from bharatcrop_foundation.routes.assistant import router as assistant_router
from bharatcrop_foundation.routes.capabilities import router as capabilities_router
from bharatcrop_foundation.routes.experimental_forecast import (
    router as experimental_forecast_router,
)
from bharatcrop_foundation.routes.explainability import router as explainability_router
from bharatcrop_foundation.routes.info import router as info_router
from bharatcrop_foundation.routes.model_insights import (
    router as model_insights_router,
)
from bharatcrop_foundation.routes.scenarios import router as scenarios_router
from bharatcrop_foundation.routes.weather import router as weather_router
from bharatcrop_foundation.routes.weather_agriculture import (
    router as weather_agriculture_router,
)
from bharatcrop_foundation.routes.weather_ml import router as weather_ml_router

api_router = APIRouter()
api_router.include_router(info_router)
api_router.include_router(capabilities_router)
api_router.include_router(agricultural_intelligence_router)
api_router.include_router(experimental_forecast_router)
api_router.include_router(agricultural_risk_router)
api_router.include_router(weather_router)
api_router.include_router(weather_agriculture_router)
api_router.include_router(weather_ml_router)
api_router.include_router(explainability_router)
api_router.include_router(scenarios_router)
api_router.include_router(model_insights_router)
api_router.include_router(assistant_router)
