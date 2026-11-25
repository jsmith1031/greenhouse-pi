"""One set of sensor readings, and a short memory of past ones."""

import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta


def vpd_kpa(temp_c, humidity):
    """Vapour pressure deficit of the air, from the Tetens equation."""
    if temp_c is None or humidity is None:
        return None
    saturation = 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))
    return saturation * (1 - humidity / 100)


@dataclass
class BedReading:
    moisture: float | None = None    # percent
    soil_temp: float | None = None   # C


@dataclass
class Snapshot:
    """Every value is None when its sensor gave no reading."""
    at: datetime
    air_temp: float | None = None    # C
    humidity: float | None = None    # percent
    co2: float | None = None         # ppm
    klx: float | None = None         # kilolux
    out_temp: float | None = None    # C
    out_humidity: float | None = None
    tank: float | None = None        # percent full
    beds: list = field(default_factory=list)
    faults: list = field(default_factory=list)   # sentences for the screen

    @property
    def vpd(self):
        return vpd_kpa(self.air_temp, self.humidity)


TRACED = ("air_temp", "humidity", "vpd", "co2", "klx")


class History:
    """Keeps one sample a minute for the traces on the screen."""

    def __init__(self, hours=6):
        self.samples = deque(maxlen=hours * 60)
        self.last = None

    def add(self, snap):
        if self.last and snap.at - self.last < timedelta(seconds=60):
            return
        self.last = snap.at
        self.samples.append({key: getattr(snap, key) for key in TRACED})

    def series(self, key):
        return [s[key] for s in self.samples if s[key] is not None]
