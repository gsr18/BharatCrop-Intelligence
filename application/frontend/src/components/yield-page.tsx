"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  type ApiErrorCode,
  type ApiRecord,
  type YieldOptions,
  type YieldPredictionResponse,
} from "../lib/api";
import { apiErrorKeys } from "../lib/i18n";
import { isAggregateSeason } from "../lib/validation";
import { useApp } from "./app-providers";
import { CapabilityReasons, PageHeading } from "./availability";
import {
  MetricGrid,
  ObservationChart,
  isApiRecord,
  recordsFrom,
  safeValue,
  textFrom,
} from "./analysis-data";
import { ExperimentalForecastPanel } from "./experimental-forecast-panel";

function formatNumber(value: number, language: string) {
  return new Intl.NumberFormat(language === "hi" ? "hi-IN" : "en-IN").format(
    value,
  );
}

function fillTemplate(template: unknown, tokens: Record<string, string>) {
  if (typeof template !== "string") return "";
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    Object.hasOwn(tokens, key) ? tokens[key] : match,
  );
}

export function YieldPage() {
  const { t, capabilities, language } = useApp();
  const [mode, setMode] = useState<"manual" | "experimental">("manual");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [options, setOptions] = useState<YieldOptions | null>(null);
  const [optionsError, setOptionsError] = useState<ApiErrorCode | null>(null);
  const [selectedState, setSelectedState] = useState("");
  const [selectedDistrict, setSelectedDistrict] = useState("");
  const [selectedYear, setSelectedYear] = useState("");
  const [result, setResult] = useState<YieldPredictionResponse | null>(null);
  const [history, setHistory] = useState<ApiRecord | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const capability = capabilities.data?.capabilities.find(
    (item) => item.name === "yield_prediction",
  );

  const loadOptions = useCallback(async () => {
    try {
      const supportedOptions = await api.yieldOptions();
      setOptionsError(null);
      setOptions(supportedOptions);
      setSelectedYear(String(supportedOptions.year_end));
    } catch (error) {
      setOptionsError(error instanceof ApiError ? error.code : "network");
    }
  }, []);

  useEffect(() => {
    let active = true;
    api.yieldOptions().then(
      (supportedOptions) => {
        if (active) {
          setOptionsError(null);
          setOptions(supportedOptions);
          setSelectedYear(String(supportedOptions.year_end));
        }
      },
      (error: unknown) => {
        if (active) {
          setOptionsError(error instanceof ApiError ? error.code : "network");
        }
      },
    );
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const season = String(form.get("season")).trim();
    setMessage(null);
    setResult(null);
    setHistory(null);
    setHistoryError(null);
    if (isAggregateSeason(season)) {
      setMessage(t("totalSeasonError"));
      return;
    }
    if (!options) {
      setMessage(t("optionsUnavailable"));
      return;
    }
    const request = {
      crop: String(form.get("crop")).trim(),
      season,
      crop_category: String(form.get("crop_category")),
      state: String(form.get("state")).trim(),
      district: String(form.get("district")).trim(),
      year_start: Number(form.get("year")),
    };
    if (
      !options.crops.includes(request.crop) ||
      !options.seasons.includes(request.season) ||
      !options.crop_categories.includes(request.crop_category) ||
      !options.states.includes(request.state) ||
      !(options.districts_by_state[request.state] ?? []).includes(
        request.district,
      ) ||
      !Number.isInteger(request.year_start) ||
      request.year_start < options.year_start ||
      request.year_start > 9999
    ) {
      setMessage(t("apiValidationError"));
      return;
    }
    setBusy(true);
    try {
      const prediction = await api.predictYield(request);
      if (capability?.status !== "enabled") {
        setMessage(t("apiUnavailableError"));
      } else {
        setResult(prediction);
        setHistory(null);
        setHistoryError(null);
        setHistoryLoading(true);
      }
    } catch (reason) {
      setMessage(
        String(
          reason instanceof ApiError
            ? t(apiErrorKeys[reason.code])
            : t("unavailableResultDesc"),
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!result) return;
    let active = true;
    api
      .cropTrend(result.crop, {
        state: result.state,
        district: result.district,
        season: result.season,
        through_year_start: result.prediction_year,
      })
      .then((data) => {
        if (active) setHistory(data);
      })
      .catch(() => {
        if (active) {
          setHistory(null);
          setHistoryError(String(t("yieldHistoryError")));
        }
      })
      .finally(() => {
        if (active) setHistoryLoading(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result]);

  const observations = recordsFrom(history?.observations);
  const statistics = isApiRecord(history?.statistics)
    ? (history.statistics as ApiRecord)
    : {};
  const outOfRange =
    result?.prediction_period_status === "out_of_training_range_extrapolation";

  const plainExplanation = result
    ? fillTemplate(t("plainExplanation"), {
        crop: result.crop,
        district: result.district,
        state: result.state,
        season: result.season,
        year: String(result.prediction_year),
        unit: result.unit,
        value: formatNumber(result.prediction, language),
      })
    : "";

  return (
    <>
      <div
        className="mode-toggle"
        role="group"
        aria-label={t("modeToggleLabel")}
      >
        <button
          type="button"
          className={mode === "manual" ? "active" : ""}
          onClick={() => setMode("manual")}
        >
          {t("modeManual")}
        </button>
        <button
          type="button"
          className={mode === "experimental" ? "active" : ""}
          onClick={() => setMode("experimental")}
        >
          {t("modeExperimental")}
        </button>
      </div>
      {mode === "experimental" ? (
        <ExperimentalForecastPanel />
      ) : (
        <>
          <PageHeading
            eyebrow={t("yield")}
            title={t("yield")}
            intro={t("yieldIntro")}
          />
          <div className="notice glass-panel" role="note">
            <strong>{t("yieldNoticeTitle")}</strong>
            {t("yieldNotice")}
            <CapabilityReasons capability={capability} />
          </div>
          <div
            className={`prediction-workspace workspace ${result ? "has-result" : ""}`}
            style={{ marginTop: 27 }}
          >
            <section className="form-section glass-panel">
              <h2>{t("formTitle")}</h2>
              <p className="intro">{t("formDescription")}</p>
              {optionsError && (
                <div role="alert" className="inline-error">
                  <p>{t("optionsUnavailable")}</p>
                  <p>{t(apiErrorKeys[optionsError])}</p>
                  <button
                    type="button"
                    className="icon-button"
                    onClick={() => void loadOptions()}
                  >
                    {t("retry")}
                  </button>
                </div>
              )}
              {!options && !optionsError && (
                <p className="loading-line" role="status">
                  {t("optionsLoading")}
                </p>
              )}
              <form onSubmit={submit}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="crop">{t("crop")}</label>
                    <select id="crop" name="crop" required disabled={!options}>
                      <option value="">{t("selectCrop")}</option>
                      {options?.crops.map((crop) => (
                        <option key={crop} value={crop}>
                          {crop}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="season">{t("season")}</label>
                    <select
                      id="season"
                      name="season"
                      required
                      disabled={!options}
                    >
                      <option value="">{t("selectSeason")}</option>
                      {options?.seasons.map((seasonOption) => (
                        <option key={seasonOption} value={seasonOption}>
                          {seasonOption}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="state">{t("state")}</label>
                    <select
                      id="state"
                      name="state"
                      required
                      disabled={!options}
                      value={selectedState}
                      onChange={(event) => {
                        setSelectedState(event.target.value);
                        setSelectedDistrict("");
                      }}
                    >
                      <option value="">{t("selectState")}</option>
                      {options?.states.map((state) => (
                        <option key={state} value={state}>
                          {state}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="district">{t("district")}</label>
                    <input
                      id="district"
                      name="district"
                      required
                      disabled={!selectedState}
                      list="supported-districts"
                      placeholder={t("districtPlaceholder")}
                      value={selectedDistrict}
                      onChange={(event) =>
                        setSelectedDistrict(event.target.value)
                      }
                      autoComplete="address-level2"
                    />
                    <datalist id="supported-districts">
                      {(options?.districts_by_state[selectedState] ?? []).map(
                        (district) => (
                          <option key={district} value={district} />
                        ),
                      )}
                    </datalist>
                  </div>
                  <div className="field">
                    <label htmlFor="year">{t("year")}</label>
                    <input
                      id="year"
                      name="year"
                      type="number"
                      required
                      disabled={!options}
                      min={options?.year_start}
                      max={9999}
                      step={1}
                      value={selectedYear}
                      onChange={(event) => setSelectedYear(event.target.value)}
                    />
                    <small>
                      {options ? t("yearRange") : t("yearPlaceholder")}
                    </small>
                  </div>
                  <div className="field">
                    <label htmlFor="crop-category">{t("cropCategory")}</label>
                    <select
                      id="crop-category"
                      name="crop_category"
                      required
                      disabled={!options}
                    >
                      {options?.crop_categories.map((category) => (
                        <option key={category} value={category}>
                          {category}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <p className="form-help" style={{ margin: "15px 0" }}>
                  {t("yearRange")} {options?.year_start}–{options?.year_end}.{" "}
                  {t("extrapolationWarning")} {t("totalSeasonWarning")}
                </p>
                <button
                  className="primary-button"
                  type="submit"
                  disabled={
                    busy ||
                    !options ||
                    capabilities.loading ||
                    capability?.availability !== "available"
                  }
                >
                  {busy ? t("apiLoading") : t("requestPrediction")}
                </button>
                {message && (
                  <p className="inline-error" role="alert">
                    {message}
                  </p>
                )}
              </form>
            </section>
            <aside className="result-area glass-panel" aria-live="polite">
              {result ? (
                <div className="yield-result">
                  <p className="eyebrow">{t("yieldLeadEyebrow")}</p>
                  <div className="yield-lead">
                    <span className="yield-figure">
                      {formatNumber(result.prediction, language)}
                      <small>{result.unit}</small>
                    </span>
                    <span className="evidence-badge predicted">
                      {t("evidencePredicted")}
                    </span>
                  </div>
                  <p className="yield-plain">{plainExplanation}</p>
                  <p className="yield-period-note">
                    {outOfRange
                      ? t("extrapolationResult")
                      : t("inTrainingRangeNote")}
                  </p>
                  <p className="yield-period-note">
                    {t("estimateNotForecast")}
                  </p>
                  {outOfRange && (
                    <p className="yield-period-note">
                      {t("extrapolationNotForecast")}
                    </p>
                  )}
                  <div className="yield-context-chips">
                    <span className="chip">{result.crop}</span>
                    <span className="chip">{result.season}</span>
                    <span className="chip">
                      {result.district}, {result.state}
                    </span>
                    <span className="chip">
                      {t("year")} {result.prediction_year}
                    </span>
                  </div>

                  <section
                    className="yield-history-section"
                    aria-label={t("yieldHistoryTitle")}
                  >
                    <header className="chart-heading">
                      <div>
                        <h3>{t("yieldHistoryTitle")}</h3>
                        <p>{t("yieldHistorySub")}</p>
                      </div>
                    </header>
                    {historyLoading && (
                      <p className="loading-line" role="status">
                        {t("yieldHistoryLoading")}
                      </p>
                    )}
                    {historyError && !historyLoading && (
                      <p className="data-message data-error" role="alert">
                        {historyError}
                      </p>
                    )}
                    {!historyLoading &&
                      !historyError &&
                      observations.length === 0 && (
                        <p className="data-message">{t("yieldHistoryEmpty")}</p>
                      )}
                    {!historyLoading && observations.length > 0 && (
                      <>
                        <MetricGrid
                          items={[
                            {
                              label: t("compareModelEstimate"),
                              value: result.prediction,
                              unit: result.unit,
                            },
                            {
                              label: t("compareRecentMedian"),
                              value: statistics.recent_median_yield,
                              unit: result.unit,
                            },
                            {
                              label: t("compareHistoricalMedian"),
                              value: statistics.historical_median_yield,
                              unit: result.unit,
                            },
                          ]}
                        />
                        <ObservationChart
                          title={t("evidenceObserved")}
                          subtitle={t("yieldHistorySub")}
                          records={observations}
                          labelKeys={["year_label", "year_start"]}
                          valueKeys={["yield_value"]}
                          unit={textFrom(
                            observations[0],
                            ["unit"],
                            result.unit,
                          )}
                          variant="line"
                        />
                        <div className="evidence-legend">
                          <span className="legend-swatch observed" />
                          {t("evidenceObserved")}
                          <span className="legend-swatch predicted" />
                          {t("evidencePredicted")} —{" "}
                          {formatNumber(result.prediction, language)}{" "}
                          {result.unit} ({result.prediction_year})
                        </div>
                        <MetricGrid
                          items={[
                            {
                              label: t("coverageValidYears"),
                              value: statistics.valid_year_count,
                            },
                            {
                              label: t("coverageValidObservations"),
                              value: statistics.valid_observation_count,
                            },
                            {
                              label: t("coverageSourceObservations"),
                              value: history?.source_observation_count,
                            },
                          ]}
                        />
                      </>
                    )}
                  </section>

                  <p className="yield-evidence-note">
                    <strong>{t("yieldEvidenceTypes")}</strong>
                  </p>

                  <details className="provenance-details yield-methodology">
                    <summary>{t("methodologyToggle")}</summary>
                    <div className="yield-governance">
                      <h4>{t("governanceHeading")}</h4>
                      <dl className="provenance-list">
                        <div>
                          <dt>{t("qualityStatusLabel")}</dt>
                          <dd>
                            {safeValue(result.quality_status)} ·{" "}
                            {t("experimentalQuality")}
                          </dd>
                        </div>
                        <div>
                          <dt>{t("productionApprovalLabel")}</dt>
                          <dd>
                            {result.production_approved
                              ? t("enabled")
                              : t("notProductionApproved")}
                          </dd>
                        </div>
                        <div>
                          <dt>{t("predictionPeriodLabel")}</dt>
                          <dd>
                            {outOfRange
                              ? t("extrapolationResult")
                              : t("enabled")}{" "}
                            · {result.training_year_start}–
                            {result.training_year_end}
                          </dd>
                        </div>
                      </dl>
                    </div>
                    <h4>{t("yieldReferenceHeading")}</h4>
                    <dl className="provenance-list">
                      <div>
                        <dt>{t("modelName")}</dt>
                        <dd>{result.model_name}</dd>
                      </div>
                      <div>
                        <dt>{t("modelVersion")}</dt>
                        <dd>
                          {result.model_version ?? t("modelVersionValue")}
                        </dd>
                      </div>
                      <div>
                        <dt>{t("targetUnit")}</dt>
                        <dd>{result.unit}</dd>
                      </div>
                      <div>
                        <dt>{t("unitVerificationLabel")}</dt>
                        <dd>
                          {result.data_provenance.unit_verification_status ===
                          "verified"
                            ? t("unitVerificationValueVerified")
                            : t("unitVerificationValuePending")}
                        </dd>
                      </div>
                      <div>
                        <dt>{t("supportedDataRangeLabel")}</dt>
                        <dd>
                          {result.training_year_start}–
                          {result.training_year_end}
                        </dd>
                      </div>
                      <div>
                        <dt>{t("artifactHash")}</dt>
                        <dd>{result.artifact_sha256}</dd>
                      </div>
                      <div>
                        <dt>{t("datasetSourceLabel")}</dt>
                        <dd>{result.data_provenance.dataset_source}</dd>
                      </div>
                    </dl>
                    <p>{result.data_provenance.target_construction}</p>
                    <p>
                      <strong>{t("unitSourceLabel")}: </strong>
                      <a
                        href={result.data_provenance.unit_source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {result.data_provenance.unit_source} (
                        {result.data_provenance.unit_source_section})
                      </a>
                    </p>
                    <p>{result.data_provenance.target_consistency_check}</p>
                    <p>{t("conversionNote")}</p>
                    <h4>{t("qualityLimitations")}</h4>
                    <ul className="reason-list">
                      {result.limitations.map((limitation) => (
                        <li key={limitation}>{limitation}</li>
                      ))}
                    </ul>
                  </details>
                </div>
              ) : (
                <>
                  <p className="eyebrow">{t("evidenceTitle")}</p>
                  <h3>{t("unavailableResult")}</h3>
                  <p>{message ?? t("resultUnitUnverified")}</p>
                  <dl className="provenance-list">
                    <div>
                      <dt>{t("targetUnit")}</dt>
                      <dd>{options?.target_unit ?? t("targetUnitValue")}</dd>
                    </div>
                    <div>
                      <dt>{t("trainingPeriod")}</dt>
                      <dd>
                        {options
                          ? `${options.year_start}–${options.year_end}`
                          : t("unknown")}
                      </dd>
                    </div>
                    <div>
                      <dt>{t("routeStatus")}</dt>
                      <dd>
                        {capability?.status === "enabled"
                          ? t("enabled")
                          : t("routeDisabled")}
                      </dd>
                    </div>
                  </dl>
                </>
              )}
            </aside>
          </div>
        </>
      )}
    </>
  );
}
