"use client";

import { safeValue } from "../analysis-data";

export type ChartPoint = {
  label: string;
  value: number;
};

export type SignedChartRow = {
  label: string;
  value: number;
  meta?: string;
};

export type RankedChartRow = {
  label: string;
  value: number;
  meta?: string;
};

const VIEW_WIDTH = 720;
const VIEW_HEIGHT = 260;
const PAD_LEFT = 52;
const PAD_RIGHT = 18;
const PAD_TOP = 18;
const PAD_BOTTOM = 40;

const axisFormatter = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 1,
});

function formatAxis(value: number) {
  return axisFormatter.format(Math.round(value * 10) / 10);
}

/**
 * Compact SVG line chart for ordered (usually yearly) observations. The plot
 * is intentionally dependency-free so it can be reused across analysis pages.
 */
export function LineChart({
  points,
  unit,
  title,
  subtitle,
  emptyLabel = "No chartable observations were returned.",
}: {
  points: ChartPoint[];
  unit?: string;
  title: string;
  subtitle: string;
  emptyLabel?: string;
}) {
  const data = points
    .filter((point) => Number.isFinite(point.value))
    .slice(0, 240);

  if (!data.length) {
    return <p className="data-message">{emptyLabel}</p>;
  }

  const values = data.map((point) => point.value);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  let floor = rawMin >= 0 ? 0 : rawMin;
  let ceil = rawMax;
  if (floor === ceil) {
    ceil = floor + (Math.abs(floor) || 1);
  }
  const rawSpan = ceil - floor || 1;
  if (rawMin < 0) floor -= rawSpan * 0.08;
  ceil += rawSpan * 0.08;
  const span = ceil - floor || 1;

  const plotWidth = VIEW_WIDTH - PAD_LEFT - PAD_RIGHT;
  const plotHeight = VIEW_HEIGHT - PAD_TOP - PAD_BOTTOM;
  const xFor = (index: number) =>
    data.length === 1
      ? PAD_LEFT + plotWidth / 2
      : PAD_LEFT + (index * plotWidth) / (data.length - 1);
  const yFor = (value: number) =>
    PAD_TOP + plotHeight - ((value - floor) / span) * plotHeight;

  const linePoints = data
    .map(
      (point, index) =>
        `${xFor(index).toFixed(1)},${yFor(point.value).toFixed(1)}`,
    )
    .join(" ");

  const zeroY = yFor(Math.min(Math.max(0, floor), ceil));
  const areaPoints = [
    `${xFor(0).toFixed(1)},${zeroY.toFixed(1)}`,
    ...data.map(
      (point, index) =>
        `${xFor(index).toFixed(1)},${yFor(point.value).toFixed(1)}`,
    ),
    `${xFor(data.length - 1).toFixed(1)},${zeroY.toFixed(1)}`,
  ].join(" ");

  const yTicks = Array.from({ length: 5 }, (_, index) => {
    return floor + (span * index) / 4;
  });
  const xTickStep = Math.max(1, Math.ceil(data.length / 8));

  return (
    <div className="line-chart-scroll">
      <svg
        aria-label={`${title}. ${subtitle}${unit ? `. Unit: ${unit}.` : ""}`}
        className="line-chart-svg"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
      >
        {yTicks.map((tick, index) => (
          <g key={`grid-${index}`}>
            <line
              className="line-chart-grid"
              x1={PAD_LEFT}
              x2={VIEW_WIDTH - PAD_RIGHT}
              y1={yFor(tick)}
              y2={yFor(tick)}
            />
            <text
              className="line-chart-axis-label"
              textAnchor="end"
              x={PAD_LEFT - 8}
              y={yFor(tick) + 4}
            >
              {formatAxis(tick)}
            </text>
          </g>
        ))}
        {floor < 0 && ceil > 0 ? (
          <line
            className="line-chart-zero"
            x1={PAD_LEFT}
            x2={VIEW_WIDTH - PAD_RIGHT}
            y1={zeroY}
            y2={zeroY}
          />
        ) : null}
        <polygon className="line-chart-area" points={areaPoints} />
        <polyline className="line-chart-line" fill="none" points={linePoints} />
        {data.map((point, index) => (
          <circle
            className="line-chart-point"
            cx={xFor(index)}
            cy={yFor(point.value)}
            key={`point-${point.label}-${index}`}
            r={data.length > 60 ? 2 : 3.5}
          >
            <title>{`${point.label}: ${safeValue(point.value)}${unit ? ` ${unit}` : ""}`}</title>
          </circle>
        ))}
        {data.map((point, index) =>
          index % xTickStep === 0 || index === data.length - 1 ? (
            <text
              className="line-chart-axis-label"
              key={`tick-${point.label}-${index}`}
              textAnchor="middle"
              x={xFor(index)}
              y={VIEW_HEIGHT - PAD_BOTTOM + 20}
            >
              {point.label}
            </text>
          ) : null,
        )}
      </svg>
    </div>
  );
}

