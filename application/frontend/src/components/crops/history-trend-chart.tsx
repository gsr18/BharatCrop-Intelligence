"use client";

import type { CropTrendObservation } from "../../lib/api";
import { buildYearAxis, formatNumber } from "../../lib/crop-analysis";

type Props = {
  title: string;
  subtitle: string;
  observations: CropTrendObservation[];
  language: "en" | "hi";
  unitFallback?: string;
  emptyLabel: string;
  gapLabel: string;
};

const VIEW_WIDTH = 620;
const VIEW_HEIGHT = 240;
const PAD_LEFT = 44;
const PAD_RIGHT = 16;
const PAD_TOP = 18;
const PAD_BOTTOM = 42;

export function HistoryTrendChart({
  title,
  subtitle,
  observations,
  language,
  unitFallback = "kg/ha",
  emptyLabel,
  gapLabel,
}: Props) {
  const axis = buildYearAxis(observations);
  const values = axis
    .map((entry) => entry.yield_value)
    .filter((value): value is number => typeof value === "number");

  if (!axis.length || !values.length) {
    return (
      <section className="observation-chart crop-trend-chart">
        <div className="chart-heading">
          <div>
            <h3>{title}</h3>
            <p>{subtitle}</p>
          </div>
        </div>
        <p className="data-message">{emptyLabel}</p>
      </section>
    );
  }

  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const span = maxValue - minValue || Math.abs(maxValue) || 1;
  const yFloor = Math.max(0, minValue - span * 0.1);
  const yCeil = maxValue + span * 0.1;
  const plotWidth = VIEW_WIDTH - PAD_LEFT - PAD_RIGHT;
  const plotHeight = VIEW_HEIGHT - PAD_TOP - PAD_BOTTOM;

  const xFor = (index: number, total: number) =>
    total === 1
      ? PAD_LEFT + plotWidth / 2
      : PAD_LEFT + (index * plotWidth) / (total - 1);
  const yFor = (value: number) =>
    PAD_TOP + plotHeight - ((value - yFloor) / (yCeil - yFloor)) * plotHeight;

  const segments: string[] = [];
  let current: string[] = [];
  axis.forEach((entry, index) => {
    if (entry.yield_value === null) {
      if (current.length >= 2) segments.push(current.join(" "));
      current = [];
      return;
    }
    current.push(`${xFor(index, axis.length).toFixed(1)},${yFor(entry.yield_value).toFixed(1)}`);
  });
  if (current.length >= 2) segments.push(current.join(" "));

  const unit = observations.find((entry) => entry.unit)?.unit ?? unitFallback;

  const tickCount = Math.min(axis.length, 8);
  const tickStep = Math.max(1, Math.ceil(axis.length / tickCount));
  const ticks = axis.filter(
    (_, index) => index % tickStep === 0 || index === axis.length - 1,
  );
  const gridLines = [yFloor, (yFloor + yCeil) / 2, yCeil];

  return (
    <section className="observation-chart crop-trend-chart">
      <div className="chart-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        <span className="chart-unit">{unit}</span>
      </div>
      <div className="crop-trend-scroll">
        <svg
          className="crop-trend-svg"
          viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label={`${title}. ${subtitle}. ${unit}`}
        >
          {gridLines.map((value, index) => (
            <g key={`grid-${index}`}>
              <line
                className="crop-trend-grid"
                x1={PAD_LEFT}
                x2={VIEW_WIDTH - PAD_RIGHT}
                y1={yFor(value)}
                y2={yFor(value)}
              />
              <text
                className="crop-trend-axis-label"
                x={PAD_LEFT - 8}
                y={yFor(value) + 4}
                textAnchor="end"
              >
                {formatNumber(value, language)}
              </text>
            </g>
          ))}
          {segments.map((points, index) => (
            <polyline
              key={`segment-${index}`}
              className="crop-trend-line"
              fill="none"
              points={points}
            />
          ))}
          {axis.map((entry, index) => {
            const cx = xFor(index, axis.length);
            if (entry.yield_value === null) {
              return (
                <circle
                  key={`gap-${entry.year_start}`}
                  className="crop-trend-gap"
                  cx={cx}
                  cy={PAD_TOP + plotHeight / 2}
                  r={2}
                >
                  <title>
                    {`${entry.year_label}: ${gapLabel}`}
                  </title>
                </circle>
              );
            }
            const cy = yFor(entry.yield_value);
            return (
              <circle
                key={`point-${entry.year_start}`}
                className="crop-trend-point"
                cx={cx}
                cy={cy}
                r={3.5}
              >
                <title>
                  {`${entry.year_label}: ${formatNumber(entry.yield_value, language)} ${entry.unit ?? unit}`}
                </title>
              </circle>
            );
          })}
          {ticks.map((entry) => {
            const cx = xFor(axis.indexOf(entry), axis.length);
            return (
              <text
                key={`tick-${entry.year_start}`}
                className="crop-trend-axis-label"
                x={cx}
                y={VIEW_HEIGHT - PAD_BOTTOM + 18}
                textAnchor="middle"
              >
                {entry.year_label}
              </text>
            );
          })}
        </svg>
      </div>
    </section>
  );
}
