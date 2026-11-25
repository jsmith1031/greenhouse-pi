"""Writes the dashboard to an SVG, using the simulated greenhouse.

    python -m greenhouse.preview docs/dashboard.svg
"""

import sys
from datetime import datetime, timedelta

from . import config
from .automation import Controller
from .readings import History
from .relays import SimulatedRelays
from .sensors import SimulatedSensors
from .ui import dashboard
from .ui.surface import SvgSurface


def render(now=datetime(2026, 6, 18, 14, 32)):
    cfg = config.load()
    sensors = SimulatedSensors(cfg)
    history = History()
    for minutes in range(359, -1, -1):
        history.add(sensors.read(now - timedelta(minutes=minutes)))

    controller = Controller(cfg, SimulatedRelays())
    earlier = now - timedelta(minutes=1)
    controller.step(sensors.read(earlier), earlier)
    controller.tap("fan", earlier)      # show what a held switch looks like
    snap = sensors.read(now)
    controller.step(snap, now)

    surface = SvgSurface(dashboard.WIDTH, dashboard.HEIGHT)
    dashboard.draw(surface, cfg, snap, history, controller, now)
    return surface.to_string()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "docs/dashboard.svg"
    with open(path, "w") as f:
        f.write(render())
    print("wrote", path)
