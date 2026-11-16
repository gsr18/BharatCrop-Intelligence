"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  type ApiRecord,
  type CropComparisonResponse,
  type CropEvidenceResponse,
  type CropRankingOptionsResponse,
  type CropRankingRequest,
  type CropRankingResponse,
  type CropTrendObservation,
  type CropTrendResponse,
} from "../lib/api";
import { useApp } from "./app-providers";
import { PageHeading } from "./availability";
import { recordsFrom, textFrom } from "./analysis-data";
import { SearchableSelect } from "./crops/searchable-select";
import { ComparisonChart } from "./crops/comparison-chart";
import { ObservedVsModelChart } from "./crops/observed-vs-model-chart";
import { HistoryTrendChart } from "./crops/history-trend-chart";
import {
  CandidateTable,
  DataCoveragePanel,
  HistoricalComparisonTable,
  MainResultPanel,
  MethodologySection,
  ObservationTable,
  PlainLanguageAnalysis,
} from "./crops/panels";
import {
  buildComparisonSentences,
  buildTrendSentences,
  byYieldRank,
} from "../lib/crop-analysis";

// The service discovers supported crops and years from valid APY evidence.
const TOP_N = 5;
const RANKING_BASIS: NonNullable<CropRankingRequest["ranking_basis"]> =
  "recent_median";

function narrowTrend(record: ApiRecord | null): CropTrendResponse | null {
  if (!record) return null;
  const observations = recordsFrom(record.observations).map(
    (entry): CropTrendObservation => ({
      year_start: Number(entry.year_start ?? 0),
      year_label: String(entry.year_label ?? entry.year_start ?? ""),
      area: Number(entry.area ?? 0),
      production: Number(entry.production ?? 0),
      yield_value: Number(entry.yield_value ?? 0),
      unit: String(entry.unit ?? "kg/ha"),
    }),
  );
  const statisticsRecord =
    record.statistics &&
    typeof record.statistics === "object" &&
    !Array.isArray(record.statistics)
      ? (record.statistics as ApiRecord)
      : null;
  const statistics = statisticsRecord
    ? {
        crop: String(statisticsRecord.crop ?? ""),
        historical_median_yield:
          typeof statisticsRecord.historical_median_yield === "number"
            ? statisticsRecord.historical_median_yield
            : null,
        historical_mean_yield:
          typeof statisticsRecord.historical_mean_yield === "number"
            ? statisticsRecord.historical_mean_yield
            : null,
        recent_median_yield:
          typeof statisticsRecord.recent_median_yield === "number"
            ? statisticsRecord.recent_median_yield
            : null,
        recent_window_year_start: Number(
          statisticsRecord.recent_window_year_start ?? 0,
        ),
        recent_window_year_end: Number(
          statisticsRecord.recent_window_year_end ?? 0,
        ),
        yield_standard_deviation:
          typeof statisticsRecord.yield_standard_deviation === "number"
            ? statisticsRecord.yield_standard_deviation
            : null,
        coefficient_of_variation:
          typeof statisticsRecord.coefficient_of_variation === "number"
            ? statisticsRecord.coefficient_of_variation
            : null,
        historical_trend_yield_per_year:
          typeof statisticsRecord.historical_trend_yield_per_year === "number"
            ? statisticsRecord.historical_trend_yield_per_year
            : null,
        valid_observation_count: Number(
          statisticsRecord.valid_observation_count ?? 0,
        ),
        valid_year_count: Number(statisticsRecord.valid_year_count ?? 0),
        latest_observation_year:
          typeof statisticsRecord.latest_observation_year === "number"
            ? statisticsRecord.latest_observation_year
            : null,
        valid_years: Array.isArray(statisticsRecord.valid_years)
          ? statisticsRecord.valid_years.filter(
              (year): year is number => typeof year === "number",
            )
          : [],
        recent_valid_year_count: Number(
          statisticsRecord.recent_valid_year_count ?? 0,
        ),
        recent_year_coverage: Number(
          statisticsRecord.recent_year_coverage ?? 0,
        ),
        evidence_quality: String(statisticsRecord.evidence_quality ?? ""),
        unit: String(statisticsRecord.unit ?? "kg/ha"),
      }
    : undefined;
  return {
    state: String(record.state ?? ""),
    district: String(record.district ?? ""),
    season: String(record.season ?? ""),
    through_year_start: Number(record.through_year_start ?? 0),
    // HistoricalStatistics is required by the response type; when the API
    // omits it we synthesise an empty entry so downstream code stays typed
    // and the UI falls back to "Not reported" labels.
    statistics: statistics ?? {
      crop: "",
      historical_median_yield: null,
      historical_mean_yield: null,
      recent_median_yield: null,
      recent_window_year_start: 0,
      recent_window_year_end: 0,
      yield_standard_deviation: null,
      coefficient_of_variation: null,
      historical_trend_yield_per_year: null,
      valid_observation_count: 0,
      valid_year_count: 0,
      latest_observation_year: null,
      valid_years: [],
      recent_valid_year_count: 0,
      recent_year_coverage: 0,
      evidence_quality: "",
      unit: "kg/ha",
    },
    observations,
    data_provenance:
      record.data_provenance && typeof record.data_provenance === "object"
        ? (record.data_provenance as CropTrendResponse["data_provenance"])
        : {
            dataset_name: "",
            dataset_source: "",
            source_file: "",
            sha256: "",
            record_count: 0,
            valid_record_count: 0,
            year_start: 0,
            year_end: 0,
            yield_unit: "kg/ha",
          },
    limitations: Array.isArray(record.limitations)
      ? record.limitations.filter(
          (entry): entry is string => typeof entry === "string",
        )
      : [],
  };
}

