"""Colours and type for the screen.

Tk cannot blend, so every tint is mixed here into a solid colour.
"""


def mix(a, b, amount):
    """Colour a with the given amount of b stirred in."""
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * amount):02X}" for x, y in zip(pa, pb))


GLASS = "#0F211C"     # the background: the house after dark
PAPER = "#1A332B"     # plant labels and switch plates
INK = "#E4EEE3"       # text
FRAME = "#6FA98F"     # painted ironwork: walls, rules, things switched on
SOIL = "#5A4635"
TIMBER = "#9A7A5B"    # bed edging
WATER = "#3A8CCB"
TOMATO = "#F26A4F"    # needs attention
SUN = "#EBBC3D"       # held by hand

MUTED = mix(INK, GLASS, 0.32)
RULE = mix(FRAME, GLASS, 0.68)
BAND = mix(FRAME, GLASS, 0.78)

# First family found on the machine wins.
SANS = ("IBM Plex Sans Condensed", "Barlow Condensed", "Roboto Condensed",
        "DejaVu Sans Condensed", "Liberation Sans Narrow", "DejaVu Sans")
SERIF = ("IBM Plex Serif", "Noto Serif", "DejaVu Serif", "Liberation Serif")
