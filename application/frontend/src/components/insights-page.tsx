"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type ApiRecord } from "../lib/api";
import { useApp } from "./app-providers";
import { PageHeading } from "./availability";
import {
  ApiStatus,
  MetricGrid,
  isApiRecord,
  recordsFrom,
  safeValue,
  textFrom,
} from "./analysis-data";

type InsightsData = {
  portfolio: ApiRecord;
  models: ApiRecord;
  evaluations: ApiRecord;
  governance: ApiRecord;
  policy: ApiRecord;
};
type InsightTab = "portfolio" | "evaluation" | "governance" | "provenance";

export function InsightsPage() {
  const { t } = useApp();
  const [data, setData] = useState<InsightsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<InsightTab>("portfolio");
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<ApiRecord | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.modelInsightsPortfolio(),
      api.modelInsightsModels(),
      api.modelInsightsEvaluations(),
      api.modelInsightsGovernance(),
      api.modelInsightsPolicyOutputs(),
    ]).then((results) => {
      if (!active) return;
      const [portfolio, models, evaluations, governance, policy] = results;
      const successful = results.some(
        (result) => result.status === "fulfilled",
      );
      if (!successful) {
        setError("The model registry service is currently unavailable.");
      } else {
        setData({
          portfolio: portfolio.status === "fulfilled" ? portfolio.value : {},
          models: models.status === "fulfilled" ? models.value : {},
          evaluations:
            evaluations.status === "fulfilled" ? evaluations.value : {},
          governance: governance.status === "fulfilled" ? governance.value : {},
          policy: policy.status === "fulfilled" ? policy.value : {},
        });
        if (results.some((result) => result.status === "rejected")) {
          setError(
            "Some registry sections are unavailable; returned sections remain visible.",
          );
        }
      }
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  const models = useMemo(() => {
    const items = data?.models.models;
    return Array.isArray(items)
      ? items.filter(
          (item): item is ApiRecord =>
            !!item && typeof item === "object" && !Array.isArray(item),
        )
      : [];
  }, [data]);

  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    Promise.all([
      api.modelInsightsModel(selectedId),
      api.modelInsightsEvidence(selectedId),
    ])
      .then(
        ([model, evidence]) => {
          if (active) setDetail({ ...model, evidence });
        },
        () => {
          if (active)
            setDetailError(
              "Registry detail or its evaluation evidence could not be loaded.",
            );
        },
      )
      .finally(() => {
        if (active) setDetailLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedId]);

  const tabNames: Record<InsightTab, string> = {
    portfolio: "Model Portfolio",
    evaluation: "Model Evaluation",
    governance: "Model Governance",
    provenance: "Provenance",
  };
  const evaluationSummary = recordsFrom(data?.evaluations.evaluation_summary);
  const policyRules = recordsFrom(data?.governance.policy_rules);
  const evidenceObject = (detail?.evidence ?? {}) as ApiRecord;
  const evidence = isApiRecord(evidenceObject.evaluation_evidence)
    ? (evidenceObject.evaluation_evidence as ApiRecord)
    : null;
  const selectedModel = detail?.model_card;
  const modelRecord = isApiRecord(selectedModel)
    ? selectedModel
    : (detail ?? {});

  return (
    <div className="insights-page">
      <PageHeading
        eyebrow={t("insights")}
        title="Model Insights"
        intro="Inspect the real model portfolio, its evaluation evidence, governance status, and provenance. Artifact existence, inference availability, and production approval are shown as separate facts."
      />
      <section className="resource-layout">
        <div className="resource-section">
          <header>
            <div>
              <p className="eyebrow">Registry-backed information</p>
              <h2>Model portfolio and governance</h2>
              <p>
                No artifact paths or internal deployment locations are
                displayed.
              </p>
            </div>
          </header>
          <nav aria-label="Model insights sections" className="detail-tabs">
            {(Object.keys(tabNames) as InsightTab[]).map((name) => (
              <button
                aria-pressed={tab === name}
                key={name}
                onClick={() => setTab(name)}
                type="button"
              >
                {tabNames[name]}
              </button>
            ))}
          </nav>
          <ApiStatus loading={loading} error={error} />

          {data && tab === "portfolio" && (
            <>
              <MetricGrid
                items={[
                  {
                    label: "Registry components",
                    value: data.portfolio.total_components,
                  },
                  {
                    label: "Portfolio entries returned",
                    value: Array.isArray(data.portfolio.portfolio)
                      ? data.portfolio.portfolio.length
                      : undefined,
                  },
                ]}
              />
              {models.length ? (
                <div className="data-card-list">
                  {models.map((model, index) => {
                    const id = textFrom(
                      model,
                      ["registry_id", "id", "model_id"],
                      `entry-${index + 1}`,
                    );
                    return (
                      <article className="data-card" key={id}>
                        <header>
                          <strong>
                            {textFrom(
                              model,
                              ["model_name", "registry_id"],
                              "Registry component",
                            )}
                          </strong>
                          <button
                            className="icon-button"
                            onClick={() => {
                              setSelectedId(id);
                              setDetailLoading(true);
                              setDetailError(null);
                            }}
                            type="button"
                          >
                            View evidence
                          </button>
                        </header>
                        <dl>
                          <div>
                            <dt>Component type</dt>
                            <dd>{textFrom(model, ["component_type"])}</dd>
                          </div>
                          <div>
                            <dt>Task</dt>
                            <dd>{textFrom(model, ["task"])}</dd>
                          </div>
                          <div>
                            <dt>Target</dt>
                            <dd>{textFrom(model, ["target"])}</dd>
                          </div>
                          <div>
                            <dt>Recorded status</dt>
                            <dd>{textFrom(model, ["recorded_status"])}</dd>
                          </div>
                          <div>
                            <dt>Registry disposition</dt>
                            <dd>{textFrom(model, ["registry_disposition"])}</dd>
                          </div>
                          <div>
                            <dt>Artifact present</dt>
                            <dd>{textFrom(model, ["artifact_exists"])}</dd>
                          </div>
                          <div>
                            <dt>Metadata present</dt>
                            <dd>{textFrom(model, ["metadata_exists"])}</dd>
                          </div>
                        </dl>
                      </article>
                    );
                  })}
                </div>
              ) : (
                <p className="data-message">
                  No registry model entries were returned.
                </p>
              )}
              <ProvenanceLine value={data.portfolio.notebook_reference} />
            </>
          )}

          {data && tab === "evaluation" && (
            <section className="resource-section">
              <header>
                <div>
                  <h2>Evaluation evidence</h2>
                  <p>
                    Components with evaluation evidence returned by the
                    registry, and those without, are shown separately.
                  </p>
                </div>
              </header>
              {evaluationSummary.length ? (
                <div className="data-card-list">
                  {evaluationSummary.map((entry, index) => (
                    <article
                      className="data-card"
                      key={`${textFrom(entry, ["registry_id"])}-${index}`}
                    >
                      <header>
                        <strong>
                          {textFrom(
                            entry,
                            ["registry_id"],
                            `Component ${index + 1}`,
                          )}
                        </strong>
                        <span>
                          {entry.evaluation_available === true
                            ? "Evidence returned"
                            : entry.evaluation_available === false
                              ? "No evidence returned"
                              : "Not reported"}
                        </span>
                      </header>
                      <dl>
                        <div>
                          <dt>Component type</dt>
                          <dd>{textFrom(entry, ["component_type"])}</dd>
                        </div>
                        <div>
                          <dt>Evaluation period</dt>
                          <dd>{formatYearList(entry.evaluation_period)}</dd>
                        </div>
                      </dl>
                      <p className="result-interpretation">
                        {textFrom(
                          entry,
                          ["interpretation"],
                          "No evaluation interpretation was returned.",
                        )}
                      </p>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="data-message">
                  No evaluation summary entries were returned.
                </p>
              )}
              <ProvenanceLine value={data.evaluations.notebook_reference} />
            </section>
          )}

          {data && tab === "governance" && (
            <section className="resource-section">
              <header>
                <div>
                  <h2>Release and governance status</h2>
                  <p>
                    Approval is not inferred from a saved artifact or successful
                    inference.
                  </p>
                </div>
              </header>
              <WhitelistedDetails
                data={data.governance}
                fields={[
                  ["production_approval", "Production approval"],
                  ["governance_note", "Governance note"],
                ]}
              />
              {policyRules.length ? (
                <div className="data-card-list">
                  {policyRules.map((rule, index) => (
                    <article
                      className="data-card"
                      key={`${textFrom(rule, ["policy_id"])}-${index}`}
                    >
                      <header>
                        <strong>
                          {textFrom(rule, ["scope"], "Policy rule")}
                        </strong>
                        <span>{textFrom(rule, ["severity"])}</span>
                      </header>
                      <p className="result-interpretation">
                        {textFrom(rule, ["rule"], "No rule text was returned.")}
                      </p>
                      <dl>
                        <div>
                          <dt>Condition</dt>
                          <dd>{textFrom(rule, ["condition"])}</dd>
                        </div>
                        <div>
                          <dt>Action</dt>
                          <dd>{textFrom(rule, ["action"])}</dd>
                        </div>
                      </dl>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="data-message">No policy rules were returned.</p>
              )}
              <MetricGrid
                items={[
                  {
                    label: "Policy outputs available",
                    value: Array.isArray(data.policy.policy_outputs_available)
                      ? data.policy.policy_outputs_available.length
                      : undefined,
                  },
                  {
                    label: "Registry entries",
                    value: data.policy.registry_entry_count,
                  },
                  {
                    label: "Policy rules",
                    value: data.policy.policy_rule_count,
                  },
                  {
                    label: "Artifact checks",
                    value: data.policy.all_artifacts_exist,
                  },
                  {
                    label: "Metadata checks",
                    value: data.policy.all_metadata_exist,
                  },
                ]}
              />
            </section>
          )}

          {data && tab === "provenance" && (
            <section className="resource-section">
              <header>
                <div>
                  <h2>Evidence provenance</h2>
                  <p>
                    Public references only; internal artifact and output
                    locations are omitted.
                  </p>
                </div>
              </header>
              <ProvenanceLine value={data.portfolio.notebook_reference} />
              <ProvenanceLine value={data.models.notebook_reference} />
              <ProvenanceLine value={data.evaluations.notebook_reference} />
              <ProvenanceLine value={data.governance.notebook_reference} />
              <p className="result-interpretation">
                The registry response may contain operational metadata. This
                view intentionally presents only selected status, evaluation,
                and provenance fields.
              </p>
            </section>
          )}
        </div>

        {selectedId && (
          <aside className="resource-section">
            <header>
              <div>
                <p className="eyebrow">Selected registry entry</p>
                <h2>
                  {textFrom(
                    modelRecord,
                    ["display_name", "name", "model_name"],
                    selectedId,
                  )}
                </h2>
              </div>
              <button
                className="icon-button"
                onClick={() => {
                  setSelectedId("");
                  setDetail(null);
                }}
                type="button"
              >
                Close
              </button>
            </header>
            <ApiStatus loading={detailLoading} error={detailError} />
            {detail && (
              <>
                <WhitelistedDetails
                  data={modelRecord}
                  fields={[
                    ["registry_id", "Registry ID"],
                    ["component_type", "Component type"],
                    ["task", "Task"],
                    ["target", "Target"],
                    ["model_name", "Model name"],
                    ["recorded_status", "Recorded status"],
                    ["registry_disposition", "Registry disposition"],
                    ["evidence_status", "Evidence status"],
                    ["artifact_exists", "Artifact present"],
                    ["metadata_exists", "Metadata present"],
                    ["artifact_sha256", "Artifact integrity hash"],
                    ["restrictions", "Restrictions"],
                  ]}
                />
                <h3>Evaluation evidence</h3>
                {evidence ? (
                  <>
                    <WhitelistedDetails
                      data={evidence}
                      fields={[
                        ["eligible_rows", "Eligible prediction rows"],
                        ["evaluated_groups", "Evaluated groups"],
                        ["top1_hit_rate", "Top-1 hit rate"],
                        ["top3_hit_rate", "Top-3 hit rate"],
                        [
                          "mean_spearman_correlation",
                          "Mean Spearman correlation",
                        ],
                        ["production_approval", "Production approval"],
                      ]}
                    />
                    <p className="provenance-list">
                      <strong>Evaluation period: </strong>
                      {formatYearList(evidence.evaluation_period)}
                    </p>
                    <p className="result-interpretation">
                      {textFrom(
                        evidence,
                        ["interpretation"],
                        "No interpretation was returned for this evidence.",
                      )}
                    </p>
                  </>
                ) : (
                  <p className="data-message">
                    The registry returned no evaluation evidence for this
                    component.
                  </p>
                )}
              </>
            )}
          </aside>
        )}
      </section>
    </div>
  );
}

function WhitelistedDetails({
  data,
  fields,
}: {
  data: ApiRecord;
  fields: Array<[string, string]>;
}) {
  const entries = fields.filter(([key]) => {
    const value = data[key];
    return (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean"
    );
  });
  if (!entries.length)
    return (
      <p className="data-message">
        No public detail was returned for this section.
      </p>
    );
  return (
    <dl className="provenance-list">
      {entries.map(([key, label]) => (
        <div key={key}>
          <dt>{label}</dt>
          <dd>{safeValue(data[key])}</dd>
        </div>
      ))}
    </dl>
  );
}

function ProvenanceLine({ value }: { value: unknown }) {
  return typeof value === "string" && value.trim() ? (
    <p className="research-privacy-note">Research reference: {value}</p>
  ) : null;
}

function formatYearList(value: unknown): string {
  if (!Array.isArray(value)) return "Not reported";
  const years = value.filter(
    (item): item is number => typeof item === "number" && Number.isFinite(item),
  );
  if (!years.length) return "Not reported";
  const low = Math.min(...years);
  const high = Math.max(...years);
  return low === high ? String(low) : `${low}–${high}`;
}