/**
 * Diverging bar chart for signed values such as prediction bias, where the
 * direction (over/under) is as important as the magnitude.
 */
export function SignedBarChart({
  title,
  subtitle,
  unit,
  rows,
  positiveLabel,
  negativeLabel,
  emptyLabel = "No signed observations were returned.",
}: {
  title: string;
  subtitle: string;
  unit?: string;
  rows: SignedChartRow[];
  positiveLabel: string;
  negativeLabel: string;
  emptyLabel?: string;
}) {
  const data = rows.filter((row) => Number.isFinite(row.value));
  const maximum = Math.max(...data.map((row) => Math.abs(row.value)), 0);

  return (
    <section className="observation-chart signed-chart">
      <div className="chart-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        {unit ? <span className="chart-unit">{unit}</span> : null}
      </div>
      {!data.length ? (
        <p className="data-message">{emptyLabel}</p>
      ) : (
        <>
          <p className="evidence-legend" aria-hidden>
            <span className="legend-swatch overprediction" /> {positiveLabel}
            <span className="legend-swatch underprediction" /> {negativeLabel}
          </p>
          <div
            aria-label={`${title}. ${subtitle}${unit ? `. Unit: ${unit}.` : ""}`}
            className="signed-bars"
            role="img"
          >
            {data.map((row, index) => {
              const widthPercent = maximum
                ? Math.max((Math.abs(row.value) / maximum) * 50, 1.5)
                : 0;
              return (
                <div
                  className="signed-bar-row"
                  key={`${row.label}-${index}`}
                  title={`${row.label}: ${safeValue(row.value)}${unit ? ` ${unit}` : ""}${row.meta ? ` — ${row.meta}` : ""}`}
                >
                  <span className="signed-bar-label">{row.label}</span>
                  <div className="signed-bar-track">
                    <span className="signed-bar-axis" aria-hidden />
                    <span
                      className={`signed-bar-fill ${row.value >= 0 ? "positive" : "negative"}`}
                      style={{ width: `${widthPercent}%` }}
                    />
                  </div>
                  <span className="signed-bar-value">
                    {row.value > 0 ? "+" : ""}
                    {safeValue(row.value)}
                  </span>
                </div>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}

/**
 * Ranked horizontal bars with an optional secondary metric line, used for
 * error tables where each row needs more than a single number.
 */
export function RankedBarChart({
  title,
  subtitle,
  unit,
  rows,
  emptyLabel = "No ranked observations were returned.",
}: {
  title: string;
  subtitle: string;
  unit?: string;
  rows: RankedChartRow[];
  emptyLabel?: string;
}) {
  const data = rows.filter((row) => Number.isFinite(row.value));
  const maximum = Math.max(...data.map((row) => Math.abs(row.value)), 0);

  return (
    <section className="observation-chart ranked-chart">
      <div className="chart-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        {unit ? <span className="chart-unit">{unit}</span> : null}
      </div>
      {!data.length ? (
        <p className="data-message">{emptyLabel}</p>
      ) : (
        <div
          aria-label={`${title}. ${subtitle}${unit ? `. Unit: ${unit}.` : ""}`}
          className="ranked-bars"
          role="img"
        >
          {data.map((row, index) => {
            const widthPercent = maximum
              ? Math.max((Math.abs(row.value) / maximum) * 100, 2)
              : 0;
            return (
              <div
                className="ranked-bar-row"
                key={`${row.label}-${index}`}
                title={`${row.label}: ${safeValue(row.value)}${unit ? ` ${unit}` : ""}${row.meta ? ` — ${row.meta}` : ""}`}
              >
                <div className="ranked-bar-head">
                  <span className="ranked-bar-label">{row.label}</span>
                  <span className="ranked-bar-value">
                    {safeValue(row.value)}
                    {unit ? <small> {unit}</small> : null}
                  </span>
                </div>
                <div className="observation-bar-track">
                  <span
                    className="observation-bar"
                    style={{ width: `${widthPercent}%` }}
                  />
                </div>
                {row.meta ? (
                  <span className="ranked-bar-meta">{row.meta}</span>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
