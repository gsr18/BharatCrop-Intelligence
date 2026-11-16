// @vitest-environment happy-dom

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  api,
  ApiError,
  type YieldOptions,
  type YieldPredictionResponse,
} from "../lib/api";
import { YieldPage } from "./yield-page";

vi.mock("./app-providers", async () => {
  const { messages } = await import("../lib/i18n");
  return {
    useApp: () => ({
      t: (key: keyof typeof messages.en) => messages.en[key],
      language: "en",
      capabilities: {
        data: {
          capabilities: [
            {
              name: "yield_prediction",
              status: "enabled",
              reason_code: "experimental",
              reason_codes: [],
              availability: "available",
              quality_status: "experimental",
              production_approved: false,
              limitations: ["Yield unit is unverified."],
            },
          ],
        },
        loading: false,
      },
    }),
  };
});

const options: YieldOptions = {
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
  target_semantics: "Yield in kg/ha",
  target_unit_source:
    "MoSPI Compendium of Datasets and Registries in India 2024",
  target_unit_source_url: "https://mospi.gov.in/source.pdf",
  target_conversion_applied: false,
  limitations: ["Predictions are experimental."],
};

const prediction: YieldPredictionResponse = {
  crop: "Rice",
  season: "Kharif",
  crop_category: "Individual Crop Candidate",
  state: "Example state",
  district: "Example district",
  prediction_year: 2013,
  prediction_period_status: "in_training_range",
  prediction: 1234.5,
  target: "Yield",
  unit: "kg/ha",
  model_name: "HistGradientBoostingRegressor",
  model_version: "individual_crop_hgb_location/2013-2022/sha256:dc057a8cbe39adef",
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
  limitations: ["Experimental validation."],
};

