// @vitest-environment happy-dom

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  api,
  ApiError,
  type CropComparisonResponse,
  type CropEvidenceResponse,
  type CropHistoricalStatistics,
  type CropRankingOptionsResponse,
  type CropRankingResponse,
  type CropTrendResponse,
  type RankedCropCandidate,
} from "../lib/api";
import { CropsPage } from "./crops-page";

const mockState: { language: "en" | "hi" } = { language: "en" };

vi.mock("./app-providers", async () => {
  const { messages } = await import("../lib/i18n");
  return {
    useApp: () => ({
      language: mockState.language,
      t: (key: keyof typeof messages.en) =>
        (messages[mockState.language] as typeof messages.en)[key],
      capabilities: {
        data: {
          capabilities: [
            {
              name: "crop_ranking",
              status: "enabled",
              reason_code: "historical_evidence_available",
              reason_codes: [],
              availability: "available",
              quality_status: "experimental",
              production_approved: false,
              limitations: [],
            },
          ],
        },
        loading: false,
        error: null,
        refresh: vi.fn(),
      },
    }),
  };
});

function statistics(
  crop: string,
  overrides: Partial<CropHistoricalStatistics> = {},
): CropHistoricalStatistics {
  return {
    crop,
    historical_median_yield: 2000,
    historical_mean_yield: 2050,
    recent_median_yield: 2100,
    recent_window_year_start: 2020,
    recent_window_year_end: 2024,
    yield_standard_deviation: 100,
    coefficient_of_variation: 4.9,
    historical_trend_yield_per_year: 15,
    valid_observation_count: 5,
    valid_year_count: 5,
    latest_observation_year: 2024,
    valid_years: [2020, 2021, 2022, 2023, 2024],
    recent_valid_year_count: 5,
    recent_year_coverage: 1,
    evidence_quality: "moderate",
    unit: "kg/ha",
    ...overrides,
  };
}

function candidate(
  crop: string,
  rank: number | null,
  evidenceRank: number | null,
  rankingValue: number | null,
  predictedYield: number | null,
  overrides: Partial<RankedCropCandidate> = {},
): RankedCropCandidate {
  return {
    crop,
    rank,
    observed_yield: 2800,
    predicted_yield: predictedYield,
    unit: "kg/ha",
    ranking_value: rankingValue,
    ranking_basis: "recent_median",
    evidence_rank: evidenceRank,
    model_reference_year: predictedYield === null ? null : 2022,
    model_prediction_period_status:
      predictedYield === null ? null : "in_training_range",
    model_difference_from_median:
      predictedYield === null ? null : predictedYield - 2000,
    has_observation_in_latest_year: true,
    warnings: [],
    candidate_eligibility: {
      eligible: true,
      reason_code: "historical_evidence_available",
      evidence_quality: "moderate",
      valid_observation_count: 5,
      valid_year_count: 5,
    },
    historical_statistics: statistics(crop),
    ...overrides,
  };
}

const provenance = {
  dataset_name: "APY",
  dataset_source: "Agricultural Production Statistics",
  source_file: "apy.csv",
  sha256: "a".repeat(64),
  record_count: 100,
  valid_record_count: 90,
  year_start: 2013,
  year_end: 2024,
  yield_unit: "kg/ha",
};

const rankingOptions: CropRankingOptionsResponse = {
  crops: ["Rice", "Wheat", "Maize"],
  states: ["Example State", "Second State"],
  districts: ["Example District", "Another District"],
  seasons: ["Kharif", "Rabi", "Total"],
  agricultural_years: [2013, 2024],
  selected_state: "Example State",
  selected_district: null,
  selected_season: "Kharif",
  data_provenance: provenance,
  limitations: [],
};

const districtOptions: CropRankingOptionsResponse = {
  ...rankingOptions,
  districts: ["Example District", "Another District"],
};

