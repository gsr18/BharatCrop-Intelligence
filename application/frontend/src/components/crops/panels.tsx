"use client";

import type {
  APYDataProvenance,
  CropComparisonResponse,
  CropEvidenceResponse,
  CropRankingModelProvenance,
  CropRankingResponse,
  CropTrendObservation,
  CropHistoricalStatistics,
  RankedCropCandidate,
} from "../../lib/api";
import {
  basisSpread,
  comparisonRows,
  formatNumber,
  rankedCandidates,
  summariseEvidence,
  summariseStatistics,
  topByBasis,
} from "../../lib/crop-analysis";

const NOT_REPORTED = "Not reported";

export function MainResultPanel({
  result,
  language,
  labels,
}: {
  result: CropRankingResponse;
  language: "en" | "hi";
  labels: {
    title: string;
    subtitle: string;
    locationLabel: string;
    seasonLabel: string;
    dataYearLabel: string;
    coverageLabel: string;
    basisValueLabel: string;
    topCropLabel: string;
    spreadLabel: string;
    eligibleLabel: string;
    rankedLabel: string;
    noRankingLabel: string;
    unitLabel: string;
    modelReferenceLabel: string;
    qualityLabel: string;
    experimentalValue: string;
    productionValue: (approved: boolean) => string;
    periodInLabel: string;
    periodOutLabel: string;
  };
}) {
  const ranked = rankedCandidates(result.candidates);
  const top = topByBasis(result.candidates);
  const spread = basisSpread(result.candidates);
  const period =
    result.ranking_model.prediction_period_status === "in_training_range"
      ? labels.periodInLabel
      : labels.periodOutLabel;
  const coverage = `${result.data_period_start}–${result.latest_data_year}`;

  return (
    <section className="resource-section crop-result-panel">
      <header>
        <div>
          <h2>{labels.title}</h2>
          <p>{labels.subtitle}</p>
        </div>
      </header>
      {!result.ranking_available || !top ? (
        <p className="data-message">{labels.noRankingLabel}</p>
      ) : (
        <div className="analysis-metrics">
          <article className="analysis-metric">
            <span>{labels.locationLabel}</span>
            <strong>
              {result.state} — {result.district}
            </strong>
            <small>
              {labels.seasonLabel}: {result.season}
            </small>
          </article>
          <article className="analysis-metric">
            <span>{labels.dataYearLabel}</span>
            <strong>{result.latest_data_year}</strong>
            <small>
              {labels.coverageLabel}: {coverage}
            </small>
          </article>
          <article className="analysis-metric">
            <span>{labels.topCropLabel}</span>
            <strong>{top.crop}</strong>
            <small>
              {labels.basisValueLabel}:{" "}
              {typeof top.ranking_value === "number"
                ? formatNumber(top.ranking_value, language)
                : NOT_REPORTED}{" "}
              {top.unit || labels.unitLabel}
            </small>
          </article>
          {spread && spread.difference > 0 && ranked.length > 1 ? (
            <article className="analysis-metric">
              <span>{labels.spreadLabel}</span>
              <strong>
                {formatNumber(spread.difference, language)}{" "}
                {spread.unit || labels.unitLabel}
              </strong>
              <small>
                {formatNumber(spread.highest, language)}
                {" – "}
                {formatNumber(spread.lowest, language)}
              </small>
            </article>
          ) : null}
          <article className="analysis-metric">
            <span>{labels.eligibleLabel}</span>
            <strong>
              {ranked.length} / {result.candidates.length}
            </strong>
            <small>
              {labels.rankedLabel}: {result.ranked_candidate_count}
            </small>
          </article>
          <article className="analysis-metric">
            <span>{labels.modelReferenceLabel}</span>
            <strong>{result.reference_year}</strong>
            <small>{period}</small>
          </article>
          <article className="analysis-metric">
            <span>{labels.qualityLabel}</span>
            <strong>{labels.experimentalValue}</strong>
            <small>
              {labels.productionValue(result.ranking_model.production_approved)}
            </small>
          </article>
        </div>
      )}
    </section>
  );
}

