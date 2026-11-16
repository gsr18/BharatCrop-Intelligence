from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
)


class ServiceInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    api_version: str


class HealthResponse(BaseModel):
    status: str
    request_id: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]
    request_id: str


class Capability(BaseModel):
    name: str
    status: str
    reason_code: str
    reason_codes: list[str] = Field(default_factory=list)
    availability: str = "unavailable"
    execution_available: bool = False
    quality_status: str = "unavailable"
    evidence_quality: str = "unavailable"
    production_approved: bool = False
    limitations: list[str] = Field(default_factory=list)


class CapabilitiesResponse(BaseModel):
    capabilities: list[Capability]


class WeatherMetricInfo(BaseModel):
    name: str
    label: str
    unit: str


class WeatherDatasetProvenance(BaseModel):
    dataset_name: str
    dataset_source: str
    source_file: str
    sha256: str
    record_count: int
    district_geography_count: int
    year_start: int
    year_end: int
    weather_metrics: list[WeatherMetricInfo]
    transformation: str


class WeatherOptionsResponse(BaseModel):
    years: list[int]
    year_start: int
    year_end: int
    states: list[str]
    districts: list[str]
    districts_by_state: dict[str, list[str]]
    selected_state: str | None
    weather_metrics: list[WeatherMetricInfo]
    dataset_provenance: WeatherDatasetProvenance
    limitations: list[str]


class WeatherOverviewResponse(BaseModel):
    record_count: int
    weather_available_record_count: int
    geography_count: int
    state_count: int
    district_count: int
    years: list[int]
    calendar_year_semantics: str
    valid_day_coverage: dict[str, dict[str, float | int | None]]
    missingness: dict[str, dict[str, float | int | None]]
    quality_flag_counts: dict[str, int]
    geography_coverage: dict[str, int]
    dataset_provenance: WeatherDatasetProvenance
    limitations: list[str]


class WeatherQualityPoint(BaseModel):
    year: int
    date_semantics: str
    state: str
    district: str
    geography_id: str
    value: float | None
    unit: str
    valid_days: dict[str, int | None]
    quality_flags: dict[str, bool]


class WeatherSeriesResponse(BaseModel):
    metric: str
    label: str
    unit: str
    date_semantics: str
    page: int
    page_size: int
    total: int
    points: list[WeatherQualityPoint]
    dataset_provenance: WeatherDatasetProvenance
    limitations: list[str]


class WeatherTrendValue(BaseModel):
    year: int
    date_semantics: str
    value: float
    unit: str
    mean: float
    median: float
    p95: float
    maximum: float
    observation_count: int


class WeatherTrendSeries(BaseModel):
    location: str
    yearly_values: list[WeatherTrendValue]
    observation_count: int


class WeatherTrendsResponse(BaseModel):
    metric: str
    label: str
    unit: str
    aggregation: str
    trend_method: str
    series: list[WeatherTrendSeries]
    dataset_provenance: WeatherDatasetProvenance
    limitations: list[str]


class WeatherAnomalyMetricStatus(BaseModel):
    value: float | None
    historical_p10: float | None
    historical_p90: float | None
    status: str
    unit: str


class WeatherAnomalyRecord(BaseModel):
    state: str
    district: str
    geography_id: str
    calendar_year: int
    historical_percentile_status: dict[str, WeatherAnomalyMetricStatus]
    tmax_mean_same_period_deviation_c: float | None
    temperature_deviation_baseline: str
    quality_flags: dict[str, bool]


class WeatherAnomaliesResponse(BaseModel):
    method: dict[str, str]
    page: int
    page_size: int
    total: int
    records: list[WeatherAnomalyRecord]
    dataset_provenance: WeatherDatasetProvenance
    limitations: list[str]


class WeatherCoverageLocation(BaseModel):
    state: str
    district: str
    geography_id: str | None
    weather_year_count: int
    weather_coverage_pct: float
    coverage_status: str
    available_years: list[int]
    valid_day_coverage: dict[str, float | None]
    quality_flag_counts: dict[str, int]
    district_latitude: float | None
    district_longitude: float | None
    coordinate_source: str | None
    geography_confidence: str | None
    representative_grid_latitude: float | None
    representative_grid_longitude: float | None
    representative_grid_elevation_m: float | None
    nearest_grid_distance_km: float | None
    mapping_quality: str


