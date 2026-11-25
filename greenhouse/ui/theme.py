"""Colours and type for the screen.

Tk cannot blend, so every tint is mixed here into a solid colour.
"""


def mix(a, b, amount):
    """Colour a with the given amount of b stirred in."""
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * amount):02X}" for x, y in zip(pa, pb))


GLASS = "#E2EBE5"     # the background: light through whitewashed panes
PAPER = "#F8FBF7"     # plant labels and switch plates
INK = "#14302A"       # text
FRAME = "#2D5647"     # painted ironwork: walls, rules, things switched on
SOIL = "#C9B498"
TIMBER = "#7B5E45"    # bed edging
WATER = "#2F74A6"
TOMATO = "#C4391F"    # needs attention
SUN = "#E0AE1B"       # held by hand

MUTED = mix(INK, GLASS, 0.32)
RULE = mix(FRAME, GLASS, 0.68)
BAND = mix(FRAME, GLASS, 0.84)

# First family found on the machine wins.
SANS = ("IBM Plex Sans Condensed", "Barlow Condensed", "Roboto Condensed",
        "DejaVu Sans Condensed", "Liberation Sans Narrow", "DejaVu Sans")
SERIF = ("IBM Plex Serif", "Noto Serif", "DejaVu Serif", "Liberation Serif")
