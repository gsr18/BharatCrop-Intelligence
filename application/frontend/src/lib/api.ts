export type Capability = {
  name: string;
  status: string;
  reason_code: string;
  reason_codes: string[];
  availability: "available" | "unavailable";
  execution_available?: boolean;
  quality_status:
    | "experimental"
    | "validated"
    | "research_notebook_generated"
    | "not_implemented"
    | "unavailable";
  evidence_quality?: string;
  production_approved: boolean;
  limitations: string[];
};

export type CapabilitiesResponse = { capabilities: Capability[] };
export type ServiceInfo = { service: string; api_version: string };
export type HealthResponse = { status: string; request_id: string };
export type ReadinessResponse = {
  status: string;
  checks: Record<string, string>;
  request_id: string;
};

export type YieldRequest = {
  crop: string;
  season: string;
  crop_category: string;
  state: string;
  district: string;
  year_start: number;
};

export type CropRankingRequest = {
  state: string;
  district: string;
  season: string;
  top_n?: number;
  ranking_basis?: "recent_median" | "historical_median";
};

export type YieldOptions = {
  crops: string[];
  seasons: string[];
  crop_categories: string[];
  states: string[];
  districts_by_state: Record<string, string[]>;
  year_start: number;
  year_end: number;
  year_range_type: "training_with_extrapolation";
  category_label_basis: string;
  location_pair_basis: string;
  target_unit: string;
  target_unit_status: "verified" | "verification_pending";
  target_semantics: string;
  target_unit_source: string;
  target_unit_source_url: string;
  target_conversion_applied: false;
  limitations: string[];
};

export type YieldDataProvenance = {
  dataset_source: string;
  target_field: string;
  target_definition: string;
  target_construction: string;
  target_consistency_check: string;
  unit_source: string;
  unit_source_url: string;
  unit_source_section: string;
  unit_verification_status: "verified" | "verification_pending";
  numerical_conversion_applied: boolean;
};

export type YieldPredictionResponse = {
  crop: string;
  season: string;
  crop_category: string;
  state: string;
  district: string;
  prediction_year: number;
  prediction_period_status:
    "in_training_range" | "out_of_training_range_extrapolation";
  prediction: number;
  target: string;
  unit: string;
  model_name: string;
  model_version: string | null;
  model_version_status: "recorded" | "not_recorded";
  artifact_sha256: string;
  training_year_start: number;
  training_year_end: number;
  quality_status: "experimental";
  production_approved: boolean;
  data_provenance: YieldDataProvenance;
  limitations: string[];
};

export type APYDataProvenance = {
  dataset_name: string;
  dataset_source: string;
  source_file: string;
  sha256: string;
  record_count: number;
  valid_record_count: number;
  year_start: number;
  year_end: number;
  yield_unit: string;
};

export type CropHistoricalStatistics = {
  crop: string;
  historical_median_yield: number | null;
  historical_mean_yield: number | null;
  recent_median_yield: number | null;
  recent_window_year_start: number;
  recent_window_year_end: number;
  yield_standard_deviation: number | null;
  coefficient_of_variation: number | null;
  historical_trend_yield_per_year: number | null;
  valid_observation_count: number;
  valid_year_count: number;
  latest_observation_year: number | null;
  valid_years: number[];
  recent_valid_year_count: number;
  recent_year_coverage: number;
  evidence_quality: string;
  unit: string;
};

export type CropRankingOptionsResponse = {
  crops: string[];
  states: string[];
  districts: string[];
  seasons: string[];
  agricultural_years: number[];
  selected_state: string | null;
  selected_district: string | null;
  selected_season: string | null;
  data_provenance: APYDataProvenance;
  limitations: string[];
};

export type CropCandidateEligibility = {
  eligible: boolean;
  reason_code: string;
  evidence_quality: string;
  valid_observation_count: number;
  valid_year_count: number;
};

export type RankedCropCandidate = {
  crop: string;
  rank: number | null;
  observed_yield: number | null;
  predicted_yield: number | null;
  unit: string;
  ranking_value: number | null;
  ranking_basis: string;
  evidence_rank: number | null;
  model_reference_year: number | null;
  model_prediction_period_status: string | null;
  model_difference_from_median: number | null;
  has_observation_in_latest_year: boolean;
  warnings: string[];
  candidate_eligibility: CropCandidateEligibility;
  historical_statistics: CropHistoricalStatistics;
};

