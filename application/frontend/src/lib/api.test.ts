import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("typed API client", () => {
  it("uses capability status as returned by the backend", async () => {
    const body = {
      capabilities: [
        {
          name: "yield_prediction",
          status: "disabled",
          reason_code: "public_api_release_not_authorized",
          reason_codes: ["public_api_release_not_authorized"],
          availability: "available",
          quality_status: "experimental",
          production_approved: false,
          limitations: ["unit not verified"],
        },
      ],
    };
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(new Response(JSON.stringify(body), { status: 200 })),
    );

    await expect(api.capabilities()).resolves.toEqual(body);
  });

  it("sanitizes an unavailable yield endpoint response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: "internal detail" }), {
          status: 503,
        }),
      ),
    );

    await expect(
      api.predictYield({
        crop: "Rice",
        season: "Kharif",
        crop_category: "Individual Crop Candidate",
        state: "Example state",
        district: "Example district",
        year_start: 2020,
      }),
    ).rejects.toMatchObject({
      name: "ApiError",
      code: "unavailable",
      status: 503,
    });
  });

  it("loads and validates evidence-backed yield options", async () => {
    const options = {
      crops: ["Rice"],
      seasons: ["Kharif"],
      crop_categories: ["Individual Crop Candidate"],
      states: ["Example state"],
      districts_by_state: { "Example state": ["Example district"] },
      year_start: 2013,
      year_end: 2022,
      year_range_type: "training_with_extrapolation",
      category_label_basis: "model_training_encoder",
      location_pair_basis: "positive_primary_training_cohort_source",
      target_unit: "kg/ha",
      target_unit_status: "verification_pending",
      target_semantics: "Yield in kg/ha (pending verification)",
      target_unit_source:
        "MoSPI Compendium of Datasets and Registries in India 2024",
      target_unit_source_url: "https://mospi.gov.in/source.pdf",
      target_conversion_applied: false,
      limitations: [],
    };
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify(options), { status: 200 }),
        ),
    );

    await expect(api.yieldOptions()).resolves.toEqual(options);
  });

  it("keeps the backend error message and request ID for diagnostics", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "resource_not_found",
              message: "The requested resource was not found.",
              details: [],
              request_id: "runtime-request-123",
            },
          }),
          { status: 404 },
        ),
      ),
    );

    await expect(api.weatherOptions()).rejects.toMatchObject({
      code: "request",
      status: 404,
      backendMessage:
        "The requested resource was not found. Request ID: runtime-request-123",
    });
  });

  it("requests weather-ML rainfall status without implying live forecasts", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          task: "wi05_rainfall_forecast",
          status: "awaiting_input_pipeline",
          forecast_available: false,
          reason_code: "awaiting_daily_weather_input_pipeline",
          production_approved: false,
          predictor_count: 53,
          horizons: [],
          input: {
            provider: "none_configured",
            forecast_available: false,
            latest_available_input_date: "2024-12-31",
            required_variables: ["T2M_MAX", "T2M_MIN", "PRECTOTCORR"],
            frequency: "consecutive UTC daily observations",
            reason_code: "awaiting_daily_weather_input_pipeline",
            message:
              "Live rainfall forecasting is awaiting a daily weather input pipeline.",
          },
          dataset: {},
          limitations: [],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.weatherMlStatus()).resolves.toMatchObject({
      forecast_available: false,
      reason_code: "awaiting_daily_weather_input_pipeline",
      predictor_count: 53,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/weather-ml/rainfall-forecast/status",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("requests district archive forecast options and posts district selections", async () => {
    const optionsPayload = {
      task: "wi05_rainfall_forecast_district_archive",
      forecast_origin_date: "2024-12-31",
      archive_end_date: "2024-12-31",
      supported_district_count: 1,
      states: ["Mizoram"],
      districts_by_state: { Mizoram: ["Hnahthial"] },
      districts: [
        {
          state: "Mizoram",
          district: "Hnahthial",
          apy_geography_id: "APY-GEO-0000",
          matched_boundary_name: "HNAHTHIAL",
          intersecting_cell_count: 2,
          valid_cell_count: 2,
        },
      ],
      aggregation_method: "area_weighted_mean",
      weight_field: "intersection_area_m2",
      limitations: [],
    };
    const forecastPayload = {
      task: "wi05_rainfall_forecast_district_archive",
      forecast_available: true,
      status: "archive_demonstration",
      reason_code: "archive_demonstration",
      message: "archive",
      notice: "archive notice",
      state: "Mizoram",
      district: "Hnahthial",
      apy_geography_id: "APY-GEO-0000",
      matched_boundary_name: "HNAHTHIAL",
      forecast_origin_date: "2024-12-31",
      archive_end_date: "2024-12-31",
      forecast_dates: ["2025-01-01"],
      spatial: {
        total_intersecting_cell_count: 2,
        valid_cell_count: 2,
        aggregation_method: "area_weighted_mean",
      },
      grid_cells: [],
      horizons: [
        {
          horizon: 1,
          label: "T+1",
          target_date: "2025-01-01",
          expected_precipitation_mm_day: 1.2,
          wet_probability: 0.4,
          conditional_wet_amount_mm_day: 3.0,
          min_cell_expected_mm_day: 1.0,
          max_cell_expected_mm_day: 1.4,
          cell_count: 2,
        },
      ],
      model: {},
      limitations: [],
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(optionsPayload), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(forecastPayload), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.weatherMlDistrictOptions()).resolves.toMatchObject({
      forecast_origin_date: "2024-12-31",
      supported_district_count: 1,
    });
    await expect(
      api.weatherMlDistrictForecast({
        state: "Mizoram",
        district: "Hnahthial",
      }),
    ).resolves.toMatchObject({
      forecast_available: true,
      forecast_origin_date: "2024-12-31",
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/weather-ml/rainfall-forecast/districts",
      expect.objectContaining({ cache: "no-store" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/weather-ml/rainfall-forecast/district",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ state: "Mizoram", district: "Hnahthial" }),
      }),
    );
  });

  it("rejects yield options with an unsupported unit verification status", async () => {
    const options = {
      crops: ["Rice"],
      seasons: ["Kharif"],
      crop_categories: ["Individual Crop Candidate"],
      states: ["Example state"],
      districts_by_state: { "Example state": ["Example district"] },
      year_start: 2013,
      year_end: 2022,
      year_range_type: "training_with_extrapolation",
      category_label_basis: "model_training_encoder",
      location_pair_basis: "positive_primary_training_cohort_source",
      target_unit: "kg/ha",
      target_unit_status: "guaranteed",
      target_semantics: "Yield in kg/ha",
      target_unit_source:
        "MoSPI Compendium of Datasets and Registries in India 2024",
      target_unit_source_url: "https://mospi.gov.in/source.pdf",
      target_conversion_applied: false,
      limitations: [],
    };
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify(options), { status: 200 }),
        ),
    );

    await expect(api.yieldOptions()).rejects.toMatchObject({
      code: "invalid-response",
    });
  });

  it("rejects a successful yield response without a verified unit", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            prediction: 123,
            target: "Yield",
            unit: "",
            crop: "Rice",
            season: "Kharif",
            crop_category: "Individual Crop Candidate",
            state: "Example state",
            district: "Example district",
            prediction_year: 2020,
            prediction_period_status: "in_training_range",
            model_name: "HistGradientBoostingRegressor",
            model_version: null,
            model_version_status: "not_recorded",
            artifact_sha256: "a".repeat(64),
            training_year_start: 2013,
            training_year_end: 2022,
            quality_status: "experimental",
            production_approved: false,
            data_provenance: {
              dataset_source: "APY source",
              target_field: "Yield",
              target_definition: "Yield in kg/ha",
              target_construction: "Source field as recorded",
              target_consistency_check: "Cross checked",
              unit_source: "MoSPI compendium",
              unit_source_url: "https://mospi.gov.in/source.pdf",
              unit_source_section: "4.10.5 Agricultural Productivity",
              unit_verification_status: "verification_pending",
              numerical_conversion_applied: false,
            },
            limitations: [],
          }),
          { status: 200 },
        ),
      ),
    );

    await expect(
      api.predictYield({
        crop: "Rice",
        season: "Kharif",
        crop_category: "Individual Crop Candidate",
        state: "Example state",
        district: "Example district",
        year_start: 2020,
      }),
    ).rejects.toMatchObject({ code: "invalid-response" });
  });

  it("accepts a real response shape only when a unit is supplied", async () => {
    const prediction = {
      prediction: 123,
      target: "Yield",
      unit: "kg/ha",
      crop: "Rice",
      season: "Kharif",
      crop_category: "Individual Crop Candidate",
      state: "Example state",
      district: "Example district",
      prediction_year: 2020,
      prediction_period_status: "in_training_range",
      model_name: "HistGradientBoostingRegressor",
      model_version:
        "individual_crop_hgb_location/2013-2022/sha256:dc057a8cbe39adef",
      model_version_status: "recorded",
      artifact_sha256: "a".repeat(64),
      training_year_start: 2013,
      training_year_end: 2022,
      quality_status: "experimental",
      production_approved: false,
      data_provenance: {
        dataset_source: "APY source",
        target_field: "Yield",
        target_definition: "Yield in kg/ha",
        target_construction: "Source field as recorded",
        target_consistency_check: "Cross checked",
        unit_source: "MoSPI compendium",
        unit_source_url: "https://mospi.gov.in/source.pdf",
        unit_source_section: "4.10.5 Agricultural Productivity",
        unit_verification_status: "verification_pending",
        numerical_conversion_applied: false,
      },
      limitations: ["Experimental validation"],
    };
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify(prediction), { status: 200 }),
        ),
    );
    await expect(
      api.predictYield({
        crop: "Rice",
        season: "Kharif",
        crop_category: "Individual Crop Candidate",
        state: "Example state",
        district: "Example district",
        year_start: 2020,
      }),
    ).resolves.toEqual(prediction);
  });

  it("encodes service filters and requires an object response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ metric: "temperature", points: [] }), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      api.weatherTemperature({
        state: "Tamil Nadu",
        year_start: 2018,
      }),
    ).resolves.toEqual({ metric: "temperature", points: [] });
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/v1/weather/temperature?state=Tamil+Nadu&year_start=2018",
    );
  });

  it("sends selected scenario years as repeated query parameters", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ predictions: [] }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await api.yieldScenario({
      crop: "Rice",
      season: "Kharif",
      crop_category: "Individual Crop Candidate",
      state: "Example state",
      district: "Example district",
      years: [2021, 2022],
    });

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/v1/scenarios/yield?crop=Rice&season=Kharif&crop_category=Individual+Crop+Candidate&state=Example+state&district=Example+district&years=2021&years=2022",
    );
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "POST" });
  });

  it("posts assistant prompts to the backend without synthesizing a reply", async () => {
    const response = {
      answer: "A backend-provided response.",
      language: "en",
      status: "available",
      sources: [],
      tools_used: [],
      suggested_followups: [],
      limitations: [],
      request_id: "request-1",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify(response), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      api.assistantChat({
        message: "Explain the result",
        preferred_language: "en",
      }),
    ).resolves.toEqual(response);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/assistant/chat");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({
      message: "Explain the result",
      preferred_language: "en",
    });
  });
});
