import { describe, expect, it } from "vitest";
import { validateBookmark } from "./bookmarkStore";

describe("validateBookmark", () => {
  it("accepts an integer string in 1..N", () => {
    expect(validateBookmark("1", 4)).toBe(1);
    expect(validateBookmark("4", 4)).toBe(4);
    expect(validateBookmark(" 3 ", 4)).toBe(3);
  });

  it("resets tampered values to 1 (never the last chapter)", () => {
    for (const bad of ["0", "-3", "999", "abc", "2.5", "1e2", "", null, undefined, "5", "0x3"]) {
      expect(validateBookmark(bad, 4)).toBe(1);
    }
  });

  it("resets when chapter_count itself is unusable", () => {
    expect(validateBookmark("3", 0)).toBe(1);
    expect(validateBookmark("3", NaN)).toBe(1);
  });
});
