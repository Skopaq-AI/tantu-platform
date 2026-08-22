import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchEvents } from "@/lib/api";

describe("lib/api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("fetchEvents falls back to demo data when fetch fails and DEMO enabled", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO", "true");
    // re-import to pick up env? isDemoEnabled reads at call time so stubEnv suffices
    const { fetchEvents: fetchDemod } = await import("@/lib/api");
    vi.stubGlobal("fetch", async () => { throw new Error("offline"); });
    const evs = await fetchDemod(1);
    expect(Array.isArray(evs)).toBe(true);
    expect(evs.length).toBeGreaterThan(0);
    expect(evs[0]).toHaveProperty("station_id");
  });

  it("fetchEvents throws when DEMO disabled and fetch fails", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO", "false");
    const { fetchEvents: fetchNoDemo } = await import("@/lib/api");
    vi.stubGlobal("fetch", async () => { throw new Error("offline"); });
    await expect(fetchNoDemo(1)).rejects.toThrow();
  });

  it("fetchEvents returns parsed json when ok", async () => {
    const demo = [{ station_id: "s1", defect_class: "none", confidence: 1, latency_ms: 10, protocol: "opcua" }];
    vi.stubGlobal("fetch", async () => ({ ok: true, json: async () => demo } as any));
    const evs = await fetchEvents(1);
    expect(evs[0].station_id).toBe("s1");
  });
});
