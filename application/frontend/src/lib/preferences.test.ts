import { describe, expect, it, vi } from "vitest";
import { readPreference, resolveTheme, writePreference } from "./preferences";

describe("persistent interface preferences", () => {
  it("resolves system appearance and preserves explicit themes", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
    expect(resolveTheme("light", true)).toBe("light");
  });

  it("reads only supported language and theme preferences", () => {
    const storage = {
      getItem: vi.fn((key: string) => (key === "language" ? "hi" : "neon")),
    };
    expect(readPreference(storage, "language", ["en", "hi"], "en")).toBe("hi");
    expect(
      readPreference(storage, "theme", ["light", "dark", "system"], "system"),
    ).toBe("system");
  });

  it("persists language and theme selection", () => {
    const storage = { setItem: vi.fn() };
    writePreference(storage, "bharatcrop-language", "hi");
    writePreference(storage, "bharatcrop-theme", "dark");
    expect(storage.setItem).toHaveBeenNthCalledWith(
      1,
      "bharatcrop-language",
      "hi",
    );
    expect(storage.setItem).toHaveBeenNthCalledWith(
      2,
      "bharatcrop-theme",
      "dark",
    );
  });
});
