"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import {
  api,
  type WeatherMlDistrictForecastResponse,
  type WeatherMlDistrictOptionsResponse,
} from "../lib/api";
import { useApp } from "./app-providers";
import { ApiStatus, MetricGrid, ObservationChart } from "./analysis-data";

export function WeatherDistrictRainfallForecast() {
  const { t } = useApp();
  const [options, setOptions] =
    useState<WeatherMlDistrictOptionsResponse | null>(null);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [forecast, setForecast] =
    useState<WeatherMlDistrictForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .weatherMlDistrictOptions()
      .then((data) => {
        if (!active) return;
        setOptions(data);
        setState(data.states[0] ?? "");
        setOptionsError(null);
      })
      .catch(() => {
        if (active) setOptionsError(t("districtForecastOptionsError"));
      })
      .finally(() => {
        if (active) setOptionsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [t]);

  const districts = useMemo(
    () => options?.districts_by_state[state] ?? [],
    [options, state],
  );
  const periodLabel = useCallback(
    (horizon: number) =>
      horizon === 1
        ? t("forecastTomorrow")
        : t("forecastInDays").replace("{days}", String(horizon)),
    [t],
  );
  const chartRecords = useMemo(
    () =>
      (forecast?.horizons ?? []).map((horizon) => ({
        label: periodLabel(horizon.horizon),
        target_date: horizon.target_date,
        value: horizon.expected_precipitation_mm_day,
      })),
    [forecast, periodLabel],
  );

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!state || !district) return;
    setLoading(true);
    setError(null);
    setForecast(null);
    try {
      setForecast(await api.weatherMlDistrictForecast({ state, district }));
    } catch {
      setError(t("districtForecastError"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="resource-section">
      <header>
        <div>
          <p className="eyebrow">{t("districtForecastEyebrow")}</p>
          <h2>{t("districtForecastTitle")}</h2>
          <p>{t("districtForecastIntro")}</p>
        </div>
      </header>
      <ApiStatus loading={optionsLoading} error={optionsError} />
      {options && (
        <>
          <form className="analysis-toolbar" onSubmit={generate}>
            <div className="field">
              <label htmlFor="rainfall-state">{t("state")}</label>
              <select
                id="rainfall-state"
                value={state}
                onChange={(event) => {
                  setState(event.target.value);
                  setDistrict("");
                  setForecast(null);
                }}
              >
                {options.states.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="rainfall-district">{t("district")}</label>
              <select
                id="rainfall-district"
                value={district}
                onChange={(event) => {
                  setDistrict(event.target.value);
                  setForecast(null);
                }}
              >
                <option value="">{t("selectDistrict")}</option>
                {districts.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
            <button
              className="primary-button"
              disabled={loading || !state || !district}
              type="submit"
            >
              {loading ? t("generating") : t("generateRainfallForecast")}
            </button>
          </form>
          <ApiStatus loading={loading} error={error} />
          {forecast && (
            <>
              <div className="notice glass-panel" role="note">
                <strong>{t("archiveDemoTitle")}</strong>
                <p>{forecast.notice}</p>
              </div>
              <MetricGrid
                items={[
                  { label: t("state"), value: forecast.state },
                  { label: t("district"), value: forecast.district },
                  {
                    label: t("forecastOrigin"),
                    value: forecast.forecast_origin_date,
                  },
                  {
                    label: t("validGridCells"),
                    value: `${forecast.spatial.valid_cell_count}/${forecast.spatial.total_intersecting_cell_count}`,
                  },
                  {
                    label: t("archiveEnd"),
                    value: forecast.archive_end_date ?? t("notReported"),
                  },
                ]}
              />
              <p className="result-interpretation">
                {t("districtForecastMethodology")}
              </p>
              {forecast.forecast_available ? (
                <>
                  <ObservationChart
                    title={t("forecastChartTitle")}
                    subtitle={t("forecastChartSubtitle")}
                    records={chartRecords}
                    labelKeys={["label", "target_date"]}
                    valueKeys={["value"]}
                    unit="mm/day"
                    variant="line"
                  />
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>{t("forecastPeriod")}</th>
                          <th>{t("targetDate")}</th>
                          <th>{t("rainfallMm")}</th>
                          <th>{t("chanceOfRain")}</th>
                          <th>{t("rainOnWetDays")}</th>
                          <th>{t("gridCellRange")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {forecast.horizons.map((horizon) => (
                          <tr key={horizon.horizon}>
                            <td>{periodLabel(horizon.horizon)}</td>
                            <td>{horizon.target_date}</td>
                            <td>
                              {horizon.expected_precipitation_mm_day.toFixed(3)}
                            </td>
                            <td>
                              {(horizon.wet_probability * 100).toFixed(1)}%
                            </td>
                            <td>
                              {horizon.conditional_wet_amount_mm_day.toFixed(3)}
                            </td>
                            <td>
                              {horizon.min_cell_expected_mm_day.toFixed(3)}–
                              {horizon.max_cell_expected_mm_day.toFixed(3)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <p className="data-message">{forecast.message}</p>
              )}
              <ul className="reason-list">
                {forecast.limitations.map((limitation) => (
                  <li key={limitation}>{limitation}</li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </section>
  );
}
