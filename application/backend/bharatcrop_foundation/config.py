from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_YIELD_ARTIFACT_PATH = (
    PROJECT_ROOT / "models" / "yield_prediction" / "individual_crop_hgb_location.joblib"
)
DEFAULT_YIELD_METADATA_PATH = (
    PROJECT_ROOT / "models" / "yield_prediction" / "individual_crop_hgb_location_metadata.json"
)
DEFAULT_YIELD_TRAINING_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "weather_regional"
    / "apy_weather_integrated_exploratory.csv"
)
DEFAULT_APY_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "weather_regional"
    / "apy_weather_integrated_exploratory.csv"
)
DEFAULT_WEATHER_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "weather_regional"
    / "district_weather_annual_cleaned_flagged_2013_2024.csv"
)
DEFAULT_WEATHER_REFERENCE_PATH = (
    PROJECT_ROOT / "models" / "weather_intelligence" / "district_weather_reference.csv"
)
DEFAULT_WEATHER_HISTORY_PATH = (
    PROJECT_ROOT / "models" / "weather_intelligence" / "district_weather_history.csv"
)
DEFAULT_WEATHER_UNMATCHED_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "weather_regional"
    / "apy_districts_without_weather_coverage.csv"
)
DEFAULT_WEATHER_INTEGRATION_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "weather_regional"
    / "apy_weather_integrated_exploratory.csv"
)
DEFAULT_WEATHER_INTEGRATION_SUMMARY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "weather_regional"
    / "apy_weather_integration_summary.csv"
)
DEFAULT_WEATHER_CLASSIFIER_EVALUATION_PATH = (
    PROJECT_ROOT
    / "models"
    / "weather_intelligence"
    / "low_yield_model_evaluation.json"
)
DEFAULT_WEATHER_INTELLIGENCE_METADATA_PATH = (
    PROJECT_ROOT / "models" / "weather_intelligence" / "weather_intelligence_metadata.json"
)
DEFAULT_WEATHER_ML_ROOT = (
    PROJECT_ROOT / "phase3b_weather_intelligence" / "reports" / "weather_intelligence_v2"
)
DEFAULT_WEATHER_ML_FEATURE_SPEC_PATH = (
    DEFAULT_WEATHER_ML_ROOT
    / "WI_05_rainfall_model_development"
    / "WI_05_feature_specification.json"
)
DEFAULT_WEATHER_ML_MODEL_DIRS = (
    DEFAULT_WEATHER_ML_ROOT / "WI_05_rainfall_model_development" / "candidate_models",
    DEFAULT_WEATHER_ML_ROOT / "candidate_models",
)
DEFAULT_WEATHER_ML_DATASET_METADATA_PATH = (
    PROJECT_ROOT
    / "phase3b_weather_intelligence"
    / "data"
    / "processed"
    / "weather_daily_v1"
    / "dataset_metadata.json"
)
DEFAULT_WEATHER_ML_FEATURE_DATASET_DIR = (
    PROJECT_ROOT
    / "phase3b_weather_intelligence"
    / "data"
    / "processed"
    / "weather_features_v1"
    / "weather-features-v1"
)
DEFAULT_WEATHER_ML_DISTRICT_GRID_PATH = (
    PROJECT_ROOT / "models" / "weather_ml" / "district_grid_cells_v1.csv"
)
DEFAULT_WEATHER_ML_FEATURE_COVERAGE_PATH = (
    PROJECT_ROOT / "models" / "weather_ml" / "cell_feature_coverage_v1.csv"
)
DEFAULT_AGRICULTURAL_RISK_METADATA_PATH = (
    PROJECT_ROOT
    / "models"
    / "agricultural_risk_intelligence"
    / "agricultural_risk_metadata.json"
)
DEFAULT_EXPLAINABILITY_SUMMARY_PATH = (
    PROJECT_ROOT
    / "models"
    / "model_explainability_and_scenarios"
    / "explainability_summary.json"
)
DEFAULT_REGISTRY_DIR = (
    PROJECT_ROOT
    / "models"
    / "registry"
)
DEFAULT_YIELD_ARTIFACT_SHA256 = "dc057a8cbe39adef03736eca32370cf41f2c830a04e8cfeae1c74fd35834dce7"
DEFAULT_YIELD_METADATA_SHA256 = "d6cf1c945c608401d740a41e3c973b01eeadc9932975a3a0e75cf035010b2a44"

