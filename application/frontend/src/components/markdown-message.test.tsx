// @vitest-environment happy-dom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { MarkdownMessage } from "./markdown-message";

afterEach(cleanup);

describe("MarkdownMessage", () => {
  it("renders headings, bold text and lists instead of raw markdown", () => {
    const { container } = render(
      <MarkdownMessage
        content={[
          "## Current operational status",
          "",
          "**No component has been granted production approval.**",
          "",
          "- First registry entry",
          "- Second registry entry",
        ].join("\n")}
      />,
    );

    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "Current operational status",
      }),
    ).toBeDefined();
    expect(container.querySelector("strong")?.textContent).toBe(
      "No component has been granted production approval.",
    );
    expect(container.querySelectorAll("li")).toHaveLength(2);
    expect(container.textContent).not.toContain("**");
    expect(container.textContent).not.toContain("##");
  });

  it("renders GFM tables with aligned headers and inline code", () => {
    const content = [
      "| Registry ID | Recorded status | Production-approved? |",
      "| --- | :---: | ---: |",
      "| `yield_prediction_individual_crop_hgb` | *CONDITIONALLY READY* | **No** |",
      "| `weather_low_yield_classifier` | *NOT READY* | **No** |",
    ].join("\n");
    const { container } = render(<MarkdownMessage content={content} />);

    expect(screen.getByRole("table")).toBeDefined();
    expect(screen.getAllByRole("columnheader")).toHaveLength(3);
    expect(screen.getAllByRole("row")).toHaveLength(3);
    expect(container.querySelector("code")?.textContent).toBe(
      "yield_prediction_individual_crop_hgb",
    );
    expect(container.querySelectorAll("strong")).toHaveLength(2);
    expect(container.textContent).not.toContain("|");
    expect(container.textContent).not.toContain("---");
  });

  it("keeps non-http links as plain text", () => {
    const { container } = render(
      <MarkdownMessage content={"[unsafe](javascript:alert(1))"} />,
    );

    expect(container.querySelector("a")).toBeNull();
    expect(container.textContent).toContain("[unsafe](javascript:alert(1))");
  });
});