const rankingResponse: CropRankingResponse = {
  state: "Example State",
  district: "Example District",
  season: "Kharif",
  crop_category: "Individual Crop Candidate",
  data_period_start: 2013,
  latest_data_year: 2024,
  ranking_basis: "recent_median",
  top_n: 5,
  reference_year: 2022,
  agricultural_year_start: 2022,
  agricultural_year_label: "2022-23",
  ranking_available: true,
  ranked_candidate_count: 3,
  eligible_candidate_count: 3,
  candidates: [
    candidate("Rice", 1, 2, 3100, 3200),
    candidate("Wheat", 2, 1, 2800, 2750),
    candidate("Maize", 3, 3, 2500, null, {
      model_difference_from_median: null,
      has_observation_in_latest_year: false,
      warnings: ["No supported model estimate is available for this crop."],
      historical_statistics: statistics("Maize", {
        historical_median_yield: 2400,
        historical_mean_yield: 2450,
        recent_median_yield: 2500,
        valid_observation_count: 3,
        valid_year_count: 3,
        valid_years: [2020, 2022, 2023],
        latest_observation_year: 2023,
        recent_valid_year_count: 2,
        recent_year_coverage: 0.4,
        evidence_quality: "limited",
      }),
    }),
  ],
  ranking_methodology:
    "Candidates are ranked by the recent five-year median of valid historical yields.",
  ranking_model: {
    model_name: "HistGradientBoostingRegressor",
    model_version: null,
    artifact_sha256: "b".repeat(64),
    target: "Yield",
    unit: "kg/ha",
    training_year_start: 2013,
    training_year_end: 2022,
    prediction_period_status: "in_training_range",
    reference_year: 2022,
    reference_year_policy:
      "Common fixed reference year selected within supported training period.",
    quality_status: "experimental",
    production_approved: false,
    limitations: ["Model estimates are supplementary experimental estimates."],
  },
  data_provenance: provenance,
  limitations: [
    "Historical yield evidence does not establish agronomic suitability or profitability.",
  ],
};

const comparisonResponse: CropComparisonResponse = {
  state: "Example State",
  district: "Example District",
  season: "Kharif",
  through_year_start: 2024,
  crops: [statistics("Rice"), statistics("Wheat"), statistics("Maize")],
  comparison_group_coverage: [],
  data_provenance: provenance,
  limitations: [],
};

const trendResponse: CropTrendResponse = {
  state: "Example State",
  district: "Example District",
  season: "Kharif",
  through_year_start: 2024,
  statistics: statistics("Rice"),
  observations: [
    {
      year_start: 2022,
      year_label: "2022-23",
      area: 10,
      production: 30000,
      yield_value: 3000,
      unit: "kg/ha",
    },
    {
      year_start: 2024,
      year_label: "2024-25",
      area: 10,
      production: 31000,
      yield_value: 3100,
      unit: "kg/ha",
    },
  ],
  data_provenance: provenance,
  limitations: [],
};

const evidenceResponse: CropEvidenceResponse = {
  ...trendResponse,
  source_observation_count: 2,
  valid_observation_count: 2,
  excluded_observation_count: 0,
};