# Phase 2E — isolated experimental future-yield forecast (research artifact).
# These point at preserved Phase 2D outputs and are separate from the manual
# HistGradientBoosting model above; the manual path is never affected by them.
DEFAULT_EXPERIMENTAL_FORECAST_ARTIFACT_PATH = (
    PROJECT_ROOT
    / "phase2d_expanded_yield_forecasting"
    / "models"
    / "phase2d_pooled_rf_research.joblib"
)
DEFAULT_EXPERIMENTAL_FORECAST_METADATA_PATH = (
    PROJECT_ROOT
    / "phase2d_expanded_yield_forecasting"
    / "models"
    / "phase2d_pooled_rf_research_metadata.json"
)
DEFAULT_EXPERIMENTAL_FORECAST_HISTORY_PATH = (
    PROJECT_ROOT
    / "phase2d_expanded_yield_forecasting"
    / "artifacts"
    / "cohort_strict.csv"
)
DEFAULT_EXPERIMENTAL_FORECAST_ARTIFACT_SHA256 = (
    "e6be004d8af21a3b89ad06dc7eab3948a5c0cc636eb62cdef9dd869993a8c3d1"
)
DEFAULT_EXPERIMENTAL_FORECAST_METADATA_SHA256 = (
    "d0700f75d50dcb5df400e37534c13fac9bfe2be769bcbcd48778c0ceaf97c347"
)

DEFAULT_LLM_PROVIDER = "none"
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_LLM_TIMEOUT_SECONDS = 30.0
DEFAULT_LLM_MAX_TOKENS = 1024


