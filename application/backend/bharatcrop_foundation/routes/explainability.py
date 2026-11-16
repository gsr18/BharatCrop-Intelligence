from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from bharatcrop_foundation.models.explainability import (
    CropSeasonErrorGroup,
    ExplainabilityService,
    GlobalImportance,
    PredictionBiasGroup,
    ScenarioBaseline,
)

router = APIRouter(prefix="/explainability", tags=["explainability"])


@router.get("/models")
async def get_explainability_models(request: Request) -> dict[str, Any]:
    """Get explainability model metadata and provenance.

    Returns information about the model used for explainability analysis,
    including training period, target, features, and analysis metadata.

    This endpoint serves static metadata from Notebook 21's explainability
    summary. It does not perform real-time analysis.
    """
    service: ExplainabilityService = request.app.state.explainability_service
    availability, reasons = service.availability()

    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Explainability data unavailable", "reason_codes": reasons},
        )

    metadata = service.metadata()

    return {
        "analysis_name": metadata.analysis_name,
        "model_name": metadata.model_name,
        "target": metadata.target,
        "target_unit": "kg/ha",
        "features": list(metadata.features),
        "training_period": {
            "start": metadata.evaluation_period.get("year_start"),
            "end": metadata.evaluation_period.get("year_end"),
        },
        "evaluation_sample": {
            "evaluation_rows": metadata.evaluation_period.get("evaluation_rows"),
            "sampling_limit": metadata.evaluation_period.get("sampling_limit"),
            "random_state": metadata.evaluation_period.get("random_state"),
        },
        "evaluation_metrics": metadata.evaluation_metrics,
        "generated_at_utc": metadata.generated_at_utc,
        "limitations": list(metadata.limitations),
        "notebook_reference": "21_model_explainability_and_scenarios.ipynb",
    }


@router.get("/global")
async def get_global_importance(request: Request) -> dict[str, Any]:
    """Get global feature importance from Notebook 21.

    Returns permutation feature importance computed on a 3000-sample
    evaluation dataset from 2021-2022 using sklearn's permutation_importance
    with neg_mean_absolute_error scoring, 3 repeats, and random_state=42.

    Importance values represent the increase in MAE when a feature is
    randomly shuffled. Larger values indicate greater predictive reliance.
    These are predictive associations, not causal effects.
    """
    service: ExplainabilityService = request.app.state.explainability_service
    availability, reasons = service.availability()

    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Explainability data unavailable", "reason_codes": reasons},
        )

    importance = service.global_importance()

    return {
        "method": "permutation_importance",
        "scoring": "neg_mean_absolute_error",
        "n_repeats": 3,
        "random_state": 42,
        "evaluation_period": "2021-2022",
        "evaluation_rows": 3000,
        "importance": [asdict(item) for item in importance],
        "interpretation": (
            "Larger positive MAE increase indicates greater reliance on that "
            "feature for this evaluation sample. These are predictive associations, "
            "not causal effects. Correlated features can share or mask importance."
        ),
    }


@router.get("/evaluation")
async def get_evaluation_metrics(request: Request) -> dict[str, Any]:
    """Get evaluation metrics and error analysis from Notebook 21.

    Returns evaluation metrics computed on a 3000-sample evaluation dataset
    from 2021-2022, plus crop-season error group analysis.

    These are sample-specific results, not an independent validation.
    """
    service: ExplainabilityService = request.app.state.explainability_service
    availability, reasons = service.availability()

    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Explainability data unavailable", "reason_codes": reasons},
        )

    metrics = service.evaluation_metrics()
    error_groups = service.crop_season_errors()

    return {
        "evaluation_metrics": metrics.get("evaluation", {}),
        "evaluation_period": metrics.get("evaluation_period", {}),
        "highest_mae_groups": [asdict(item) for item in error_groups],
        "notebook_reference": "21_model_explainability_and_scenarios.ipynb",
        "interpretation": (
            "Metrics were computed on a sample of 3000 observations from 2021-2022. "
            "These are sample-specific results, not a new independent validation. "
            "Group-level metrics can be unstable for small groups."
        ),
    }


@router.get("/bias")
async def get_prediction_bias(request: Request) -> dict[str, Any]:
    """Get prediction bias analysis from Notebook 21.

    Returns crop-season groups with strongest overprediction and
    underprediction bias from the evaluation sample.

    Positive signed error means overprediction; negative means underprediction.
    Bias describes this evaluation sample; it does not establish the same
    bias in future data.
    """
    service: ExplainabilityService = request.app.state.explainability_service
    availability, reasons = service.availability()

    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Explainability data unavailable", "reason_codes": reasons},
        )

    over_groups, under_groups = service.prediction_bias()

    return {
        "strongest_overprediction_groups": [asdict(item) for item in over_groups],
        "strongest_underprediction_groups": [asdict(item) for item in under_groups],
        "notebook_reference": "21_model_explainability_and_scenarios.ipynb",
        "interpretation": (
            "Signed error describes this evaluation sample; it does not establish "
            "the same bias in future data. Groups with fewer than 20 observations "
            "were excluded from the bias analysis."
        ),
    }


@router.get("/uncertainty")
async def get_uncertainty_status(request: Request) -> dict[str, Any]:
    """Get prediction uncertainty calibration status.

    Returns information about whether prediction intervals and confidence
    calibration are available.

    Notebook 21 did not implement prediction interval calibration. This
    endpoint explicitly reports uncertainty as unavailable.
    """
    service: ExplainabilityService = request.app.state.explainability_service
    uncertainty_status = service.uncertainty_status()

    return {
        "prediction_interval_available": uncertainty_status["prediction_interval_available"],
        "confidence_calibration_available": uncertainty_status["confidence_calibration_available"],
        "reason": uncertainty_status["reason"],
        "limitations": uncertainty_status["limitations"],
        "notebook_reference": "21_model_explainability_and_scenarios.ipynb",
    }
