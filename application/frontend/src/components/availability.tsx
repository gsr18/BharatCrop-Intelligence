"use client";

import { useApp } from "./app-providers";
import type { Capability } from "../lib/api";

export function CapabilityStatus({ capability }: { capability?: Capability }) {
  const { t } = useApp();
  if (capability?.availability === "available") {
    return (
      <>
        <span className="status-label ready">{t("inferenceAvailable")}</span>
        <span className="status-label pending">
          {t(
            capability.quality_status === "validated"
              ? "validatedQuality"
              : "experimentalQuality",
          )}
        </span>
        {!capability.production_approved && (
          <span className="status-label pending">
            {t("productionNotApproved")}
          </span>
        )}
        {capability.status === "disabled" && (
          <span className="status-label error">{t("routeDisabled")}</span>
        )}
      </>
    );
  }
  const isEnabled = capability?.status === "enabled";
  const isDisabled = capability?.status === "disabled";
  const label = isEnabled
    ? t("enabled")
    : isDisabled
      ? t("disabled")
      : t("unknown");
  return (
    <span
      className={`status-label ${isEnabled ? "ready" : isDisabled ? "pending" : "error"}`}
    >
      {label}
    </span>
  );
}

export function CapabilityReasons({ capability }: { capability?: Capability }) {
  const { t, language } = useApp();
  const reasons = capability?.reason_codes.length
    ? capability.reason_codes
    : capability?.reason_code
      ? [capability.reason_code]
      : [];
  if (!reasons.length) return null;
  return (
    <ul className="reason-list" lang={language}>
      {reasons.map((reason) => (
        <li key={reason}>
          {t("reasonMap")[reason] ?? reason.replaceAll("_", " ")}
        </li>
      ))}
    </ul>
  );
}

export function CapabilityPanel() {
  const { capabilities, t, language } = useApp();
  if (capabilities.loading && !capabilities.data) {
    return (
      <p className="loading-line" role="status">
        {t("apiLoading")}
      </p>
    );
  }
  if (capabilities.error && !capabilities.data) {
    return (
      <div role="alert">
        <p className="inline-error">{t("apiError")}</p>
        <button
          className="icon-button"
          type="button"
          onClick={() => void capabilities.refresh()}
        >
          {t("retry")}
        </button>
      </div>
    );
  }
  const filteredCapabilities = (capabilities.data?.capabilities ?? []).filter(
    (cap) => cap.name !== "mandi_prices",
  );
  return (
    <div className="capability-list" lang={language}>
      {filteredCapabilities.map((capability) => (
        <div className="capability-row" key={capability.name}>
          <div>
            <div className="capability-name">
              {t("capabilityMap")[capability.name] ??
                capability.name.replaceAll("_", " ")}
            </div>
            <div className="capability-reason">
              {capability.reason_codes.length
                ? capability.reason_codes
                    .slice(0, 3)
                    .map(
                      (reason) =>
                        t("reasonMap")[reason] ?? reason.replaceAll("_", " "),
                    )
                    .join(" · ")
                : t("capabilitiesIntro")}
            </div>
          </div>
          <CapabilityStatus capability={capability} />
        </div>
      ))}
    </div>
  );
}

export function PageHeading({
  eyebrow,
  title,
  intro,
}: {
  eyebrow: string;
  title: string;
  intro: string;
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="intro">{intro}</p>
      </div>
    </div>
  );
}