@dataclass(frozen=True)
class Settings:
    service_name: str = "BharatCrop Intelligence"
    api_prefix: str = "/api/v1"
    api_version: str = "v1"
    database_url: str | None = None
    yield_artifact_path: Path = DEFAULT_YIELD_ARTIFACT_PATH
    yield_metadata_path: Path = DEFAULT_YIELD_METADATA_PATH
    yield_training_data_path: Path = DEFAULT_YIELD_TRAINING_DATA_PATH
    apy_data_path: Path = DEFAULT_APY_DATA_PATH
    weather_data_path: Path = DEFAULT_WEATHER_DATA_PATH
    weather_reference_path: Path = DEFAULT_WEATHER_REFERENCE_PATH
    weather_history_path: Path = DEFAULT_WEATHER_HISTORY_PATH
    weather_unmatched_path: Path = DEFAULT_WEATHER_UNMATCHED_PATH
    weather_integration_path: Path = DEFAULT_WEATHER_INTEGRATION_PATH
    weather_integration_summary_path: Path = DEFAULT_WEATHER_INTEGRATION_SUMMARY_PATH
    weather_classifier_evaluation_path: Path = DEFAULT_WEATHER_CLASSIFIER_EVALUATION_PATH
    weather_intelligence_metadata_path: Path = DEFAULT_WEATHER_INTELLIGENCE_METADATA_PATH
    weather_ml_feature_spec_path: Path = DEFAULT_WEATHER_ML_FEATURE_SPEC_PATH
    weather_ml_model_dirs: tuple[Path, ...] = DEFAULT_WEATHER_ML_MODEL_DIRS
    weather_ml_dataset_metadata_path: Path = DEFAULT_WEATHER_ML_DATASET_METADATA_PATH
    weather_ml_feature_dataset_dir: Path = DEFAULT_WEATHER_ML_FEATURE_DATASET_DIR
    weather_ml_district_grid_path: Path = DEFAULT_WEATHER_ML_DISTRICT_GRID_PATH
    weather_ml_feature_coverage_path: Path = DEFAULT_WEATHER_ML_FEATURE_COVERAGE_PATH
    agricultural_risk_metadata_path: Path = DEFAULT_AGRICULTURAL_RISK_METADATA_PATH
    explainability_summary_path: Path = DEFAULT_EXPLAINABILITY_SUMMARY_PATH
    registry_dir: Path = DEFAULT_REGISTRY_DIR
    yield_artifact_sha256: str | None = DEFAULT_YIELD_ARTIFACT_SHA256
    yield_metadata_sha256: str | None = DEFAULT_YIELD_METADATA_SHA256
    experimental_forecast_artifact_path: Path = DEFAULT_EXPERIMENTAL_FORECAST_ARTIFACT_PATH
    experimental_forecast_metadata_path: Path = DEFAULT_EXPERIMENTAL_FORECAST_METADATA_PATH
    experimental_forecast_history_path: Path = DEFAULT_EXPERIMENTAL_FORECAST_HISTORY_PATH
    experimental_forecast_artifact_sha256: str | None = (
        DEFAULT_EXPERIMENTAL_FORECAST_ARTIFACT_SHA256
    )
    experimental_forecast_metadata_sha256: str | None = (
        DEFAULT_EXPERIMENTAL_FORECAST_METADATA_SHA256
    )
    experimental_forecast_reference_year: int | None = None
    llm_provider: str = DEFAULT_LLM_PROVIDER
    llm_api_key: str | None = None
    llm_model: str = DEFAULT_LLM_MODEL
    llm_base_url: str | None = None
    llm_timeout_seconds: float = DEFAULT_LLM_TIMEOUT_SECONDS
    llm_max_tokens: int = DEFAULT_LLM_MAX_TOKENS


