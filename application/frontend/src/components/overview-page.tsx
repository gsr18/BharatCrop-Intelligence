"use client";

import Link from "next/link";
import { useState } from "react";
import { navItems } from "../lib/i18n";
import { useApp } from "./app-providers";
import { AiAssistantIcon } from "./icons";

const modules = [
  {
    index: "01",
    nav: navItems[1],
    descKey: "yieldDesc",
    capability: "yield_prediction",
    symbol: "↗",
    tone: "gold",
  },
  {
    index: "02",
    nav: navItems[2],
    descKey: "cropsDesc",
    capability: "crop_ranking",
    symbol: "✳",
    tone: "leaf",
  },
  {
    index: "03",
    nav: navItems[3],
    descKey: "weatherDesc",
    capability: "weather_insights",
    symbol: "☁",
    tone: "sky",
  },
  {
    index: "04",
    nav: navItems[4],
    descKey: "riskDesc",
    capability: "agricultural_risk_indicators",
    symbol: "⌁",
    tone: "earth",
  },
  {
    index: "05",
    nav: navItems[5],
    descKey: "explainabilityDesc",
    capability: "global_explainability",
    symbol: "◌",
    tone: "violet",
  },
  {
    index: "06",
    nav: navItems[6],
    descKey: "insightsDesc",
    capability: "model_insights",
    symbol: "▦",
    tone: "forest",
  },
] as const;

function moduleStatus(
  capability:
    | {
        availability?: string;
        quality_status?: string;
        production_approved?: boolean;
      }
    | undefined,
  loading: boolean,
  t: ReturnType<typeof useApp>["t"],
) {
  if (loading)
    return { label: t("statusChecking"), className: "status-checking" };
  if (!capability || !capability.availability)
    return { label: t("statusResearchModule"), className: "status-research" };
  if (capability.availability === "available") {
    // No capability is production-approved, so never imply "Operational".
    // The badge reflects the honest research quality of the connected service.
    switch (capability.quality_status) {
      case "experimental":
        return {
          label: t("statusExperimental"),
          className: "status-experimental",
        };
      case "exploratory":
        return {
          label: t("statusExploratory"),
          className: "status-experimental",
        };
      default:
        return { label: t("statusResearch"), className: "status-research" };
    }
  }
  return { label: t("statusUnavailable"), className: "status-unavailable" };
}

