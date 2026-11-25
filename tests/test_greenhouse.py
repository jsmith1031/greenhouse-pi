import unittest
from datetime import datetime, time, timedelta

from greenhouse import config, preview
from greenhouse.automation import Controller
from greenhouse.readings import BedReading, Snapshot, vpd_kpa
from greenhouse.relays import SimulatedRelays

NOON = datetime(2026, 6, 18, 12, 0)


def snapshot(**changes):
    values = dict(at=NOON, air_temp=24.0, humidity=65.0, co2=600.0, klx=30.0,
                  out_temp=15.0, out_humidity=70.0, tank=80.0,
                  beds=[BedReading(60.0, 20.0) for _ in range(4)])
    values.update(changes)
    return Snapshot(**values)


class Base(unittest.TestCase):
    def setUp(self):
        self.cfg = config.load()
        self.relays = SimulatedRelays()
        self.c = Controller(self.cfg, self.relays)


class Readings(Base):
    def test_vpd(self):
        self.assertAlmostEqual(vpd_kpa(25, 60), 1.267, places=2)
        self.assertIsNone(vpd_kpa(None, 60))

    def test_periods_wrap_past_midnight(self):
        day, ends = self.cfg.period_at(time(12, 0))
        self.assertEqual((day.name, ends), ("day", time(20, 0)))
        night, ends = self.cfg.period_at(time(2, 0))
        self.assertEqual((night.name, ends), ("night", time(6, 0)))


class Rules(Base):
    def test_calm_house_switches_nothing(self):
        self.c.step(snapshot(), NOON)
        self.assertFalse(any(self.c.on.values()))

    def test_ac_has_a_dead_band(self):
        self.c.step(snapshot(air_temp=27.5), NOON)
        self.assertTrue(self.relays.on["ac"])
        later = NOON + timedelta(minutes=5)
        self.c.step(snapshot(air_temp=26.5), later)
        self.assertTrue(self.c.on["ac"], "still on inside the dead band")
        self.c.step(snapshot(air_temp=25.5), later + timedelta(minutes=5))
        self.assertFalse(self.c.on["ac"])

    def test_no_rapid_switching(self):
        self.c.step(snapshot(air_temp=28), NOON)
        self.c.step(snapshot(air_temp=20), NOON + timedelta(seconds=30))
        self.assertTrue(self.c.on["ac"])
        self.assertEqual(self.c.reason["ac"], "Auto: waiting to switch")

    def test_dry_air_runs_humidifier_damp_air_runs_dehumidifier(self):
        self.c.step(snapshot(air_temp=26, humidity=40), NOON)
        self.assertTrue(self.c.on["humidifier"])
        self.assertFalse(self.c.on["dehumidifier"])
        c = Controller(self.cfg, SimulatedRelays())
        c.step(snapshot(air_temp=22, humidity=74), NOON)
        self.assertTrue(c.on["dehumidifier"])
        self.assertFalse(c.on["humidifier"])

    def test_missing_reading_leaves_device_off(self):
        self.c.step(snapshot(air_temp=None), NOON)
        self.assertFalse(self.c.on["ac"])
        self.assertEqual(self.c.reason["ac"], "No temperature reading")

    def test_lights_only_in_the_day(self):
        self.c.step(snapshot(klx=2), NOON)
        self.assertTrue(self.c.on["lights"])
        c = Controller(self.cfg, SimulatedRelays())
        c.step(snapshot(klx=0), NOON.replace(hour=23))
        self.assertFalse(c.on["lights"])


class Watering(Base):
    def dry(self, **changes):
        beds = [BedReading(60.0, 20.0) for _ in range(4)]
        beds[1] = BedReading(20.0, 20.0)
        return snapshot(beds=beds, **changes)

    def test_waters_then_soaks(self):
        self.c.step(self.dry(), NOON)
        self.assertTrue(self.c.on["pump"])
        self.assertEqual(self.c.reason["pump"], "Auto: basil is dry")
        self.c.step(self.dry(), NOON + timedelta(seconds=60))
        self.assertTrue(self.c.on["pump"])
        self.c.step(self.dry(), NOON + timedelta(seconds=95))
        self.assertFalse(self.c.on["pump"])
        self.c.step(self.dry(), NOON + timedelta(minutes=10))
        self.assertEqual(self.c.reason["pump"], "Auto: soaking in")
        self.c.step(self.dry(), NOON + timedelta(minutes=35))
        self.assertTrue(self.c.on["pump"])

    def test_never_pumps_an_empty_tank(self):
        self.c.step(self.dry(tank=5), NOON)
        self.assertFalse(self.c.on["pump"])
        self.c.tap("pump", NOON)
        self.c.step(self.dry(tank=5), NOON)
        self.assertFalse(self.c.on["pump"])
        self.assertEqual(self.c.reason["pump"], "Tank too low to pump")

    def test_held_pump_is_cut_off(self):
        self.c.step(snapshot(), NOON)
        self.c.tap("pump", NOON)
        self.c.step(snapshot(), NOON)
        self.assertTrue(self.c.on["pump"])
        self.c.step(snapshot(), NOON + timedelta(seconds=301))
        self.assertFalse(self.c.on["pump"])
        self.assertNotIn("pump", self.c.holds)

    def test_not_at_night(self):
        self.c.step(self.dry(), NOON.replace(hour=22))
        self.assertFalse(self.c.on["pump"])


class Holds(Base):
    def test_tap_cycle_and_expiry(self):
        self.c.step(snapshot(), NOON)
        self.c.tap("fan", NOON)
        self.c.step(snapshot(), NOON)
        self.assertTrue(self.c.on["fan"])
        self.assertEqual(self.c.reason["fan"], "Held 30 min more")

        self.c.tap("fan", NOON)
        self.c.step(snapshot(), NOON)
        self.assertFalse(self.c.on["fan"])
        self.assertIn("fan", self.c.holds)

        self.c.tap("fan", NOON)
        self.assertNotIn("fan", self.c.holds)

        self.c.tap("fan", NOON)
        self.c.step(snapshot(), NOON + timedelta(minutes=29))
        self.assertTrue(self.c.on["fan"])
        self.c.step(snapshot(), NOON + timedelta(minutes=31))
        self.assertFalse(self.c.on["fan"], "back to automation after the hold")

    def test_hold_length_cycles(self):
        seen = []
        for _ in range(4):
            self.c.next_hold_length()
            seen.append(self.c.hold_minutes)
        self.assertEqual(seen, [60, 180, 15, 30])


class Screen(unittest.TestCase):
    def test_preview_renders(self):
        svg = preview.render()
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("Held 29 min more", svg)


if __name__ == "__main__":
    unittest.main()
