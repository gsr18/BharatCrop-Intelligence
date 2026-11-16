from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final


@dataclass(frozen=True)
class SourceCitation:
    source_id: str
    title: str
    source_type: str
    dataset_or_model: str
    observation_or_training_period: str
    metrics_and_units: str
    evidence_status: str
    limitations: list[str] = field(default_factory=list)


YIELD_MODEL_CITATION: Final[SourceCitation] = SourceCitation(
    source_id="yield_model_hgb",
    title="HistGradientBoosting Yield Prediction Model (Notebook 16 & 17)",
    source_type="model_artifact",
    dataset_or_model="HistGradientBoostingRegressor (individual_crop_hgb_location.joblib)",
    observation_or_training_period="2013-2022 (Training cohort)",
    metrics_and_units="Yield in kilograms per hectare (kg/ha)",
    evidence_status="Experimental — Conditionally ready for integration",
    limitations=[
        "Predictions are model estimates, not guaranteed outcomes.",
        "Years beyond 2022 are unverified extrapolations.",
        "The model does not incorporate weather features directly.",
        "Uncalibrated prediction uncertainty is not available.",
    ],
)

APY_DATASET_CITATION: Final[SourceCitation] = SourceCitation(
    source_id="apy_historical_dataset",
    title="Historical District APY Food Grains Dataset (Notebook 18)",
    source_type="dataset",
    dataset_or_model="apy_weather_integrated_exploratory.csv (UPAg / MoA&FW)",
    observation_or_training_period="2013-2022 (Historical records)",
    metrics_and_units="Area (ha), Production (tonnes), Yield (kg/ha)",
    evidence_status="Historical observations recorded; discovered in registry",
    limitations=[
        "Historical APY yields describe recorded outcomes, not expected future yields.",
        "Rankings reflect historical yield and do not establish profitability or soil suitability.",
        "Evidence coverage varies by crop, district, and season.",
    ],
)

WEATHER_DATASET_CITATION: Final[SourceCitation] = SourceCitation(
    source_id="weather_intelligence_dataset",
    title="District Weather Annual Summary (NASA POWER daily MERRA2 estimates, Notebook 19)",
    source_type="dataset",
    dataset_or_model="district_weather_annual_cleaned_flagged_2013_2024.csv",
    observation_or_training_period="2013-2024 (Annual aggregated)",
    metrics_and_units="Precipitation (mm), Temperature (°C)",
    evidence_status="Historical NASA POWER gridded estimates, aggregated annually",
    limitations=[
        "Historical records only; not a live weather forecast or future prediction.",
        "Calendar-year aggregates may differ from crop-season boundaries.",
        "Daily NASA POWER source variables are gridded MERRA2 estimates, "
        "not local station measurements.",
    ],
)

AGRICULTURAL_RISK_CITATION: Final[SourceCitation] = SourceCitation(
    source_id="agricultural_risk_methodology",
    title="Historical Yield Risk Indicators Methodology (Notebook 20)",
    source_type="research_notebook",
    dataset_or_model="yield_risk_indicators.csv",
    observation_or_training_period="2013-2022",
    metrics_and_units="Yield anomaly category (High/Moderate Concern), CV (%), HHI",
    evidence_status="Exploratory research output — Not validated for farmer warnings",
    limitations=[
        "Exploratory indicators only; does not predict future crop failure.",
        "No composite risk score or weighting formula is defined.",
        "Retrospective classifications (<80% baseline) are research diagnostics.",
    ],
)

EXPLAINABILITY_CITATION: Final[SourceCitation] = SourceCitation(
    source_id="model_explainability_analysis",
    title="Yield Model Explainability & Permutation Importance (Notebook 21)",
    source_type="research_notebook",
    dataset_or_model="explainability_summary.json",
    observation_or_training_period="2021-2022 holdout sample (3000 rows)",
    metrics_and_units="Permutation importance (mean MAE increase), MAE (kg/ha), RMSE, R²",
    evidence_status="Research notebook diagnostic results",
    limitations=[
        "Permutation importance measures predictive reliance, not agronomic causation.",
        "Local SHAP and calibrated uncertainty intervals are NOT implemented.",
        "Scenarios compare input variants, not causal interventions.",
    ],
)

