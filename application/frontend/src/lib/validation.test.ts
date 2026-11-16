import { describe, expect, it } from "vitest";
import { isAggregateSeason, parseCropNames } from "./validation";

describe("agricultural form validation", () => {
  it("rejects aggregate Total but leaves specific season names untouched", () => {
    expect(isAggregateSeason("Total")).toBe(true);
    expect(isAggregateSeason(" total ")).toBe(true);
    expect(isAggregateSeason("Kharif")).toBe(false);
  });

  it("requires two distinct crop names without inventing a catalog", () => {
    expect(parseCropNames("Rice")).toEqual({
      valid: false,
      reason: "too-few",
    });
    expect(parseCropNames("Rice, Rice")).toEqual({
      valid: false,
      reason: "duplicate",
    });
    expect(parseCropNames(" Rice, Wheat ")).toEqual({
      valid: true,
      crops: ["Rice", "Wheat"],
    });
  });
});
