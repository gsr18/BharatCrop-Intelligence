from typing import cast

from fastapi import APIRouter, Request

from bharatcrop_foundation.models.agricultural_risk import (
    AgriculturalRiskService,
)
from bharatcrop_foundation.schemas import CapabilitiesResponse, Capability

router = APIRouter(tags=["capabilities"])

STATIC_CAPABILITIES = [
    Capability(
        name="mandi_prices",
        status="disabled",
        reason_code="source_rights_and_provenance_unverified",
    ),
    Capability(
        name="farmer_data",
        status="disabled",
        reason_code="authentication_and_persistence_contracts_not_implemented",
    ),
    Capability(
        name="expert_workflows",
        status="disabled",
        reason_code="consent_and_authorization_lifecycle_not_implemented",
    ),
    Capability(
        name="data_export_and_deletion",
        status="disabled",
        reason_code="retention_and_completion_contracts_unresolved",
    ),
]


@router.get("/capabilities", response_model=CapabilitiesResponse)
def get_capabilities(request: Request) -> CapabilitiesResponse:
    yield_readiness = request.app.state.yield_prediction_service.readiness()
    yield_reasons = [
        *yield_readiness.reason_codes,
    ]
    ranking_readiness = request.app.state.apy_data_service.readiness()
    ranking_reasons = list(ranking_readiness.reason_codes)
    weather_service = request.app.state.weather_data_service
    weather_readiness = weather_service.readiness()
    integration_readiness = weather_service.integration_readiness()
    classifier_readiness = weather_service.classifier_readiness()
    risk_service = cast(
        AgriculturalRiskService,
        request.app.state.agricultural_risk_service,
    )
    risk_readiness = risk_service.readiness()
    explainability_service = request.app.state.explainability_service
    explainability_availability, explainability_reasons = explainability_service.availability()
    yield_capability = Capability(
        name="yield_prediction",
        status="enabled" if yield_readiness.execution_available else "disabled",
        reason_code=yield_reasons[0] if yield_reasons else "experimental",
        reason_codes=yield_reasons,
        availability=yield_readiness.availability,
        execution_available=yield_readiness.execution_available,
        quality_status=yield_readiness.quality_status,
        evidence_quality=(
            "model_estimates_require_caution"
            if yield_readiness.execution_available
            else "unavailable"
        ),
        production_approved=yield_readiness.production_approved,
        limitations=list(yield_readiness.limitations),
    )
    ranking_capability = Capability(
        name="crop_ranking",
        status="enabled" if ranking_readiness.execution_available else "disabled",
        reason_code=ranking_reasons[0] if ranking_reasons else "apy_dataset_unavailable",
        reason_codes=ranking_reasons,
        availability=ranking_readiness.availability,
        execution_available=ranking_readiness.execution_available,
        quality_status=ranking_readiness.quality_status,
        evidence_quality=ranking_readiness.evidence_quality,
        production_approved=ranking_readiness.production_approved,
        limitations=list(ranking_readiness.limitations),
    )
    weather_capability = Capability(
        name="weather_insights",
        status="enabled" if weather_readiness.execution_available else "disabled",
        reason_code=(
            weather_readiness.reason_codes[0]
            if weather_readiness.reason_codes
            else "historical_weather_unavailable"
        ),
        reason_codes=list(weather_readiness.reason_codes),
        availability=weather_readiness.availability,
        execution_available=weather_readiness.execution_available,
        quality_status=weather_readiness.quality_status,
        evidence_quality=weather_readiness.evidence_quality,
        production_approved=weather_readiness.production_approved,
        limitations=list(weather_readiness.limitations),
    )
    crop_weather_capability = Capability(
        name="crop_weather_context",
        status="enabled" if integration_readiness.execution_available else "disabled",
        reason_code=(
            integration_readiness.reason_codes[0]
            if integration_readiness.reason_codes
            else "apy_weather_integration_unavailable"
        ),
        reason_codes=list(integration_readiness.reason_codes),
        availability=integration_readiness.availability,
        execution_available=integration_readiness.execution_available,
        quality_status=integration_readiness.quality_status,
        evidence_quality=integration_readiness.evidence_quality,
        production_approved=integration_readiness.production_approved,
        limitations=list(integration_readiness.limitations),
    )
    classifier_capability = Capability(
        name="low_yield_classifier",
        status="disabled",
        reason_code=classifier_readiness.reason_codes[0],
        reason_codes=list(classifier_readiness.reason_codes),
        availability=classifier_readiness.availability,
        execution_available=classifier_readiness.execution_available,
        quality_status=classifier_readiness.quality_status,
        evidence_quality=classifier_readiness.evidence_quality,
        production_approved=classifier_readiness.production_approved,
        limitations=list(classifier_readiness.limitations),
    )
    risk_reason_codes = list(risk_readiness.reason_codes)
    historical_risk_capabilities = [
        Capability(
            name=name,
            status="enabled" if risk_readiness.execution_available else "disabled",
            reason_code=(
                risk_reason_codes[0]
                if risk_reason_codes
                else "notebook_20_data_unavailable"
            ),
            reason_codes=risk_reason_codes,
            availability=risk_readiness.availability,
            execution_available=risk_readiness.execution_available,
            quality_status=risk_readiness.quality_status,
            evidence_quality=risk_readiness.evidence_quality,
            production_approved=False,
            limitations=list(risk_readiness.limitations),
        )
        for name in (
            "agricultural_risk_indicators",
            "agricultural_yield_anomalies",
            "yield_instability_analysis",
            "crop_diversification",
            "district_benchmarking",
        )
    ]
    composite_capability = Capability(
        name="composite_agricultural_risk_score",
        status="disabled",
        reason_code="notebook_20_does_not_define_composite_formula",
        reason_codes=["notebook_20_does_not_define_composite_formula"],
        availability="unavailable",
        execution_available=False,
        quality_status="not_implemented",
        evidence_quality="no_verified_composite_method",
        production_approved=False,
        limitations=[
            "Notebook 20 defines separate exploratory yield indicators and does not "
            "specify a composite formula or weights.",
            "Data coverage and weather quality are evidence descriptors, not "
            "agricultural risk components.",
        ],
    )
    # Explainability capabilities from Notebook 21
    explainability_capability = Capability(
        name="global_explainability",
        status="enabled" if explainability_availability == "available" else "disabled",
        reason_code=explainability_reasons[0] if explainability_reasons else "explainability_summary_unavailable",
        reason_codes=list(explainability_reasons),
        availability=explainability_availability,
        execution_available=explainability_availability == "available",
        quality_status="research_notebook_generated" if explainability_availability == "available" else "unavailable",
        evidence_quality="notebook_21_permutation_importance" if explainability_availability == "available" else "unavailable",
        production_approved=False,
        limitations=[
            "Permutation importance measures predictive reliance, not causation.",
            "Evaluation used a sample of 3000 observations from 2021-2022.",
            "The final holdout was repeatedly inspected during prior diagnostics.",
            "These are research notebook results, not production-certified analysis.",
        ],
    )
    local_explainability_capability = Capability(
        name="local_explainability",
        status="disabled",
        reason_code="notebook_21_did_not_implement_local_explanations",
        reason_codes=["notebook_21_did_not_implement_local_explanations"],
        availability="unavailable",
        execution_available=False,
        quality_status="not_implemented",
        evidence_quality="no_local_explanation_method",
        production_approved=False,
        limitations=[
            "Notebook 21 did not implement SHAP, LIME, or other local explanation methods.",
            "Individual prediction explanations are not available from the existing research.",
        ],
    )
    uncertainty_capability = Capability(
        name="prediction_uncertainty",
        status="disabled",
        reason_code="notebook_21_did_not_implement_uncertainty_calibration",
        reason_codes=["notebook_21_did_not_implement_uncertainty_calibration"],
        availability="unavailable",
        execution_available=False,
        quality_status="not_implemented",
        evidence_quality="no_uncertainty_calibration_method",
        production_approved=False,
        limitations=[
            "Notebook 21 did not implement prediction interval calibration.",
            "No time-aware calibration using out-of-sample residuals was performed.",
            "No conformal prediction experiments were conducted.",
            "No validation of interval coverage or width was performed.",
        ],
    )
    scenario_capability = Capability(
        name="yield_scenarios",
        status="enabled" if explainability_availability == "available" else "disabled",
        reason_code=explainability_reasons[0] if explainability_reasons else "explainability_summary_unavailable",
        reason_codes=list(explainability_reasons),
        availability=explainability_availability,
        execution_available=explainability_availability == "available",
        quality_status="research_notebook_generated" if explainability_availability == "available" else "unavailable",
        evidence_quality="notebook_21_year_scenarios" if explainability_availability == "available" else "unavailable",
        production_approved=False,
        limitations=[
            "Scenarios are model-input comparisons, not causal forecasts.",
            "Years beyond 2022 are outside the model's documented training period.",
            "The model does not use weather features; year changes only affect FE_YearStart.",
            "These are hypothetical model-output comparisons, not agricultural recommendations.",
        ],
    )
    # Model insights capabilities from Notebook 22
    model_registry_service = request.app.state.model_registry_service
    registry_availability, registry_reasons = model_registry_service.availability()
    model_insights_capability = Capability(
        name="model_insights",
        status="enabled" if registry_availability == "available" else "disabled",
        reason_code=(
            registry_reasons[0]
            if registry_reasons
            else "notebook_22_registry_unavailable"
        ),
        reason_codes=list(registry_reasons),
        availability=registry_availability,
        execution_available=registry_availability == "available",
        quality_status="research_notebook_generated" if registry_availability == "available" else "unavailable",
        evidence_quality="notebook_22_model_registry" if registry_availability == "available" else "unavailable",
        production_approved=False,
        limitations=[
            "Model registry records artifact availability and documented evidence.",
            "It does not independently validate model performance or authorize production deployment.",
            "Production approval is NOT ESTABLISHED for any component.",
            "These are governance records from research notebooks, not production-certified models.",
        ],
    )
    # Grounded assistant capability
    assistant_service = getattr(request.app.state, "assistant_orchestrator", None)
    assistant_available = assistant_service.is_available() if assistant_service else False
    assistant_capability = Capability(
        name="grounded_assistant",
        status="enabled" if assistant_available else "disabled",
        reason_code=(
            "assistant_ready"
            if assistant_available
            else "provider_credentials_unconfigured"
        ),
        reason_codes=(
            ["assistant_ready"]
            if assistant_available
            else ["provider_credentials_unconfigured"]
        ),
        availability="available" if assistant_available else "unavailable",
        execution_available=assistant_available,
        quality_status="experimental" if assistant_available else "unavailable",
        evidence_quality=(
            "grounded_retrieval_and_backend_services"
            if assistant_available
            else "unavailable"
        ),
        production_approved=False,
        limitations=[
            "Assistant explains verified backend machine learning and analytical outputs.",
            "Numerical claims are strictly grounded in existing project datasets and model outputs.",
            "Agronomic recommendations, pesticide dosages, and soil diagnoses are not supported.",
            "AI generation is disabled when LLM provider credentials are unconfigured.",
        ],
    )
    return CapabilitiesResponse(
        capabilities=[
            yield_capability,
            ranking_capability,
            weather_capability,
            crop_weather_capability,
            classifier_capability,
            *historical_risk_capabilities,
            composite_capability,
            explainability_capability,
            local_explainability_capability,
            uncertainty_capability,
            scenario_capability,
            model_insights_capability,
            assistant_capability,
            *STATIC_CAPABILITIES,
        ]
    )
