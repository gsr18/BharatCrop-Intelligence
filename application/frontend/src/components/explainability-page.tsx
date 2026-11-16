"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  type ApiRecord,
  type YieldOptions,
  type YieldScenarioRequest,
} from "../lib/api";
import { useApp } from "./app-providers";
import { PageHeading } from "./availability";
import {
  ApiStatus,
  MetricGrid,
  ObservationChart,
  ProvenanceDetails,
  isApiRecord,
  recordsFrom,
  safeValue,
  textFrom,
} from "./analysis-data";
import { RankedBarChart, SignedBarChart } from "./charts/analysis-charts";

type ExplainabilityData = {
  model: ApiRecord;
  global: ApiRecord;
  evaluation: ApiRecord;
  bias: ApiRecord;
  uncertainty: ApiRecord;
};

export function ExplainabilityPage() {
  const { t, capabilities } = useApp();
  const [data, setData] = useState<ExplainabilityData | null>(null);
  const [options, setOptions] = useState<YieldOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [crop, setCrop] = useState("");
  const [season, setSeason] = useState("");
  const [category, setCategory] = useState("");
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [years, setYears] = useState<number[]>([]);
  const [scenario, setScenario] = useState<ApiRecord | null>(null);
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const yieldCapability = capabilities.data?.capabilities.find(
    (item) => item.name === "yield_prediction",
  );

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.explainabilityModels(),
      api.explainabilityGlobal(),
      api.explainabilityEvaluation(),
      api.explainabilityBias(),
      api.explainabilityUncertainty(),
      api.yieldOptions(),
    ]).then((results) => {
      if (!active) return;
      const [model, global, evaluation, bias, uncertainty, yieldOpts] = results;
      const explanationResults = results.slice(0, 5);
      if (!explanationResults.some((result) => result.status === "fulfilled")) {
        setError(
          "Explainability evidence from Notebook 21 is currently unavailable.",
        );
      } else {
        setData({
          model: model.status === "fulfilled" ? model.value : {},
          global: global.status === "fulfilled" ? global.value : {},
          evaluation: evaluation.status === "fulfilled" ? evaluation.value : {},
          bias: bias.status === "fulfilled" ? bias.value : {},
          uncertainty:
            uncertainty.status === "fulfilled" ? uncertainty.value : {},
        });
        if (explanationResults.some((result) => result.status === "rejected")) {
          setError("Some explainability sections could not be loaded.");
        }
      }
      if (yieldOpts.status === "fulfilled") {
        setOptions(yieldOpts.value);
        setCrop(yieldOpts.value.crops[0] ?? "");
        setSeason(yieldOpts.value.seasons[0] ?? "");
        setCategory(yieldOpts.value.crop_categories[0] ?? "");
        setState(yieldOpts.value.states[0] ?? "");
        setDistrict(
          yieldOpts.value.districts_by_state[
            yieldOpts.value.states[0] ?? ""
          ]?.[0] ?? "",
        );
        setYears([
          Math.max(yieldOpts.value.year_start, yieldOpts.value.year_end - 2),
          Math.max(yieldOpts.value.year_start, yieldOpts.value.year_end - 1),
          yieldOpts.value.year_end,
        ]);
      }
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  const districts = useMemo(
    () => options?.districts_by_state[state] ?? [],
    [options, state],
  );
  const importance = recordsFrom(data?.global.importance).slice(0, 10);
  const overprediction = recordsFrom(
    data?.bias.strongest_overprediction_groups,
  ).slice(0, 4);
  const underprediction = recordsFrom(
    data?.bias.strongest_underprediction_groups,
  ).slice(0, 4);
  const errorGroups = recordsFrom(data?.evaluation.highest_mae_groups).slice(
    0,
    6,
  );
  const biasRows = [...overprediction, ...underprediction]
    .map((record) => ({
      label: groupLabel(record),
      value: numericFrom(record.mean_signed_error),
      meta: [
        `Bias ${safeValue(record.mean_bias_pct_of_actual)}% of actual`,
        `${safeValue(record.observations)} historical records`,
      ].join(" · "),
    }))
    .filter(
      (row): row is { label: string; value: number; meta: string } =>
        row.value !== null,
    )
    .sort((a, b) => b.value - a.value);
  const errorRows = errorGroups
    .map((record) => ({
      label: groupLabel(record),
      value: numericFrom(record.mae),
      meta: [
        `RMSE ${safeValue(record.rmse)} kg/ha`,
        `${safeValue(record.observations)} historical records`,
      ].join(" · "),
    }))
    .filter(
      (row): row is { label: string; value: number; meta: string } =>
        row.value !== null,
    );
  const evaluationMetrics = isApiRecord(data?.evaluation.evaluation_metrics)
    ? data.evaluation.evaluation_metrics
    : isApiRecord(data?.model.evaluation_metrics)
      ? data.model.evaluation_metrics
      : {};

  async function submitScenario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setScenario(null);
    setScenarioError(null);
    if (!crop || !season || !category || !state || !district || !years.length) {
      setScenarioError(
        "Choose supported crop, season, location, and at least one year.",
      );
      return;
    }
    if (yieldCapability?.availability !== "available") {
      setScenarioError(
        "The live yield service reports scenario inference as unavailable.",
      );
      return;
    }
    const request: YieldScenarioRequest = {
      crop,
      season,
      crop_category: category,
      state,
      district,
      years,
    };
    setScenarioLoading(true);
    try {
      setScenario(await api.yieldScenario(request));
    } catch (reason) {
      setScenarioError(
        reason instanceof ApiError && reason.status === 503
          ? "Scenario inference is currently unavailable. No scenario output was returned."
          : "The scenario request could not be completed.",
      );
    } finally {
      setScenarioLoading(false);
    }
  }

  const scenarioPredictions = recordsFrom(scenario?.predictions);
  const trainingStart = options?.year_start ?? 2013;
  const trainingEnd = options?.year_end ?? 2022;

  return (
    <div className="explainability-page">
      <PageHeading
        eyebrow={t("explainability")}
        title={t("explainability")}
        intro="Inspect genuine Notebook 21 model-interpretation evidence and compare actual model outputs for supported year-based scenarios. Importance describes model behavior—not cause."
      />
      <section className="resource-layout">
        <div className="resource-section">
          <header>
            <div>
              <p className="eyebrow">01 / Global permutation importance</p>
              <h2>Which inputs mattered to this fitted model?</h2>
              <p>
                Importance is measured by how evaluation performance changes
                when an input is permuted.
              </p>
            </div>
          </header>
          <ApiStatus loading={loading} error={error} />
          {data && (
            <>
              <details className="help-popover">
                <summary>How to read this chart</summary>
                <p>
                  Permutation importance describes how the fitted model behaves
                  on its evaluation data. It does not show that an input causes
                  a yield change, and correlated inputs can share or mask
                  importance.
                </p>
              </details>
              <ObservationChart
                title="Global importance"
                subtitle={`${textFrom(data.global, ["method"], "Permutation importance")} · evaluated on ${textFrom(data.global, ["evaluation_period"], "the returned evaluation period")}`}
                records={importance}
                labelKeys={["feature", "name"]}
                valueKeys={[
                  "importance_mean_mae_increase",
                  "importance_mean",
                  "importance",
                ]}
                unit="Mean MAE increase when permuted"
              />
              <p className="result-interpretation">
                {textFrom(
                  data.global,
                  ["interpretation"],
                  "Importance is evidence about this model and evaluation sample, not a causal explanation.",
                )}
              </p>
              <MetricGrid
                items={[
                  {
                    label: "Evaluation rows",
                    value: data.global.evaluation_rows,
                  },
                  {
                    label: "Permutation repeats",
                    value: data.global.n_repeats,
                  },
                  { label: "Model", value: data.model.model_name },
                  {
                    label: "Evaluation period",
                    value: formatPeriod(
                      data.model.training_period,
                      "Not reported",
                    ),
                  },
                ]}
              />
            </>
          )}
        </div>

        {data && (
          <>
            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">02 / Evaluation performance</p>
                  <h2>Performance evidence</h2>
                  <p>
                    Reported metrics retain the model&apos;s evaluation context.
                  </p>
                </div>
              </header>
              <MetricGrid
                items={[
                  {
                    label: "Average prediction error (MAE)",
                    value: evaluationMetrics.MAE,
                    unit: "kg/ha",
                  },
                  {
                    label: "RMSE",
                    value: evaluationMetrics.RMSE,
                    unit: "kg/ha",
                  },
                  {
                    label: "Model fit indicator (R²)",
                    value: evaluationMetrics.R2,
                  },
                  {
                    label: "Evaluation rows",
                    value: evaluationMetrics.evaluation_rows,
                  },
                  {
                    label: "Evaluation period",
                    value: formatPeriod(
                      data.evaluation.evaluation_period,
                      "Not reported",
                    ),
                  },
                ]}
              />
              <div className="result-interpretation">
                {textFrom(
                  data.evaluation,
                  ["interpretation"],
                  "Performance varies by evaluation period and subgroup. Interpret metrics with their evaluation design.",
                )}
              </div>
              <ProvenanceDetails data={data.evaluation} />
            </section>

            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">03 / Crop-season error analysis</p>
                  <h2>Where errors differed</h2>
                  <p>
                    Returned groups summarize model errors, not crop
                    suitability.
                  </p>
                </div>
              </header>
              <div className="chart-grid">
                <SignedBarChart
                  title="Over- and under-prediction by group"
                  subtitle="Mean signed error · positive values over-predict, negative values under-predict"
                  unit="kg/ha"
                  rows={biasRows}
                  positiveLabel="Overprediction"
                  negativeLabel="Underprediction"
                  emptyLabel="No signed bias groups were returned."
                />
                <RankedBarChart
                  title="Highest-error crop-season groups"
                  subtitle="Average absolute error (MAE) in the evaluation sample"
                  unit="kg/ha"
                  rows={errorRows}
                  emptyLabel="No crop-season error groups were returned."
                />
              </div>
              <div className="error-detail-grid">
                <GroupList
                  title="Largest overprediction groups"
                  records={overprediction}
                />
                <GroupList
                  title="Largest underprediction groups"
                  records={underprediction}
                />
              </div>
              <ProvenanceDetails data={data.bias} />
            </section>

            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">04 / Prediction uncertainty</p>
                  <h2>What uncertainty is available?</h2>
                  <p>
                    No interval or confidence percentage is inferred when the
                    service has none.
                  </p>
                </div>
              </header>
              <MetricGrid
                items={[
                  {
                    label: "Prediction interval available",
                    value: data.uncertainty.prediction_interval_available,
                  },
                  {
                    label: "Confidence calibration available",
                    value: data.uncertainty.confidence_calibration_available,
                  },
                ]}
              />
              <p className="result-interpretation">
                {textFrom(
                  data.uncertainty,
                  ["reason"],
                  "The service reports no prediction interval or calibrated confidence percentage.",
                )}
              </p>
              <ProvenanceDetails data={data.uncertainty} />
            </section>

            <section className="resource-section">
              <header>
                <div>
                  <p className="eyebrow">05 / Year-based scenarios</p>
                  <h2>Compare genuine model outputs</h2>
                  <p>
                    All non-year inputs stay fixed; the selected years are sent
                    to the scenario API.
                  </p>
                </div>
              </header>
              {options ? (
                <form
                  className="analysis-toolbar"
                  onSubmit={(event) => void submitScenario(event)}
                >
                  <div className="field">
                    <label htmlFor="scenario-crop">{t("crop")}</label>
                    <select
                      id="scenario-crop"
                      onChange={(event) => setCrop(event.target.value)}
                      value={crop}
                    >
                      {options.crops.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="scenario-season">{t("season")}</label>
                    <select
                      id="scenario-season"
                      onChange={(event) => setSeason(event.target.value)}
                      value={season}
                    >
                      {options.seasons.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="scenario-state">{t("state")}</label>
                    <select
                      id="scenario-state"
                      onChange={(event) => {
                        setState(event.target.value);
                        setDistrict("");
                      }}
                      value={state}
                    >
                      {options.states.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="scenario-district">{t("district")}</label>
                    <select
                      id="scenario-district"
                      onChange={(event) => setDistrict(event.target.value)}
                      value={district}
                    >
                      {districts.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="scenario-category">Crop category</label>
                    <select
                      id="scenario-category"
                      onChange={(event) => setCategory(event.target.value)}
                      value={category}
                    >
                      {options.crop_categories.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </div>
                  <fieldset className="scenario-years">
                    <legend>
                      Compare years · outside-training years are extrapolations
                    </legend>
                    {Array.from(
                      { length: Math.min(15, trainingEnd - trainingStart + 4) },
                      (_, index) => trainingStart + index,
                    ).map((item) => (
                      <label key={item}>
                        <input
                          checked={years.includes(item)}
                          onChange={(event) =>
                            setYears((current) =>
                              event.target.checked
                                ? [...current, item].sort((a, b) => a - b)
                                : current.filter((year) => year !== item),
                            )
                          }
                          type="checkbox"
                        />
                        {item}
                        {item > trainingEnd ? (
                          <span className="extrapolation-chip">
                            Extrapolation
                          </span>
                        ) : null}
                      </label>
                    ))}
                  </fieldset>
                  <button
                    className="primary-button"
                    disabled={
                      scenarioLoading ||
                      capabilities.loading ||
                      yieldCapability?.availability !== "available"
                    }
                    type="submit"
                  >
                    {scenarioLoading
                      ? "Running scenarios…"
                      : "Compare scenario outputs"}
                  </button>
                </form>
              ) : (
                <p className="data-message">
                  Model-supported scenario inputs are unavailable.
                </p>
              )}
              <ApiStatus loading={scenarioLoading} error={scenarioError} />
              {scenario && (
                <>
                  {scenarioPredictions.some(
                    (item) =>
                      item.year_status === "extrapolation" ||
                      (() => {
                        const year = item.year ?? item.year_start;
                        return (
                          typeof year === "number" &&
                          (year < trainingStart || year > trainingEnd)
                        );
                      })(),
                  ) && (
                    <p className="status-label pending">
                      Contains year(s) outside the{" "}
                      {formatPeriod(
                        scenario.training_period,
                        `${trainingStart}–${trainingEnd}`,
                      )}{" "}
                      training range: extrapolation
                    </p>
                  )}
                  <ObservationChart
                    title="Returned scenario predictions"
                    subtitle="Actual model output · fixed supported inputs"
                    records={scenarioPredictions}
                    labelKeys={["year", "year_start", "prediction_year"]}
                    valueKeys={[
                      "predicted_yield",
                      "prediction",
                      "yield_prediction",
                    ]}
                    unit="kg/ha"
                    variant="line"
                  />
                  <p className="result-interpretation">
                    {textFrom(
                      scenario,
                      ["interpretation"],
                      "These are model outputs under the selected inputs, not validated future forecasts.",
                    )}
                  </p>
                  <ProvenanceDetails data={scenario} />
                </>
              )}
            </section>
          </>
        )}
      </section>
    </div>
  );
}

function GroupList({
  title,
  records,
}: {
  title: string;
  records: ApiRecord[];
}) {
  return (
    <div className="error-group-panel">
      <header>
        <div>
          <h3>{title}</h3>
          <p>Service-returned evaluation groups</p>
        </div>
      </header>
      {records.length ? (
        <div className="data-card-list">
          {records.map((record, index) => (
            <article
              className="data-card"
              key={`${textFrom(record, ["crop", "season", "group"])}-${index}`}
            >
              <header>
                <strong>{groupLabel(record)}</strong>
              </header>
              <dl>
                <div>
                  <dt>Average direction error</dt>
                  <dd>{safeValue(record.mean_signed_error)} kg/ha</dd>
                </div>
                <div>
                  <dt>Bias % of actual</dt>
                  <dd>{safeValue(record.mean_bias_pct_of_actual)}</dd>
                </div>
                <div>
                  <dt>Historical records</dt>
                  <dd>{safeValue(record.observations)}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      ) : (
        <p className="data-message">No bias groups were returned.</p>
      )}
    </div>
  );
}

function numericFrom(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function groupLabel(record: ApiRecord): string {
  const crop = textFrom(record, ["crop", "group"], "Evaluation group");
  const season = textFrom(record, ["season"], "");
  return season ? `${crop} · ${season}` : crop;
}

function formatPeriod(value: unknown, fallback = "Not reported"): string {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (isApiRecord(value)) {
    const start = value.start ?? value.year_start;
    const end = value.end ?? value.year_end;
    const hasStart = typeof start === "number" || typeof start === "string";
    const hasEnd = typeof end === "number" || typeof end === "string";
    if (hasStart && hasEnd) return `${String(start)}–${String(end)}`;
    if (hasStart || hasEnd) return String(start ?? end);
  }
  return fallback;
}