export function CropsPage() {
  const { t, language, capabilities } = useApp();
  const strings = t("cropStrings");
  const narrative = t("cropNarrative");

  const [options, setOptions] = useState<CropRankingOptionsResponse | null>(
    null,
  );
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [districtOptions, setDistrictOptions] = useState<string[]>([]);
  const [districtsError, setDistrictsError] = useState<string | null>(null);

  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [season, setSeason] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const [result, setResult] = useState<CropRankingResponse | null>(null);
  const [resultLoading, setResultLoading] = useState(false);
  const [resultError, setResultError] = useState<string | null>(null);

  const [selectedCrop, setSelectedCrop] = useState<string | null>(null);
  const [trend, setTrend] = useState<CropTrendResponse | null>(null);
  const [trendLoading, setTrendLoading] = useState(false);
  const [trendError, setTrendError] = useState<string | null>(null);

  const [evidence, setEvidence] = useState<CropEvidenceResponse | null>(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  const [comparison, setComparison] = useState<CropComparisonResponse | null>(
    null,
  );
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState<string | null>(null);

  // Monotonic request sequences used to discard stale trend/evidence/ranking
  // responses when the user changes inputs quickly.
  const trendSeqRef = useRef(0);
  const evidenceSeqRef = useRef(0);
  const rankingSeqRef = useRef(0);
  const districtOptionsSeqRef = useRef(0);

  const capability = capabilities.data?.capabilities.find(
    (item) => item.name === "crop_ranking",
  );
  const rankingAvailable = capability?.availability === "available";

  useEffect(() => {
    let active = true;
    api
      .cropRankingOptions()
      .then(
        (ranking) => {
          if (!active) return;
          setOptions(ranking);
          const firstState = ranking.selected_state ?? ranking.states[0] ?? "";
          setState(firstState);
          setDistrict(ranking.selected_district ?? "");
          setSeason(ranking.selected_season ?? ranking.seasons[0] ?? "");
          setOptionsError(null);
        },
        () => {
          if (!active) return;
          setOptionsError(strings.optionsError);
        },
      )
      .finally(() => {
        if (active) setOptionsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [strings.optionsError]);

  useEffect(() => {
    if (!state || !options) return;
    let active = true;
    const sequence = ++districtOptionsSeqRef.current;
    api
      .cropRankingOptions({ state })
      .then((response) => {
        if (!active || sequence !== districtOptionsSeqRef.current) return;
        setDistrictsError(null);
        setDistrictOptions(response.districts);
        setDistrict((current) =>
          current && response.districts.includes(current)
            ? current
            : (response.selected_district ?? response.districts[0] ?? ""),
        );
      })
      .catch(() => {
        if (active && sequence === districtOptionsSeqRef.current) {
          setDistrictsError(strings.districtsError);
        }
      });
    return () => {
      active = false;
    };
  }, [options, state, strings.districtsError]);

  const states = useMemo(() => options?.states ?? [], [options]);
  const districts = districtOptions;
  const seasons = useMemo(
    () =>
      options?.seasons?.filter(
        (entry) => entry.trim().toLowerCase() !== "total",
      ) ?? [],
    [options],
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setResultError(null);
    if (!state || !district || !season) {
      setFormError(strings.locationRequired);
      return;
    }
    if (!rankingAvailable) {
      setResultError(strings.rankingUnavailable);
      return;
    }
    const sequence = ++rankingSeqRef.current;
    setResultLoading(true);
    setResult(null);
    setComparison(null);
    setComparisonError(null);
    inspectCrop(null);
    try {
      const ranking = await api.rankCrops({
        state,
        district,
        season,
        top_n: TOP_N,
        ranking_basis: RANKING_BASIS,
      });
      if (sequence !== rankingSeqRef.current) return;
      setResult(ranking);
      setComparisonLoading(true);
      try {
        const nextComparison = await api.cropComparison({
          state,
          district,
          season,
          through_year_start: ranking.latest_data_year,
        });
        if (sequence !== rankingSeqRef.current) return;
        setComparison(nextComparison);
      } catch {
        if (sequence === rankingSeqRef.current) {
          setComparisonError(strings.historyTableError);
        }
      } finally {
        if (sequence === rankingSeqRef.current) setComparisonLoading(false);
      }
    } catch (error) {
      if (sequence !== rankingSeqRef.current) return;
      setResultError(
        error instanceof ApiError && error.status === 503
          ? strings.rankingUnavailable
          : strings.resultError,
      );
    } finally {
      if (sequence === rankingSeqRef.current) setResultLoading(false);
    }
  }

  function inspectCrop(crop: string | null) {
    setSelectedCrop(crop);
    setTrend(null);
    setEvidence(null);
    setTrendError(null);
    setEvidenceError(null);
    setTrendLoading(Boolean(crop));
    setEvidenceLoading(Boolean(crop));
  }

  const throughYear = result?.latest_data_year;

  useEffect(() => {
    if (!selectedCrop || !state || !district || !season) return;
    const trendSeq = ++trendSeqRef.current;
    const evidenceSeq = ++evidenceSeqRef.current;
    const filters = {
      state,
      district,
      season,
      through_year_start: throughYear,
    };
    api
      .cropTrend(selectedCrop, filters)
      .then((record) => {
        if (trendSeq !== trendSeqRef.current) return;
        setTrend(narrowTrend(record));
      })
      .catch(() => {
        if (trendSeq === trendSeqRef.current) setTrendError(strings.trendError);
      })
      .finally(() => {
        if (trendSeq === trendSeqRef.current) setTrendLoading(false);
      });
    api
      .cropEvidence(selectedCrop, filters)
      .then((response) => {
        if (evidenceSeq !== evidenceSeqRef.current) return;
        setEvidence(response);
      })
      .catch(() => {
        if (evidenceSeq === evidenceSeqRef.current)
          setEvidenceError(strings.coverageError);
      })
      .finally(() => {
        if (evidenceSeq === evidenceSeqRef.current) setEvidenceLoading(false);
      });
  }, [
    district,
    season,
    selectedCrop,
    state,
    strings.coverageError,
    strings.trendError,
    throughYear,
  ]);

  const comparisonSentences = useMemo(
    () =>
      result
        ? buildComparisonSentences(result, {
            highestLabel: narrative.highest,
            spreadLabel: narrative.spread,
            eligibleLabel: narrative.eligibleCount,
            noRankingLabel: narrative.noRanking,
            ineligibleLabel: narrative.ineligibleCrops,
            locale: language,
          })
        : [],
    [language, narrative, result],
  );
  const trendSentences = useMemo(
    () =>
      selectedCrop && trend
        ? buildTrendSentences(
            selectedCrop,
            trend.observations,
            trend.statistics,
            {
              trendLabel: narrative.trendRange,
              observationLabel: narrative.observationCount,
              noTrendLabel: narrative.noTrend,
              locale: language,
            },
          )
        : [],
    [language, narrative, selectedCrop, trend],
  );

  const analysisSentences = result
    ? [...comparisonSentences, ...(selectedCrop ? trendSentences : [])]
    : [];

  const orderedCandidates = useMemo(() => {
    if (!result) return [];
    return byYieldRank(result.candidates);
  }, [result]);

  return (
    <div className="crop-page crop-page-pass2">
      <PageHeading
        eyebrow={strings.eyebrow}
        title={strings.title}
        intro={strings.intro}
      />
      <p className="crop-explainer">{strings.explainer}</p>
      <section className="resource-layout">
        <div className="resource-section crop-controls">
          <header>
            <div>
              <p className="eyebrow">{strings.controlsTitle}</p>
              <h2>{strings.controlsHeading}</h2>
              <p>{strings.controlsIntro}</p>
            </div>
            <span
              className={`status-label ${rankingAvailable ? "ready" : "pending"}`}
            >
              {rankingAvailable
                ? t("inferenceAvailable")
                : strings.rankingUnavailable}
            </span>
          </header>
          {optionsLoading ? (
            <p className="loading-line" role="status">
              {strings.optionsLoading}
            </p>
          ) : optionsError ? (
            <p className="inline-error" role="alert">
              {optionsError}
            </p>
          ) : (
            <form
              className="crop-controls-grid"
              onSubmit={(event) => void submit(event)}
            >
              <SearchableSelect
                id="crop-state"
                label={strings.stateLabel}
                value={state}
                options={states}
                placeholder={strings.statePlaceholder}
                emptyMessage={strings.emptyOptionLabel}
                onChange={(value) => {
                  setState(value);
                  setDistrict("");
                  setDistrictOptions([]);
                  setDistrictsError(null);
                }}
              />
              <SearchableSelect
                id="crop-district"
                label={strings.districtLabel}
                value={district}
                options={districts}
                placeholder={strings.districtPlaceholder}
                emptyMessage={strings.emptyOptionLabel}
                helpText={strings.districtHint}
                disabled={!districts.length || Boolean(districtsError)}
                onChange={setDistrict}
              />
              <SearchableSelect
                id="crop-season"
                label={strings.seasonLabel}
                value={season}
                options={seasons}
                placeholder={strings.seasonPlaceholder}
                emptyMessage={strings.emptyOptionLabel}
                helpText={strings.seasonHint}
                onChange={setSeason}
              />
              <div className="crop-controls-actions">
                <button
                  className="primary-button"
                  type="submit"
                  disabled={
                    resultLoading ||
                    optionsLoading ||
                    capabilities.loading ||
                    !rankingAvailable
                  }
                >
                  {resultLoading
                    ? strings.compareButtonBusy
                    : strings.compareButton}
                </button>
                <button
                  className="icon-button"
                  type="button"
                  onClick={() => {
                    setFormError(null);
                    setResultError(null);
                    setResult(null);
                    setComparison(null);
                    inspectCrop(null);
                  }}
                >
                  {strings.resetButton}
                </button>
              </div>
            </form>
          )}
          {districtsError ? (
            <p className="inline-error" role="alert">
              {districtsError}
            </p>
          ) : null}
          {formError ? (
            <p className="inline-error" role="alert">
              {formError}
            </p>
          ) : null}
          {resultError ? (
            <p className="inline-error" role="alert">
              {resultError}
            </p>
          ) : null}
          {resultLoading ? (
            <p className="loading-line" role="status">
              {strings.resultLoading}
            </p>
          ) : null}
        </div>

        {result ? (
          <>
            <MainResultPanel
              result={result}
              language={language}
              labels={{
                title: strings.resultTitle,
                subtitle: strings.resultSubtitle,
                locationLabel: strings.locationLabel,
                seasonLabel: strings.seasonMetaLabel,
                dataYearLabel: strings.latestDataYearLabel,
                coverageLabel: strings.coveragePeriodLabel,
                basisValueLabel: strings.basisValueLabel,
                topCropLabel: strings.topCropLabel,
                spreadLabel: strings.spreadLabel,
                eligibleLabel: strings.eligibleCountLabel,
                rankedLabel: strings.rankedCountLabel,
                noRankingLabel: result.ranking_available
                  ? strings.resultEmpty
                  : narrative.noRanking,
                unitLabel: strings.unitFallbackLabel,
                modelReferenceLabel: strings.modelReferenceLabel,
                qualityLabel: strings.qualityLabel,
                experimentalValue: strings.experimentalValueLabel,
                productionValue: (approved) =>
                  approved
                    ? strings.productionApprovedLabel
                    : strings.productionNotApprovedLabel,
                periodInLabel: strings.periodInLabel,
                periodOutLabel: strings.periodOutLabel,
              }}
            />
            <PlainLanguageAnalysis
              title={strings.analysisTitle}
              intro={strings.analysisIntro}
              emptyLabel={strings.analysisEmpty}
              sentences={analysisSentences}
            />
            <div className="chart-stack">
              <ComparisonChart
                title={strings.chartComparisonTitle}
                subtitle={strings.chartComparisonSubtitle}
                candidates={orderedCandidates}
                language={language}
                unitFallback={strings.unitFallbackLabel}
                ineligibleLabel={strings.ineligibleTagLabel}
                notReportedLabel={strings.notReportedLabel}
                emptyLabel={strings.chartEmptyLabel}
                tooltipObservedLabel={strings.tooltipObservedLabel}
                tooltipEligibleLabel={strings.tooltipEligibleLabel}
              />
              <ObservedVsModelChart
                title={strings.chartObservedTitle}
                subtitle={strings.chartObservedSubtitle}
                candidates={orderedCandidates}
                language={language}
                observedLabel={strings.observedLabel}
                modelLabel={strings.modelLabel}
                notReportedLabel={strings.notReportedLabel}
                ineligibleLabel={strings.ineligibleTagLabel}
                emptyLabel={strings.chartEmptyLabel}
              />
            </div>
            {result.candidates.length ? (
              <section className="resource-section">
                <header>
                  <div>
                    <h2>{strings.trendSectionTitle}</h2>
                    <p>{strings.trendSectionIntro}</p>
                  </div>
                </header>
                <div
                  className="crop-candidate-picker"
                  role="group"
                  aria-label={strings.trendSelectHint}
                >
                  {orderedCandidates.map((candidate) => (
                    <button
                      type="button"
                      key={candidate.crop}
                      className="detail-tab"
                      aria-pressed={selectedCrop === candidate.crop}
                      onClick={() => inspectCrop(candidate.crop)}
                    >
                      {candidate.crop}
                    </button>
                  ))}
                </div>
                <CandidateTable
                  candidates={orderedCandidates}
                  referenceYear={result.reference_year}
                  language={language}
                  labels={{
                    cropHeader: strings.columnCrop,
                    yieldRankHeader: strings.columnYieldRank,
                    evidenceRankHeader: strings.columnEvidenceRank,
                    basisValueHeader: strings.columnBasisValue,
                    historicalMedianHeader: strings.columnHistoricalMedian,
                    recentMedianHeader: strings.columnRecentMedian,
                    modelEstimateHeader: strings.columnModelEstimate,
                    variabilityHeader: strings.columnVariability,
                    evidenceQualityHeader: strings.columnEvidenceQuality,
                    coverageHeader: strings.columnRecentCoverage,
                    latestYearHeader: strings.columnLatestYear,
                    detailsHeader: strings.detailsLabel,
                    meanYieldLabel: strings.columnHistoricalMean,
                    standardDeviationLabel: strings.columnStandardDeviation,
                    trendLabel: strings.columnTrend,
                    observationsLabel: strings.columnValidObservations,
                    validYearsLabel: strings.columnValidYears,
                    recentCoverageLabel: strings.columnRecentCoverage,
                    latestObservationLabel: strings.columnObservedInLatestYear,
                    yesLabel: strings.yesLabel,
                    noLabel: strings.noLabel,
                    modelDifferenceLabel: strings.columnModelDifference,
                    predictionPeriodLabel: strings.columnPredictionPeriod,
                    periodInLabel: strings.periodInLabel,
                    periodOutLabel: strings.periodOutLabel,
                    modelReferenceLabel: strings.modelReferenceLabel,
                    eligibilityReasonLabel: strings.eligibilityReasonLabel,
                    eligibilityHeader: strings.columnEligibility,
                    eligibleValue: strings.eligibleValueLabel,
                    ineligibleValue: strings.ineligibleValueLabel,
                    modelUnsupportedValue: strings.modelUnsupportedLabel,
                    warningLabel: strings.warningLabel,
                  }}
                />
                {result.ranking_available ? null : (
                  <p className="data-message" role="status">
                    {strings.notEnoughCandidates}
                  </p>
                )}
              </section>
            ) : null}
          </>
        ) : null}

        {selectedCrop ? (
          <section className="resource-section crop-trend-section">
            <header>
              <div>
                <h2>
                  {strings.chartTrendTitle} · {selectedCrop}
                </h2>
                <p>{strings.chartTrendSubtitle}</p>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setSelectedCrop(null)}
              >
                {strings.resetButton}
              </button>
            </header>
            {trendLoading ? (
              <p className="loading-line" role="status">
                {strings.trendLoading}
              </p>
            ) : trendError ? (
              <p className="inline-error" role="alert">
                {trendError}
              </p>
            ) : trend ? (
              <>
                <HistoryTrendChart
                  title={strings.chartTrendTitle}
                  subtitle={`${selectedCrop} · ${textFrom(
                    trend as unknown as ApiRecord,
                    ["season"],
                    season,
                  )}`}
                  observations={trend.observations}
                  language={language}
                  unitFallback={strings.unitFallbackLabel}
                  emptyLabel={strings.trendEmpty}
                  gapLabel={strings.trendGapLabel}
                />
                <ObservationTable
                  observations={trend.observations}
                  language={language}
                  labels={{
                    yearHeader: strings.observationTableYear,
                    yieldHeader: strings.observationTableYield,
                    areaHeader: strings.observationTableArea,
                    productionHeader: strings.observationTableProduction,
                    unitHeader: strings.columnUnit,
                  }}
                />
              </>
            ) : null}
            <DataCoveragePanel
              selectedCrop={selectedCrop}
              statistics={trend?.statistics ?? null}
              evidence={evidence}
              loading={evidenceLoading}
              error={evidenceError}
              language={language}
              labels={{
                title: strings.coverageTitle,
                subtitle: strings.coverageSubtitle,
                loadingLabel: strings.coverageLoading,
                emptyLabel: strings.coverageEmpty,
                validYearsLabel: strings.coverageValidYearsLabel,
                validObservationsLabel: strings.coverageValidObservationsLabel,
                sourceObservationsLabel:
                  strings.coverageSourceObservationsLabel,
                excludedObservationsLabel:
                  strings.coverageExcludedObservationsLabel,
                firstYearLabel: strings.coverageFirstYearLabel,
                lastYearLabel: strings.coverageLastYearLabel,
                recentCoverageLabel: strings.coverageRecentCoverageLabel,
                evidenceQualityLabel: strings.coverageEvidenceQualityLabel,
                standardDeviationLabel: strings.coverageStdDevLabel,
                coefficientOfVariationLabel: strings.coverageCoVLabel,
                trendLabel: strings.coverageTrendLabel,
                cropLabel: strings.coverageCropLabel,
                perYearUnit: strings.coveragePerYearUnit,
              }}
            />
          </section>
        ) : null}

        {result ? (
          <HistoricalComparisonTable
            comparison={comparison}
            loading={comparisonLoading}
            error={comparisonError}
            language={language}
            labels={{
              title: strings.historyTableTitle,
              subtitle: strings.historyTableSubtitle,
              cropHeader: strings.columnCrop,
              historicalHeader: strings.columnHistoricalMedian,
              recentHeader: strings.columnRecentMedian,
              coverageHeader: strings.columnCoverage,
              yearsHeader: strings.columnYears,
              evidenceHeader: strings.columnEvidenceQuality,
              unitHeader: strings.columnUnit,
              loadingLabel: strings.historyTableLoading,
              emptyLabel: strings.historyTableEmpty,
              rangeSeparator: strings.yearRangeSeparator,
            }}
          />
        ) : null}

        <MethodologySection
          ranking={result}
          trendStatistics={trend?.statistics ?? null}
          labels={{
            summary: strings.methodologySummary,
            datasetHeading: strings.methodologyDatasetHeading,
            modelNameHeading: strings.methodologyModelHeading,
            methodologyHeading: strings.methodologyDescriptionHeading,
            limitationsHeading: strings.methodologyLimitationsHeading,
            noLimitations: strings.methodologyNoLimitations,
            datasetName: strings.methodologyDatasetName,
            datasetSource: strings.methodologyDatasetSource,
            yearRange: strings.methodologyYearRange,
            recordCount: strings.methodologyRecordCount,
            validRecordCount: strings.methodologyValidRecordCount,
            yieldUnit: strings.methodologyYieldUnit,
            modelName: strings.methodologyModelName,
            modelVersion: strings.methodologyModelVersion,
            target: strings.methodologyTarget,
            unit: strings.methodologyUnit,
            trainingRange: strings.methodologyTrainingRange,
            quality: strings.methodologyQuality,
            productionApproved: strings.methodologyProductionApproved,
            yes: strings.methodologyYes,
            no: strings.methodologyNo,
            notRecorded: strings.methodologyNotRecorded,
            historicalMedian: strings.methodologyHistoricalMedian,
            evidenceQuality: strings.methodologyEvidenceQuality,
            validYearCount: strings.methodologyValidYearCount,
            rankingBasis: strings.methodologyRankingBasis,
            referenceYear: strings.methodologyReferenceYear,
            referenceYearPolicy: strings.methodologyReferenceYearPolicy,
            latestDataYear: strings.methodologyLatestDataYear,
          }}
        />
      </section>
      <section className="research-privacy-note">
        {t("criteriaTitle")}: {t("criteriaBody")}
      </section>
    </div>
  );
}
