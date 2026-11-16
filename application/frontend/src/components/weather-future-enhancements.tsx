"use client";

import { useApp } from "./app-providers";

const FUTURE_CAPABILITIES = [
  {
    titleKey: "futureTemperatureTitle",
    descriptionKey: "futureTemperatureDesc",
  },
  {
    titleKey: "futureUnusualTitle",
    descriptionKey: "futureUnusualDesc",
  },
  {
    titleKey: "futurePatternsTitle",
    descriptionKey: "futurePatternsDesc",
  },
  {
    titleKey: "futureCropImpactTitle",
    descriptionKey: "futureCropImpactDesc",
  },
  {
    titleKey: "futureRiskTitle",
    descriptionKey: "futureRiskDesc",
  },
  {
    titleKey: "futureAdvisoryTitle",
    descriptionKey: "futureAdvisoryDesc",
  },
  {
    titleKey: "futureDistrictTitle",
    descriptionKey: "futureDistrictDesc",
  },
] as const;

export function WeatherFutureEnhancements() {
  const { t } = useApp();
  return (
    <section className="resource-section weather-future-enhancements">
      <header>
        <div>
          <p className="eyebrow">{t("futureRoadmapEyebrow")}</p>
          <h2>{t("futureEnhancementsTitle")}</h2>
          <p>
            <em>{t("futureEnhancementsSubtitle")}</em>
          </p>
          <p>{t("futureEnhancementsNote")}</p>
        </div>
      </header>
      <div className="future-enhancements future-enhancements--top">
        {FUTURE_CAPABILITIES.slice(0, 4).map((item) => (
          <article className="future-capability-card" key={item.titleKey}>
            <span className="future-capability-badge">{t("plannedBadge")}</span>
            <h3>{t(item.titleKey)}</h3>
            <p>{t(item.descriptionKey)}</p>
          </article>
        ))}
      </div>
      <div className="future-enhancements future-enhancements--bottom">
        {FUTURE_CAPABILITIES.slice(4).map((item) => (
          <article className="future-capability-card" key={item.titleKey}>
            <span className="future-capability-badge">{t("plannedBadge")}</span>
            <h3>{t(item.titleKey)}</h3>
            <p>{t(item.descriptionKey)}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
