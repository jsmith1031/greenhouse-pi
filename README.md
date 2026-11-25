# greenhouse-pi

A Raspberry Pi with a 7-inch touchscreen that watches the plants in a small
greenhouse and runs the fan, AC, humidifier, dehumidifier, grow lights and
water pump for them.

![Sensors on the left feed the Pi and its touchscreen, which switches six devices through a relay board](docs/hardware.svg)

![The dashboard: four beds seen from above, air readings with six-hour traces, and six switches](docs/dashboard.svg)

Tap a switch to hold it on or off for a while. It goes back to automation on
its own.

## Run

Without a Pi (Python 3.11+ with Tkinter, simulated readings):

```
python -m greenhouse --sim --window
```

On the Pi, with I2C and 1-Wire turned on in `raspi-config`:

```
sudo apt install python3-tk fonts-ibm-plex
pip install -r requirements-pi.txt
python -m greenhouse
```

Beds, targets, watering hours and pin numbers are in
[`greenhouse.toml`](greenhouse.toml). Tests: `python -m unittest`.

## Not done yet

- The sensor and relay drivers have not been run against real hardware.
- Twitch streaming from the Pi camera.
- Readings are not saved across restarts.

**Jeffrey Smith** - Github: [jsmith1031](https://github.com/jsmith1031). GPL v3, see [LICENSE](LICENSE).
