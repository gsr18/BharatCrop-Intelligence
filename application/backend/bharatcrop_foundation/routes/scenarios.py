from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status

from bharatcrop_foundation.models.explainability import ExplainabilityService
from bharatcrop_foundation.models.yield_prediction import (
    ModelArtifactError,
    ModelNotReadyError,
    YieldFeatures,
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("/yield")
async def yield_year_scenario(
    request: Request,
    crop: str,
    season: str,
    crop_category: str,
    state: str,
    district: str,
    years: list[int] = Query(..., description="List of years to compare", min_length=1),
) -> dict[str, Any]:
    """Generate year-based yield scenario comparison using the actual model.

    This endpoint compares predictions across multiple years while holding
    crop, season, and location constant. It uses the actual saved yield model
    to generate predictions for each year.

    Years outside the documented training period (2013-2022) are
    extrapolations and must be treated especially cautiously.

    These are model-input comparisons, not causal effects or future forecasts.
    """
    # Validate yield prediction service availability
    availability, reasons = request.app.state.yield_prediction_service.availability()
    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Yield prediction service unavailable", "reason_codes": reasons},
        )

    # Get training period from metadata
    metadata, _ = request.app.state.yield_prediction_service.adapter.inspect()
    if metadata is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Model metadata unavailable"},
        )

    training_start = metadata.training_year_start
    training_end = metadata.training_year_end

    # Generate predictions for each year
    predictions = []
    baseline_prediction = None
    baseline_year = None

    for year in years:
        try:
            features = YieldFeatures(
                Crop=crop,
                Season=season,
                Crop_Category=crop_category,
                State=state,
                District=district,
                FE_YearStart=year,
            )
            prediction = request.app.state.yield_prediction_service.predict(features)
            pred_value = prediction.value

            # Use the first year as baseline
            if baseline_prediction is None:
                baseline_prediction = pred_value
                baseline_year = year

            # Calculate change vs baseline
            change_vs_baseline = pred_value - baseline_prediction if baseline_prediction is not None else 0.0
            change_vs_baseline_pct = (
                (change_vs_baseline / baseline_prediction * 100) if baseline_prediction != 0 else None
            )

            # Determine if year is within training range
            year_status = "within_training" if training_start <= year <= training_end else "extrapolation"

            predictions.append(
                {
                    "year": year,
                    "predicted_yield": pred_value,
                    "unit": "kg/ha",
                    "change_vs_baseline": change_vs_baseline,
                    "change_vs_baseline_pct": change_vs_baseline_pct,
                    "year_status": year_status,
                }
            )
        except ModelNotReadyError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"reason": "Model not ready", "reason_codes": error.reason_codes},
            ) from error
        except ModelArtifactError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"reason": "Model artifact error"},
            ) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"reason": str(error)},
            ) from error

    return {
        "fixed_features": {
            "crop": crop,
            "season": season,
            "crop_category": crop_category,
            "state": state,
            "district": district,
        },
        "baseline_year": baseline_year,
        "baseline_prediction": baseline_prediction,
        "training_period": {
            "start": training_start,
            "end": training_end,
        },
        "predictions": predictions,
        "interpretation": (
            "This is a model-input comparison scenario, not a causal forecast. "
            "Years outside the training period are extrapolations. "
            "Flat predictions for years beyond learned split thresholds do not "
            "imply constant real-world yield."
        ),
        "limitations": [
            "The model does not use weather features; changing years only affects "
            "the FE_YearStart input, not actual weather data.",
            "Years beyond 2022 are outside the model's documented training period "
            "and must not be treated as validated forecasts.",
            "These are hypothetical model-output comparisons, not agricultural "
            "causal scenarios or production recommendations.",
            "Prediction reliability for unseen category combinations is not established.",
        ],
        "notebook_reference": "21_model_explainability_and_scenarios.ipynb",
    }


@router.get("/yield/baseline")
async def get_scenario_baseline(request: Request) -> dict[str, Any]:
    """Get the baseline scenario from Notebook 21.

    Returns the specific crop-season-location-year combination used for
    year-based scenario comparisons in the notebook's scenario analysis.
    """
    service: ExplainabilityService = request.app.state.explainability_service
    availability, reasons = service.availability()

    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Explainability data unavailable", "reason_codes": reasons},
        )

    baseline = service.scenario_baseline()

    return {
        "baseline_features": {
            "crop": baseline.crop,
            "season": baseline.season,
            "crop_category": baseline.crop_category,
            "state": baseline.state,
            "district": baseline.district,
            "fe_year_start": baseline.fe_year_start,
        },
        "baseline_prediction": baseline.baseline_prediction,
        "notebook_reference": "21_model_explainability_and_scenarios.ipynb",
        "interpretation": (
            "This is the baseline scenario used in Notebook 21 for year-based "
            "comparisons. The baseline combination appeared only twice in the "
            "evaluation sample."
        ),
    }
