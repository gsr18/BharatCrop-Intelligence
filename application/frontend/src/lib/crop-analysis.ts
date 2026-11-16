import type {
  CropComparisonResponse,
  CropEvidenceResponse,
  CropHistoricalStatistics,
  CropRankingResponse,
  CropTrendObservation,
  RankedCropCandidate,
} from "./api";

export function formatNumber(value: number, language: "en" | "hi") {
  return new Intl.NumberFormat(language === "hi" ? "hi-IN" : "en-IN", {
    maximumFractionDigits: 1,
  }).format(value);
}

export function fillTemplate(
  template: string,
  tokens: Record<string, string | number>,
) {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    Object.hasOwn(tokens, key) ? String(tokens[key]) : match,
  );
}

export function eligibleCandidates(
  candidates: RankedCropCandidate[],
): RankedCropCandidate[] {
  return candidates.filter(
    (candidate) => candidate.candidate_eligibility?.eligible,
  );
}

export function ineligibleCandidates(
  candidates: RankedCropCandidate[],
): RankedCropCandidate[] {
  return candidates.filter(
    (candidate) => !candidate.candidate_eligibility?.eligible,
  );
}

/** Candidates the service actually placed in the yield-based order (rank set). */
export function rankedCandidates(
  candidates: RankedCropCandidate[],
): RankedCropCandidate[] {
  return candidates.filter((candidate) => candidate.rank !== null);
}

/** The top yield-based candidate: the lowest rank number, case-folded tie-break. */
export function topByBasis(
  candidates: RankedCropCandidate[],
): RankedCropCandidate | null {
  const placed = rankedCandidates(candidates);
  if (!placed.length) return null;
  return placed.reduce((best, current) =>
    (current.rank ?? Number.POSITIVE_INFINITY) <
    (best.rank ?? Number.POSITIVE_INFINITY)
      ? current
      : best,
  );
}

function finiteBasisValues(
  candidates: RankedCropCandidate[],
): RankedCropCandidate[] {
  return candidates.filter(
    (candidate) =>
      typeof candidate.ranking_value === "number" &&
      Number.isFinite(candidate.ranking_value),
  );
}

/** Spread of the primary yield basis (recent/historical median) across candidates. */
export function basisSpread(candidates: RankedCropCandidate[]): {
  highest: number;
  lowest: number;
  difference: number;
  unit: string;
} | null {
  const withValue = finiteBasisValues(candidates);
  if (withValue.length < 2) return null;
  const values = withValue.map((candidate) => candidate.ranking_value ?? 0);
  const highest = Math.max(...values);
  const lowest = Math.min(...values);
  return {
    highest,
    lowest,
    difference: highest - lowest,
    unit: withValue[0]?.unit ?? "kg/ha",
  };
}

/** Yield-view ordering: rank ascending, then case-folded crop name. */
export function byYieldRank(
  candidates: RankedCropCandidate[],
): RankedCropCandidate[] {
  return [...candidates].sort(
    (a, b) =>
      (a.rank ?? Number.POSITIVE_INFINITY) -
        (b.rank ?? Number.POSITIVE_INFINITY) ||
      a.crop.localeCompare(b.crop, "en", { sensitivity: "base" }),
  );
}

/** Evidence-view ordering: evidence_rank ascending, then case-folded crop name. */
export function byEvidenceRank(
  candidates: RankedCropCandidate[],
): RankedCropCandidate[] {
  return [...candidates].sort(
    (a, b) =>
      (a.evidence_rank ?? Number.POSITIVE_INFINITY) -
        (b.evidence_rank ?? Number.POSITIVE_INFINITY) ||
      a.crop.localeCompare(b.crop, "en", { sensitivity: "base" }),
  );
}

export type CoverageSummary = {
  validYears: number;
  validObservations: number;
  excludedObservations?: number;
  sourceObservations?: number;
  firstYear?: number;
  lastYear?: number;
};

export function summariseStatistics(
  stats: CropHistoricalStatistics | undefined,
): CoverageSummary {
  if (!stats) {
    return { validYears: 0, validObservations: 0 };
  }
  const years = Array.isArray(stats.valid_years) ? stats.valid_years : [];
  return {
    validYears: stats.valid_year_count ?? years.length,
    validObservations: stats.valid_observation_count ?? 0,
    firstYear: years.length ? Math.min(...years) : undefined,
    lastYear: years.length ? Math.max(...years) : undefined,
  };
}

export function summariseEvidence(
  evidence: CropEvidenceResponse | null,
): CoverageSummary | null {
  if (!evidence) return null;
  const base = summariseStatistics(evidence.statistics);
  return {
    ...base,
    excludedObservations: evidence.excluded_observation_count,
    sourceObservations: evidence.source_observation_count,
  };
}

