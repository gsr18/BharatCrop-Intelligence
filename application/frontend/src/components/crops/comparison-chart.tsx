"use client";

import type { RankedCropCandidate } from "../../lib/api";
import { formatNumber } from "../../lib/crop-analysis";

type Props = {
  title: string;
  subtitle: string;
  candidates: RankedCropCandidate[];
  language: "en" | "hi";
  unitFallback?: string;
  ineligibleLabel: string;
  notReportedLabel: string;
  emptyLabel: string;
  tooltipObservedLabel: string;
  tooltipEligibleLabel: string;
};

type Point = {
  crop: string;
  value: number | null;
  observed: number | null;
  unit: string;
  eligible: boolean;
};

export function ComparisonChart({
  title,
  subtitle,
  candidates,
  language,
  unitFallback = "kg/ha",
  ineligibleLabel,
  notReportedLabel,
  emptyLabel,
  tooltipObservedLabel,
  tooltipEligibleLabel,
}: Props) {
  const points: Point[] = candidates
    .map((candidate) => ({
      crop: candidate.crop,
      value:
        typeof candidate.ranking_value === "number" &&
        Number.isFinite(candidate.ranking_value)
          ? candidate.ranking_value
          : null,
      observed:
        typeof candidate.observed_yield === "number" &&
        Number.isFinite(candidate.observed_yield)
          ? candidate.observed_yield
          : null,
      unit: candidate.unit || unitFallback,
      eligible: candidate.rank !== null,
    }))
    .sort((a, b) => (b.value ?? -1) - (a.value ?? -1));

  const hasData = points.some((point) => point.value !== null);
  const maximum = hasData
    ? Math.max(...points.map((point) => Math.abs(point.value ?? 0)), 0)
    : 0;
  const dominantUnit = points.find((point) => point.value !== null)?.unit;

  return (
    <section className="observation-chart crop-comparison-chart" aria-labelledby={`${title}-heading`}>
      <div className="chart-heading">
        <div>
          <h3 id={`${title}-heading`}>{title}</h3>
          <p>{subtitle}</p>
        </div>
        {dominantUnit ? <span className="chart-unit">{dominantUnit}</span> : null}
      </div>
      {!points.length || !hasData ? (
        <p className="data-message">{emptyLabel}</p>
      ) : (
        <div
          className="observation-bars"
          role="img"
          aria-label={`${title}. ${subtitle}${dominantUnit ? `. ${dominantUnit}` : ""}`}
        >
          {points.map((point, index) => {
            const widthPercent =
              point.value !== null && maximum > 0
                ? Math.max((Math.abs(point.value) / maximum) * 100, 2)
                : 0;
            const tooltipParts: string[] = [point.crop];
            if (point.value !== null) {
              tooltipParts.push(
                `${formatNumber(point.value, language)} ${point.unit}`,
              );
            } else {
              tooltipParts.push(notReportedLabel);
            }
            if (point.observed !== null) {
              tooltipParts.push(
                `${tooltipObservedLabel}: ${formatNumber(point.observed, language)} ${point.unit}`,
              );
            }
            if (!point.eligible) tooltipParts.push(tooltipEligibleLabel);
            return (
              <div
                key={`${point.crop}-${index}`}
                className={`observation-bar-item crop-bar${point.eligible ? "" : " ineligible"}`}
                title={tooltipParts.join(" — ")}
              >
                <span className="observation-value">
                  {point.value !== null
                    ? formatNumber(point.value, language)
                    : notReportedLabel}
                </span>
                <div className="observation-bar-track">
                  <span
                    className="observation-bar crop-bar-fill"
                    style={{ width: `${widthPercent}%` }}
                  />
                </div>
                <span className="observation-label">
                  {point.crop}
                  {!point.eligible ? (
                    <em className="crop-ineligible-tag"> · {ineligibleLabel}</em>
                  ) : null}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
