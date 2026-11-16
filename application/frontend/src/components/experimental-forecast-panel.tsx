"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  type ApiErrorCode,
  type ApiRecord,
  type ExperimentalForecastOptions,
  type ExperimentalForecastResponse,
} from "../lib/api";
import { apiErrorKeys } from "../lib/i18n";
import { isAggregateSeason } from "../lib/validation";
import { useApp } from "./app-providers";
import { PageHeading } from "./availability";
import {
  MetricGrid,
  ObservationChart,
  isApiRecord,
  recordsFrom,
  safeValue,
  textFrom,
} from "./analysis-data";

function formatNumber(value: number, language: string) {
  return new Intl.NumberFormat(language === "hi" ? "hi-IN" : "en-IN").format(
    value,
  );
}

const HIGH_HORIZONS = new Set([4, 5]);

export function ExperimentalForecastPanel() {
  const { t, language } = useApp();
  const [options, setOptions] = useState<ExperimentalForecastOptions | null>(
    null,
  );
  const [optionsError, setOptionsError] = useState<ApiErrorCode | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ExperimentalForecastResponse | null>(
    null,
  );
  const [selectedState, setSelectedState] = useState("");
  const [selectedDistrict, setSelectedDistrict] = useState("");
  const [selectedHorizon, setSelectedHorizon] = useState("1");
  const [history, setHistory] = useState<ApiRecord | null>(null);

  const loadOptions = useCallback(async () => {
    setOptionsError(null);
    try {
      setOptions(await api.experimentalForecastOptions());
    } catch (error) {
      setOptionsError(error instanceof ApiError ? error.code : "network");
    }
  }, []);

  useEffect(() => {
    let active = true;
    api
      .experimentalForecastOptions()
      .then((value) => {
        if (active) {
          setOptions(value);
          setOptionsError(null);
        }
      })
      .catch((error: unknown) => {
        if (active)
          setOptionsError(error instanceof ApiError ? error.code : "network");
      });
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setMessage(null);
    setResult(null);
    setHistory(null);
    const season = String(form.get("season")).trim();
    if (isAggregateSeason(season)) {
      setMessage(t("totalSeasonError"));
      return;
    }
    if (!options) {
      setMessage(t("forecastOptionsUnavailable"));
      return;
    }
    const body = {
      crop: String(form.get("crop")).trim(),
      season,
      state: String(form.get("state")).trim(),
      district: String(form.get("district")).trim(),
      horizon: Number(form.get("horizon")),
    };
    if (
      !Number.isInteger(body.horizon) ||
      body.horizon < 1 ||
      body.horizon > 5 ||
      !options.crops.includes(body.crop) ||
      !options.seasons.includes(body.season) ||
      !options.states.includes(body.state) ||
      !(options.districts_by_state[body.state] ?? []).includes(body.district)
    ) {
      setMessage(t("apiValidationError"));
      return;
    }
    setBusy(true);
    try {
      const projection = await api.forecastYieldExperimental(body);
      setResult(projection);
      api
        .cropTrend(projection.crop, {
          state: projection.state,
          district: projection.district,
          season: projection.season,
          through_year_start: projection.origin_year,
        })
        .then((data) => setHistory(data as unknown as ApiRecord))
        .catch(() => setHistory(null));
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.code === "validation"
            ? t("forecastInsufficientError")
            : t(apiErrorKeys[error.code])
          : t("apiError"),
      );
    } finally {
      setBusy(false);
    }
  }

  const observations = recordsFrom(history?.observations);
  // Combine observed history with the projected point to show the boundary.
  const projectedRecord: ApiRecord = result
    ? {
        year_label: `${result.target_year} (proj)`,
        projected_value: result.predicted_yield,
      }
    : {};
  const combinedRecords: ApiRecord[] = [
    ...observations,
    ...(result ? [projectedRecord] : []),
  ];

  const stale =
    options && options.reference_year > options.latest_observation_year
      ? options.reference_year - options.latest_observation_year
      : 0;
  const isHighHorizon = result ? HIGH_HORIZONS.has(result.horizon) : false;

  return (
    <>
      <PageHeading
        eyebrow={t("forecastModeEyebrow")}
        title={t("forecastModeTitle")}
        intro={t("forecastModeIntro")}
      />
      <div className="notice glass-panel" role="note">
        <strong>{t("forecastModeNoticeTitle")}</strong>
        {t("forecastModeNotice")}
      </div>

      {options && (
        <div className="glass-panel" style={{ marginTop: 16 }}>
          <MetricGrid
            items={[
              {
                label: t("trainingCutoffLabel"),
                value: options.training_cutoff_year,
              },
              {
                label: t("latestObsLabel"),
                value: options.latest_observation_year,
              },
              { label: t("referenceYearLabel"), value: options.reference_year },
              { label: t("staleDataWarning"), value: stale },
            ]}
          />
        </div>
      )}

      <div
        className={`prediction-workspace workspace ${result ? "has-result" : ""}`}
        style={{ marginTop: 27 }}
      >
        <section className="form-section glass-panel">
          <h2>{t("forecastFormTitle")}</h2>
          <p className="intro">{t("forecastFormDescription")}</p>
          {optionsError && (
            <div role="alert" className="inline-error">
              <p>{t("forecastOptionsUnavailable")}</p>
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
              {t("forecastOptionsLoading")}
            </p>
          )}
          <form onSubmit={submit}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="f-crop">{t("crop")}</label>
                <select id="f-crop" name="crop" required disabled={!options}>
                  <option value="">{t("selectCrop")}</option>
                  {options?.crops.map((crop) => (
                    <option key={crop} value={crop}>
                      {crop}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="f-season">{t("season")}</label>
                <select
                  id="f-season"
                  name="season"
                  required
                  disabled={!options}
                >
                  <option value="">{t("selectSeason")}</option>
                  {options?.seasons.map((season) => (
                    <option key={season} value={season}>
                      {season}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="f-state">{t("state")}</label>
                <select
                  id="f-state"
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
                <label htmlFor="f-district">{t("district")}</label>
                <input
                  id="f-district"
                  name="district"
                  required
                  disabled={!selectedState}
                  list="experimental-districts"
                  placeholder={t("districtPlaceholder")}
                  value={selectedDistrict}
                  onChange={(event) => setSelectedDistrict(event.target.value)}
                  autoComplete="off"
                />
                <datalist id="experimental-districts">
                  {(options?.districts_by_state[selectedState] ?? []).map(
                    (district) => (
                      <option key={district} value={district} />
                    ),
                  )}
                </datalist>
              </div>
              <div className="field">
                <label htmlFor="f-horizon">{t("forecastHorizonLabel")}</label>
                <select
                  id="f-horizon"
                  name="horizon"
                  required
                  disabled={!options}
                  value={selectedHorizon}
                  onChange={(event) => setSelectedHorizon(event.target.value)}
                >
                  {options?.valid_horizons.map((horizon) => (
                    <option key={horizon} value={horizon}>
                      T+{horizon}
                      {HIGH_HORIZONS.has(horizon)
                        ? ` · ${t("lowEvidenceLabel")}`
                        : ""}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <p className="form-help" style={{ margin: "15px 0" }}>
              {t("eligibilityRulesHeading")}:{" "}
              {Object.entries(options?.eligibility_rules ?? {}).map(
                ([rule, text]) => (
                  <span key={rule}>
                    <strong>{rule}</strong> — {text}.{" "}
                  </span>
                ),
              )}
            </p>
            <button
              className="primary-button"
              type="submit"
              disabled={busy || !options}
            >
              {busy ? t("apiLoading") : t("requestProjection")}
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
              <p className="eyebrow">{t("forecastResultEyebrow")}</p>
              <div className="yield-lead">
                <span className="yield-figure">
                  {formatNumber(result.predicted_yield, language)}
                  <small>{result.unit}</small>
                </span>
                <span
                  className={`evidence-badge predicted${isHighHorizon ? " low-evidence" : ""}`}
                >
                  {isHighHorizon
                    ? t("lowEvidenceLabel")
                    : t("experimentalQuality")}
                </span>
              </div>

              <p className="yield-plain">
                {`The model projects approximately ${formatNumber(result.predicted_yield, language)} ${result.unit} for ${result.crop} in ${result.district}, ${result.state} for the ${result.target_year} agricultural year (horizon T+${result.horizon}), based on historical training data through ${result.origin_year}.`}
              </p>

              {isHighHorizon && (
                <p className="yield-period-note">{t("highHorizonNote")}</p>
              )}
              {!result.future_projection && (
                <p className="inline-error" role="alert">
                  {t("notFutureWarning")}
                </p>
              )}

              <MetricGrid
                items={[
                  { label: t("originYearLabel"), value: result.origin_year },
                  { label: t("targetYearLabel"), value: result.target_year },
                  {
                    label: t("historyCountLabel"),
                    value: result.history_count,
                  },
                  {
                    label: t("eligibilityStatusLabel"),
                    value: result.eligibility_status,
                  },
                  {
                    label: t("futureStatusLabel"),
                    value: result.target_year_status,
                  },
                ]}
              />

              <div className="yield-context-chips">
                <span className="chip">{result.crop}</span>
                <span className="chip">{result.season}</span>
                <span className="chip">
                  {result.district}, {result.state}
                </span>
                <span className="chip">T+{result.horizon}</span>
              </div>

              {observations.length > 0 && (
                <section
                  className="yield-history-section"
                  aria-label={t("observedVsProjectedTitle")}
                >
                  <header className="chart-heading">
                    <div>
                      <h3>{t("observedVsProjectedTitle")}</h3>
                      <p>{t("observedVsProjectedSub")}</p>
                    </div>
                  </header>
                  <ObservationChart
                    title={t("observedVsProjectedTitle")}
                    subtitle={t("boundaryNote")}
                    records={combinedRecords}
                    labelKeys={["year_label", "year_start"]}
                    valueKeys={["yield_value", "projected_value"]}
                    unit={textFrom(observations[0], ["unit"], result.unit)}
                    variant="line"
                  />
                  <div className="evidence-legend">
                    <span className="legend-swatch observed" />
                    {t("evidenceObserved")} · {observations.length}
                    <span className="legend-swatch predicted" />
                    {t("evidencePredicted")} —{" "}
                    {formatNumber(result.predicted_yield, language)}{" "}
                    {result.unit} ({result.target_year})
                  </div>
                </section>
              )}

              <h4 className="yield-evidence-note">{t("warningsHeading")}</h4>
              <ul className="reason-list">
                {result.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>

              <details className="provenance-details yield-methodology">
                <summary>{t("methodologyToggle")}</summary>
                <dl className="provenance-list">
                  <div>
                    <dt>{t("modelIdLabel")}</dt>
                    <dd>{result.provenance.model_id}</dd>
                  </div>
                  <div>
                    <dt>{t("modelVersion")}</dt>
                    <dd>{result.provenance.model_version}</dd>
                  </div>
                  <div>
                    <dt>{t("strategyLabel")}</dt>
                    <dd>
                      {result.provenance.strategy} ·{" "}
                      {result.provenance.base_model}
                    </dd>
                  </div>
                  <div>
                    <dt>{t("cohortLabel")}</dt>
                    <dd>{result.provenance.cohort}</dd>
                  </div>
                  <div>
                    <dt>{t("trainingCutoffLabel")}</dt>
                    <dd>{result.provenance.training_cutoff_year}</dd>
                  </div>
                  <div>
                    <dt>{t("latestObsLabel")}</dt>
                    <dd>{result.provenance.latest_observation_year}</dd>
                  </div>
                  <div>
                    <dt>{t("referenceYearLabel")}</dt>
                    <dd>{result.provenance.reference_year}</dd>
                  </div>
                  <div>
                    <dt>{t("targetUnit")}</dt>
                    <dd>
                      {result.unit} ·{" "}
                      {result.unit_status === "verified"
                        ? t("unitVerificationValueVerified")
                        : t("unitVerificationValuePending")}
                    </dd>
                  </div>
                  <div>
                    <dt>{t("designWidthLabel")}</dt>
                    <dd>{result.provenance.design_width}</dd>
                  </div>
                  <div>
                    <dt>{t("qualityStatusLabel")}</dt>
                    <dd>
                      {result.quality_status} · {t("experimentalQuality")}
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
                    <dt>{t("artifactHash")}</dt>
                    <dd>{result.provenance.artifact_sha256}</dd>
                  </div>
                  <div>
                    <dt>{t("metadataHashLabel")}</dt>
                    <dd>{result.provenance.metadata_sha256}</dd>
                  </div>
                </dl>
                <h4>{t("researchMetricsHeading")}</h4>
                <ul className="reason-list">
                  {Object.entries(
                    result.provenance.research_expanding_window_mae,
                  ).map(([horizon, mae]) => (
                    <li key={horizon}>
                      T+{horizon}: {safeValue(Math.round(mae))} kg/ha
                    </li>
                  ))}
                </ul>
                <p>
                  <strong>{t("unitSourceLabel")}: </strong>
                  <a
                    href={result.provenance.target_unit_source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {result.provenance.target_unit_source}
                  </a>
                </p>
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
              <p>{message ?? t("forecastModeIntro")}</p>
              {isApiRecord(history) && <p>{t("observedVsProjectedTitle")}</p>}
            </>
          )}
        </aside>
      </div>
    </>
  );
}
