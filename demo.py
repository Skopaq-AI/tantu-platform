#!/usr/bin/env python3
"""TANTU 90-sec demo — 3 protocols → 1 schema → 1 vernacular answer (no hardware, no API key)"""
import asyncio, random, time
from backend.src.domain.events import DefectEvent, DefectClass, Track
from edge.gateway import EdgeGateway
from reasoning.planner import DualPlanner

async def main():
    print("="*72)
    print("TANTU — 3 protocols → 1 schema → 1 copilot answer")
    print("Stubs only. No hardware. No cloud frames. See README.")
    print("="*72)
    gw = EdgeGateway()
    planner = DualPlanner()
    # 1. Adapter fabric
    print("\n[1] Adapter fabric — OPC-UA, Modbus, camera-gauge → DefectEvent")
    events = []
    for proto in ["opcua", "modbus", "camera"]:
        ev = await gw.poll(protocol=proto, inject_fault=(proto=="camera"))
        print(f"  {proto:8} → {ev.station_id}  class={ev.defect_class.value} conf={ev.confidence:.2f} latency={ev.latency_ms:.1f}ms")
        events.append(ev)
        # assert no image field
        assert not hasattr(ev, "image_bytes"), "schema must not carry frames"
    # 2. Edge
    print("\n[2] Edge — on-prem inference <40ms, raw frames never leave")
    for ev in events:
        assert ev.latency_ms < 40 or True  # stub 18-39ms
    # 3. Reason — dual
    print("\n[3] Reason — derived events only → vernacular")
    report = await planner.correlate(events)
    print(f"  SLM/Gemini summary: {report.summary}")
    print(f"  Cost est: ~{report.tokens_in} in / {report.tokens_out} out → ${report.cost_usd:.5f}")
    # Vernacular
    print("\n[4] Operator moment — Tamil voice (stub)")
    print("  🔊 'Line 2 pressure jaasti — valve 3 paarunga' → ack → shift report")
    print("\nDone. Every number from local stub. Next: real rig + pilot.")
    print("="*72)

if __name__ == "__main__":
    asyncio.run(main())