export function OverviewPage() {
  const { t, capabilities } = useApp();
  const [showGuide, setShowGuide] = useState(true);

  function dismissGuide() {
    setShowGuide(false);
  }

  const prediction = capabilities.data?.capabilities.find(
    (item) => item.name === "yield_prediction",
  );
  const assistant = capabilities.data?.capabilities.find(
    (item) => item.name === "grounded_assistant",
  );
  const assistantAvailable = assistant?.availability === "available";

  return (
    <div className="overview-page">
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-left">
            <span className="hero-badge">
              <i /> {t("region")} · {t("overviewEvidenceLed")}
            </span>
            <h1>{t("overviewTitle")}</h1>
            <p className="hero-description">{t("overviewIntro")}</p>
            <div className="hero-buttons">
              <Link className="btn-primary" href="/yield">
                <span>{t("overviewStartEstimate")}</span>
                <span aria-hidden="true">↗</span>
              </Link>
              <Link className="btn-secondary" href="/research">
                {t("overviewExploreResearch")}
              </Link>
            </div>
            <p className="hero-footnote">{t("overviewHeroFootnote")}</p>
          </div>
          <aside
            className="hero-evidence glass-panel"
            aria-label={t("overviewPlatformEvidenceAria")}
          >
            <div className="evidence-topline">
              <span>{t("overviewPlatformGlance")}</span>
              <span className="live-dot" /> {t("overviewLiveStatus")}
            </div>
            <div className="evidence-primary">
              <span className="evidence-number">22</span>
              <div>
                <strong>{t("overviewResearchNotebooks")}</strong>
                <small>{t("overviewNotebookSub")}</small>
              </div>
            </div>
            <div className="evidence-divider" />
            <div className="evidence-status">
              <span className="evidence-mark">↗</span>
              <div>
                <strong>{t("overviewYieldCard")}</strong>
                <small>{t("overviewYieldCardSub")}</small>
              </div>
              {prediction?.availability === "available" ? (
                <span className="status-pill status-experimental">
                  {t("statusExperimental")}
                </span>
              ) : (
                <span className="status-pill status-unavailable">
                  {capabilities.loading
                    ? t("overviewChecking")
                    : t("overviewUnavailableShort")}
                </span>
              )}
            </div>
            <div className="evidence-disclaimer">
              <span aria-hidden="true">i</span>
              {t("overviewAvailabilityNote")}
            </div>
          </aside>
        </div>
        <span className="hero-caption">
          Agriculture · research · decision support
        </span>
      </section>

      {showGuide && (
        <section className="first-steps" aria-labelledby="first-steps-title">
          <div className="first-steps-heading">
            <div>
              <p className="eyebrow">{t("overviewGuidedStart")}</p>
              <h2 id="first-steps-title">{t("overviewThreeSteps")}</h2>
            </div>
            <button
              aria-label={t("overviewDismissGuide")}
              className="guide-close"
              onClick={dismissGuide}
              type="button"
            >
              ×
            </button>
          </div>
          <div className="first-steps-grid">
            <Link href="/yield">
              <span>01</span>
              <strong>{t("overviewStep1Title")}</strong>
              <small>{t("overviewStep1Sub")}</small>
              <i aria-hidden="true">↗</i>
            </Link>
            <Link href="/crops">
              <span>02</span>
              <strong>{t("overviewStep2Title")}</strong>
              <small>{t("overviewStep2Sub")}</small>
              <i aria-hidden="true">↗</i>
            </Link>
            <Link href="/model-development">
              <span>03</span>
              <strong>{t("overviewStep3Title")}</strong>
              <small>{t("overviewStep3Sub")}</small>
              <i aria-hidden="true">↗</i>
            </Link>
          </div>
        </section>
      )}

      <section className="modules-section" aria-labelledby="modules-title">
        <div className="modules-header">
          <div>
            <p className="eyebrow">{t("overviewModulesEyebrow")}</p>
            <h2 id="modules-title">{t("overviewModulesTitle")}</h2>
          </div>
          <p className="modules-subtitle">{t("overviewModulesSubtitle")}</p>
        </div>
        <div className="modules-grid">
          {modules.map(
            ({
              index,
              nav,
              descKey,
              capability: capabilityName,
              symbol,
              tone,
            }) => {
              const capability = capabilities.data?.capabilities.find(
                (item) => item.name === capabilityName,
              );
              const status = moduleStatus(capability, capabilities.loading, t);
              return (
                <Link
                  className={`module-card module-${tone}`}
                  href={nav.href}
                  key={nav.href}
                >
                  <div className="module-topline">
                    <span>{index}</span>
                    <span className={`module-status ${status.className}`}>
                      {status.label}
                    </span>
                  </div>
                  <div aria-hidden="true" className="module-illustration">
                    {symbol}
                  </div>
                  <h3>{t(nav.key)}</h3>
                  <p>{t(descKey)}</p>
                  <span className="module-link">
                    {t("overviewExploreModule")}{" "}
                    <span aria-hidden="true">→</span>
                  </span>
                </Link>
              );
            },
          )}
        </div>
      </section>

      <section className="assistant-promo">
        <div className="assistant-orbit" aria-hidden="true">
          <AiAssistantIcon size={28} />
        </div>
        <div>
          <p className="eyebrow">
            {t("overviewAssistantEyebrow")}{" "}
            <span
              className={`status-pill ${
                assistantAvailable
                  ? "status-experimental"
                  : "status-unavailable"
              }`}
            >
              {assistantAvailable
                ? t("enabled")
                : capabilities.loading
                  ? t("overviewChecking")
                  : t("overviewUnavailableShort")}
            </span>
          </p>
          <h2>{t("overviewAssistantTitle")}</h2>
          <p>
            {assistantAvailable
              ? t("assistantPromoAvailable")
              : t("assistantPromoUnavailable")}
          </p>
        </div>
        <Link href="/assistant">
          {t("overviewAssistantCta")} <span aria-hidden="true">↗</span>
        </Link>
      </section>
    </div>
  );
}
