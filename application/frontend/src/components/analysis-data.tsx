"use client";

import type { ApiRecord } from "../lib/api";
import { LineChart } from "./charts/analysis-charts";

export function isApiRecord(value: unknown): value is ApiRecord {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

export function recordsFrom(value: unknown): ApiRecord[] {
  return Array.isArray(value) ? value.filter(isApiRecord) : [];
}

export function textFrom(
  record: ApiRecord,
  keys: string[],
  fallback = "Not reported",
) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value;
    if (typeof value === "number" && Number.isFinite(value)) {
      return new Intl.NumberFormat("en-IN", {
        maximumFractionDigits: 2,
      }).format(value);
    }
    if (typeof value === "boolean") return value ? "Yes" : "No";
  }
  return fallback;
}

export function numbersFrom(value: unknown) {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (typeof item === "number" && Number.isFinite(item)) return [item];
    if (
      typeof item === "string" &&
      item.trim() &&
      Number.isFinite(Number(item))
    ) {
      return [Number(item)];
    }
    return [];
  });
}

export function safeValue(value: unknown) {
  if (typeof value === "string" || typeof value === "boolean") {
    return String(value);
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return new Intl.NumberFormat("en-IN", {
      maximumFractionDigits: 2,
    }).format(value);
  }
  return "Not reported";
}

export function ApiStatus({
  loading,
  error,
  empty,
}: {
  loading: boolean;
  error: string | null;
  empty?: boolean;
}) {
  if (loading) {
    return (
      <p className="data-message" role="status">
        Loading service-backed information…
      </p>
    );
  }
  if (error) {
    return (
      <p className="data-message data-error" role="alert">
        {error}
      </p>
    );
  }
  if (empty) {
    return (
      <p className="data-message">
        The service returned no observations for this selection.
      </p>
    );
  }
  return null;
}

export function MetricGrid({
  items,
}: {
  items: Array<{ label: string; value: unknown; unit?: string }>;
}) {
  const visible = items.filter(
    (item) =>
      typeof item.value === "string" ||
      typeof item.value === "number" ||
      typeof item.value === "boolean",
  );
  if (!visible.length) {
    return <p className="data-message">No summary metrics were returned.</p>;
  }
  return (
    <div className="analysis-metrics">
      {visible.map((item) => (
        <article className="analysis-metric" key={item.label}>
          <span>{item.label}</span>
          <strong>
            {safeValue(item.value)}
            {item.unit ? <small> {item.unit}</small> : null}
          </strong>
        </article>
      ))}
    </div>
  );
}

function chartLabel(record: ApiRecord, keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    // Years are identifiers, not quantities: keep "2013" instead of "2,013".
    if (
      typeof value === "number" &&
      Number.isInteger(value) &&
      value >= 1000 &&
      value <= 2999
    ) {
      return String(value);
    }
  }
  return textFrom(record, keys);
}

export function ObservationChart({
  title,
  subtitle,
  records,
  labelKeys,
  valueKeys,
  unit,
  variant = "bars",
}: {
  title: string;
  subtitle: string;
  records: ApiRecord[];
  labelKeys: string[];
  valueKeys: string[];
  unit?: string;
  variant?: "bars" | "line";
}) {
  const points = records.flatMap((record) => {
    const valueKey = valueKeys.find((key) => {
      const value = record[key];
      return typeof value === "number" && Number.isFinite(value);
    });
    if (!valueKey) return [];
    const value = record[valueKey];
    if (typeof value !== "number") return [];
    return [{ label: chartLabel(record, labelKeys), value }];
  });
  const maximum = Math.max(...points.map((point) => Math.abs(point.value)), 0);

  return (
    <section className="observation-chart">
      <div className="chart-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        {unit ? <span className="chart-unit">{unit}</span> : null}
      </div>
      {points.length ? (
        variant === "line" ? (
          <LineChart
            points={points}
            subtitle={subtitle}
            title={title}
            unit={unit}
          />
        ) : (
          <div
            aria-label={`${title}. ${subtitle}${unit ? ` Unit: ${unit}.` : ""}`}
            className="observation-bars"
            role="img"
          >
            {points.slice(0, 12).map((point, index) => (
              <div
                className="observation-bar-item"
                key={`${point.label}-${index}`}
              >
                <span className="observation-value">
                  {safeValue(point.value)}
                </span>
                <div className="observation-bar-track">
                  <span
                    className="observation-bar"
                    style={{
                      width: `${maximum ? Math.max((Math.abs(point.value) / maximum) * 100, 2) : 0}%`,
                    }}
                  />
                </div>
                <span className="observation-label">{point.label}</span>
              </div>
            ))}
          </div>
        )
      ) : (
        <p className="data-message">No chartable observations were returned.</p>
      )}
    </section>
  );
}

export function ProvenanceDetails({ data }: { data: ApiRecord }) {
  const provenance = data.data_provenance ?? data.dataset_provenance;
  const limitations = Array.isArray(data.limitations)
    ? data.limitations.filter(
        (item): item is string => typeof item === "string",
      )
    : [];
  return (
    <details className="provenance-details">
      <summary>Methodology & data quality</summary>
      <p>
        <strong>Data provenance: </strong>
        {typeof provenance === "string"
          ? provenance
          : isApiRecord(provenance)
            ? textFrom(provenance, [
                "dataset_source",
                "dataset_name",
                "source",
                "dataset",
                "description",
              ])
            : "No provenance detail was returned."}
      </p>
      {limitations.length ? (
        <ul>
          {limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>No additional limitations were returned by the service.</p>
      )}
    </details>
  );
}
