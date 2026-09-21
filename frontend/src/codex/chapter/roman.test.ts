import { describe, expect, it } from "vitest";
import { roman } from "./roman";

describe("roman", () => {
  it("renders 1..39 as Roman numerals", () => {
    expect(roman(1)).toBe("I");
    expect(roman(4)).toBe("IV");
    expect(roman(9)).toBe("IX");
    expect(roman(14)).toBe("XIV");
    expect(roman(39)).toBe("XXXIX");
  });

  it("falls back to Arabic above 39", () => {
    expect(roman(40)).toBe("40");
    expect(roman(347)).toBe("347");
  });

  it("passes non-positive / non-integer input through as Arabic", () => {
    expect(roman(0)).toBe("0");
    expect(roman(-3)).toBe("-3");
    expect(roman(2.5)).toBe("2.5");
  });
});