beforeEach(() => {
  vi.spyOn(api, "yieldOptions").mockResolvedValue(options);
  vi.spyOn(api, "cropTrend").mockResolvedValue({
    observations: [],
    statistics: {},
    source_observation_count: 0,
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

async function renderWithOptions() {
  render(<YieldPage />);
  await screen.findByRole("option", { name: "Rice" });
}

function fillSupportedInputs(district = "Example district") {
  fireEvent.change(screen.getByLabelText("Crop"), {
    target: { value: "Rice" },
  });
  fireEvent.change(screen.getByLabelText("Season"), {
    target: { value: "Kharif" },
  });
  fireEvent.change(screen.getByLabelText("State"), {
    target: { value: "Example state" },
  });
  fireEvent.change(screen.getByLabelText("District"), {
    target: { value: district },
  });
  fireEvent.change(screen.getByLabelText("Prediction year"), {
    target: { value: "2013" },
  });
}

async function submitForm() {
  const button = screen.getByRole("button", { name: "Request prediction" });
  const form = button.closest("form");
  expect(form).not.toBeNull();
  fireEvent.submit(form!);
}

describe("yield prediction page", () => {
  it("loads and displays model-supported options dynamically", async () => {
    const yieldOptions = vi.spyOn(api, "yieldOptions");

    await renderWithOptions();

    expect(yieldOptions).toHaveBeenCalledOnce();
    expect(screen.getByRole("option", { name: "Example state" })).toBeDefined();
    fireEvent.change(screen.getByLabelText("State"), {
      target: { value: "Example state" },
    });
    expect(
      document.querySelector(
        'datalist#supported-districts option[value="Example district"]',
      ),
    ).not.toBeNull();
    expect(screen.getByText("Model training period:")).toBeDefined();
    expect(screen.getByText("kg/ha")).toBeDefined();
  });

  it("validates the district against the selected state's backend options", async () => {
    const predict = vi.spyOn(api, "predictYield");

    await renderWithOptions();
    fillSupportedInputs("Unlisted district");
    await submitForm();

    expect(predict).not.toHaveBeenCalled();
    expect(screen.getByRole("alert").textContent).toBe(
      "Please review the fields and try again.",
    );
  });

  it("renders a successful result with its unit, plain-language explanation and methodology", async () => {
    vi.spyOn(api, "predictYield").mockResolvedValue(prediction);

    await renderWithOptions();
    fillSupportedInputs();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByText("Model estimate")).toBeDefined();
    });
    expect(screen.getAllByText("1,234.5").length).toBeGreaterThan(0);
    expect(screen.getAllByText("kg/ha").length).toBeGreaterThan(0);
    expect(
      screen.getByText(/For Rice in Example district, Example state/),
    ).toBeDefined();
    expect(
      screen.getByText("Methodology, governance & limitations"),
    ).toBeDefined();
    expect(screen.getByText("Not approved")).toBeDefined();
    expect(screen.getByText("HistGradientBoostingRegressor")).toBeDefined();
    expect(screen.getByText("Experimental validation.")).toBeDefined();
    expect(
      screen.getByRole("link", {
        name: /MoSPI compendium.*4.10.5 Agricultural Productivity/,
      }),
    ).toBeDefined();
  });

  it("shows a real observed-vs-model comparison when trend data is returned", async () => {
    vi.spyOn(api, "predictYield").mockResolvedValue(prediction);
    vi.spyOn(api, "cropTrend").mockResolvedValue({
      observations: [
        {
          year_start: 2019,
          year_label: "2019-20",
          yield_value: 2900,
          unit: "kg/ha",
        },
        {
          year_start: 2020,
          year_label: "2020-21",
          yield_value: 2923,
          unit: "kg/ha",
        },
      ],
      statistics: {
        historical_median_yield: 2916.5,
        recent_median_yield: 2923,
        valid_observation_count: 2,
        valid_year_count: 2,
      },
      source_observation_count: 2,
    });

    await renderWithOptions();
    fillSupportedInputs();
    await submitForm();

    expect(
      await screen.findByText("Historical median (observed)"),
    ).toBeDefined();
    expect(screen.getByText("Recent median (observed)")).toBeDefined();
    expect(
      screen.queryByText(/No historical observations are available/),
    ).toBeNull();
  });

  it("discloses unit-verification status, data range, version and estimate-not-forecast", async () => {
    vi.spyOn(api, "predictYield").mockResolvedValue(prediction);

    await renderWithOptions();
    fillSupportedInputs();
    await submitForm();

    await waitFor(() => {
      expect(
        screen.getByText(
          "This is a feature-based model estimate, not a validated forecast of future yield.",
        ),
      ).toBeDefined();
    });
    expect(
      screen.getByText("Pending — source unit consistency is not proven"),
    ).toBeDefined();
    expect(
      screen.getByText(
        "individual_crop_hgb_location/2013-2022/sha256:dc057a8cbe39adef",
      ),
    ).toBeDefined();
    expect(
      screen.getByText("Supported historical data range"),
    ).toBeDefined();
  });

  it("labels post-training-year results as extrapolations", async () => {
    vi.spyOn(api, "predictYield").mockResolvedValue({
      ...prediction,
      prediction_year: 2028,
      prediction_period_status: "out_of_training_range_extrapolation",
    });

    await renderWithOptions();
    fillSupportedInputs();
    fireEvent.change(screen.getByLabelText("Prediction year"), {
      target: { value: "2028" },
    });
    await submitForm();

    expect(
      await screen.findByText(
        "Extrapolation — outside the 2013–2022 training period",
      ),
    ).toBeDefined();
    expect(
      screen.getByText(
        "This year is outside the training period; it is an extrapolated estimate, not a validated forecast. No confidence interval is available.",
      ),
    ).toBeDefined();
  });

  it("shows a clear unavailable state for HTTP 503", async () => {
    vi.spyOn(api, "predictYield").mockRejectedValue(
      new ApiError("unavailable", 503),
    );

    await renderWithOptions();
    fillSupportedInputs();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toBe(
        "This service is currently unavailable.",
      );
    });
    expect(screen.queryByText("1,234.5")).toBeNull();
  });

  it("surfaces API failures without rendering a fabricated result", async () => {
    vi.spyOn(api, "predictYield").mockRejectedValue(new ApiError("network"));

    await renderWithOptions();
    fillSupportedInputs();
    await submitForm();

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toBe(
        "Unable to reach the BharatCrop service.",
      );
    });
    expect(screen.queryByText("1,234.5")).toBeNull();
  });
});