class WeatherCoverageSummary(BaseModel):
    reference_location_count: int
    locations_with_weather: int
    locations_without_weather: int
    district_year_observations: int
    year_start: int
    year_end: int


class WeatherCoverageResponse(BaseModel):
    page: int
    page_size: int
    total: int
    locations: list[WeatherCoverageLocation]
    coverage_summary: WeatherCoverageSummary
    dataset_provenance: WeatherDatasetProvenance
    limitations: list[str]


class WeatherCropPoint(BaseModel):
    crop: str
    season: str
    crop_category: str
    agricultural_year: str
    agricultural_year_start: int
    weather_proxy_calendar_year: int | None
    area: float | None
    production: float | None
    yield_value: float | None = Field(alias="yield")
    yield_unit: str
    weather_available: bool
    weather_match_status: str
    weather_alignment_method: str
    full_season_alignment_verified: bool
    weather_values: dict[str, float | None]
    valid_days: dict[str, int | None]
    weather_quality_flags: dict[str, bool | None]


class WeatherCropDataProvenance(BaseModel):
    dataset_name: str
    dataset_source: str
    source_file: str
    sha256: str
    record_count: int
    alignment_method: str


class WeatherCropContextResponse(BaseModel):
    state: str
    district: str
    page: int
    page_size: int
    total: int
    matched_count: int
    unmatched_count: int
    points: list[WeatherCropPoint]
    alignment_method: str
    temporal_semantics: str
    full_season_alignment_verified: bool
    project_integration_totals: dict[str, str | int | float | bool | None]
    interpretation: str
    crop_data_provenance: WeatherCropDataProvenance
    dataset_provenance: WeatherDatasetProvenance
    limitations: list[str]


class WeatherClassifierStatusResponse(BaseModel):
    task: str
    execution_available: bool
    availability: str
    artifact_available: bool
    artifact_path: str | None
    status: str
    reason_code: str
    target_definition: str | None
    algorithms_evaluated: list[str]
    features_evaluated: list[str]
    baseline_features: list[str]
    weather_feature_additions: list[str]
    evaluation_method: str
    training_years: list[int] | None
    test_years: list[int] | None
    train_rows: int | None
    test_rows: int | None
    recorded_experimental_metrics: dict[str, dict[str, float]] | None
    weather_added_predictive_value: bool | None
    deployment_status: str
    production_approved: bool
    limitations: list[str]
    notebook: str
    dataset_provenance: WeatherDatasetProvenance


class WeatherMlHorizonStatus(BaseModel):
    horizon: int
    label: str
    status: str
    classifier_artifact: str | None
    amount_regressor_artifact: str | None
    reason_code: str | None = None


class WeatherMlInputStatus(BaseModel):
    provider: str
    forecast_available: bool
    latest_available_input_date: str | None
    required_variables: list[str]
    frequency: str
    reason_code: str
    message: str


class WeatherMlStatusResponse(BaseModel):
    task: str
    status: str
    forecast_available: bool
    reason_code: str
    production_approved: bool
    model_directories: list[str]
    feature_specification: dict[str, Any]
    predictor_count: int
    horizons: list[WeatherMlHorizonStatus]
    input: WeatherMlInputStatus
    dataset: dict[str, Any]
    limitations: list[str]


class WeatherMlForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=7.0, le=34.5)
    longitude: float = Field(ge=69.375, le=96.875)
    as_of_date: StrictStr | None = None
    horizons: list[StrictInt] | None = None


class WeatherMlForecastResponse(BaseModel):
    task: str
    forecast_available: bool
    status: str
    reason_code: str
    message: str
    latitude: float
    longitude: float
    as_of_date: str | None
    latest_available_input_date: str | None
    required_input_variables: list[str]
    horizons: list[WeatherMlHorizonStatus]
    dataset: dict[str, Any]
    limitations: list[str]