export type CropRankingModelProvenance = {
  model_name: string;
  model_version: string | null;
  artifact_sha256: string;
  target: string;
  unit: string;
  training_year_start: number;
  training_year_end: number;
  prediction_period_status:
    "in_training_range" | "out_of_training_range_extrapolation";
  reference_year: number;
  reference_year_policy: string;
  quality_status: "experimental";
  production_approved: boolean;
  limitations: string[];
};

export type CropRankingResponse = {
  state: string;
  district: string;
  season: string;
  crop_category: string;
  data_period_start: number;
  latest_data_year: number;
  ranking_basis: string;
  top_n: number;
  reference_year: number;
  agricultural_year_start: number;
  agricultural_year_label: string | null;
  ranking_available: boolean;
  ranked_candidate_count: number;
  eligible_candidate_count: number;
  candidates: RankedCropCandidate[];
  ranking_methodology: string;
  ranking_model: CropRankingModelProvenance;
  data_provenance: APYDataProvenance;
  limitations: string[];
};

export type CropComparisonCoverage = {
  year_start: number;
  year_label: string;
  valid_observation_count: number;
  candidate_count: number;
  comparable: boolean;
};

export type CropComparisonResponse = {
  state: string;
  district: string;
  season: string;
  through_year_start: number;
  crops: CropHistoricalStatistics[];
  comparison_group_coverage: CropComparisonCoverage[];
  data_provenance: APYDataProvenance;
  limitations: string[];
};

export type CropTrendObservation = {
  year_start: number;
  year_label: string;
  area: number;
  production: number;
  yield_value: number;
  unit: string;
};

export type CropTrendResponse = {
  state: string;
  district: string;
  season: string;
  through_year_start: number;
  statistics: CropHistoricalStatistics;
  observations: CropTrendObservation[];
  data_provenance: APYDataProvenance;
  limitations: string[];
};

export type CropEvidenceResponse = CropTrendResponse & {
  source_observation_count: number;
  valid_observation_count: number;
  excluded_observation_count: number;
};

export class ApiError extends Error {
  constructor(
    readonly code:
      "network" | "unavailable" | "validation" | "request" | "invalid-response",
    readonly status?: number,
    readonly backendMessage?: string,
  ) {
    super(code);
    this.name = "ApiError";
  }
}
export type ApiErrorCode = ApiError["code"];

export type ExperimentalForecastRequest = {
  crop: string;
  season: string;
  state: string;
  district: string;
  horizon: number;
};

export type ExperimentalForecastProvenance = {
  model_id: string;
  model_name: string;
  model_version: string;
  strategy: string;
  base_model: string;
  cohort: string;
  artifact_sha256: string;
  metadata_sha256: string;
  training_cutoff_year: number;
  latest_observation_year: number;
  reference_year: number;
  target: string;
  target_unit: string;
  target_unit_status: "verified" | "verification_pending";
  target_unit_source: string;
  target_unit_source_url: string;
  design_width: number;
  numeric_features: string[];
  research_expanding_window_mae: Record<string, number>;
  research_expanding_window_r2: Record<string, number>;
};

export type ExperimentalForecastOptions = {
  model_id: string;
  model_name: string;
  model_version: string;
  experimental_status: string;
  crops: string[];
  seasons: string[];
  states: string[];
  districts_by_state: Record<string, string[]>;
  valid_horizons: number[];
  latest_observation_year: number;
  training_cutoff_year: number;
  reference_year: number;
  eligibility_rules: Record<string, string>;
  unit: string;
  unit_status: "verified" | "verification_pending";
  research_mae_by_horizon: Record<string, number>;
  limitations: string[];
};

export type ExperimentalForecastResponse = {
  crop: string;
  season: string;
  state: string;
  district: string;
  horizon: number;
  origin_year: number;
  target_year: number;
  predicted_yield: number;
  unit: string;
  unit_status: "verified" | "verification_pending";
  history_count: number;
  eligibility_status:
    "eligible_experimental" | "eligible_high_horizon_restricted";
  future_projection: boolean;
  target_year_status:
    | "target_already_observed"
    | "target_in_past_or_present"
    | "future_target_beyond_latest_data";
  experimental_status: string;
  quality_status: "experimental";
  production_approved: false;
  provenance: ExperimentalForecastProvenance;
  limitations: string[];
  warnings: string[];
};
export type ApiRecord = Record<string, unknown>;
export type ApiFilters = Record<string, string | number | undefined>;

