"""Decides what each device should be doing.

Left alone, every device follows the rules below. A tap on the screen holds a
device on or off for a while, after which it goes back to the rules.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from .relays import DEVICES

IN_RANGE = "Auto: in range"


@dataclass
class Hold:
    on: bool
    until: datetime
    flipped: bool = False


class Controller:
    def __init__(self, cfg, relays):
        self.cfg = cfg
        self.relays = relays
        self.hold_minutes = cfg.hold_minutes
        self.on = {key: False for key, _ in DEVICES}
        self.reason = {key: IN_RANGE for key, _ in DEVICES}
        self.holds = {}
        self.changed = {}       # when each device last switched
        self.latched = {}       # memory for the on/off thresholds

    # -- taps ---------------------------------------------------------------

    def tap(self, key, now):
        """First tap flips the device, second flips it back, third releases."""
        until = now + timedelta(minutes=self.hold_minutes)
        hold = self.holds.get(key)
        if hold is None:
            self.holds[key] = Hold(not self.on[key], until)
        elif not hold.flipped:
            self.holds[key] = Hold(not hold.on, until, flipped=True)
        else:
            del self.holds[key]

    def next_hold_length(self):
        choices = self.cfg.hold_choices
        later = [c for c in choices if c > self.hold_minutes]
        self.hold_minutes = later[0] if later else choices[0]

    # -- the loop -----------------------------------------------------------

    def step(self, snap, now):
        period, _ = self.cfg.period_at(now.time())
        for key, _ in DEVICES:
            want, why = getattr(self, f"_{key}")(snap, period, now)

            hold = self.holds.get(key)
            if hold and self._hold_over(key, hold, now):
                del self.holds[key]
                hold = None

            if hold:
                want = hold.on
                left = math.ceil((hold.until - now).total_seconds() / 60)
                why = f"Held {left} min more"
            elif key != "pump" and want != self.on[key] and self._too_soon(key, now):
                want, why = self.on[key], "Auto: waiting to switch"

            if key == "pump" and want and snap.tank is not None \
                    and snap.tank < self.cfg.tank_min_percent:
                want, why = False, "Tank too low to pump"

            if want != self.on[key]:
                self.on[key] = want
                self.changed[key] = now
                self.relays.set(key, want)
            self.reason[key] = why

    def _hold_over(self, key, hold, now):
        if hold.until <= now:
            return True
        # A pump left held on would flood the beds.
        return (key == "pump" and hold.on and self.on["pump"]
                and self._since_change("pump", now) >= self.cfg.max_manual_seconds)

    def _since_change(self, key, now):
        if key not in self.changed:
            return math.inf
        return (now - self.changed[key]).total_seconds()

    def _too_soon(self, key, now):
        return self._since_change(key, now) < self.cfg.min_switch_seconds

    def _latch(self, name, value, on_above, off_below):
        """On above one threshold, off below a lower one, unchanged between."""
        if value > on_above:
            self.latched[name] = True
        elif value < off_below:
            self.latched[name] = False
        return self.latched.get(name, False)

    # -- rules, one per device ----------------------------------------------

    def _ac(self, snap, period, now):
        if snap.air_temp is None:
            return False, "No temperature reading"
        high = period.temp[1]
        if self._latch("ac", snap.air_temp, high, high - 1):
            return True, "Auto: too warm"
        return False, IN_RANGE

    def _fan(self, snap, period, now):
        if snap.air_temp is None or snap.humidity is None:
            return False, "No air reading"
        high = period.temp[1]
        warm = self._latch("fan.warm", snap.air_temp, high - 1, high - 2)
        if warm and (snap.out_temp is None or snap.out_temp < snap.air_temp):
            return True, "Auto: venting heat"
        damp = self.cfg.humidity[1]
        if self._latch("fan.damp", snap.humidity, damp, damp - 4):
            return True, "Auto: venting damp air"
        # A closed house full of plants runs short of CO2 by midday.
        low = self.cfg.co2[0]
        if snap.co2 is not None and self._latch("fan.co2", -snap.co2, -low, -(low + 50)):
            return True, "Auto: letting in CO2"
        return False, IN_RANGE

    def _humidifier(self, snap, period, now):
        if snap.vpd is None:
            return False, "No humidity reading"
        low, high = period.vpd
        if self._latch("humidifier", snap.vpd, high, (low + high) / 2):
            return True, "Auto: air too dry"
        return False, IN_RANGE

    def _dehumidifier(self, snap, period, now):
        if snap.vpd is None:
            return False, "No humidity reading"
        low, high = period.vpd
        if self._latch("dehumidifier", -snap.vpd, -low, -(low + high) / 2):
            return True, "Auto: air too damp"
        return False, IN_RANGE

    def _lights(self, snap, period, now):
        if not self.cfg.lights_on <= now.time() < self.cfg.lights_off:
            return False, "Auto: night"
        if snap.klx is None:
            return False, "No light reading"
        dim = self.cfg.lights_below_klx
        if self._latch("lights", -snap.klx, -dim, -dim * 1.5):
            return True, "Auto: daylight is dim"
        return False, "Auto: enough daylight"

    def _pump(self, snap, period, now):
        cfg = self.cfg
        running = self.on["pump"] and "pump" not in self.holds
        if running:
            if self._since_change("pump", now) < cfg.run_seconds:
                why = self.reason["pump"]
                return True, "Auto: watering" if why.startswith("Held") else why
            return False, "Auto: soaking in"
        if snap.tank is None:
            return False, "No tank reading"
        if not self.on["pump"] and self._since_change("pump", now) < cfg.soak_minutes * 60:
            return False, "Auto: soaking in"
        if not cfg.water_from <= now.time() < cfg.water_until:
            return False, "Auto: off hours"
        for bed, reading in zip(cfg.beds, snap.beds):
            if reading.moisture is not None and reading.moisture < bed.moisture[0]:
                return True, f"Auto: {bed.crop.lower()} is dry"
        return False, "Auto: beds are moist"