MODEL_REGISTRY_CITATION: Final[SourceCitation] = SourceCitation(
    source_id="model_registry_governance",
    title="Model Registry & Policy Rules (Notebook 22)",
    source_type="governance_policy",
    dataset_or_model="model_registry.csv & model_policy_rules.json",
    observation_or_training_period="Current registry audit",
    metrics_and_units="Artifact SHA-256 digests, policy rules (8 rules), readiness flags",
    evidence_status="Audited governance catalog",
    limitations=[
        "Records artifact availability; does NOT authorize production deployment.",
        "Production approval is NOT ESTABLISHED for any component.",
    ],
)


@dataclass(frozen=True)
class DomainCheckResult:
    is_out_of_scope: bool
    domain: str | None = None
    reason_en: str | None = None
    reason_hi: str | None = None


# Patterns for strictly out-of-scope agricultural domains
OUT_OF_SCOPE_DOMAINS: list[tuple[str, list[str], str, str]] = [
    (
        "prompt_injection_or_system_override",
        [
            r"ignore\s+(all\s+)?(previous|prior|system)\s+instructions",
            r"you\s+are\s+now\b",
            r"pretend\s+(to\s+be|you\s+are)\b",
            r"\bjailbreak\b",
            r"system\s+prompt\b",
        ],
        "system prompt override attempts or adversarial roleplay",
        "सिस्टम निर्देशों को ओवरराइड करने या अनधिकृत भूमिका निभाने के प्रयास",
    ),
    (
        "pesticide_and_pest_control",
        [
            r"\bpesticid\w*",
            r"\binsecticid\w*",
            r"\bfungicid\w*",
            r"\bherbicide\w*",
            r"\bweedicide\w*",
            r"\bchlorpyrifos\b",
            r"\bchemical\w*",
            r"\bprescribe\b",
            r"\bprescription\b",
            r"\bspray\b",
            r"\bdisease\s+treatment\b",
            r"\bpest\w*",
            r"\bmedicine\s+for\b",
            r"\bकीटनाशक\b",
            r"\bकीट\b",
            r"\bरोग\s+उपचार\b",
            r"\bदवा\b",
            r"\bछिड़काव\b",
            r"\bफफूंद\b",
        ],
        "pesticide prescriptions, chemical treatments, and plant disease diagnosis",
        "कीटनाशक नुस्खे, रासायनिक उपचार और फसल रोग निदान",
    ),
    (
        "fertilizer_dosage",
        [
            r"\bfertilizer\s+dos\w*",
            r"\burea\b",
            r"\bdap\b",
            r"\bnpk\b",
            r"\bchemical\s+dose\b",
            r"\bhow\s+much\s+fertilizer\b",
            r"\bखाद\s+की\s+मात्रा\b",
            r"\bयूरिया\b",
            r"\bउर्वरक\b",
            r"\bडीएपी\b",
        ],
        "fertilizer dosages and chemical application schedules",
        "उर्वरक (खाद) की अनुशंसित मात्रा और रासायनिक अनुप्रयोग",
    ),
    (
        "soil_suitability_and_testing",
        [
            r"\bsoil\b",
            r"\bsoil\s+test\w*",
            r"\bsoil\s+suitability\b",
            r"\bsoil\s+type\b",
            r"\bsoil\s+ph\b",
            r"\bsoil\s+health\b",
            r"\bमिट्टी\b",
            r"\bमृदा\b",
        ],
        "soil testing, soil chemistry, and soil suitability evaluations",
        "मिट्टी परीक्षण, मृदा रसायन और मिट्टी की उपयुक्तता मूल्यांकन",
    ),
    (
        "live_weather_forecast",
        [
            r"\btomorrow('?s)?\s+weather\b",
            r"\bwill\s+it\s+rain\b",
            r"\bforecast\s+for\s+(today|tomorrow|next\s+week)\b",
            r"\blive\s+weather\b",
            r"\bmonsoon\s+forecast\b",
            r"\bकल\s+का\s+मौसम\b",
            r"\bकल\s+बारिश\b",
            r"\bमौसम\s+पूर्वानुमान\b",
            r"\bआज\s+बारिश\b",
        ],
        "live weather observations and future weather forecasting",
        "लाइव मौसम की स्थिति और भविष्य का मौसम पूर्वानुमान",
    ),
    (
        "live_mandi_prices",
        [
            r"\btoday('?s)?\s+price\b",
            r"\bmandi\s+price\b",
            r"\bmandi\s+rate\b",
            r"\bcurrent\s+market\s+price\b",
            r"\bapmc\s+rate\b",
            r"\bमंडी\s+भाव\b",
            r"\bआज\s+का\s+भाव\b",
            r"\bताजा\s+भाव\b",
            r"\bबाजार\s+मूल्य\b",
        ],
        "live APMC mandi commodity prices and daily market rates",
        "दैनिक एपीएमसी मंडी भाव और आज के बाजार भाव",
    ),
    (
        "commercial_profit_guarantees",
        [
            r"\bprofit\s+guarantee\b",
            r"\bguaranteed\s+income\b",
            r"\bhow\s+much\s+money\s+will\s+i\s+make\b",
            r"\bfinancial\s+return\b",
            r"\bमुनाफा\s+गारंटी\b",
            r"\bकमाई\s+की\s+गारंटी\b",
        ],
        "farm profitability guarantees and financial return assurances",
        "कृषि लाभ की गारंटी और वित्तीय आय का आश्वासन",
    ),
]


