"""Loads greenhouse.toml into plain objects."""

import tomllib
from dataclasses import dataclass
from datetime import time
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "greenhouse.toml"


@dataclass(frozen=True)
class Period:
    name: str
    starts: time
    temp: tuple
    vpd: tuple


@dataclass(frozen=True)
class Bed:
    crop: str
    latin: str
    moisture: tuple
    adc_channel: int
    soil_probe: str
    dry_volts: float
    wet_volts: float


@dataclass(frozen=True)
class Config:
    temperature_unit: str
    read_seconds: float
    periods: tuple
    humidity: tuple
    co2: tuple
    min_switch_seconds: int
    hold_minutes: int
    hold_choices: tuple
    lights_on: time
    lights_off: time
    lights_below_klx: float
    water_from: time
    water_until: time
    run_seconds: int
    soak_minutes: int
    max_manual_seconds: int
    tank_min_percent: float
    beds: tuple
    tank: dict
    relays: dict

    def period_at(self, clock):
        """The period in force at a time of day, and when the next one starts."""
        ordered = sorted(self.periods, key=lambda p: p.starts)
        current = ordered[-1]
        following = ordered[0]
        for i, period in enumerate(ordered):
            if period.starts <= clock:
                current = period
                following = ordered[(i + 1) % len(ordered)]
        return current, following.starts


def load(path=None):
    with open(path or DEFAULT_PATH, "rb") as f:
        raw = tomllib.load(f)
    hhmm = time.fromisoformat
    control, lights, water = raw["control"], raw["lights"], raw["irrigation"]
    return Config(
        temperature_unit=raw["screen"].get("temperature_unit", "F").upper(),
        read_seconds=raw["screen"].get("read_seconds", 5),
        periods=tuple(
            Period(p["name"], hhmm(p["starts"]), tuple(p["temp"]), tuple(p["vpd"]))
            for p in raw["period"]
        ),
        humidity=tuple(raw["targets"]["humidity"]),
        co2=tuple(raw["targets"]["co2"]),
        min_switch_seconds=control["min_switch_seconds"],
        hold_minutes=control["hold_minutes"],
        hold_choices=tuple(control["hold_choices"]),
        lights_on=hhmm(lights["on"]),
        lights_off=hhmm(lights["off"]),
        lights_below_klx=lights["below_klx"],
        water_from=hhmm(water["from"]),
        water_until=hhmm(water["until"]),
        run_seconds=water["run_seconds"],
        soak_minutes=water["soak_minutes"],
        max_manual_seconds=water["max_manual_seconds"],
        tank_min_percent=water["tank_min_percent"],
        beds=tuple(
            Bed(b["crop"], b["latin"], tuple(b["moisture"]), b["adc_channel"],
                b["soil_probe"], b["dry_volts"], b["wet_volts"])
            for b in raw["bed"]
        ),
        tank=raw["tank"],
        relays=raw["relays"],
    )