def _read_env_file(path: Path | None = None) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file. Missing files yield no values."""
    env_path = path if path is not None else BACKEND_DIR / ".env"
    values: dict[str, str] = {}
    if not env_path.is_file():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def load_settings() -> Settings:
    for env_key, env_value in _read_env_file().items():
        os.environ.setdefault(env_key, env_value)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        parsed = urlsplit(database_url)
        if parsed.scheme not in {"postgresql", "postgresql+psycopg"}:
            raise ValueError("DATABASE_URL must use PostgreSQL.")
        if not parsed.hostname or not parsed.path.strip("/"):
            raise ValueError("DATABASE_URL must identify a PostgreSQL database.")
        if parsed.scheme == "postgresql":
            database_url = database_url.replace(
                "postgresql://",
                "postgresql+psycopg://",
                1,
            )
    artifact_path = Path(os.getenv("YIELD_MODEL_ARTIFACT_PATH", str(DEFAULT_YIELD_ARTIFACT_PATH)))
    metadata_path = Path(os.getenv("YIELD_MODEL_METADATA_PATH", str(DEFAULT_YIELD_METADATA_PATH)))
    training_data_path = Path(
        os.getenv("YIELD_MODEL_TRAINING_DATA_PATH", str(DEFAULT_YIELD_TRAINING_DATA_PATH))
    )
    apy_data_path = Path(os.getenv("APY_DATA_PATH", str(DEFAULT_APY_DATA_PATH)))
    weather_data_path = Path(os.getenv("WEATHER_DATA_PATH", str(DEFAULT_WEATHER_DATA_PATH)))
    registry_dir = Path(os.getenv("MODEL_REGISTRY_DIR", str(DEFAULT_REGISTRY_DIR)))
    expected_hash = os.getenv("YIELD_MODEL_SHA256", DEFAULT_YIELD_ARTIFACT_SHA256)
    expected_metadata_hash = os.getenv(
        "YIELD_MODEL_METADATA_SHA256",
        DEFAULT_YIELD_METADATA_SHA256,
    )
    for name, value in (
        ("YIELD_MODEL_SHA256", expected_hash),
        ("YIELD_MODEL_METADATA_SHA256", expected_metadata_hash),
    ):
        if value is not None and (
            len(value) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in value)
        ):
            raise ValueError(f"{name} must be a SHA-256 hexadecimal digest.")

    exp_artifact_path = Path(
        os.getenv(
            "EXPERIMENTAL_FORECAST_ARTIFACT_PATH",
            str(DEFAULT_EXPERIMENTAL_FORECAST_ARTIFACT_PATH),
        )
    )
    exp_metadata_path = Path(
        os.getenv(
            "EXPERIMENTAL_FORECAST_METADATA_PATH",
            str(DEFAULT_EXPERIMENTAL_FORECAST_METADATA_PATH),
        )
    )
    exp_history_path = Path(
        os.getenv(
            "EXPERIMENTAL_FORECAST_HISTORY_PATH",
            str(DEFAULT_EXPERIMENTAL_FORECAST_HISTORY_PATH),
        )
    )
    exp_artifact_hash = os.getenv(
        "EXPERIMENTAL_FORECAST_ARTIFACT_SHA256",
        DEFAULT_EXPERIMENTAL_FORECAST_ARTIFACT_SHA256,
    )
    exp_metadata_hash = os.getenv(
        "EXPERIMENTAL_FORECAST_METADATA_SHA256",
        DEFAULT_EXPERIMENTAL_FORECAST_METADATA_SHA256,
    )
    for name, value in (
        ("EXPERIMENTAL_FORECAST_ARTIFACT_SHA256", exp_artifact_hash),
        ("EXPERIMENTAL_FORECAST_METADATA_SHA256", exp_metadata_hash),
    ):
        if value is not None and (
            len(value) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in value)
        ):
            raise ValueError(f"{name} must be a SHA-256 hexadecimal digest.")
    reference_year_raw = os.getenv("EXPERIMENTAL_FORECAST_REFERENCE_YEAR")
    exp_reference_year: int | None = None
    if reference_year_raw:
        try:
            exp_reference_year = int(reference_year_raw)
        except ValueError:
            exp_reference_year = None

    llm_provider = os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER)
    llm_api_key = os.getenv("LLM_API_KEY")
    llm_model = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
    llm_base_url = os.getenv("LLM_BASE_URL")
    try:
        llm_timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", str(DEFAULT_LLM_TIMEOUT_SECONDS)))
    except ValueError:
        llm_timeout = DEFAULT_LLM_TIMEOUT_SECONDS
    try:
        llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", str(DEFAULT_LLM_MAX_TOKENS)))
    except ValueError:
        llm_max_tokens = DEFAULT_LLM_MAX_TOKENS

    return Settings(
        database_url=database_url,
        yield_artifact_path=artifact_path,
        yield_metadata_path=metadata_path,
        yield_training_data_path=training_data_path,
        apy_data_path=apy_data_path,
        weather_data_path=weather_data_path,
        registry_dir=registry_dir,
        yield_artifact_sha256=expected_hash.lower() if expected_hash else None,
        yield_metadata_sha256=(expected_metadata_hash.lower() if expected_metadata_hash else None),
        experimental_forecast_artifact_path=exp_artifact_path,
        experimental_forecast_metadata_path=exp_metadata_path,
        experimental_forecast_history_path=exp_history_path,
        experimental_forecast_artifact_sha256=(
            exp_artifact_hash.lower() if exp_artifact_hash else None
        ),
        experimental_forecast_metadata_sha256=(
            exp_metadata_hash.lower() if exp_metadata_hash else None
        ),
        experimental_forecast_reference_year=exp_reference_year,
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        llm_timeout_seconds=llm_timeout,
        llm_max_tokens=llm_max_tokens,
    )


settings = load_settings()
