import { describe, it, expect } from "vitest";
import { t, dict, LANG_LABEL } from "@/lib/i18n";

describe("i18n", () => {
  it("has hi/ta/te/kn translations for vernacular_pressure", () => {
    for (const lang of ["en", "hi", "ta", "te", "kn"] as const) {
      const v = t("vernacular_pressure", lang);
      expect(typeof v).toBe("string");
      expect(v.length).toBeGreaterThan(5);
    }
  });

  it("code-switch keeps english technical terms", () => {
    expect(t("vernacular_pressure", "hi")).toContain("Line 2");
    expect(t("vernacular_pressure", "ta")).toContain("Line 2");
  });

  it("fallback to en when key missing", () => {
    expect(t("nonexistent_key_xyz", "ta")).toBe("nonexistent_key_xyz");
  });

  it("LANG_LABEL covers all langs", () => {
    expect(Object.keys(LANG_LABEL)).toEqual(expect.arrayContaining(["en", "hi", "ta", "te", "kn"]));
  });

  it("dict has operator/maintenance/plant_head", () => {
    for (const k of ["operator", "maintenance", "plant_head"]) {
      expect(dict[k]).toBeDefined();
      for (const lang of ["en", "hi", "ta", "te", "kn"] as const) {
        expect(dict[k][lang]).toBeDefined();
      }
    }
  });
});