def check_out_of_scope_intent(query: str) -> DomainCheckResult:
    """Check if the user query is asking for agricultural domains unsupported by project evidence."""
    clean_query = query.strip().casefold()

    for domain_name, patterns, desc_en, desc_hi in OUT_OF_SCOPE_DOMAINS:
        for pattern in patterns:
            if re.search(pattern, clean_query, re.IGNORECASE):
                reason_en = (
                    f"BharatCrop Intelligence does not have verified project evidence for {desc_en}. "
                    "Our platform is strictly scoped to historical APY crop yields, "
                    "historical NASA POWER weather summaries, "
                    "exploratory yield risk diagnostics, model explainability, and governance transparency. "
                    "For agronomic, pest, soil, or chemical management, please consult your local "
                    "Krishi Vigyan Kendra (KVK) or certified agricultural extension expert."
                )
                reason_hi = (
                    f"भारतक्रॉप इंटेलिजेंस के पास {desc_hi} के लिए सत्यापित प्रमाण उपलब्ध नहीं है। "
                    "यह प्रणाली केवल ऐतिहासिक फसल पैदावार (APY), ऐतिहासिक मौसम सारांश (NASA POWER), "
                    "खोजपूर्ण उपज जोखिम संकेतक, "
                    "मॉडल व्याख्या और गवर्नेंस पारदर्शिता के लिए बनाई गई है। "
                    "कीटनाशक, उर्वरक, मृदा या कृषि संबंधी सलाह के लिए कृपया अपने स्थानीय "
                    "कृषि विज्ञान केंद्र (KVK) या प्रमाणित कृषि विशेषज्ञ से संपर्क करें।"
                )
                return DomainCheckResult(
                    is_out_of_scope=True,
                    domain=domain_name,
                    reason_en=reason_en,
                    reason_hi=reason_hi,
                )

    return DomainCheckResult(is_out_of_scope=False)
