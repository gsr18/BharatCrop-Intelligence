// @vitest-environment happy-dom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ModelDevelopmentPage } from "./model-development-page";

vi.mock("./app-providers", () => ({
  useApp: () => ({ language: "en" }),
}));

afterEach(cleanup);

describe("model development lesson", () => {
  it("explains the model-selection journey and labels the metric example synthetic", () => {
    render(<ModelDevelopmentPage />);

    expect(
      screen.getByRole("heading", { name: "How a model is selected" }),
    ).toBeDefined();
    expect(screen.getByText("SYNTHETIC EXAMPLE")).toBeDefined();
    expect(
      screen.getByText(/not project observations or model results/i),
    ).toBeDefined();
    expect(
      screen.getByText(
        "HistGradientBoostingRegressor was selected from the candidates evaluated in this project. This is a project-specific choice—not a claim that boosting is universally best.",
      ),
    ).toBeDefined();
  });

  it("lets visitors move through the interactive learning steps", () => {
    render(<ModelDevelopmentPage />);

    fireEvent.click(
      screen.getByRole("button", { name: /Evaluate generalization/ }),
    );

    expect(
      screen.getByRole("heading", { name: "Evaluate generalization" }),
    ).toBeDefined();
    expect(screen.getByText(/Test on later observations/)).toBeDefined();
  });
});
