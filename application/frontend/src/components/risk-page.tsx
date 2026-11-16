"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, type ApiRecord } from "../lib/api";
import { useApp } from "./app-providers";
import { PageHeading } from "./availability";
import {
  ApiStatus,
  MetricGrid,
  ObservationChart,
  ProvenanceDetails,
  isApiRecord,
  numbersFrom,
  recordsFrom,
  safeValue,
  textFrom,
} from "./analysis-data";

type RiskResult = {
  overview: ApiRecord;
  anomalies: ApiRecord;
  instability: ApiRecord;
  indicators: ApiRecord;
  diversification: ApiRecord;
  benchmarking: ApiRecord;
};

export function RiskPage() {
  const { t } = useApp();
  const [options, setOptions] = useState<ApiRecord | null>(null);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [crop, setCrop] = useState("");
  const [season, setSeason] = useState("");
  const [year, setYear] = useState("");
  const [result, setResult] = useState<RiskResult | null>(null);
  const [resultError, setResultError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .riskOptions()
      .then(
        (data) => {
          if (!active) return;
          const years = numbersFrom(data.years);
          const states = stringOptions(data.states);
          const initialState = textFrom(
            data,
            ["selected_state"],
            states[0] ?? "",
          );
          setOptions(data);
          setState(initialState);
          setDistrict(districtsForState(data, initialState)[0] ?? "");
          setCrop(stringOptions(data.crops)[0] ?? "");
          setSeason(stringOptions(data.seasons)[0] ?? "");
          setYear(String(years.at(-1) ?? data.year_end ?? ""));
        },
        () => {
          if (active)
            setOptionsError(
              "Risk-analysis filters are unavailable from the service.",
            );
        },
      )
      .finally(() => {
        if (active) setOptionsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const states = useMemo(() => stringOptions(options?.states), [options]);
  const districtOptions = useMemo(
    () => districtsForState(options, state),
    [options, state],
  );
  const crops = useMemo(() => stringOptions(options?.crops), [options]);
  const seasons = useMemo(() => stringOptions(options?.seasons), [options]);
  const years = useMemo(() => numbersFrom(options?.years), [options]);

  async function loadRisk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setResultError(null);
    setResult(null);
    if (!state || !district || !crop || !season || !year) {
      setResultError(
        "Risk analysis needs a specific state, district, crop, season, and agricultural year. Please choose each value before exploring.",
      );
      setLoading(false);
      return;
    }
    const numericYear = Number(year);
    const groupFilters = {
      state,
      district,
      crop,
      season,
      year_start: numericYear,
      year_end: numericYear,
      page: 1,
      page_size: 20,
    };
    const requests = await Promise.allSettled([
      api.riskOverview(),
      api.riskAnomalies(groupFilters),
      api.riskInstability(groupFilters),
      api.riskIndicators(groupFilters),
      api.riskDiversification({
        state,
        district,
        season,
        year_start: numericYear,
        page: 1,
        page_size: 20,
      }),
      api.riskBenchmarking({
        state,
        crop,
        season,
        year_start: numericYear,
        through_year_start: numericYear,
        page: 1,
        page_size: 20,
      }),
    ]);
    const keys = [
      "overview",
      "anomalies",
      "instability",
      "indicators",
      "diversification",
      "benchmarking",
    ] as const;
    const data: Partial<RiskResult> = {};
    let failures = 0;
    requests.forEach((request, index) => {
      const key = keys[index];
      if (key) data[key] = request.status === "fulfilled" ? request.value : {};
      if (request.status === "rejected") failures += 1;
    });
    if (failures === requests.length) {
      setResultError(
        "Risk indicators are currently unavailable. No risk assessment is displayed.",
      );
      setLoading(false);
      return;
    }
    setResult(data as RiskResult);
    if (failures) {
      setResultError(
        "Some exploratory indicators could not be loaded; available results are shown.",
      );
    }
    setLoading(false);
  }

  const anomalies = recordsFrom(result?.anomalies.records).slice(0, 6);
  const shares = recordsFrom(result?.diversification.crop_area_shares);
  const benchmarkDistricts = recordsFrom(result?.benchmarking.districts);
  const instabilityProvenance = isApiRecord(
    result?.instability.dataset_provenance,
  )
    ? (result?.instability.dataset_provenance as ApiRecord)
    : {};
  const instabilityUnit = textFrom(
    recordsFrom(result?.instability.years)[0] ?? instabilityProvenance,
    ["yield_unit"],
    "",
  );

  return (
    <div className="risk-page">
      <PageHeading
        eyebrow={t("risk")}
        title={t("risk")}
        intro="Explore historical yield abnormalities and descriptive agricultural indicators. A data anomaly is not the same as an agricultural disaster or a forecast of future crop failure."
      />
      <section className="resource-layout">
        <div className="resource-section risk-intro">
          <header>
            <div>
              <p className="eyebrow">Exploratory · Notebook 20</p>
              <h2>Understand historical signals</h2>
              <p>
                No synthetic risk score or future failure prediction is shown.
              </p>
            </div>
            <span className="status-label pending">Exploratory</span>
          </header>
          <form
            className="analysis-toolbar"
            onSubmit={(event) => void loadRisk(event)}
          >
            <div className="field">
              <label htmlFor="risk-state">{t("state")}</label>
              <select
                id="risk-state"
                onChange={(event) => {
                  setState(event.target.value);
                  setDistrict("");
                }}
                value={state}
              >
                <option value="">All available states</option>
                {states.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="risk-district">{t("district")}</label>
              <select
                id="risk-district"
                onChange={(event) => setDistrict(event.target.value)}
                value={district}
              >
                <option value="">All available districts</option>
                {districtOptions.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="risk-crop">{t("crop")}</label>
              <select
                id="risk-crop"
                onChange={(event) => setCrop(event.target.value)}
                value={crop}
              >
                <option value="">All available crops</option>
                {crops.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="risk-season">{t("season")}</label>
              <select
                id="risk-season"
                onChange={(event) => setSeason(event.target.value)}
                value={season}
              >
                <option value="">All available seasons</option>
                {seasons.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="risk-year">Agricultural year</label>
              <select
                id="risk-year"
                onChange={(event) => setYear(event.target.value)}
                value={year}
              >
                <option value="">Latest available</option>
                {years.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
            <button
              className="primary-button"
              disabled={loading || optionsLoading}
              type="submit"
            >
              {loading ? "Loading indicators…" : "Explore historical signals"}
            </button>
          </form>
          <ApiStatus loading={optionsLoading} error={optionsError} />
          <ApiStatus loading={loading} error={resultError} />
        </div>

        {result && (
          <>
            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">01 / Historical anomalies</p>
                  <h2>Observed yield vs historical baseline</h2>
                  <p>
                    Anomaly classifications summarize past observations and
                    their available baseline.
                  </p>
                </div>
              </header>
              <MetricGrid
                items={[
                  {
                    label: "Prepared observations",
                    value: result.overview.prepared_observation_count,
                  },
                  {
                    label: "With historical baseline",
                    value:
                      result.overview.observations_with_historical_baseline,
                  },
                  {
                    label: "Insufficient history",
                    value:
                      result.overview.observations_without_sufficient_history,
                  },
                  {
                    label: "Historical classifications returned",
                    value: result.anomalies.total,
                  },
                ]}
              />
              {anomalies.length ? (
                <div className="data-card-list">
                  {anomalies.map((record, index) => (
                    <article
                      className="data-card"
                      key={`${String(record.district)}-${String(record.year_start)}-${index}`}
                    >
                      <header>
                        <strong>
                          {textFrom(record, ["crop"])} ·{" "}
                          {textFrom(record, ["district"])}
                        </strong>
                        <span>
                          {textFrom(record, [
                            "agricultural_year",
                            "year_start",
                          ])}
                        </span>
                      </header>
                      <dl>
                        <div>
                          <dt>Actual observation</dt>
                          <dd>
                            {safeValue(record.yield_value)}{" "}
                            {safeValue(record.yield_unit)}
                          </dd>
                        </div>
                        <div>
                          <dt>Historical median</dt>
                          <dd>
                            {safeValue(record.historical_median_yield)}{" "}
                            {safeValue(record.yield_unit)}
                          </dd>
                        </div>
                        <div>
                          <dt>Historical label</dt>
                          <dd>{safeValue(record.risk_indicator)}</dd>
                        </div>
                        <div>
                          <dt>Baseline observations</dt>
                          <dd>
                            {safeValue(record.historical_observation_count)}
                          </dd>
                        </div>
                      </dl>
                    </article>
                  ))}
                </div>
              ) : (
                <ApiStatus loading={loading} error={null} empty />
              )}
              <p className="result-interpretation">
                <strong>What this means:</strong> The classification describes
                an observed departure from a historical reference. It does not
                declare a disaster, identify a cause, or predict a future crop
                loss.
              </p>
              <ProvenanceDetails data={result.anomalies} />
            </section>

            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">02 / Yield instability</p>
                  <h2>Variation across observed years</h2>
                  <p>
                    Summary statistics depend on the selected crop, place,
                    season, period, and available history.
                  </p>
                </div>
              </header>
              <MetricGrid
                items={[
                  {
                    label: "Valid observations",
                    value: result.instability.valid_observation_count,
                  },
                  {
                    label: "Observed years",
                    value: result.instability.observed_year_count,
                  },
                  {
                    label: "Mean yield",
                    value: result.instability.mean_yield,
                    unit: instabilityUnit,
                  },
                  {
                    label: "Median yield",
                    value: result.instability.median_yield,
                    unit: instabilityUnit,
                  },
                  {
                    label: "Standard deviation",
                    value: result.instability.sample_standard_deviation,
                  },
                  {
                    label: "Coefficient of variation",
                    value: result.instability.coefficient_of_variation_pct,
                    unit: "%",
                  },
                  {
                    label: "Trend status",
                    value: result.instability.trend_status,
                  },
                  {
                    label: "Robust variability",
                    value: result.instability.robust_variability_status,
                  },
                ]}
              />
              <p className="result-interpretation">
                {textFrom(
                  result.instability,
                  ["calculation_method"],
                  "Instability is descriptive variation in historical observations, not a forward-looking risk score.",
                )}
              </p>
              <ProvenanceDetails data={result.instability} />
            </section>

            <div className="chart-stack">
              <section className="resource-section">
                <header>
                  <div>
                    <p className="eyebrow">03 / Crop diversification</p>
                    <h2>Crop area shares</h2>
                    <p>
                      Observed shares describe the selected area&apos;s recorded
                      crop mix.
                    </p>
                  </div>
                  <button
                    className="inline-help"
                    title="HHI summarizes concentration in crop shares. It is not a forecast of crop failure."
                    type="button"
                  >
                    ?
                  </button>
                </header>
                <ObservationChart
                  title="Share of comparable area"
                  subtitle="Historical recorded crop area · returned shares"
                  records={shares}
                  labelKeys={["crop"]}
                  valueKeys={["share_pct"]}
                  unit="%"
                />
                <MetricGrid
                  items={[
                    {
                      label: "Positive-area crops",
                      value: result.diversification.positive_area_crop_count,
                    },
                    {
                      label: "Comparable area",
                      value: result.diversification.total_comparable_area,
                      unit: textFrom(result.diversification, ["area_unit"], ""),
                    },
                    {
                      label: "HHI concentration",
                      value: result.diversification.herfindahl_hirschman_index,
                    },
                    {
                      label: "Excluded records",
                      value:
                        result.diversification
                          .excluded_missing_zero_or_negative_area_record_count,
                    },
                  ]}
                />
                <p className="result-interpretation">
                  {textFrom(
                    result.diversification,
                    ["interpretation"],
                    "HHI describes concentration in observed crop-area shares; it is not a risk score.",
                  )}
                </p>
                <ProvenanceDetails data={result.diversification} />
              </section>
              <section className="resource-section">
                <header>
                  <div>
                    <p className="eyebrow">04 / District benchmarking</p>
                    <h2>Comparable historical districts</h2>
                    <p>
                      Benchmark only within the returned comparison group and
                      period.
                    </p>
                  </div>
                </header>
                <MetricGrid
                  items={[
                    {
                      label: "Districts in comparison",
                      value: result.benchmarking.district_count,
                    },
                    {
                      label: "Benchmark year",
                      value: result.benchmarking.benchmark_year_start,
                    },
                    {
                      label: "Through year",
                      value: result.benchmarking.through_year_start,
                    },
                  ]}
                />
                <ObservationChart
                  title="Current-year yield by district"
                  subtitle={textFrom(
                    result.benchmarking,
                    ["comparison_group"],
                    "Returned comparison group",
                  )}
                  records={benchmarkDistricts}
                  labelKeys={["district"]}
                  valueKeys={["current_year_yield"]}
                  unit={textFrom(
                    benchmarkDistricts[0] ?? {},
                    ["yield_unit"],
                    "As reported",
                  )}
                />
                <ProvenanceDetails data={result.benchmarking} />
              </section>
            </div>

            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">Supporting context</p>
                  <h2>Data quality and interpretation</h2>
                </div>
              </header>
              <p className="result-interpretation">
                {textFrom(
                  result.indicators,
                  ["interpretation"],
                  "Yield anomalies and statistical instability are descriptive signals. Their meaning depends on evidence coverage, historical baselines, and source quality.",
                )}
              </p>
              <ProvenanceDetails data={result.indicators} />
            </section>
          </>
        )}
      </section>
    </div>
  );
}

function districtsForState(options: ApiRecord | null, state: string) {
  const byState = options?.districts_by_state;
  if (byState && typeof byState === "object" && !Array.isArray(byState)) {
    const entry = (byState as Record<string, unknown>)[state];
    if (state) return stringOptions(entry);
  }
  return stringOptions(options?.districts);
}

function stringOptions(value: unknown) {
  return Array.isArray(value)
    ? value.flatMap((item) =>
        typeof item === "string" || typeof item === "number"
          ? [String(item)]
          : [],
      )
    : [];
}