export type WeatherMlHorizonStatus = {
  horizon: number;
  label: string;
  status: string;
  classifier_artifact: string | null;
  amount_regressor_artifact: string | null;
  reason_code: string | null;
};

export type WeatherMlInputStatus = {
  provider: string;
  forecast_available: boolean;
  latest_available_input_date: string | null;
  required_variables: string[];
  frequency: string;
  reason_code: string;
  message: string;
};

export type WeatherMlStatusResponse = {
  task: string;
  status: string;
  forecast_available: boolean;
  reason_code: string;
  production_approved: boolean;
  model_directories: string[];
  feature_specification: ApiRecord;
  predictor_count: number;
  horizons: WeatherMlHorizonStatus[];
  input: WeatherMlInputStatus;
  dataset: ApiRecord;
  limitations: string[];
};

export type WeatherMlForecastRequest = {
  latitude: number;
  longitude: number;
  as_of_date?: string;
  horizons?: number[];
};

export type WeatherMlForecastResponse = {
  task: string;
  forecast_available: boolean;
  status: string;
  reason_code: string;
  message: string;
  latitude: number;
  longitude: number;
  as_of_date: string | null;
  latest_available_input_date: string | null;
  required_input_variables: string[];
  horizons: WeatherMlHorizonStatus[];
  dataset: ApiRecord;
  limitations: string[];
};

export type WeatherMlDistrictOption = {
  state: string;
  district: string;
  apy_geography_id: string;
  matched_boundary_name: string;
  intersecting_cell_count: number;
  valid_cell_count: number;
};

export type WeatherMlDistrictOptionsResponse = {
  task: string;
  forecast_origin_date: string;
  archive_end_date: string | null;
  supported_district_count: number;
  states: string[];
  districts_by_state: Record<string, string[]>;
  districts: WeatherMlDistrictOption[];
  aggregation_method: string;
  weight_field: string;
  limitations: string[];
};

export type WeatherMlDistrictForecastRequest = {
  state: string;
  district: string;
  horizons?: number[];
};

export type WeatherMlDistrictGridCell = {
  cell_id: string;
  latitude: number;
  longitude: number;
  intersection_area_km2: number;
};

export type WeatherMlDistrictHorizonForecast = {
  horizon: number;
  label: string;
  target_date: string;
  expected_precipitation_mm_day: number;
  wet_probability: number;
  conditional_wet_amount_mm_day: number;
  min_cell_expected_mm_day: number;
  max_cell_expected_mm_day: number;
  cell_count: number;
};

export type WeatherMlDistrictForecastResponse = {
  task: string;
  forecast_available: boolean;
  status: string;
  reason_code: string;
  message: string;
  notice: string;
  state: string;
  district: string;
  apy_geography_id: string | null;
  matched_boundary_name: string | null;
  forecast_origin_date: string;
  archive_end_date: string | null;
  forecast_dates: string[];
  spatial: ApiRecord;
  grid_cells: WeatherMlDistrictGridCell[];
  horizons: WeatherMlDistrictHorizonForecast[];
  model: ApiRecord;
  limitations: string[];
};
export type YieldScenarioRequest = {
  crop: string;
  season: string;
  crop_category: string;
  state: string;
  district: string;
  years: number[];
};
export type AssistantChatRequest = {
  message: string;
  preferred_language: "en" | "hi" | "auto";
  conversation_context?: Array<{
    role: "user" | "assistant" | "system";
    content: string;
  }>;
  location_context?: { state?: string; district?: string };
};

function isInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

