from dataclasses import dataclass


@dataclass
class Measurement:
    value: float
    unit: str