class WeatherMlDistrictOption(BaseModel):
    state: str
    district: str
    apy_geography_id: str
    matched_boundary_name: str
    intersecting_cell_count: int
    valid_cell_count: int


class WeatherMlDistrictOptionsResponse(BaseModel):
    task: str
    forecast_origin_date: str
    archive_end_date: str | None
    supported_district_count: int
    states: list[str]
    districts_by_state: dict[str, list[str]]
    districts: list[WeatherMlDistrictOption]
    aggregation_method: str
    weight_field: str
    limitations: list[str]


class WeatherMlDistrictForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: StrictStr
    district: StrictStr
    horizons: list[StrictInt] | None = None


class WeatherMlDistrictGridCell(BaseModel):
    cell_id: str
    latitude: float
    longitude: float
    intersection_area_km2: float


class WeatherMlDistrictHorizonForecast(BaseModel):
    horizon: int
    label: str
    target_date: str
    expected_precipitation_mm_day: float
    wet_probability: float
    conditional_wet_amount_mm_day: float
    min_cell_expected_mm_day: float
    max_cell_expected_mm_day: float
    cell_count: int


class WeatherMlDistrictForecastResponse(BaseModel):
    task: str
    forecast_available: bool
    status: str
    reason_code: str
    message: str
    notice: str
    state: str
    district: str
    apy_geography_id: str | None
    matched_boundary_name: str | None
    forecast_origin_date: str
    archive_end_date: str | None
    forecast_dates: list[str]
    spatial: dict[str, Any]
    grid_cells: list[WeatherMlDistrictGridCell]
    horizons: list[WeatherMlDistrictHorizonForecast]
    model: dict[str, Any]
    limitations: list[str]


class RiskDatasetProvenance(BaseModel):
    dataset: dict[str, Any]
    apy_source_description: str
    apy_source_limitations: list[str]
    research_notebook: str
    research_metadata_file: str
    research_metadata_sha256: str
    yield_unit: str
    prepared_rows: int
    observations_with_notebook_baseline: int
    year_start: int
    year_end: int


class RiskOptionsResponse(BaseModel):
    states: list[str]
    districts: list[str]
    districts_by_state: dict[str, list[str]]
    crops: list[str]
    seasons: list[str]
    years: list[int]
    year_start: int
    year_end: int
    selected_state: str | None
    dataset_provenance: RiskDatasetProvenance
    methodology: dict[str, Any]
    limitations: list[str]


class RiskOverviewResponse(BaseModel):
    prepared_observation_count: int
    observations_with_historical_baseline: int
    observations_without_sufficient_history: int
    district_crop_season_group_count: int
    crop_count: int
    state_count: int
    district_count: int
    year_start: int
    year_end: int
    indicator_counts: dict[str, int]
    weather_context: dict[str, Any]
    research_metadata: dict[str, Any]
    dataset_provenance: RiskDatasetProvenance
    limitations: list[str]


class RiskBaselineObservation(BaseModel):
    year_start: int
    agricultural_year: str
    yield_value: float


class RiskAnomalyRecord(BaseModel):
    state: str
    district: str
    crop: str
    season: str
    agricultural_year: str
    year_start: int
    yield_value: float
    yield_unit: str
    baseline_available: bool
    historical_median_yield: float | None
    historical_observation_count: int
    baseline_observations: list[RiskBaselineObservation]
    yield_difference_from_baseline: float | None
    yield_vs_historical_pct: float | None
    yield_to_baseline_ratio: float | None
    anomaly_direction: str
    risk_indicator: str
    extreme_deviation_review: bool
    standardized_deviation: float | None
    standardized_deviation_status: str
    source_quality_flags: dict[str, bool | None]


class RiskAnomaliesResponse(BaseModel):
    state: str
    district: str
    crop: str
    season: str
    page: int
    page_size: int
    total: int
    records: list[RiskAnomalyRecord]
    methodology: dict[str, Any]
    dataset_provenance: RiskDatasetProvenance
    limitations: list[str]


class RiskHistoryObservation(BaseModel):
    year_start: int
    agricultural_year: str
    yield_value: float
    yield_unit: str
    source_quality_flags: dict[str, bool | None]