function isYieldOptions(value: unknown): value is YieldOptions {
  if (!value || typeof value !== "object") return false;
  const options = value as Partial<YieldOptions>;
  const isStringArray = (items: unknown): items is string[] =>
    Array.isArray(items) &&
    items.length > 0 &&
    items.every((item) => typeof item === "string" && item.length > 0);
  const districts = options.districts_by_state;
  return (
    isStringArray(options.crops) &&
    isStringArray(options.seasons) &&
    isStringArray(options.crop_categories) &&
    isStringArray(options.states) &&
    !!districts &&
    typeof districts === "object" &&
    !Array.isArray(districts) &&
    Object.values(districts).every(isStringArray) &&
    options.states.every(
      (state) =>
        Object.hasOwn(districts, state) && isStringArray(districts[state]),
    ) &&
    isInteger(options.year_start) &&
    isInteger(options.year_end) &&
    options.year_start <= options.year_end &&
    options.year_range_type === "training_with_extrapolation" &&
    typeof options.category_label_basis === "string" &&
    typeof options.location_pair_basis === "string" &&
    typeof options.target_semantics === "string" &&
    options.target_unit === "kg/ha" &&
    (options.target_unit_status === "verified" ||
      options.target_unit_status === "verification_pending") &&
    typeof options.target_unit_source === "string" &&
    typeof options.target_unit_source_url === "string" &&
    options.target_unit_source_url.startsWith("https://") &&
    options.target_conversion_applied === false &&
    Array.isArray(options.limitations) &&
    options.limitations.every((limitation) => typeof limitation === "string")
  );
}

function isYieldPrediction(value: unknown): value is YieldPredictionResponse {
  if (!value || typeof value !== "object") return false;
  const result = value as Partial<YieldPredictionResponse>;
  return (
    typeof result.prediction === "number" &&
    Number.isFinite(result.prediction) &&
    typeof result.target === "string" &&
    typeof result.unit === "string" &&
    result.unit.trim().length > 0 &&
    typeof result.crop === "string" &&
    typeof result.season === "string" &&
    typeof result.crop_category === "string" &&
    typeof result.state === "string" &&
    typeof result.district === "string" &&
    isInteger(result.prediction_year) &&
    isInteger(result.training_year_start) &&
    isInteger(result.training_year_end) &&
    (result.prediction_period_status === "in_training_range" ||
      result.prediction_period_status ===
        "out_of_training_range_extrapolation") &&
    (result.prediction_period_status === "in_training_range"
      ? result.prediction_year >= result.training_year_start &&
        result.prediction_year <= result.training_year_end
      : result.prediction_year < result.training_year_start ||
        result.prediction_year > result.training_year_end) &&
    typeof result.model_name === "string" &&
    (typeof result.model_version === "string" ||
      result.model_version === null) &&
    (result.model_version_status === "recorded" ||
      result.model_version_status === "not_recorded") &&
    (result.model_version_status === "not_recorded"
      ? result.model_version === null
      : typeof result.model_version === "string") &&
    result.target === "Yield" &&
    result.unit === "kg/ha" &&
    typeof result.artifact_sha256 === "string" &&
    /^[0-9a-f]{64}$/i.test(result.artifact_sha256) &&
    result.quality_status === "experimental" &&
    typeof result.production_approved === "boolean" &&
    !!result.data_provenance &&
    typeof result.data_provenance.dataset_source === "string" &&
    typeof result.data_provenance.target_field === "string" &&
    typeof result.data_provenance.target_definition === "string" &&
    typeof result.data_provenance.target_construction === "string" &&
    typeof result.data_provenance.target_consistency_check === "string" &&
    typeof result.data_provenance.unit_source === "string" &&
    typeof result.data_provenance.unit_source_url === "string" &&
    result.data_provenance.unit_source_url.startsWith("https://") &&
    result.data_provenance.unit_source_section ===
      "4.10.5 Agricultural Productivity" &&
    (result.data_provenance.unit_verification_status === "verified" ||
      result.data_provenance.unit_verification_status ===
        "verification_pending") &&
    result.data_provenance.numerical_conversion_applied === false &&
    Array.isArray(result.limitations) &&
    result.limitations.every((limitation) => typeof limitation === "string")
  );
}

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(
  /\/+$/,
  "",
);
let capabilitiesRequest: Promise<CapabilitiesResponse> | undefined;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch {
    throw new ApiError("network");
  }

  if (!response.ok) {
    const backendMessage = await responseErrorMessage(response);
    if (response.status === 503) {
      throw new ApiError("unavailable", response.status, backendMessage);
    }
    if (response.status === 422) {
      throw new ApiError("validation", response.status, backendMessage);
    }
    throw new ApiError("request", response.status, backendMessage);
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError("invalid-response", response.status);
  }
}