/**
 * Build a year axis covering [min, max] of the observations so that missing
 * years are represented as gaps rather than being interpolated or removed.
 */
export function buildYearAxis(observations: CropTrendObservation[]): Array<{
  year_start: number;
  year_label: string;
  yield_value: number | null;
  unit?: string;
}> {
  if (!observations.length) return [];
  const sorted = [...observations].sort((a, b) => a.year_start - b.year_start);
  const min = sorted[0].year_start;
  const max = sorted[sorted.length - 1].year_start;
  const byYear = new Map(
    sorted.map((observation) => [observation.year_start, observation]),
  );
  const axis: Array<{
    year_start: number;
    year_label: string;
    yield_value: number | null;
    unit?: string;
  }> = [];
  for (let year = min; year <= max; year += 1) {
    const match = byYear.get(year);
    if (match) {
      axis.push({
        year_start: match.year_start,
        year_label: match.year_label,
        yield_value:
          typeof match.yield_value === "number" &&
          Number.isFinite(match.yield_value)
            ? match.yield_value
            : null,
        unit: match.unit,
      });
    } else {
      axis.push({
        year_start: year,
        year_label: `${year}-${String(year + 1).slice(-2)}`,
        yield_value: null,
      });
    }
  }
  return axis;
}

export function buildComparisonSentences(
  result: CropRankingResponse,
  tokens: {
    highestLabel: string;
    spreadLabel: string;
    eligibleLabel: string;
    noRankingLabel: string;
    ineligibleLabel: string;
    locale: "en" | "hi";
  },
): string[] {
  const sentences: string[] = [];
  const eligible = eligibleCandidates(result.candidates);
  const ineligible = ineligibleCandidates(result.candidates);

  if (!result.ranking_available || !eligible.length) {
    sentences.push(tokens.noRankingLabel);
    return sentences;
  }

  const top = topByBasis(result.candidates);
  if (top && typeof top.ranking_value === "number") {
    sentences.push(
      fillTemplate(tokens.highestLabel, {
        crop: top.crop,
        value: formatNumber(top.ranking_value, tokens.locale),
        unit: top.unit,
      }),
    );
  }
  const spread = basisSpread(result.candidates);
  if (spread && spread.difference > 0 && eligible.length > 1) {
    sentences.push(
      fillTemplate(tokens.spreadLabel, {
        difference: formatNumber(spread.difference, tokens.locale),
        unit: spread.unit,
      }),
    );
  }
  sentences.push(
    fillTemplate(tokens.eligibleLabel, {
      eligible: String(eligible.length),
      total: String(result.candidates.length),
    }),
  );
  if (ineligible.length) {
    sentences.push(
      fillTemplate(tokens.ineligibleLabel, {
        crops: ineligible.map((candidate) => candidate.crop).join(", "),
      }),
    );
  }
  return sentences;
}

export function buildTrendSentences(
  crop: string,
  observations: CropTrendObservation[],
  statistics: CropHistoricalStatistics | undefined,
  tokens: {
    trendLabel: string;
    observationLabel: string;
    noTrendLabel: string;
    locale: "en" | "hi";
  },
): string[] {
  const sentences: string[] = [];
  if (!observations.length) {
    sentences.push(tokens.noTrendLabel);
    return sentences;
  }
  const values = observations
    .map((observation) => observation.yield_value)
    .filter((value) => Number.isFinite(value));
  if (values.length >= 2) {
    const min = Math.min(...values);
    const max = Math.max(...values);
    sentences.push(
      fillTemplate(tokens.trendLabel, {
        crop,
        min: formatNumber(min, tokens.locale),
        max: formatNumber(max, tokens.locale),
        unit: observations[0]?.unit ?? "kg/ha",
      }),
    );
  }
  sentences.push(
    fillTemplate(tokens.observationLabel, {
      crop,
      years: String(statistics?.valid_year_count ?? observations.length),
    }),
  );
  return sentences;
}

export function comparisonRows(
  comparison: CropComparisonResponse | null,
): Array<{
  crop: string;
  historicalMedian: number | null;
  recentMedian: number | null;
  validObservations: number;
  validYears: number;
  firstYear?: number;
  lastYear?: number;
  coverage: number;
  unit: string;
  evidenceQuality: string;
}> {
  if (!comparison) return [];
  return comparison.crops.map((stats) => {
    const summary = summariseStatistics(stats);
    return {
      crop: stats.crop,
      historicalMedian: stats.historical_median_yield,
      recentMedian: stats.recent_median_yield,
      validObservations: stats.valid_observation_count,
      validYears: stats.valid_year_count,
      firstYear: summary.firstYear,
      lastYear: summary.lastYear,
      coverage: stats.recent_year_coverage,
      unit: stats.unit,
      evidenceQuality: stats.evidence_quality,
    };
  });
}
