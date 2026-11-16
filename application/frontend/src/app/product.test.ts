import { describe, expect, it } from "vitest";
import { productName } from "./product";

describe("foundation identity", () => {
  it("uses the approved product name", () => {
    expect(productName).toBe("BharatCrop Intelligence");
  });
});