function isRecord(value: unknown): value is ApiRecord {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

async function responseErrorMessage(
  response: Response,
): Promise<string | undefined> {
  try {
    const payload: unknown = await response.clone().json();
    if (!isRecord(payload)) return undefined;
    const error = isRecord(payload.error) ? payload.error : payload;
    const message =
      typeof error.message === "string"
        ? error.message
        : typeof error.detail === "string"
          ? error.detail
          : undefined;
    const details = Array.isArray(error.details)
      ? error.details
          .map((item) => {
            if (typeof item === "string") return item;
            if (!isRecord(item)) return undefined;
            return typeof item.msg === "string"
              ? item.msg
              : typeof item.message === "string"
                ? item.message
                : undefined;
          })
          .filter((item): item is string => !!item)
      : [];
    const requestId =
      typeof error.request_id === "string"
        ? error.request_id
        : typeof payload.request_id === "string"
          ? payload.request_id
          : undefined;
    const parts = [message, ...details];
    if (requestId) parts.push(`Request ID: ${requestId}`);
    return (
      parts.filter((part): part is string => !!part).join(" ") || undefined
    );
  } catch {
    return undefined;
  }
}

async function requestRecord(
  path: string,
  init?: RequestInit,
): Promise<ApiRecord> {
  const value = await request<unknown>(path, init);
  if (!isRecord(value)) throw new ApiError("invalid-response");
  return value;
}

function withQuery(path: string, filters: ApiFilters = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && String(value).trim() !== "") {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export const api = {
  info: () => request<ServiceInfo>("/api/v1/info"),
  capabilities: () => {
    capabilitiesRequest ??= request<CapabilitiesResponse>(
      "/api/v1/capabilities",
    ).catch((error: unknown) => {
      capabilitiesRequest = undefined;
      throw error;
    });
    return capabilitiesRequest;
  },
  refreshCapabilities: () => {
    capabilitiesRequest = undefined;
    return api.capabilities();
  },
  live: () => request<HealthResponse>("/health/live"),
  ready: () => request<ReadinessResponse>("/health/ready"),
  yieldOptions: async () => {
    const options = await request<unknown>("/api/v1/predictions/yield/options");
    if (!isYieldOptions(options)) {
      throw new ApiError("invalid-response");
    }
    return options;
  },
  predictYield: async (body: YieldRequest) => {
    const result = await request<unknown>("/api/v1/predictions/yield", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (!isYieldPrediction(result)) throw new ApiError("invalid-response");
    return result;
  },
  experimentalForecastOptions: async () => {
    const options = await request<ExperimentalForecastOptions>(
      "/api/v1/predictions/yield/forecast/options",
    );
    if (
      !options ||
      typeof options !== "object" ||
      !Array.isArray(options.crops) ||
      !Array.isArray(options.states)
    ) {
      throw new ApiError("invalid-response");
    }
    return options;
  },
  forecastYieldExperimental: async (body: ExperimentalForecastRequest) => {
    const result = await request<ExperimentalForecastResponse>(
      "/api/v1/predictions/yield/forecast",
      { method: "POST", body: JSON.stringify(body) },
    );
    if (
      !result ||
      typeof result !== "object" ||
      typeof result.predicted_yield !== "number" ||
      !Number.isFinite(result.predicted_yield)
    ) {
      throw new ApiError("invalid-response");
    }
    return result;
  },
  rankCrops: (body: CropRankingRequest) =>
    requestRecord("/api/v1/rankings/crops", {
      method: "POST",
      body: JSON.stringify(body),
    }) as Promise<CropRankingResponse>,
  cropRankingOptions: (filters?: ApiFilters) =>
    requestRecord(
      withQuery("/api/v1/rankings/crops/options", filters),
    ) as Promise<CropRankingOptionsResponse>,
  cropComparison: (filters?: ApiFilters) =>
    requestRecord(
      withQuery("/api/v1/rankings/crops/comparison", filters),
    ) as Promise<CropComparisonResponse>,
  cropTrend: (crop: string, filters?: ApiFilters) =>
    requestRecord(
      withQuery(
        `/api/v1/rankings/crops/history/${encodeURIComponent(crop)}/trend`,
        filters,
      ),
    ),
  cropEvidence: (crop: string, filters?: ApiFilters) =>
    requestRecord(
      withQuery(
        `/api/v1/rankings/crops/history/${encodeURIComponent(crop)}/evidence`,
        filters,
      ),
    ) as Promise<CropEvidenceResponse>,
  weatherOptions: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/weather/options", filters)),
  weatherOverview: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/weather/overview", filters)),
  weatherTrends: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/weather/trends", filters)),
  weatherTemperature: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/weather/temperature", filters)),
  weatherPrecipitation: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/weather/precipitation", filters)),
  weatherAnomalies: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/weather/anomalies", filters)),
  weatherCoverage: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/weather/coverage", filters)),
  weatherCropContext: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/weather/crop-context", filters)),
  weatherClassifier: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/weather/classifier", filters)),
  weatherMlStatus: () =>
    requestRecord(
      "/api/v1/weather-ml/rainfall-forecast/status",
    ) as Promise<WeatherMlStatusResponse>,
  weatherMlForecast: (body: WeatherMlForecastRequest) =>
    requestRecord("/api/v1/weather-ml/rainfall-forecast", {
      method: "POST",
      body: JSON.stringify(body),
    }) as Promise<WeatherMlForecastResponse>,
  weatherMlDistrictOptions: () =>
    requestRecord(
      "/api/v1/weather-ml/rainfall-forecast/districts",
    ) as Promise<WeatherMlDistrictOptionsResponse>,
  weatherMlDistrictForecast: (body: WeatherMlDistrictForecastRequest) =>
    requestRecord("/api/v1/weather-ml/rainfall-forecast/district", {
      method: "POST",
      body: JSON.stringify(body),
    }) as Promise<WeatherMlDistrictForecastResponse>,
  riskOptions: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/risk/options", filters)),
  riskOverview: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/risk/overview", filters)),
  riskAnomalies: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/risk/anomalies", filters)),
  riskInstability: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/risk/instability", filters)),
  riskIndicators: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/risk/indicators", filters)),
  riskDiversification: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/risk/diversification", filters)),
  riskBenchmarking: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/risk/benchmarking", filters)),
  riskCoverage: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/risk/coverage", filters)),
  explainabilityModels: () => requestRecord("/api/v1/explainability/models"),
  explainabilityGlobal: () => requestRecord("/api/v1/explainability/global"),
  explainabilityEvaluation: () =>
    requestRecord("/api/v1/explainability/evaluation"),
  explainabilityBias: () => requestRecord("/api/v1/explainability/bias"),
  explainabilityUncertainty: () =>
    requestRecord("/api/v1/explainability/uncertainty"),
  yieldScenarioBaseline: (filters?: ApiFilters) =>
    requestRecord(withQuery("/api/v1/scenarios/yield/baseline", filters)),
  yieldScenario: (body: YieldScenarioRequest) => {
    const params = new URLSearchParams();
    params.set("crop", body.crop);
    params.set("season", body.season);
    params.set("crop_category", body.crop_category);
    params.set("state", body.state);
    params.set("district", body.district);
    body.years.forEach((year) => params.append("years", String(year)));
    return requestRecord(`/api/v1/scenarios/yield?${params.toString()}`, {
      method: "POST",
    });
  },
  modelInsightsPortfolio: () =>
    requestRecord("/api/v1/model-insights/portfolio"),
  modelInsightsModels: () => requestRecord("/api/v1/model-insights/models"),
  modelInsightsModel: (registryId: string) =>
    requestRecord(
      `/api/v1/model-insights/models/${encodeURIComponent(registryId)}`,
    ),
  modelInsightsEvidence: (registryId: string) =>
    requestRecord(
      `/api/v1/model-insights/models/${encodeURIComponent(registryId)}/evidence`,
    ),
  modelInsightsEvaluations: () =>
    requestRecord("/api/v1/model-insights/evaluations"),
  modelInsightsGovernance: () =>
    requestRecord("/api/v1/model-insights/governance"),
  modelInsightsPolicyOutputs: () =>
    requestRecord("/api/v1/model-insights/policy-outputs"),
  modelInsightsHealth: () => requestRecord("/api/v1/model-insights/health"),
  assistantStatus: () => requestRecord("/api/v1/assistant/status"),
  assistantSuggestions: () => requestRecord("/api/v1/assistant/suggestions"),
  assistantChat: (body: AssistantChatRequest) =>
    requestRecord("/api/v1/assistant/chat", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
