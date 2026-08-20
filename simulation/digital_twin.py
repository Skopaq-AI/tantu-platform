"""Digital twin stub — swap to Isaac Sim in prod."""
from dataclasses import dataclass
from typing import Iterator
import random, time

@dataclass
class SimTick:
    tick: int; inject: bool; note: str

class ScenarioRunner:
    def __init__(self, n=12, faults=(4,5,9)): self.n=n; self.faults=set(faults)
    def run(self) -> Iterator[SimTick]:
        for i in range(1,self.n+1): yield SimTick(i, i in self.faults, "fault" if i in self.faults else "nominal")
