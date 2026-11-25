"""Starts the dashboard.

    python -m greenhouse                 on the Pi, full screen
    python -m greenhouse --sim --window  anywhere, with made-up readings
"""

import argparse
import logging

from . import config


def main():
    parser = argparse.ArgumentParser(prog="greenhouse", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sim", action="store_true",
                        help="simulate the sensors and relays")
    parser.add_argument("--window", action="store_true",
                        help="open a 1024x600 window instead of going full screen")
    parser.add_argument("--config", help="path to a settings file")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    cfg = config.load(args.config)
    if args.sim:
        from .relays import SimulatedRelays
        from .sensors import SimulatedSensors
        sensors, relays = SimulatedSensors(cfg), SimulatedRelays()
    else:
        from .relays import PiRelays
        from .sensors import PiSensors
        try:
            sensors, relays = PiSensors(cfg), PiRelays(cfg)
        except (ImportError, NotImplementedError) as error:
            parser.exit(1, f"Could not reach the Pi hardware ({error}).\n"
                           "Install requirements-pi.txt, or run with --sim.\n")

    from .ui.app import App
    App(cfg, sensors, relays, fullscreen=not args.window, prefill=args.sim).run()


if __name__ == "__main__":
    main()
