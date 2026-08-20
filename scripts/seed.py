#!/usr/bin/env python3
import asyncio, httpx, json
BASE="http://localhost:8000"
async def main():
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            h=await c.get(f"{BASE}/health"); print("gateway",h.json())
        except Exception as e: print("gateway not ready yet (run docker compose up first):",e); return
        # seed via adapter-fabric tag maps (stub)
        for proto in ["opcua","modbus","mqtt","camera"]:
            try:
                r=await c.post(f"{BASE}/api/v1/poll", json={"protocol":proto,"station_id":f"line2-cluster1-{proto}","tag":"ns=2;i=1001"})
                print(proto, r.status_code, r.text[:120])
            except Exception as e: print(proto, e)
        # ask
        try:
            r=await c.post(f"{BASE}/api/v1/ask", json={"question":"why did line 2 slow down?","plant_id":"plant-demo-01","lang":"ta"})
            print("ask", r.json())
        except Exception as e: print("ask",e)
if __name__=="__main__": asyncio.run(main())
