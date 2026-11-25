"""Switches the mains devices through the relay board."""

DEVICES = (
    ("fan", "Vent fan"),
    ("ac", "AC"),
    ("humidifier", "Humidifier"),
    ("dehumidifier", "Dehumidifier"),
    ("lights", "Grow lights"),
    ("pump", "Water pump"),
)


class SimulatedRelays:
    def __init__(self):
        self.on = {key: False for key, _ in DEVICES}

    def set(self, key, on):
        self.on[key] = on


class PiRelays:
    """Everything starts switched off, and goes off again on exit."""

    def __init__(self, cfg):
        from gpiozero import OutputDevice

        active_high = not cfg.relays.get("active_low", True)
        self.outputs = {
            key: OutputDevice(cfg.relays[key], active_high=active_high,
                              initial_value=False)
            for key, _ in DEVICES
        }

    def set(self, key, on):
        self.outputs[key].value = on