export function HistoricalComparisonTable({
  comparison,
  loading,
  error,
  language,
  labels,
}: {
  comparison: CropComparisonResponse | null;
  loading: boolean;
  error: string | null;
  language: "en" | "hi";
  labels: {
    title: string;
    subtitle: string;
    cropHeader: string;
    historicalHeader: string;
    recentHeader: string;
    coverageHeader: string;
    yearsHeader: string;
    evidenceHeader: string;
    unitHeader: string;
    loadingLabel: string;
    emptyLabel: string;
    rangeSeparator: string;
  };
}) {
  const rows = comparisonRows(comparison);
  return (
    <section className="resource-section">
      <header>
        <div>
          <h2>{labels.title}</h2>
          <p>{labels.subtitle}</p>
        </div>
      </header>
      {loading ? (
        <p className="loading-line" role="status">
          {labels.loadingLabel}
        </p>
      ) : error ? (
        <p className="inline-error" role="alert">
          {error}
        </p>
      ) : !rows.length ? (
        <p className="data-message">{labels.emptyLabel}</p>
      ) : (
        <div className="table-scroll">
          <table className="comparison-table crop-history-table">
            <thead>
              <tr>
                <th scope="col">{labels.cropHeader}</th>
                <th scope="col">{labels.historicalHeader}</th>
                <th scope="col">{labels.recentHeader}</th>
                <th scope="col">{labels.yearsHeader}</th>
                <th scope="col">{labels.coverageHeader}</th>
                <th scope="col">{labels.evidenceHeader}</th>
                <th scope="col">{labels.unitHeader}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const range =
                  row.firstYear !== undefined && row.lastYear !== undefined
                    ? `${row.firstYear}${labels.rangeSeparator}${row.lastYear}`
                    : NOT_REPORTED;
                return (
                  <tr key={row.crop}>
                    <th scope="row">{row.crop}</th>
                    <td>
                      {row.historicalMedian === null
                        ? NOT_REPORTED
                        : formatNumber(row.historicalMedian, language)}
                    </td>
                    <td>
                      {row.recentMedian === null
                        ? NOT_REPORTED
                        : formatNumber(row.recentMedian, language)}
                    </td>
                    <td>{range}</td>
                    <td>
                      {row.validYears} / {row.validObservations}
                    </td>
                    <td>{row.evidenceQuality}</td>
                    <td>{row.unit}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function DataCoveragePanel({
  selectedCrop,
  statistics,
  evidence,
  loading,
  error,
  language,
  labels,
}: {
  selectedCrop: string | null;
  statistics: CropHistoricalStatistics | null;
  evidence: CropEvidenceResponse | null;
  loading: boolean;
  error: string | null;
  language: "en" | "hi";
  labels: {
    title: string;
    subtitle: string;
    loadingLabel: string;
    emptyLabel: string;
    validYearsLabel: string;
    validObservationsLabel: string;
    sourceObservationsLabel: string;
    excludedObservationsLabel: string;
    firstYearLabel: string;
    lastYearLabel: string;
    recentCoverageLabel: string;
    evidenceQualityLabel: string;
    standardDeviationLabel: string;
    coefficientOfVariationLabel: string;
    trendLabel: string;
    cropLabel: string;
    perYearUnit: string;
  };
}) {
  if (loading) {
    return (
      <section className="resource-section">
        <header>
          <div>
            <h2>{labels.title}</h2>
            <p>{labels.subtitle}</p>
          </div>
        </header>
        <p className="loading-line" role="status">
          {labels.loadingLabel}
        </p>
      </section>
    );
  }
  if (error) {
    return (
      <section className="resource-section">
        <header>
          <div>
            <h2>{labels.title}</h2>
            <p>{labels.subtitle}</p>
          </div>
        </header>
        <p className="inline-error" role="alert">
          {error}
        </p>
      </section>
    );
  }
  if (!statistics || !selectedCrop) {
    return (
      <section className="resource-section">
        <header>
          <div>
            <h2>{labels.title}</h2>
            <p>{labels.subtitle}</p>
          </div>
        </header>
        <p className="data-message">{labels.emptyLabel}</p>
      </section>
    );
  }
  const summary = summariseStatistics(statistics);
  const evidenceSummary = summariseEvidence(evidence);
  const items: Array<{ label: string; value: string | number | null }> = [
    { label: labels.cropLabel, value: selectedCrop },
    { label: labels.validYearsLabel, value: summary.validYears },
    { label: labels.validObservationsLabel, value: summary.validObservations },
    {
      label: labels.firstYearLabel,
      value: summary.firstYear ?? null,
    },
    {
      label: labels.lastYearLabel,
      value: summary.lastYear ?? null,
    },
    {
      label: labels.recentCoverageLabel,
      value: `${Math.round((statistics.recent_year_coverage ?? 0) * 100)}%`,
    },
    { label: labels.evidenceQualityLabel, value: statistics.evidence_quality },
    {
      label: labels.standardDeviationLabel,
      value:
        statistics.yield_standard_deviation === null
          ? null
          : formatNumber(statistics.yield_standard_deviation, language),
    },
    {
      label: labels.coefficientOfVariationLabel,
      value:
        statistics.coefficient_of_variation === null
          ? null
          : formatNumber(statistics.coefficient_of_variation, language),
    },
    {
      label: labels.trendLabel,
      value:
        statistics.historical_trend_yield_per_year === null
          ? null
          : `${formatNumber(statistics.historical_trend_yield_per_year, language)} ${labels.perYearUnit}`,
    },
  ];
  if (evidenceSummary) {
    items.push({
      label: labels.sourceObservationsLabel,
      value: evidenceSummary.sourceObservations ?? null,
    });
    items.push({
      label: labels.excludedObservationsLabel,
      value: evidenceSummary.excludedObservations ?? null,
    });
  }
  return (
    <section className="resource-section">
      <header>
        <div>
          <h2>{labels.title}</h2>
          <p>{labels.subtitle}</p>
        </div>
      </header>
      <dl className="crop-coverage-grid">
        {items.map((item) => (
          <div key={item.label} className="crop-coverage-cell">
            <dt>{item.label}</dt>
            <dd>
              {item.value === null || item.value === undefined
                ? NOT_REPORTED
                : item.value}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function PlainLanguageAnalysis({
  sentences,
  title,
  intro,
  emptyLabel,
}: {
  sentences: string[];
  title: string;
  intro: string;
  emptyLabel: string;
}) {
  return (
    <section className="resource-section crop-analysis-section">
      <header>
        <div>
          <h2>{title}</h2>
          <p>{intro}</p>
        </div>
      </header>
      {sentences.length ? (
        <ul className="result-interpretation crop-analysis-list">
          {sentences.map((sentence) => (
            <li key={sentence}>{sentence}</li>
          ))}
        </ul>
      ) : (
        <p className="data-message">{emptyLabel}</p>
      )}
    </section>
  );
}

export function MethodologySection({
  ranking,
  trendStatistics,
  labels,
}: {
  ranking: CropRankingResponse | null;
  trendStatistics: CropHistoricalStatistics | null;
  labels: {
    summary: string;
    datasetHeading: string;
    modelNameHeading: string;
    methodologyHeading: string;
    limitationsHeading: string;
    noLimitations: string;
    datasetName: string;
    datasetSource: string;
    yearRange: string;
    recordCount: string;
    validRecordCount: string;
    yieldUnit: string;
    modelName: string;
    modelVersion: string;
    target: string;
    unit: string;
    trainingRange: string;
    quality: string;
    productionApproved: string;
    yes: string;
    no: string;
    notRecorded: string;
    historicalMedian: string;
    evidenceQuality: string;
    validYearCount: string;
    rankingBasis: string;
    referenceYear: string;
    referenceYearPolicy: string;
    latestDataYear: string;
  };
}) {
  const provenance: APYDataProvenance | null = ranking?.data_provenance ?? null;
  const model: CropRankingModelProvenance | null =
    ranking?.ranking_model ?? null;
  const limitations = ranking?.limitations ?? [];
  return (
    <details className="provenance-details crop-methodology">
      <summary>{labels.summary}</summary>
      {provenance ? (
        <>
          <h4>{labels.datasetHeading}</h4>
          <dl className="provenance-list">
            <div>
              <dt>{labels.datasetName}</dt>
              <dd>{provenance.dataset_name}</dd>
            </div>
            <div>
              <dt>{labels.datasetSource}</dt>
              <dd>{provenance.dataset_source}</dd>
            </div>
            <div>
              <dt>{labels.yearRange}</dt>
              <dd>
                {provenance.year_start}–{provenance.year_end}
              </dd>
            </div>
            <div>
              <dt>{labels.recordCount}</dt>
              <dd>{provenance.record_count}</dd>
            </div>
            <div>
              <dt>{labels.validRecordCount}</dt>
              <dd>{provenance.valid_record_count}</dd>
            </div>
            <div>
              <dt>{labels.yieldUnit}</dt>
              <dd>{provenance.yield_unit}</dd>
            </div>
          </dl>
        </>
      ) : null}
      {model ? (
        <>
          <h4>{labels.modelNameHeading}</h4>
          <dl className="provenance-list">
            <div>
              <dt>{labels.modelName}</dt>
              <dd>{model.model_name}</dd>
            </div>
            <div>
              <dt>{labels.modelVersion}</dt>
              <dd>{model.model_version ?? labels.notRecorded}</dd>
            </div>
            <div>
              <dt>{labels.target}</dt>
              <dd>{model.target}</dd>
            </div>
            <div>
              <dt>{labels.unit}</dt>
              <dd>{model.unit}</dd>
            </div>
            <div>
              <dt>{labels.trainingRange}</dt>
              <dd>
                {model.training_year_start}–{model.training_year_end}
              </dd>
            </div>
            <div>
              <dt>{labels.quality}</dt>
              <dd>{model.quality_status}</dd>
            </div>
            <div>
              <dt>{labels.productionApproved}</dt>
              <dd>{model.production_approved ? labels.yes : labels.no}</dd>
            </div>
            <div>
              <dt>{labels.referenceYear}</dt>
              <dd>{model.reference_year}</dd>
            </div>
            <div>
              <dt>{labels.referenceYearPolicy}</dt>
              <dd>{model.reference_year_policy}</dd>
            </div>
          </dl>
        </>
      ) : null}
      {ranking ? (
        <>
          <h4>{labels.methodologyHeading}</h4>
          <p>{ranking.ranking_methodology}</p>
          <dl className="provenance-list">
            <div>
              <dt>{labels.rankingBasis}</dt>
              <dd>{ranking.ranking_basis}</dd>
            </div>
            <div>
              <dt>{labels.latestDataYear}</dt>
              <dd>{ranking.latest_data_year}</dd>
            </div>
          </dl>
        </>
      ) : null}
      {trendStatistics ? (
        <>
          <h4>{labels.methodologyHeading}</h4>
          <dl className="provenance-list">
            <div>
              <dt>{labels.historicalMedian}</dt>
              <dd>
                {trendStatistics.historical_median_yield === null
                  ? NOT_REPORTED
                  : trendStatistics.historical_median_yield}
              </dd>
            </div>
            <div>
              <dt>{labels.evidenceQuality}</dt>
              <dd>{trendStatistics.evidence_quality}</dd>
            </div>
            <div>
              <dt>{labels.validYearCount}</dt>
              <dd>{trendStatistics.valid_year_count}</dd>
            </div>
          </dl>
        </>
      ) : null}
      <h4>{labels.limitationsHeading}</h4>
      {limitations.length ? (
        <ul>
          {limitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      ) : (
        <p>{labels.noLimitations}</p>
      )}
    </details>
  );
}

/**
 * Compact candidate detail table used inside the results section. Renders one
 * row per candidate returned by `POST /api/v1/rankings/crops`.
 */
export function CandidateTable({
  candidates,
  referenceYear,
  language,
  labels,
}: {
  candidates: RankedCropCandidate[];
  referenceYear: number;
  language: "en" | "hi";
  labels: {
    cropHeader: string;
    yieldRankHeader: string;
    evidenceRankHeader: string;
    basisValueHeader: string;
    historicalMedianHeader: string;
    recentMedianHeader: string;
    modelEstimateHeader: string;
    variabilityHeader: string;
    evidenceQualityHeader: string;
    coverageHeader: string;
    latestYearHeader: string;
    detailsHeader: string;
    meanYieldLabel: string;
    standardDeviationLabel: string;
    trendLabel: string;
    observationsLabel: string;
    validYearsLabel: string;
    recentCoverageLabel: string;
    latestObservationLabel: string;
    yesLabel: string;
    noLabel: string;
    modelDifferenceLabel: string;
    predictionPeriodLabel: string;
    periodInLabel: string;
    periodOutLabel: string;
    modelReferenceLabel: string;
    eligibilityReasonLabel: string;
    eligibilityHeader: string;
    eligibleValue: string;
    ineligibleValue: string;
    modelUnsupportedValue: string;
    warningLabel: string;
  };
}) {
  const modelHeader = labels.modelEstimateHeader.replace(
    "{year}",
    String(referenceYear),
  );
  return (
    <div className="table-scroll">
      <table className="comparison-table crop-candidate-table">
        <thead>
          <tr>
            <th scope="col">{labels.cropHeader}</th>
            <th scope="col">{labels.yieldRankHeader}</th>
            <th scope="col">{labels.evidenceRankHeader}</th>
            <th scope="col">{labels.basisValueHeader}</th>
            <th scope="col">{labels.historicalMedianHeader}</th>
            <th scope="col">{labels.recentMedianHeader}</th>
            <th scope="col">{modelHeader}</th>
            <th scope="col">{labels.variabilityHeader}</th>
            <th scope="col">{labels.evidenceQualityHeader}</th>
            <th scope="col">{labels.coverageHeader}</th>
            <th scope="col">{labels.latestYearHeader}</th>
            <th scope="col">{labels.detailsHeader}</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((candidate) => {
            const stats = candidate.historical_statistics;
            return (
              <tr key={candidate.crop}>
                <th scope="row">{candidate.crop}</th>
                <td>{candidate.rank ?? NOT_REPORTED}</td>
                <td>{candidate.evidence_rank ?? NOT_REPORTED}</td>
                <td>
                  {candidate.ranking_value === null
                    ? NOT_REPORTED
                    : formatNumber(candidate.ranking_value, language)}
                </td>
                <td>
                  {stats?.historical_median_yield == null
                    ? NOT_REPORTED
                    : formatNumber(stats.historical_median_yield, language)}
                </td>
                <td>
                  {stats?.recent_median_yield == null
                    ? NOT_REPORTED
                    : formatNumber(stats.recent_median_yield, language)}
                </td>
                <td>
                  {candidate.predicted_yield === null
                    ? labels.modelUnsupportedValue
                    : formatNumber(candidate.predicted_yield, language)}
                </td>
                <td>
                  {stats?.coefficient_of_variation == null
                    ? NOT_REPORTED
                    : `${formatNumber(stats.coefficient_of_variation, language)}%`}
                </td>
                <td>{stats?.evidence_quality ?? NOT_REPORTED}</td>
                <td>
                  {stats
                    ? `${stats.recent_valid_year_count} / ${Math.max(
                        0,
                        stats.recent_window_year_end -
                          stats.recent_window_year_start +
                          1,
                      )}`
                    : NOT_REPORTED}
                </td>
                <td>{stats?.latest_observation_year ?? NOT_REPORTED}</td>
                <td>
                  <details>
                    <summary>{labels.detailsHeader}</summary>
                    <dl className="provenance-list crop-candidate-detail-list">
                      <div>
                        <dt>{labels.eligibilityHeader}</dt>
                        <dd>
                          {candidate.candidate_eligibility?.eligible
                            ? labels.eligibleValue
                            : labels.ineligibleValue}
                        </dd>
                      </div>
                      <div>
                        <dt>{labels.eligibilityReasonLabel}</dt>
                        <dd>
                          {candidate.candidate_eligibility?.reason_code ??
                            NOT_REPORTED}
                        </dd>
                      </div>
                      <div>
                        <dt>{labels.meanYieldLabel}</dt>
                        <dd>
                          {stats?.historical_mean_yield == null
                            ? NOT_REPORTED
                            : `${formatNumber(stats.historical_mean_yield, language)} ${candidate.unit}`}
                        </dd>
                      </div>
                      <div>
                        <dt>{labels.standardDeviationLabel}</dt>
                        <dd>
                          {stats?.yield_standard_deviation == null
                            ? NOT_REPORTED
                            : `${formatNumber(stats.yield_standard_deviation, language)} ${candidate.unit}`}
                        </dd>
                      </div>
                      <div>
                        <dt>{labels.trendLabel}</dt>
                        <dd>
                          {stats?.historical_trend_yield_per_year == null
                            ? NOT_REPORTED
                            : `${formatNumber(stats.historical_trend_yield_per_year, language)} ${candidate.unit} / year`}
                        </dd>
                      </div>
                      <div>
                        <dt>{labels.observationsLabel}</dt>
                        <dd>
                          {stats?.valid_observation_count ?? NOT_REPORTED}
                        </dd>
                      </div>
                      <div>
                        <dt>{labels.validYearsLabel}</dt>
                        <dd>{stats?.valid_year_count ?? NOT_REPORTED}</dd>
                      </div>
                      <div>
                        <dt>{labels.recentCoverageLabel}</dt>
                        <dd>
                          {stats
                            ? `${stats.recent_valid_year_count} / ${Math.max(
                                0,
                                stats.recent_window_year_end -
                                  stats.recent_window_year_start +
                                  1,
                              )} (${formatNumber(
                                stats.recent_year_coverage * 100,
                                language,
                              )}%)`
                            : NOT_REPORTED}
                        </dd>
                      </div>
                      <div>
                        <dt>{labels.latestObservationLabel}</dt>
                        <dd>
                          {candidate.has_observation_in_latest_year
                            ? labels.yesLabel
                            : labels.noLabel}
                        </dd>
                      </div>
                      <div>
                        <dt>{labels.modelReferenceLabel}</dt>
                        <dd>
                          {candidate.predicted_yield === null
                            ? NOT_REPORTED
                            : (candidate.model_reference_year ?? referenceYear)}
                        </dd>
                      </div>
                      <div>
                        <dt>{labels.modelDifferenceLabel}</dt>
                        <dd>
                          {candidate.model_difference_from_median == null
                            ? NOT_REPORTED
                            : `${formatNumber(candidate.model_difference_from_median, language)} ${candidate.unit}`}
                        </dd>
                      </div>
                      <div>
                        <dt>{labels.predictionPeriodLabel}</dt>
                        <dd>
                          {candidate.model_prediction_period_status ===
                          "in_training_range"
                            ? labels.periodInLabel
                            : candidate.model_prediction_period_status ===
                                "out_of_training_range_extrapolation"
                              ? labels.periodOutLabel
                              : (candidate.model_prediction_period_status ??
                                NOT_REPORTED)}
                        </dd>
                      </div>
                    </dl>
                    {candidate.warnings?.length ? (
                      <div className="crop-candidate-warnings">
                        <strong>{labels.warningLabel}</strong>
                        <ul>
                          {candidate.warnings.map((warning) => (
                            <li key={`${candidate.crop}-${warning}`}>
                              {warning}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </details>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Small observations table shown when a trend chart exists so keyboard and
 * screen-reader users can access the same numbers as the visual line chart.
 */
export function ObservationTable({
  observations,
  language,
  labels,
}: {
  observations: CropTrendObservation[];
  language: "en" | "hi";
  labels: {
    yearHeader: string;
    yieldHeader: string;
    areaHeader: string;
    productionHeader: string;
    unitHeader: string;
  };
}) {
  if (!observations.length) return null;
  return (
    <div className="table-scroll crop-observation-table">
      <table className="comparison-table">
        <caption className="sr-only">
          {labels.yearHeader} / {labels.yieldHeader}
        </caption>
        <thead>
          <tr>
            <th scope="col">{labels.yearHeader}</th>
            <th scope="col">{labels.yieldHeader}</th>
            <th scope="col">{labels.areaHeader}</th>
            <th scope="col">{labels.productionHeader}</th>
            <th scope="col">{labels.unitHeader}</th>
          </tr>
        </thead>
        <tbody>
          {observations.map((entry) => (
            <tr key={entry.year_start}>
              <th scope="row">{entry.year_label}</th>
              <td>{formatNumber(entry.yield_value, language)}</td>
              <td>{formatNumber(entry.area, language)}</td>
              <td>{formatNumber(entry.production, language)}</td>
              <td>{entry.unit}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