beforeEach(() => {
  mockState.language = "en";
  vi.spyOn(api, "cropRankingOptions").mockImplementation(async (filters) =>
    filters?.state ? districtOptions : rankingOptions,
  );
  vi.spyOn(api, "rankCrops").mockResolvedValue(rankingResponse);
  vi.spyOn(api, "cropComparison").mockResolvedValue(comparisonResponse);
  vi.spyOn(api, "cropTrend").mockResolvedValue(trendResponse);
  vi.spyOn(api, "cropEvidence").mockResolvedValue(evidenceResponse);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

async function renderLoaded() {
  render(<CropsPage />);
  await screen.findByRole("button", { name: "Show crop candidates" });
  await waitFor(() => {
    expect(screen.getByLabelText("District").getAttribute("placeholder")).toBe(
      "Example District",
    );
  });
}

async function submitRanking() {
  fireEvent.click(
    await screen.findByRole("button", { name: "Show crop candidates" }),
  );
}

describe("Crop Intelligence season-based ranking", () => {
  it("offers only state, district and season as selection controls", async () => {
    await renderLoaded();

    expect(screen.getByLabelText("State")).toBeDefined();
    expect(screen.getByLabelText("District")).toBeDefined();
    expect(screen.getByLabelText("Season")).toBeDefined();
    expect(screen.queryByLabelText(/year/i)).toBeNull();
    expect(
      screen.queryByLabelText(/crop category|crops to compare/i),
    ).toBeNull();
    expect(
      screen.getByText(
        "Top yield-based crop candidates for this district and season, based on available historical agricultural evidence.",
      ),
    ).toBeDefined();
    expect(api.cropRankingOptions).toHaveBeenCalledWith({
      state: "Example State",
    });
  });

  it("requests up to five candidates without a user-selected year", async () => {
    await renderLoaded();
    await submitRanking();

    await waitFor(() => expect(api.rankCrops).toHaveBeenCalledOnce());
    expect(api.rankCrops).toHaveBeenCalledWith({
      state: "Example State",
      district: "Example District",
      season: "Kharif",
      top_n: 5,
      ranking_basis: "recent_median",
    });
    expect(api.cropComparison).toHaveBeenCalledWith({
      state: "Example State",
      district: "Example District",
      season: "Kharif",
      through_year_start: 2024,
    });
  });

  it("orders candidates by yield rank without a ranking-view toggle and keeps model estimates supplementary", async () => {
    await renderLoaded();
    await submitRanking();

    expect(
      await screen.findByText("Model-estimated yield (supplementary)"),
    ).toBeDefined();
    expect(screen.getAllByText("Historical median").length).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Recent five-year median").length,
    ).toBeGreaterThan(0);
    expect(
      screen.queryByRole("button", { name: "Yield-based ranking" }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Evidence-quality ranking" }),
    ).toBeNull();
    expect(
      screen.getAllByText("Internal model reference year").length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText("2022").length).toBeGreaterThan(0);

    const candidateTable = document.querySelector(".crop-candidate-table");
    expect(candidateTable).not.toBeNull();
    const rows = within(candidateTable as HTMLElement).getAllByRole("row");
    expect(within(rows[1]).getByRole("rowheader").textContent).toBe("Rice");
  });

  it("shows model and evidence limitations without excluding historical records", async () => {
    await renderLoaded();
    await submitRanking();

    await waitFor(() => {
      expect(document.querySelector(".crop-candidate-table")).not.toBeNull();
    });
    const candidateTable = document.querySelector(".crop-candidate-table");
    expect(candidateTable).not.toBeNull();
    const maizeRow = within(candidateTable as HTMLElement).getByRole("row", {
      name: /Maize/,
    });
    fireEvent.click(within(maizeRow).getByText("Evidence details"));
    expect(
      within(maizeRow).getByText(
        "No supported model estimate is available for this crop.",
      ),
    ).toBeDefined();
    expect(within(maizeRow).getByText("No")).toBeDefined();
    expect(within(maizeRow).getByText("2023")).toBeDefined();
  });

  it("reports insufficient candidates without presenting a ranking", async () => {
    const insufficient: CropRankingResponse = {
      ...rankingResponse,
      ranking_available: false,
      ranked_candidate_count: 0,
      eligible_candidate_count: 1,
      candidates: [
        candidate("Rice", null, 1, null, null, {
          candidate_eligibility: {
            eligible: true,
            reason_code: "limited_evidence",
            evidence_quality: "limited",
            valid_observation_count: 1,
            valid_year_count: 1,
          },
        }),
      ],
    };
    vi.spyOn(api, "rankCrops").mockResolvedValue(insufficient);
    await renderLoaded();
    await submitRanking();

    expect(
      await screen.findByText(/Fewer than two supported crops/),
    ).toBeDefined();
    const candidateTable = document.querySelector(".crop-candidate-table");
    expect(candidateTable).not.toBeNull();
    expect(
      within(candidateTable as HTMLElement).getByRole("row", { name: /Rice/ }),
    ).toBeDefined();
  });

  it("surfaces an unavailable service without fabricating candidates", async () => {
    vi.spyOn(api, "rankCrops").mockRejectedValue(
      new ApiError("unavailable", 503),
    );
    await renderLoaded();
    await submitRanking();

    expect(
      await screen.findByText(
        "The crop ranking service is not currently available.",
      ),
    ).toBeDefined();
    expect(document.querySelector(".crop-candidate-table")).toBeNull();
  });
});
