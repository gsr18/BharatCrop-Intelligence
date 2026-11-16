"use client";

import type { RankedCropCandidate } from "../../lib/api";
import { formatNumber } from "../../lib/crop-analysis";

type Props = {
  title: string;
  subtitle: string;
  candidates: RankedCropCandidate[];
  language: "en" | "hi";
  observedLabel: string;
  modelLabel: string;
  notReportedLabel: string;
  ineligibleLabel: string;
  emptyLabel: string;
};

type Pair = {
  crop: string;
  observed: number | null;
  model: number | null;
  unit: string;
  eligible: boolean;
};

export function ObservedVsModelChart({
  title,
  subtitle,
  candidates,
  language,
  observedLabel,
  modelLabel,
  notReportedLabel,
  ineligibleLabel,
  emptyLabel,
}: Props) {
  const pairs: Pair[] = candidates.map((candidate) => ({
    crop: candidate.crop,
    observed:
      typeof candidate.observed_yield === "number" &&
      Number.isFinite(candidate.observed_yield)
        ? candidate.observed_yield
        : null,
    model:
      typeof candidate.predicted_yield === "number" &&
      Number.isFinite(candidate.predicted_yield)
        ? candidate.predicted_yield
        : null,
    unit: candidate.unit || "kg/ha",
    eligible: candidate.candidate_eligibility?.eligible !== false,
  }));

  const hasAny = pairs.some(
    (pair) => pair.observed !== null || pair.model !== null,
  );
  const maximum = hasAny
    ? Math.max(
        ...pairs.flatMap((pair) =>
          [pair.observed, pair.model].filter(
            (value): value is number => typeof value === "number",
          ),
        ),
        0,
      )
    : 0;
  const dominantUnit = pairs.find((pair) => pair.model || pair.observed)?.unit;

  return (
    <section className="observation-chart crop-observed-chart">
      <div className="chart-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        {dominantUnit ? <span className="chart-unit">{dominantUnit}</span> : null}
      </div>
      {!pairs.length || !hasAny ? (
        <p className="data-message">{emptyLabel}</p>
      ) : (
        <>
          <p className="evidence-legend" aria-hidden>
            <span className="legend-swatch observed" /> {observedLabel}
            <span className="legend-swatch predicted" /> {modelLabel}
          </p>
          <ul
            className="crop-paired-bars"
            role="list"
            aria-label={`${title}. ${subtitle}`}
          >
            {pairs.map((pair) => {
              const observedWidth =
                pair.observed !== null && maximum > 0
                  ? Math.max((pair.observed / maximum) * 100, 2)
                  : 0;
              const modelWidth =
                pair.model !== null && maximum > 0
                  ? Math.max((pair.model / maximum) * 100, 2)
                  : 0;
              const tooltip = `${pair.crop}${pair.eligible ? "" : ` — ${ineligibleLabel}`} · ${observedLabel}: ${pair.observed === null ? notReportedLabel : `${formatNumber(pair.observed, language)} ${pair.unit}`} · ${modelLabel}: ${pair.model === null ? notReportedLabel : `${formatNumber(pair.model, language)} ${pair.unit}`}`;
              return (
                <li
                  key={pair.crop}
                  className={`crop-pair${pair.eligible ? "" : " ineligible"}`}
                  title={tooltip}
                >
                  <div className="crop-pair-head">
                    <strong>{pair.crop}</strong>
                    {!pair.eligible ? (
                      <span className="crop-ineligible-tag">{ineligibleLabel}</span>
                    ) : null}
                  </div>
                  <div className="crop-pair-rows">
                    <div className="crop-pair-row observed">
                      <span className="crop-pair-label">{observedLabel}</span>
                      <div className="observation-bar-track">
                        <span
                          className="observation-bar observed-bar"
                          style={{ width: `${observedWidth}%` }}
                        />
                      </div>
                      <span className="observation-value">
                        {pair.observed === null
                          ? notReportedLabel
                          : formatNumber(pair.observed, language)}
                      </span>
                    </div>
                    <div className="crop-pair-row predicted">
                      <span className="crop-pair-label">{modelLabel}</span>
                      <div className="observation-bar-track">
                        <span
                          className="observation-bar predicted-bar"
                          style={{ width: `${modelWidth}%` }}
                        />
                      </div>
                      <span className="observation-value">
                        {pair.model === null
                          ? notReportedLabel
                          : formatNumber(pair.model, language)}
                      </span>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}
