from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from bharatcrop_foundation.models.model_registry import ModelRegistryService

router = APIRouter(prefix="/model-insights", tags=["model-insights"])


@router.get("/portfolio")
async def get_model_portfolio(request: Request) -> dict[str, Any]:
    """Get the complete model and analytical-system portfolio.

    Returns all registered components including trained models,
    derived analytical systems, and experimental evaluations.

    This endpoint serves static registry data from Notebook 22's
    model_registry.csv. It does not perform real-time analysis.
    """
    service: ModelRegistryService = request.app.state.model_registry_service
    availability, reasons = service.availability()

    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Model registry unavailable", "reason_codes": reasons},
        )

    cards = service.portfolio()

    return {
        "portfolio": [asdict(card) for card in cards],
        "total_components": len(cards),
        "notebook_reference": "22_model_registry_and_policy_outputs.ipynb",
    }


@router.get("/models")
async def list_models(request: Request) -> dict[str, Any]:
    """List all registered models and analytical systems.

    Returns summary information for each component including
    registry ID, component type, task, and disposition.
    """
    service: ModelRegistryService = request.app.state.model_registry_service
    availability, reasons = service.availability()

    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Model registry unavailable", "reason_codes": reasons},
        )

    cards = service.portfolio()

    return {
        "models": [
            {
                "registry_id": card.registry_id,
                "component_type": card.component_type,
                "task": card.task,
                "target": card.target,
                "model_name": card.model_name,
                "recorded_status": card.recorded_status,
                "registry_disposition": card.registry_disposition,
                "artifact_exists": card.artifact_exists,
                "metadata_exists": card.metadata_exists,
            }
            for card in cards
        ],
        "notebook_reference": "22_model_registry_and_policy_outputs.ipynb",
    }


@router.get("/models/{registry_id}")
async def get_model_card(registry_id: str, request: Request) -> dict[str, Any]:
    """Get detailed model card for a specific component.

    Returns complete model card information including artifact paths,
    hashes, restrictions, and governance status.

    Args:
        registry_id: The registry ID of the component.
    """
    service: ModelRegistryService = request.app.state.model_registry_service
    availability, reasons = service.availability()

    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Model registry unavailable", "reason_codes": reasons},
        )

    card = service.model_card(registry_id)

    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"reason": f"Registry ID not found: {registry_id}"},
        )

    return {
        "model_card": asdict(card),
        "notebook_reference": "22_model_registry_and_policy_outputs.ipynb",
    }


@router.get("/models/{registry_id}/evidence")
async def get_model_evidence(registry_id: str, request: Request) -> dict[str, Any]:
    """Get evaluation evidence for a specific component.

    Returns evaluation metrics and provenance information where
    available from Notebook 22's analysis.

    Args:
        registry_id: The registry ID of the component.
    """
    service: ModelRegistryService = request.app.state.model_registry_service
    availability, reasons = service.availability()

    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Model registry unavailable", "reason_codes": reasons},
        )

    evidence = service.evaluation_evidence(registry_id)

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"reason": f"Evidence not available for registry ID: {registry_id}"},
        )

    return {
        "registry_id": registry_id,
        "evaluation_evidence": asdict(evidence),
        "notebook_reference": "22_model_registry_and_policy_outputs.ipynb",
    }


@router.get("/evaluations")
async def get_evaluation_summary(request: Request) -> dict[str, Any]:
    """Get summary of available evaluation evidence.

    Returns information about which components have evaluation
    evidence and what metrics are available.
    """
    service: ModelRegistryService = request.app.state.model_registry_service
    availability, reasons = service.availability()

    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Model registry unavailable", "reason_codes": reasons},
        )

    cards = service.portfolio()

    evaluation_summary = []
    for card in cards:
        evidence = service.evaluation_evidence(card.registry_id)
        evaluation_summary.append(
            {
                "registry_id": card.registry_id,
                "component_type": card.component_type,
                "evaluation_available": evidence is not None,
                "evaluation_period": evidence.evaluation_period if evidence else None,
                "interpretation": evidence.interpretation if evidence else None,
            }
        )

    return {
        "evaluation_summary": evaluation_summary,
        "notebook_reference": "22_model_registry_and_policy_outputs.ipynb",
    }


@router.get("/governance")
async def get_governance_status(request: Request) -> dict[str, Any]:
    """Get governance and validation status.

    Returns policy rules, validation status summary, and
    production approval information.
    """
    service: ModelRegistryService = request.app.state.model_registry_service
    availability, reasons = service.availability()

    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Model registry unavailable", "reason_codes": reasons},
        )

    policy_rules = service.policy_rules()
    validation_status = service.validation_status()

    return {
        "policy_rules": [asdict(rule) for rule in policy_rules],
        "validation_status": validation_status,
        "production_approval": validation_status.get("production_approval", "NOT ESTABLISHED"),
        "governance_note": (
            "This report records artifact availability and documented evidence. "
            "It does not independently validate model performance or authorize "
            "production deployment."
        ),
        "notebook_reference": "22_model_registry_and_policy_outputs.ipynb",
    }


@router.get("/policy-outputs")
async def get_policy_outputs(request: Request) -> dict[str, Any]:
    """Get available policy outputs from Notebook 22.

    Returns information about which policy outputs were generated
    and their availability status.
    """
    service: ModelRegistryService = request.app.state.model_registry_service
    availability, reasons = service.availability()

    if availability != "available":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "Model registry unavailable", "reason_codes": reasons},
        )

    validation_status = service.validation_status()

    return {
        "policy_outputs_available": [
            "model_registry.csv",
            "model_policy_rules.json",
            "crop_recommendation_evaluation_evidence.json",
            "model_validation_status.csv",
            "model_validation_status_summary.json",
        ],
        "registry_entry_count": validation_status.get("registry_entry_count", 0),
        "policy_rule_count": validation_status.get("policy_rule_count", 0),
        "all_artifacts_exist": validation_status.get("all_registry_entries_have_artifact", False),
        "all_metadata_exist": validation_status.get("all_registry_entries_have_metadata", False),
        "notebook_reference": "22_model_registry_and_policy_outputs.ipynb",
        "notebook_outputs_path": "models/registry/",
    }


@router.get("/health")
async def get_registry_health(request: Request) -> dict[str, Any]:
    """Get model registry health status.

    Returns availability status and basic registry counts.
    """
    service: ModelRegistryService = request.app.state.model_registry_service
    health = service.health()

    return health
