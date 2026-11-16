from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Request

from bharatcrop_foundation.assistant.orchestrator import AssistantOrchestrator
from bharatcrop_foundation.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantStatusResponse,
    AssistantSuggestionsResponse,
)

router = APIRouter(prefix="/assistant", tags=["assistant"])

CURATED_SUGGESTIONS: list[dict[str, str]] = [
    {
        "topic": "yield_prediction",
        "en": "What yield does your model estimate for Rice in Meerut?",
        "hi": "मेरठ में चावल के लिए मॉडल का अनुमानित उत्पादन क्या है?",
    },
    {
        "topic": "crop_intelligence",
        "en": "Which crops historically performed better in Meerut?",
        "hi": "मेरठ में किन फसलों ने ऐतिहासिक रूप से बेहतर प्रदर्शन किया?",
    },
    {
        "topic": "weather_intelligence",
        "en": "How has rainfall changed in Meerut?",
        "hi": "मेरठ में वर्षा का ऐतिहासिक रुझान क्या है?",
    },
    {
        "topic": "agricultural_risk",
        "en": "Why is this historical yield observation marked High Concern?",
        "hi": "यह ऐतिहासिक फसल उपज 'हाई कंसर्न' के रूप में क्यों चिह्नित है?",
    },
    {
        "topic": "explainability",
        "en": "What features does the yield model use to produce its prediction?",
        "hi": "पैदावार मॉडल भविष्यवाणी करने के लिए किन विशेषताओं का उपयोग करता है?",
    },
    {
        "topic": "uncertainty",
        "en": "Why is prediction uncertainty unavailable?",
        "hi": "भविष्यवाणी अनिश्चितता (Prediction Uncertainty) क्यों उपलब्ध नहीं है?",
    },
    {
        "topic": "model_registry",
        "en": "Which model is currently operational?",
        "hi": "वर्तमान में कौन सा मॉडल उपलब्ध है?",
    },
]


@router.post("/chat", response_model=AssistantChatResponse)
async def chat_with_assistant(
    payload: AssistantChatRequest,
    request: Request,
) -> AssistantChatResponse:
    """Conversational endpoint for the AI Agricultural Assistant.

    Retrieves evidence from backend services, explains it in English or Hindi,
    and returns source citations and limitations.
    """
    request_id = getattr(request.state, "request_id", None) or request.headers.get("x-request-id") or str(uuid.uuid4())
    orchestrator: AssistantOrchestrator = request.app.state.assistant_orchestrator
    return await orchestrator.process_chat(payload, request_id)


@router.get("/status", response_model=AssistantStatusResponse)
async def get_assistant_status(request: Request) -> AssistantStatusResponse:
    """Get operational status and provider readiness of the AI Assistant."""
    orchestrator: AssistantOrchestrator = request.app.state.assistant_orchestrator
    info = orchestrator.readiness()

    return AssistantStatusResponse(
        status="ready" if info["available"] else "provider_unconfigured",
        provider=info["provider"],
        model=info["model"],
        capabilities=info["supported_tools"],
        supported_languages=info["supported_languages"],
        limitations=[
            "The assistant explains verified backend evidence and does not independently calculate predictions.",
            "Predictions and historical rankings do not establish soil suitability, irrigation, or profitability.",
            "AI generation is disabled when LLM provider credentials are unconfigured.",
        ],
    )


@router.get("/suggestions", response_model=AssistantSuggestionsResponse)
async def get_assistant_suggestions() -> AssistantSuggestionsResponse:
    """Get approved sample questions in English and Hindi for exploring the platform."""
    return AssistantSuggestionsResponse(suggestions=CURATED_SUGGESTIONS)
