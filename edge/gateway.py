"""Edge gateway — tiered, offline-first, camera-as-adapter."""
import asyncio, random, time
from backend.src.domain.events import DefectEvent, DefectClass, Track, TelemetryReading

class OpcUaAdapter:
    async def read(self, station_id: str): return random.uniform(0,100)
class ModbusAdapter:
    async def read(self, station_id: str): return random.uniform(0,100)
class CameraAdapter:
    """Camera-as-adapter for analog gauges — Hailo-8L/Orin stub."""
    async def read_gauge(self, station_id: str) -> tuple[float,float]:
        # dust/glare/parallax simulated; value + confidence
        val = random.uniform(0, 10) + random.uniform(-0.3,0.3)
        conf = random.uniform(0.82,0.99) if random.random()>0.2 else random.uniform(0.5,0.82)
        await asyncio.sleep(random.uniform(0.018,0.039))  # <40ms tier
        return val, conf

class EdgeGateway:
    def __init__(self):
        self.opc = OpcUaAdapter(); self.mod = ModbusAdapter(); self.cam = CameraAdapter()
        self.health = {"opcua": "ok", "modbus": "ok", "camera": "ok", "store_forward_len": 0}
    async def poll(self, protocol="opcua", station_id="line2-cluster1-gauge3", inject_fault=False):
        import random
        t0 = time.time()
        defect = DefectClass.NONE; conf=random.uniform(0.90,0.98); latency=random.uniform(18,39)
        if protocol=="camera":
            val, conf = await self.cam.read_gauge(station_id)
            defect = DefectClass.PRESSURE_DRIFT if val>7 or inject_fault else DefectClass.NONE
            latency = random.uniform(18,39)
        elif inject_fault or random.random()<0.15:
            defect = random.choice([DefectClass.PRESSURE_DRIFT, DefectClass.VIB_HIGH, DefectClass.THERMAL_HIGH])
            conf = random.uniform(0.85,0.98)
        return DefectEvent(station_id=station_id, track=Track.LINE, defect_class=defect, confidence=conf, latency_ms=latency, protocol=protocol)
    async def telemetry(self, station_id: str) -> TelemetryReading:
        import random
        return TelemetryReading(station_id=station_id, metric="vibration_rms", value=random.uniform(0.1,2.5), unit="mm/s")
