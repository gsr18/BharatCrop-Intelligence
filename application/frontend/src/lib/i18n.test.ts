import { describe, expect, it } from "vitest";
import { messages, navItems } from "./i18n";

describe("localized navigation", () => {
  it("provides bilingual labels for every product route", () => {
    expect(navItems).toHaveLength(10);
    for (const item of navItems) {
      expect(messages.en[item.key]).toBeTruthy();
      expect(messages.hi[item.key]).toBeTruthy();
    }
    expect(navItems.map((item) => item.href)).toEqual([
      "/",
      "/yield",
      "/crops",
      "/weather",
      "/risk",
      "/explainability",
      "/insights",
      "/assistant",
      "/research",
      "/model-development",
    ]);
  });

  it("includes translated unavailable and validation messages", () => {
    expect(messages.en.apiUnavailableError).toContain("unavailable");
    expect(messages.hi.apiUnavailableError).toContain("उपलब्ध");
    expect(messages.en.totalSeasonError).toContain("Total");
    expect(messages.hi.totalSeasonError).toContain("Total");
    expect(messages.en.experimentalQuality).toBeTruthy();
    expect(messages.hi.experimentalQuality).toBeTruthy();
  });
});