class RiskInstabilityResponse(BaseModel):
    state: str
    district: str
    crop: str
    season: str
    window_start_year: int | None
    window_end_year: int | None
    valid_observation_count: int
    observed_year_count: int
    source_quality_flagged_observation_count: int
    years: list[RiskHistoryObservation]
    mean_yield: float | None
    median_yield: float | None
    sample_standard_deviation: float | None
    coefficient_of_variation_pct: float | None
    robust_variability: float | None
    robust_variability_status: str
    trend_slope: float | None
    trend_status: str
    calculation_method: str
    dataset_provenance: RiskDatasetProvenance
    limitations: list[str]


class RiskWeatherContext(BaseModel):
    available: bool
    calendar_year: int | None
    alignment_method: str
    full_season_alignment_verified: bool
    temporal_semantics: str
    weather_values: dict[str, float | None]
    quality_flags: dict[str, bool | None]
    weather_coverage_pct: float | None
    nearest_grid_distance_km: float | None
    mapping_quality: str
    dataset_provenance: dict[str, Any]
    apy_weather_integration_provenance: dict[str, Any]


class RiskDataQuality(BaseModel):
    these_flags_do_not_change_notebook_20_eligibility: bool


class RiskIndicatorRecord(RiskAnomalyRecord):
    weather_context: RiskWeatherContext
    data_quality: RiskDataQuality


class RiskIndicatorSummary(BaseModel):
    window_start_year: int | None
    window_end_year: int | None
    observation_count: int
    high_concern_count: int
    moderate_concern_count: int
    extreme_deviation_count: int
    high_concern_pct: float | None
    moderate_concern_pct: float | None
    high_concern_years: list[int]
    persistence_indicator: str
    evidence_status: str
    definition: str


class RiskIndicatorsResponse(BaseModel):
    state: str
    district: str
    crop: str
    season: str
    page: int
    page_size: int
    total: int
    records: list[RiskIndicatorRecord]
    historical_pattern_summary: RiskIndicatorSummary
    methodology: dict[str, Any]
    dataset_provenance: RiskDatasetProvenance
    limitations: list[str]
    interpretation: str


class RiskCropAreaShare(BaseModel):
    crop: str
    area: float
    area_unit: str
    share: float
    share_pct: float


class RiskDiversificationResponse(BaseModel):
    state: str
    district: str
    season: str
    year_start: int
    agricultural_year: str
    crop_category: str
    source_record_count: int
    source_quality_flagged_record_count: int
    positive_area_crop_count: int
    positive_area_record_count: int
    excluded_missing_zero_or_negative_area_record_count: int
    total_comparable_area: float | None
    area_unit: str
    crop_area_shares: list[RiskCropAreaShare]
    herfindahl_hirschman_index: float | None
    hhi_formula: str
    methodology_source: str
    interpretation: str
    dataset_provenance: RiskDatasetProvenance
    limitations: list[str]


class RiskDistrictBenchmark(BaseModel):
    district: str
    benchmark_year: int
    agricultural_year: str
    current_year_yield: float
    yield_unit: str
    historical_window_start: int
    historical_window_end: int
    valid_historical_observation_count: int
    quality_flagged_historical_observation_count: int
    historical_mean_yield: float
    historical_median_yield: float
    sample_standard_deviation: float | None
    coefficient_of_variation_pct: float | None
    historical_years: list[int]
    coverage_pct_of_window: float


class RiskBenchmarkingResponse(BaseModel):
    state: str
    crop: str
    season: str
    benchmark_year_start: int
    through_year_start: int
    comparison_group: str
    district_count: int
    districts: list[RiskDistrictBenchmark]
    districts_ranked: bool
    historical_calculation: str
    dataset_provenance: RiskDatasetProvenance
    limitations: list[str]


class RiskCoverageLocation(BaseModel):
    state: str
    district: str
    individual_crop_records: int
    valid_positive_yield_records: int
    positive_area_records: int
    matched_weather_records: int
    weather_unavailable_records: int


