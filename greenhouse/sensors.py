"""Where readings come from: the real sensors on a Pi, or a simulation."""

import glob
import logging
import math
from datetime import datetime

from .readings import BedReading, Snapshot

log = logging.getLogger(__name__)


class SimulatedSensors:
    """A plausible day in the greenhouse, for running without hardware."""

    def __init__(self, cfg):
        self.cfg = cfg

    def read(self, at=None):
        at = at or datetime.now()
        hour = at.hour + at.minute / 60 + at.second / 3600
        t = at.timestamp()

        def sun(h):
            return max(0.0, math.sin(math.pi * (h - 6.5) / 11))

        warmth = sun(hour - 1.5)    # the air lags the sun
        # Each bed dries out, gets watered, and starts again.
        wet = (72, 66, 64, 76)
        rate = (4.5, 5.0, 3.0, 3.0)
        offset = (2.0, 5.9, 4.0, 3.0)
        cycle = (7.0, 7.5, 8.0, 6.0)
        beds = [
            BedReading(
                moisture=wet[i % 4] - rate[i % 4] * ((hour + offset[i % 4]) % cycle[i % 4]),
                soil_temp=16 + 4 * sun(hour - 3) + 0.4 * i,
            )
            for i in range(len(self.cfg.beds))
        ]
        return Snapshot(
            at=at,
            air_temp=17.5 + 7.5 * warmth + 0.3 * math.sin(t / 600),
            humidity=78 - 16 * warmth + 1.5 * math.sin(t / 420 + 1),
            co2=780 - 260 * sun(hour) + 15 * math.sin(t / 300),
            klx=26 * sun(hour) * (0.94 + 0.06 * math.sin(t / 1700)),
            out_temp=6 + 6 * warmth,
            out_humidity=80 - 15 * warmth,
            tank=92 - 35 * hour / 24,
            beds=beds,
        )


class PiSensors:
    """The sensors wired to the Pi.

    SHT31    air temperature and humidity    I2C 0x44
    SCD41    CO2                             I2C 0x62
    BH1750   daylight                        I2C 0x23
    BME280   outside temperature, humidity   I2C 0x76
    ADS1115  capacitive soil probes, A0-A3   I2C 0x48
    DS18B20  soil temperature, one per bed   1-Wire
    HC-SR04  water tank level                GPIO

    A sensor that is missing or stops answering gives None and a line in
    Snapshot.faults; the rest carry on.
    """

    def __init__(self, cfg):
        import board

        self.cfg = cfg
        self.co2 = None
        i2c = board.I2C()
        self.sht = self._open("air sensor", lambda: _sht31(i2c))
        self.scd = self._open("CO2 sensor", lambda: _scd41(i2c))
        self.bh = self._open("light sensor", lambda: _bh1750(i2c))
        self.bme = self._open("outside sensor", lambda: _bme280(i2c))
        self.soil = self._open("soil probes", lambda: _soil_channels(i2c, cfg))
        self.sonar = self._open("tank sensor", lambda: _sonar(cfg.tank))

    def _open(self, label, factory):
        try:
            return factory()
        except Exception as error:
            log.warning("%s not found: %s", label, error)
            return None

    def read(self, at=None):
        snap = Snapshot(at=at or datetime.now())

        def get(label, device, fn):
            if device is not None:
                try:
                    return fn(device)
                except Exception as error:
                    log.warning("%s read failed: %s", label, error)
            fault = f"{label[0].upper()}{label[1:]} is not answering"
            if fault not in snap.faults:
                snap.faults.append(fault)
            return None

        snap.air_temp = get("air sensor", self.sht, lambda d: d.temperature)
        snap.humidity = get("air sensor", self.sht, lambda d: d.relative_humidity)
        snap.co2 = get("CO2 sensor", self.scd, self._co2)
        lux = get("light sensor", self.bh, lambda d: d.lux)
        snap.klx = None if lux is None else lux / 1000
        snap.out_temp = get("outside sensor", self.bme, lambda d: d.temperature)
        snap.out_humidity = get("outside sensor", self.bme, lambda d: d.relative_humidity)
        distance = get("tank sensor", self.sonar, lambda d: d.distance * 100)
        if distance is not None:
            empty, full = self.cfg.tank["empty_cm"], self.cfg.tank["full_cm"]
            snap.tank = _clamp(100 * (empty - distance) / (empty - full))

        for i, bed in enumerate(self.cfg.beds):
            volts = get("soil probes", self.soil, lambda d: d[i].voltage)
            moisture = None
            if volts is not None:
                span = bed.dry_volts - bed.wet_volts
                moisture = _clamp(100 * (bed.dry_volts - volts) / span)
            soil_temp = get(f"{bed.crop.lower()} soil thermometer",
                            bed.soil_probe, _ds18b20)
            snap.beds.append(BedReading(moisture, soil_temp))
        return snap

    def _co2(self, scd):
        # The SCD41 has a new value every five seconds; keep the last one.
        if scd.data_ready:
            self.co2 = scd.CO2
        if self.co2 is None:
            raise RuntimeError("no measurement yet")
        return self.co2


def _clamp(value):
    return max(0.0, min(100.0, value))


def _sht31(i2c):
    import adafruit_sht31d
    return adafruit_sht31d.SHT31D(i2c)


def _scd41(i2c):
    import adafruit_scd4x
    scd = adafruit_scd4x.SCD4X(i2c)
    scd.start_periodic_measurement()
    return scd


def _bh1750(i2c):
    import adafruit_bh1750
    return adafruit_bh1750.BH1750(i2c)


def _bme280(i2c):
    from adafruit_bme280 import basic
    return basic.Adafruit_BME280_I2C(i2c, address=0x76)


def _soil_channels(i2c, cfg):
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    adc = ADS.ADS1115(i2c)
    return [AnalogIn(adc, bed.adc_channel) for bed in cfg.beds]


def _sonar(tank):
    from gpiozero import DistanceSensor
    return DistanceSensor(echo=tank["echo_pin"], trigger=tank["trigger_pin"],
                          max_distance=2)


def _ds18b20(probe_id):
    paths = glob.glob(f"/sys/bus/w1/devices/{probe_id}/temperature")
    if not paths:
        raise FileNotFoundError(probe_id)
    with open(paths[0]) as f:
        return int(f.read().strip()) / 1000
