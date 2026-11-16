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
import { SignedBarChart } from "./charts/analysis-charts";
import { WeatherDistrictRainfallForecast } from "./weather-district-rainfall-forecast";
import { WeatherFutureEnhancements } from "./weather-future-enhancements";

type WeatherResult = {
  overview: ApiRecord;
  temperature: ApiRecord;
  precipitation: ApiRecord;
  trends: ApiRecord;
  anomalies: ApiRecord;
  coverage: ApiRecord;
  cropContext: ApiRecord;
  classifier: ApiRecord;
};

export function WeatherPage() {
  const { t } = useApp();
  const [options, setOptions] = useState<ApiRecord | null>(null);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [yearStart, setYearStart] = useState("");
  const [yearEnd, setYearEnd] = useState("");
  const [result, setResult] = useState<WeatherResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .weatherOptions()
      .then(
        (data) => {
          if (!active) return;
          setOptions(data);
          const years = numbersFrom(data.years);
          setState(
            textFrom(
              data,
              ["selected_state"],
              stringOptions(data.states)[0] ?? "",
            ),
          );
          setYearStart(String(years[0] ?? data.year_start ?? ""));
          setYearEnd(String(years.at(-1) ?? data.year_end ?? ""));
          setOptionsError(null);
        },
        () => {
          if (active)
            setOptionsError(
              "Weather filters are unavailable from the service.",
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
  const districts = useMemo(
    () => districtsForState(options, state),
    [options, state],
  );
  const years = useMemo(() => numbersFrom(options?.years), [options]);

  async function loadWeather(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    const filters = {
      state: state || undefined,
      district: district || undefined,
      year_start: yearStart ? Number(yearStart) : undefined,
      year_end: yearEnd ? Number(yearEnd) : undefined,
    };
    const labeled: Array<[keyof WeatherResult, Promise<ApiRecord>]> = [
      ["overview", api.weatherOverview(filters)],
      [
        "temperature",
        api.weatherTemperature({ ...filters, page: 1, page_size: 100 }),
      ],
      [
        "precipitation",
        api.weatherPrecipitation({ ...filters, page: 1, page_size: 100 }),
      ],
      ["trends", api.weatherTrends(filters)],
      [
        "anomalies",
        api.weatherAnomalies({ ...filters, page: 1, page_size: 20 }),
      ],
      ["coverage", api.weatherCoverage({ ...filters, page: 1, page_size: 50 })],
      ["classifier", api.weatherClassifier(filters)],
    ];
    if (state && district) {
      labeled.push([
        "cropContext",
        api.weatherCropContext({
          ...filters,
          state,
          district,
          page: 1,
          page_size: 50,
        }),
      ]);
    }
    const settled = await Promise.allSettled(
      labeled.map(([, request]) => request),
    );
    const data: Partial<WeatherResult> = {};
    let failures = 0;
    settled.forEach((request, index) => {
      const key = labeled[index]?.[0];
      if (key) data[key] = request.status === "fulfilled" ? request.value : {};
      if (request.status === "rejected") failures += 1;
    });
    if (failures === settled.length) {
      setError(
        "Weather services are currently unavailable. No observations are shown.",
      );
    } else {
      setResult({ cropContext: {}, ...data } as WeatherResult);
      if (failures) {
        setError(
          "Some weather views could not be loaded. Available results remain visible.",
        );
      }
    }
    setLoading(false);
  }

  const anomalyRecords = recordsFrom(result?.anomalies.records).slice(0, 5);
  const anomalyRows = recordsFrom(result?.anomalies.records).flatMap(
    (record) => {
      const value = record.tmax_mean_same_period_deviation_c;
      if (typeof value !== "number" || !Number.isFinite(value)) return [];
      const district = textFrom(record, ["district"], "Weather observation");
      const rawYear = record.calendar_year ?? record.year;
      const year =
        typeof rawYear === "number" && Number.isFinite(rawYear)
          ? String(rawYear)
          : textFrom(record, ["calendar_year", "year"], "");
      return [
        {
          label: year ? `${district} · ${year}` : district,
          value,
          meta: textFrom(
            record,
            ["temperature_deviation_baseline"],
            "Deviation baseline not reported",
          ),
        },
      ];
    },
  );
  const coverage = result?.coverage;
  const classifier = result?.classifier ?? {};
  const trendSeries = recordsFrom(result?.trends.series).slice(0, 6);
  const trendUnit = textFrom(result?.trends ?? {}, ["unit"]);

  return (
    <div className="weather-page">
      <PageHeading
        eyebrow={t("weather")}
        title={t("weather")}
        intro="Explore service-backed historical weather observations and their limits. Weather metrics use calendar-year records; crop records follow agricultural-year definitions."
      />
      <section className="resource-layout">
        <div className="resource-section weather-hero">
          <header>
            <div>
              <p className="eyebrow">Atmospheric history</p>
              <h2>Read the conditions, not a forecast</h2>
              <p>
                Temperature and precipitation are shown on separate,
                unit-labelled scales.
              </p>
            </div>
            <span className="weather-cloud" aria-hidden="true">
              ☁
            </span>
          </header>
          <form
            className="analysis-toolbar"
            onSubmit={(event) => void loadWeather(event)}
          >
            <div className="field">
              <label htmlFor="weather-state">{t("state")}</label>
              <select
                id="weather-state"
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
              <label htmlFor="weather-district">{t("district")}</label>
              <select
                id="weather-district"
                onChange={(event) => setDistrict(event.target.value)}
                value={district}
              >
                <option value="">All available districts</option>
                {districts.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="weather-from">From year</label>
              <select
                id="weather-from"
                onChange={(event) => setYearStart(event.target.value)}
                value={yearStart}
              >
                <option value="">Earliest</option>
                {years.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="weather-to">Through year</label>
              <select
                id="weather-to"
                onChange={(event) => setYearEnd(event.target.value)}
                value={yearEnd}
              >
                <option value="">Latest</option>
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
              {loading ? "Loading observations…" : "Explore weather history"}
            </button>
          </form>
          <ApiStatus loading={optionsLoading} error={optionsError} />
          <ApiStatus loading={loading} error={error} />
        </div>

        {result && (
          <>
            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">01 / Coverage</p>
                  <h2>Coverage and available observations</h2>
                  <p>
                    {textFrom(
                      result.overview,
                      ["calendar_year_semantics"],
                      "Annual weather records",
                    )}
                  </p>
                </div>
              </header>
              <MetricGrid
                items={[
                  {
                    label: "Weather records",
                    value: result.overview.record_count,
                  },
                  {
                    label: "Records with weather",
                    value: result.overview.weather_available_record_count,
                  },
                  {
                    label: "Geographic coverage",
                    value: result.overview.geography_count,
                  },
                  { label: "States", value: result.overview.state_count },
                  { label: "Districts", value: result.overview.district_count },
                  {
                    label: "Covered years",
                    value: Array.isArray(result.overview.years)
                      ? `${result.overview.years.length} years`
                      : undefined,
                  },
                ]}
              />
              <div className="result-interpretation">
                <strong>Time-grain legend:</strong> Weather measurements are
                annual calendar-year observations. Crop-weather context reports
                agricultural-year crop records and an explicit alignment method;
                the two should not be read as the same period.
              </div>
              <ProvenanceDetails data={result.overview} />
            </section>

            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">02 / Annual observations</p>
                  <h2>Year-by-year temperature and precipitation</h2>
                  <p>
                    Both series use their own unit scale and calendar-year
                    semantics; they are descriptive, not a forecast.
                  </p>
                </div>
              </header>
              <div className="chart-grid">
                <ObservationChart
                  title={textFrom(result.temperature, ["label"], "Temperature")}
                  subtitle="Annual weather observations · selected geography and period"
                  records={recordsFrom(result.temperature.points)}
                  labelKeys={["year", "date_semantics"]}
                  valueKeys={["value"]}
                  unit={textFrom(result.temperature, ["unit"])}
                  variant="line"
                />
                <ObservationChart
                  title={textFrom(
                    result.precipitation,
                    ["label"],
                    "Precipitation",
                  )}
                  subtitle="Annual weather observations · separate precipitation scale"
                  records={recordsFrom(result.precipitation.points)}
                  labelKeys={["year", "date_semantics"]}
                  valueKeys={["value"]}
                  unit={textFrom(result.precipitation, ["unit"])}
                  variant="line"
                />
              </div>
              <ProvenanceDetails data={result.precipitation} />
            </section>

            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">03 / Historical trends</p>
                  <h2>
                    {textFrom(
                      result.trends,
                      ["label"],
                      "Annual weather trend series",
                    )}
                  </h2>
                  <p>
                    {textFrom(
                      result.trends,
                      ["trend_method", "aggregation"],
                      "Aggregated annual observations by location; descriptive only, not a forecast.",
                    )}
                  </p>
                </div>
              </header>
              {trendSeries.length ? (
                <div className="chart-grid">
                  {trendSeries.map((series, index) => (
                    <ObservationChart
                      key={`${textFrom(series, ["location"])}-${index}`}
                      title={textFrom(
                        series,
                        ["location"],
                        `Location ${index + 1}`,
                      )}
                      subtitle="Annual trend series · observed yearly values"
                      records={recordsFrom(series.yearly_values)}
                      labelKeys={["year", "date_semantics"]}
                      valueKeys={["value"]}
                      unit={trendUnit}
                      variant="line"
                    />
                  ))}
                </div>
              ) : (
                <p className="data-message">
                  No weather trend series were returned for this selection.
                </p>
              )}
              <ProvenanceDetails data={result.trends} />
            </section>

            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">04 / Historical patterns</p>
                  <h2>Observed anomalies and geographic coverage</h2>
                  <p>
                    Descriptive summaries only; an anomaly is not a forecast or
                    a disaster classification.
                  </p>
                </div>
              </header>
              <MetricGrid
                items={[
                  { label: "Weather locations", value: coverage?.total },
                  { label: "Annual records", value: result.temperature.total },
                  {
                    label: "Precipitation records",
                    value: result.precipitation.total,
                  },
                  {
                    label: "Anomaly records classified",
                    value: result.anomalies.total,
                  },
                ]}
              />
              <SignedBarChart
                title="Same-period temperature deviation"
                subtitle="Returned anomaly records · positive values are warmer than the baseline"
                unit="°C"
                rows={anomalyRows}
                positiveLabel="Warmer than baseline"
                negativeLabel="Cooler than baseline"
                emptyLabel="No signed anomaly deviations were returned."
              />
              {anomalyRecords.length ? (
                <div className="data-card-list">
                  {anomalyRecords.map((record, index) => (
                    <article
                      className="data-card"
                      key={`${String(record.calendar_year)}-${String(record.district)}-${index}`}
                    >
                      <header>
                        <strong>
                          {textFrom(
                            record,
                            ["district"],
                            "Weather observation",
                          )}
                          {" · "}
                          {textFrom(record, ["state"])}
                        </strong>
                        <span>
                          {typeof record.calendar_year === "number"
                            ? String(record.calendar_year)
                            : textFrom(record, ["calendar_year", "year"])}
                        </span>
                      </header>
                      <dl>
                        <div>
                          <dt>Same-period temperature deviation</dt>
                          <dd>
                            {safeValue(
                              record.tmax_mean_same_period_deviation_c,
                            )}{" "}
                            °C
                          </dd>
                        </div>
                        <div>
                          <dt>Deviation baseline</dt>
                          <dd>
                            {textFrom(
                              record,
                              ["temperature_deviation_baseline"],
                              "Not reported",
                            )}
                          </dd>
                        </div>
                      </dl>
                      <PercentileStatuses
                        value={record.historical_percentile_status}
                      />
                    </article>
                  ))}
                </div>
              ) : (
                <ApiStatus loading={loading} error={null} empty />
              )}
              <ProvenanceDetails data={result.anomalies} />
            </section>

            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">05 / Crop-weather context</p>
                  <h2>Contextual alignment</h2>
                  <p>Only available when a state and district are selected.</p>
                </div>
              </header>
              {state && district ? (
                <>
                  <MetricGrid
                    items={[
                      {
                        label: "Matched crop records",
                        value: result.cropContext.matched_count,
                      },
                      {
                        label: "Unmatched records",
                        value: result.cropContext.unmatched_count,
                      },
                      {
                        label: "Season alignment verified",
                        value:
                          result.cropContext.full_season_alignment_verified,
                      },
                    ]}
                  />
                  <p className="result-interpretation">
                    {textFrom(
                      result.cropContext,
                      ["interpretation", "alignment_method"],
                      "The returned alignment metadata describes how annual weather records relate to crop records.",
                    )}
                  </p>
                  <ProvenanceDetails data={result.cropContext} />
                </>
              ) : (
                <p className="data-message">
                  Choose a state and district to request crop-weather context.
                </p>
              )}
            </section>

            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">06 / Experimental research</p>
                  <h2>Weather classifier status</h2>
                  <p>
                    This experimental classifier is separate from historical
                    weather observations.
                  </p>
                </div>
              </header>
              <MetricGrid
                items={[
                  {
                    label: "Classifier available",
                    value: classifier.execution_available,
                  },
                  {
                    label: "Artifact available",
                    value: classifier.artifact_available,
                  },
                  { label: "Research status", value: classifier.status },
                ]}
              />
              <p className="result-interpretation">
                The classifier status does not convert observed weather into a
                production-ready yield-risk forecast.
              </p>
            </section>
          </>
        )}
        <WeatherDistrictRainfallForecast />
        <WeatherFutureEnhancements />
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

function PercentileStatuses({ value }: { value: unknown }) {
  if (!isApiRecord(value)) {
    return <p className="data-message">No percentile status was reported.</p>;
  }
  const entries = Object.entries(value).filter(([, status]) =>
    isApiRecord(status),
  );
  if (!entries.length) {
    return <p className="data-message">No percentile status was reported.</p>;
  }
  return (
    <ul className="percentile-statuses">
      {entries.map(([metric, status]) => {
        const record = status as ApiRecord;
        const unit = textFrom(record, ["unit"], "");
        return (
          <li key={metric}>
            <span className="percentile-metric">
              {metric.replaceAll("_", " ")}
            </span>
            <span className="percentile-state">
              {textFrom(record, ["status"], "Not reported")}
            </span>
            <span className="percentile-value">
              {safeValue(record.value)}
              {unit ? ` ${unit}` : ""}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