class RiskCoverageResponse(BaseModel):
    page: int
    page_size: int
    total_locations: int
    locations: list[RiskCoverageLocation]
    year_start: int
    year_end: int
    dataset_provenance: RiskDatasetProvenance
    limitations: list[str]


class YieldOptionsResponse(BaseModel):
    crops: list[str]
    seasons: list[str]
    crop_categories: list[str]
    states: list[str]
    districts_by_state: dict[str, list[str]]
    year_start: int
    year_end: int
    year_range_type: Literal["training_with_extrapolation"]
    category_label_basis: str
    location_pair_basis: str
    target_unit: str
    target_unit_status: Literal["verified", "verification_pending"]
    target_semantics: str
    target_unit_source: str
    target_unit_source_url: str
    target_conversion_applied: Literal[False]
    limitations: list[str]


class YieldDataProvenance(BaseModel):
    dataset_source: str
    target_field: str
    target_definition: str
    target_construction: str
    target_consistency_check: str
    unit_source: str
    unit_source_url: str
    unit_source_section: str
    unit_verification_status: Literal["verified", "verification_pending"]
    numerical_conversion_applied: bool


class YieldPredictionResponse(BaseModel):
    crop: str
    season: str
    crop_category: str
    state: str
    district: str
    prediction_year: int
    prediction_period_status: Literal[
        "in_training_range",
        "out_of_training_range_extrapolation",
    ]
    prediction: float
    target: str
    unit: str
    model_name: str
    model_version: str | None
    model_version_status: Literal["recorded", "not_recorded"]
    artifact_sha256: str
    training_year_start: int
    training_year_end: int
    quality_status: Literal["experimental"]
    production_approved: bool
    data_provenance: YieldDataProvenance
    limitations: list[str]


class YieldPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop: StrictStr = Field(min_length=1, max_length=128)
    season: StrictStr = Field(min_length=1, max_length=64)
    crop_category: StrictStr = Field(min_length=1, max_length=128)
    state: StrictStr = Field(min_length=1, max_length=128)
    district: StrictStr = Field(min_length=1, max_length=128)
    year_start: StrictInt = Field(ge=1, le=9999)

    @field_validator("crop", "season", "crop_category", "state", "district")
    @classmethod
    def require_unpadded_text(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("Text values must be non-empty and unpadded.")
        return value

    @field_validator("season")
    @classmethod
    def reject_aggregate_season(cls, value: str) -> str:
        if value.casefold() == "total":
            raise ValueError("Aggregate Total season is not accepted.")
        return value


class WeatherAgricultureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop: StrictStr = Field(min_length=1, max_length=128)
    season: StrictStr = Field(min_length=1, max_length=64)
    state: StrictStr | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("crop", "season", "state")
    @classmethod
    def require_unpadded_text(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or value != value.strip()):
            raise ValueError("Text values must be non-empty and unpadded.")
        return value

    @field_validator("season")
    @classmethod
    def require_named_season(cls, value: str) -> str:
        if value not in {"Kharif", "Rabi", "Summer"}:
            raise ValueError("Season must be Kharif, Rabi, or Summer.")
        return value


class WeatherAgricultureOptionsResponse(BaseModel):
    crops: list[str]
    states: list[str]
    seasons: list[str]
    apy_year_start: int
    latest_apy_year: int
    weather_year_start: int
    weather_year_end: int
    weather_source: str
    available_calendar_mappings: list[dict[str, str]]
    limitations: list[str]


class CropRegionYieldEvidence(BaseModel):
    rank: int | None
    state: str
    district: str
    ranking_basis: str
    historical_median_yield: float | None
    historical_mean_yield: float | None
    recent_five_year_median_yield: float | None
    yield_standard_deviation: float | None
    coefficient_of_variation: float | None
    valid_observation_count: int
    valid_observation_year_count: int
    valid_observation_years: list[int]
    latest_observation_year: int | None
    recent_observation_year_count: int
    recent_window_year_start: int
    recent_window_year_end: int
    evidence_quality: Literal["insufficient", "limited", "moderate", "strong"]
    ranking_status: Literal[
        "ranked",
        "no_recent_observation",
        "insufficient_comparison_set",
    ]
    evidence_explanation: str
    unit: str


class CropCalendarProvenance(BaseModel):
    mapping_id: str
    version: str
    classification: Literal["normal_calendar_proxy"]
    source: str
    source_url: str
    applicable_state: str
    crop: str
    season: str
    recommended_nursery_sowing_window: str
    recommended_transplanting_window: str
    crop_duration_after_transplant_days: list[int]
    weather_window_start: str
    weather_window_end: str
    assumptions: list[str]
    limitations: list[str]


class WeatherGridProvenance(BaseModel):
    mapping_status: Literal["matched", "unmatched"]
    apy_geography_id: str | None
    coordinate_source: str | None
    geography_confidence: str | None
    grid_latitude: float | None
    grid_longitude: float | None
    mapping_distance_km: float | None
    long_distance_flag: bool | None
    shared_grid_district_count: int | None


class MonthlyPrecipitationProfile(BaseModel):
    month: int
    median_total_mm: float | None
    median_share_percent: float | None


class MonthlyPrecipitationYearProfile(BaseModel):
    month: int
    total_mm: float | None
    share_percent: float | None


class WeatherAgricultureYearProfile(BaseModel):
    year: int
    complete_window: bool
    expected_days: int
    complete_days: int
    precipitation_valid_days: int
    tmax_valid_days: int
    tmin_valid_days: int
    seasonal_total_precipitation_mm: float | None
    mean_daily_precipitation_mm: float | None
    maximum_daily_precipitation_mm: float | None
    daily_precipitation_standard_deviation_mm: float | None
    mean_daily_tmax_c: float | None
    mean_daily_tmin_c: float | None
    monthly_precipitation: list[MonthlyPrecipitationYearProfile]


class CropRegionWeatherProfile(BaseModel):
    available: bool
    status: Literal[
        "available",
        "calendar_unavailable",
        "geography_unmatched",
        "no_complete_weather_year",
        "features_unavailable",
    ]
    unavailable_reason: str | None
    calendar: CropCalendarProvenance | None
    grid: WeatherGridProvenance
    source: str
    expected_year_count: int
    complete_year_count: int
    matched_apy_years: list[int]
    complete_weather_years: list[int]
    median_seasonal_total_precipitation_mm: float | None
    median_mean_daily_precipitation_mm: float | None
    maximum_daily_precipitation_mm: float | None
    median_daily_precipitation_standard_deviation_mm: float | None
    interannual_seasonal_precipitation_standard_deviation_mm: float | None
    interannual_seasonal_precipitation_cv: float | None
    median_mean_daily_tmax_c: float | None
    median_mean_daily_tmin_c: float | None
    monthly_precipitation: list[MonthlyPrecipitationProfile]
    rainy_day_count: None = None
    dry_spell_count: None = None
    extreme_temperature_day_count: None = None
    threshold_status: str
    year_profiles: list[WeatherAgricultureYearProfile]
    limitations: list[str]


class CropRegionEvidenceResponse(BaseModel):
    crop: str
    season: str
    state_filter: str | None
    ranking_basis: str
    ranking_available: bool
    data_period_start: int
    latest_available_apy_year: int
    recent_window_year_start: int
    recent_window_year_end: int
    ranked_district_count: int
    unranked_district_count: int
    candidates: list[CropRegionYieldEvidence]
    weather_profiles: dict[str, CropRegionWeatherProfile]
    data_source: str
    apy_source_file: str
    apy_sha256: str
    weather_source: str
    weather_feature_dataset: str
    weather_feature_sha256: str | None
    limitations: list[str]


class CropRankingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    season: StrictStr = Field(min_length=1, max_length=64)
    state: StrictStr = Field(min_length=1, max_length=128)
    district: StrictStr = Field(min_length=1, max_length=128)
    top_n: StrictInt = Field(default=5, ge=1, le=5)
    ranking_basis: Literal["recent_median", "historical_median"] = "recent_median"

    @field_validator("season", "state", "district")
    @classmethod
    def require_unpadded_text(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("Text values must be non-empty and unpadded.")
        return value

    @field_validator("season")
    @classmethod
    def reject_aggregate_season(cls, value: str) -> str:
        if value not in {"Kharif", "Rabi", "Summer"}:
            raise ValueError("Season must be Kharif, Rabi, or Summer.")
        return value


class APYDataProvenance(BaseModel):
    dataset_name: str
    dataset_source: str
    source_file: str
    sha256: str
    record_count: int
    valid_record_count: int
    year_start: int
    year_end: int
    yield_unit: str


class CropRankingOptionsResponse(BaseModel):
    crops: list[str]
    states: list[str]
    districts: list[str]
    seasons: list[str]
    agricultural_years: list[int]
    selected_state: str | None
    selected_district: str | None
    selected_season: str | None
    data_provenance: APYDataProvenance
    limitations: list[str]


class CropHistoricalStatistics(BaseModel):
    crop: str
    historical_median_yield: float | None
    historical_mean_yield: float | None
    recent_median_yield: float | None
    recent_window_year_start: int
    recent_window_year_end: int
    yield_standard_deviation: float | None
    coefficient_of_variation: float | None
    historical_trend_yield_per_year: float | None
    valid_observation_count: int
    valid_year_count: int
    latest_observation_year: int | None
    valid_years: list[int]
    recent_valid_year_count: int
    recent_year_coverage: float
    evidence_quality: str
    unit: str


class CropComparisonCoverage(BaseModel):
    year_start: int
    year_label: str
    valid_observation_count: int
    candidate_count: int
    comparable: bool


class CropComparisonResponse(BaseModel):
    state: str
    district: str
    season: str
    through_year_start: int
    crops: list[CropHistoricalStatistics]
    comparison_group_coverage: list[CropComparisonCoverage]
    data_provenance: APYDataProvenance
    limitations: list[str]


class CropCandidateEligibility(BaseModel):
    eligible: bool
    reason_code: str
    evidence_quality: str
    valid_observation_count: int
    valid_year_count: int


class RankedCropCandidate(BaseModel):
    crop: str
    rank: int | None
    observed_yield: float | None
    predicted_yield: float | None
    unit: str
    ranking_value: float | None
    ranking_basis: str
    evidence_rank: int | None
    model_reference_year: int | None
    model_prediction_period_status: str | None
    model_difference_from_median: float | None
    has_observation_in_latest_year: bool
    warnings: list[str] = []
    candidate_eligibility: CropCandidateEligibility
    historical_statistics: CropHistoricalStatistics


class CropRankingModelProvenance(BaseModel):
    model_name: str
    model_version: str | None
    artifact_sha256: str
    target: str
    unit: str
    training_year_start: int
    training_year_end: int
    prediction_period_status: Literal[
        "in_training_range",
        "out_of_training_range_extrapolation",
    ]
    reference_year: int
    reference_year_policy: str
    quality_status: Literal["experimental"]
    production_approved: bool
    limitations: list[str]


class CropRankingResponse(BaseModel):
    state: str
    district: str
    season: str
    crop_category: str
    data_period_start: int
    latest_data_year: int
    ranking_basis: str
    top_n: int
    reference_year: int
    agricultural_year_start: int
    agricultural_year_label: str | None
    ranking_available: bool
    ranked_candidate_count: int
    eligible_candidate_count: int
    candidates: list[RankedCropCandidate]
    ranking_methodology: str
    ranking_model: CropRankingModelProvenance
    data_provenance: APYDataProvenance
    limitations: list[str]


class CropTrendObservation(BaseModel):
    year_start: int
    year_label: str
    area: float
    production: float
    yield_value: float
    unit: str


class CropTrendResponse(BaseModel):
    state: str
    district: str
    season: str
    through_year_start: int
    statistics: CropHistoricalStatistics
    observations: list[CropTrendObservation]
    data_provenance: APYDataProvenance
    limitations: list[str]


class CropEvidenceResponse(BaseModel):
    state: str
    district: str
    season: str
    through_year_start: int
    statistics: CropHistoricalStatistics
    source_observation_count: int
    valid_observation_count: int
    excluded_observation_count: int
    observations: list[CropTrendObservation]
    data_provenance: APYDataProvenance
    limitations: list[str]


class ErrorDetail(BaseModel):
    location: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail]
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant", "system"]
    content: StrictStr = Field(min_length=1, max_length=2000)


class LocationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str | None = None
    district: str | None = None


class SourceCitationSchema(BaseModel):
    source_id: str
    title: str
    source_type: str
    dataset_or_model: str
    observation_or_training_period: str
    metrics_and_units: str
    evidence_status: str
    limitations: list[str] = Field(default_factory=list)


class AssistantChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: StrictStr = Field(min_length=1, max_length=1000)
    preferred_language: Literal["en", "hi", "auto"] = "auto"
    conversation_context: list[ChatMessage] | None = Field(default=None, max_length=6)
    location_context: LocationContext | None = None


class AssistantChatResponse(BaseModel):
    answer: str
    language: Literal["en", "hi"]
    status: Literal["answered", "abstained", "unavailable", "error"]
    sources: list[SourceCitationSchema]
    tools_used: list[str]
    suggested_followups: list[str]
    limitations: list[str]
    request_id: str


class AssistantStatusResponse(BaseModel):
    status: Literal["ready", "provider_unconfigured", "provider_unavailable"]
    provider: str
    model: str | None
    capabilities: list[str]
    supported_languages: list[str]
    limitations: list[str]


class AssistantSuggestionsResponse(BaseModel):
    suggestions: list[dict[str, str]]


class ExperimentalForecastOptionsResponse(BaseModel):
    model_id: str
    model_name: str
    model_version: str
    experimental_status: str
    crops: list[str]
    seasons: list[str]
    states: list[str]
    districts_by_state: dict[str, list[str]]
    valid_horizons: list[int]
    latest_observation_year: int
    training_cutoff_year: int
    reference_year: int
    eligibility_rules: dict[str, str]
    unit: str
    unit_status: Literal["verified", "verification_pending"]
    research_mae_by_horizon: dict[str, float]
    limitations: list[str]


class ExperimentalForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop: StrictStr = Field(min_length=1, max_length=128)
    season: StrictStr = Field(min_length=1, max_length=64)
    state: StrictStr = Field(min_length=1, max_length=128)
    district: StrictStr = Field(min_length=1, max_length=128)
    horizon: StrictInt = Field(ge=1, le=5)

    @field_validator("crop", "season", "state", "district")
    @classmethod
    def require_unpadded_text(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("Text values must be non-empty and unpadded.")
        return value

    @field_validator("season")
    @classmethod
    def reject_aggregate_season(cls, value: str) -> str:
        if value.casefold() == "total":
            raise ValueError("Aggregate Total season is not accepted.")
        return value


class ExperimentalForecastProvenance(BaseModel):
    model_id: str
    model_name: str
    model_version: str
    strategy: str
    base_model: str
    cohort: str
    artifact_sha256: str
    metadata_sha256: str
    training_cutoff_year: int
    latest_observation_year: int
    reference_year: int
    target: str
    target_unit: str
    target_unit_status: Literal["verified", "verification_pending"]
    target_unit_source: str
    target_unit_source_url: str
    design_width: int
    numeric_features: list[str]
    research_expanding_window_mae: dict[str, float]
    research_expanding_window_r2: dict[str, float]


class ExperimentalForecastResponse(BaseModel):
    crop: str
    season: str
    state: str
    district: str
    horizon: int
    origin_year: int
    target_year: int
    predicted_yield: float
    unit: str
    unit_status: Literal["verified", "verification_pending"]
    history_count: int
    eligibility_status: Literal[
        "eligible_experimental",
        "eligible_high_horizon_restricted",
    ]
    future_projection: bool
    target_year_status: Literal[
        "target_already_observed",
        "target_in_past_or_present",
        "future_target_beyond_latest_data",
    ]
    experimental_status: str
    quality_status: Literal["experimental"]
    production_approved: Literal[False]
    provenance: ExperimentalForecastProvenance
    limitations: list[str]
    warnings: list[str]
