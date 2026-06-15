import { describe, it, expect } from "vitest";
import { fmt, ACTION_LABELS } from "../utils/format";

describe("format utils", () => {
  it("formats numbers with fr locale", () => {
    expect(fmt(3.456)).toBe("3,46");
    expect(fmt(null)).toBe("—");
  });

  it("maps fuzzy actions to labels", () => {
    expect(ACTION_LABELS.CHARGER_BATTERIE).toBe("Charger la batterie");
  });
});
