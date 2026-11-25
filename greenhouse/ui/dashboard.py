"""Draws the whole screen, 1024 by 600.

Left: the greenhouse seen from above, each bed filled with water to the level
of its soil moisture. Right: the air. Bottom: the switches.
"""

import math

from ..relays import DEVICES
from .theme import (BAND, FRAME, GLASS, INK, MUTED, PAPER, RULE, SOIL, SUN,
                    TIMBER, TOMATO, WATER, mix)

WIDTH, HEIGHT = 1024, 600

BEDS = ((44, 110), (276, 110), (44, 290), (276, 290))   # top-left corners
BED_W, BED_H, LABEL_H = 220, 140, 62


def draw(s, cfg, snap, history, controller, now):
    """Paints one frame and returns the touch areas as (x0, y0, x1, y1, action)."""
    period, period_ends = cfg.period_at(now.time())
    s.clear(GLASS)
    _top(s, cfg, snap, controller, now, period, period_ends)
    _plan(s, cfg, snap)
    _air(s, cfg, snap, history, period)
    return _switches(s, controller)


# -- words and numbers --------------------------------------------------------

def temp(celsius, unit, places=0):
    if celsius is None:
        return "--"
    value = celsius * 9 / 5 + 32 if unit == "F" else celsius
    return f"{value:.{places}f}"


def problems(cfg, snap, controller, period):
    """Everything that wants a person, most urgent first."""
    unit = cfg.temperature_unit
    found = list(snap.faults)
    if snap.tank is not None and snap.tank < cfg.tank_min_percent:
        found.append(f"Water tank is low ({snap.tank:.0f}%), refill it")
    for bed, reading in zip(cfg.beds, snap.beds):
        if reading.moisture is None:
            continue
        low, high = bed.moisture
        if reading.moisture < low:
            watering = ", watering now" if controller.on["pump"] else ""
            found.append(f"{bed.crop} bed is dry ({reading.moisture:.0f}%){watering}")
        elif reading.moisture > high:
            found.append(f"{bed.crop} bed is too wet ({reading.moisture:.0f}%)")
    if snap.air_temp is not None:
        low, high = period.temp
        if snap.air_temp > high:
            found.append(f"Air is too warm ({temp(snap.air_temp, unit)}°{unit})")
        elif snap.air_temp < low:
            found.append(f"Air is too cold ({temp(snap.air_temp, unit)}°{unit})")
    if snap.vpd is not None:
        low, high = period.vpd
        if snap.vpd > high:
            found.append(f"Air is too dry for the plants (VPD {snap.vpd:.2f})")
        elif snap.vpd < low:
            found.append(f"Air is too damp for the plants (VPD {snap.vpd:.2f})")
    return found


# -- top strip ----------------------------------------------------------------

def _top(s, cfg, snap, controller, now, period, period_ends):
    s.text(20, 29, f"{now:%H:%M}", 38, INK, bold=True)
    s.text(140, 19, f"{now:%A} {now.day} {now:%B}", 16, INK)
    s.text(140, 40, f"{period.name.capitalize()} targets until {period_ends:%H:%M}",
           13, MUTED)

    found = problems(cfg, snap, controller, period)
    s.rect(372, 10, 1008, 48, fill=PAPER)
    if found:
        s.rect(372, 10, 410, 48, fill=TOMATO)
        s.text(391, 29, "!", 26, PAPER, "center", bold=True)
        more = f", and {len(found) - 1} more" if len(found) > 1 else ""
        s.text(424, 29, found[0] + more, 18, INK)
    else:
        s.rect(372, 10, 410, 48, fill=FRAME)
        s.line([(382, 30), (389, 37), (401, 22)], PAPER, 3)
        s.text(424, 29, "Everything is in range", 18, INK)


# -- the greenhouse from above ------------------------------------------------

def _plan(s, cfg, snap):
    unit = cfg.temperature_unit
    outside = "Outside: no reading"
    if snap.out_temp is not None:
        outside = f"Outside {temp(snap.out_temp, unit)}°{unit}"
        if snap.out_humidity is not None:
            outside += f", {snap.out_humidity:.0f}% humidity"
    s.text(24, 76, outside, 13, MUTED)

    # Glazed walls, with the door in the east wall at the end of the aisle.
    s.rect(24, 92, 632, 444, outline=FRAME, width=3)
    s.rect(31, 99, 625, 437, outline=FRAME, width=1)
    for x in range(62, 632, 38):
        s.line([(x, 92), (x, 99)], FRAME)
        s.line([(x, 437), (x, 444)], FRAME)
    for y in range(130, 444, 38):
        s.line([(24, y), (31, y)], FRAME)
        s.line([(625, y), (632, y)], FRAME)
    s.rect(620, 252, 636, 288, fill=GLASS)
    s.line([(628, 252), (590, 252)], FRAME, 3)
    s.line(_arc(628, 252, 38, 180, 90), FRAME)

    for (x, y), bed, reading in zip(BEDS, cfg.beds, snap.beds):
        _bed(s, x, y, bed, reading, unit)

    for x, label in ((56, "Air and CO2 sensor"), (288, "Light sensor")):
        s.oval(x - 4, 266, x + 4, 274, fill=FRAME)
        s.text(x + 11, 270, label, 12, MUTED)

    _tank(s, 562, 168, 40, snap.tank, cfg.tank_min_percent)
    s.rect(540, 366, 584, 394, fill=PAPER, outline=FRAME, width=1.5)
    s.text(562, 408, "This screen", 12, MUTED, "center")


def _bed(s, x, y, bed, reading, unit):
    x1, y1 = x + BED_W, y + BED_H
    top = y + LABEL_H
    low, high = bed.moisture
    moisture = reading.moisture
    dry = moisture is not None and moisture < low

    s.rect(x, top, x1, y1, fill=SOIL)
    if moisture is not None:
        level = y1 - (y1 - top) * max(0, min(100, moisture)) / 100
        s.rect(x, level, x1, y1, fill=WATER)
    for mark in (low, high):
        my = y1 - (y1 - top) * mark / 100
        s.line([(x + 6, my), (x1 - 6, my)], INK, 1, dash=(2, 4))

    s.rect(x, y, x1, top, fill=PAPER)
    s.text(x + 10, y + 21, bed.crop, 19, INK, bold=True)
    s.text(x + 10, y + 44, bed.latin, 12, MUTED, italic=True, serif=True)
    if moisture is None:
        s.text(x1 - 10, y + 21, "no reading", 15, TOMATO, "e")
    else:
        s.text(x1 - 26, y + 21, f"{moisture:.0f}", 30, TOMATO if dry else INK,
               "e", bold=True)
        s.text(x1 - 23, y + 25, "%", 15, TOMATO if dry else INK)
    if reading.soil_temp is not None:
        s.text(x1 - 10, y + 46, f"soil {temp(reading.soil_temp, unit)}°{unit}",
               13, MUTED, "e")
    s.rect(x, y, x1, y1, outline=TOMATO if dry else TIMBER, width=3 if dry else 2)


def _tank(s, cx, cy, r, percent, minimum):
    low = percent is not None and percent < minimum
    s.oval(cx - r, cy - r, cx + r, cy + r, fill=PAPER)
    if percent:
        # The part of the circle below the water line.
        half = math.acos(max(-1.0, min(1.0, 1 - 2 * percent / 100)))
        steps = [-half + 2 * half * i / 40 for i in range(41)]
        s.polygon([(cx + r * math.sin(a), cy + r * math.cos(a)) for a in steps],
                  fill=WATER)
    s.oval(cx - r, cy - r, cx + r, cy + r, outline=TOMATO if low else FRAME, width=2)
    s.text(cx, cy + r + 16, "Water tank", 13, MUTED, "center")
    s.text(cx, cy + r + 37, "no reading" if percent is None else f"{percent:.0f}%",
           20, TOMATO if low or percent is None else INK, "center", bold=True)


# -- the air ------------------------------------------------------------------

def _air(s, cfg, snap, history, period):
    unit = cfg.temperature_unit

    def degrees(celsius):
        return celsius * 9 / 5 + 32 if unit == "F" else celsius

    rows = (
        ("Air temperature", "air_temp", snap.air_temp, f"°{unit}", period.temp, 1, degrees),
        ("Humidity", "humidity", snap.humidity, "%", cfg.humidity, 0, None),
        ("VPD", "vpd", snap.vpd, "kPa", period.vpd, 2, None),
        ("CO2", "co2", snap.co2, "ppm", cfg.co2, 0, None),
        ("Daylight", "klx", snap.klx, "klx", None, 1, None),
    )
    x, w, h = 656, 352, 78
    s.text(x + w, 76, "last 6 hours", 12, MUTED, "e")
    for i, (label, key, value, units, target, places, convert) in enumerate(rows):
        y = 64 + i * h
        convert = convert or (lambda v: v)
        target = tuple(convert(t) for t in target) if target else None
        shown = None if value is None else convert(value)
        outside = shown is not None and target and not target[0] <= shown <= target[1]

        if i:
            s.line([(x, y), (x + w, y)], RULE)
        if outside:
            s.rect(x, y + 8, x + 4, y + h - 8, fill=TOMATO)
        s.text(x + 14, y + 17, label, 14, MUTED)
        if shown is None:
            s.text(x + 14, y + 48, "no reading", 22, TOMATO, bold=True)
            continue
        s.text(x + 112, y + 48, f"{shown:.{places}f}", 36,
               TOMATO if outside else INK, "e", bold=True)
        s.text(x + 118, y + 42, units, 15, INK)
        if target:
            form = "{:.0f}" if key == "air_temp" else "{:g}"
            s.text(x + 118, y + 60,
                   f"target {form.format(target[0])}–{form.format(target[1])}",
                   12, MUTED)
        _trace(s, x + 222, y + 26, x + w - 4, y + h - 10,
               [convert(v) for v in history.series(key)], target)


def _trace(s, x0, y0, x1, y1, values, target):
    if len(values) < 2:
        return
    spread = list(values) + list(target or ())
    low, high = min(spread), max(spread)
    pad = (high - low) * 0.12 or 1
    low, high = low - pad, high + pad

    def at(value):
        return y1 - (y1 - y0) * (value - low) / (high - low)

    if target:
        s.rect(x0, at(target[1]), x1, at(target[0]), fill=BAND)
    step = (x1 - x0) / (len(values) - 1)
    points = [(x0 + i * step, at(v)) for i, v in enumerate(values)]
    s.line(points, INK, 1.5)
    ex, ey = points[-1]
    s.oval(ex - 3, ey - 3, ex + 3, ey + 3, fill=INK)


# -- switches -----------------------------------------------------------------

def _switches(s, controller):
    areas = []
    y0, y1, w = 464, 588, 140
    for i, (key, name) in enumerate(DEVICES):
        x0 = 16 + i * (w + 8)
        x1 = x0 + w
        on = controller.on[key]
        held = key in controller.holds
        face, words = (FRAME, PAPER) if on else (PAPER, INK)
        quiet = mix(words, face, 0.3)

        s.polygon(_rounded(x0, y0, x1, y1, 7), fill=face, outline=FRAME, width=1.5)
        s.text(x0 + 13, y0 + 21, name, 15, quiet)
        s.text(x0 + 13, y0 + 59, "On" if on else "Off", 36, words, bold=True)
        if held:
            s.rect(x0 + 4, y1 - 32, x1 - 4, y1 - 4, fill=SUN)
            s.text(x0 + 13, y1 - 18, controller.reason[key], 13, INK, bold=True)
        else:
            s.text(x0 + 13, y1 - 18, controller.reason[key], 12, quiet)
        areas.append((x0, y0, x1, y1, ("tap", key)))

    x0, x1 = 904, 1008
    minutes = controller.hold_minutes
    length = f"{minutes} min" if minutes < 60 else f"{minutes / 60:g} h"
    s.polygon(_rounded(x0, y0, x1, y1, 7), fill=GLASS, outline=FRAME, width=1.5)
    s.text(x0 + 12, y0 + 21, "A tap holds for", 13, MUTED)
    s.text(x0 + 12, y0 + 59, length, 26, INK, bold=True)
    s.text(x0 + 12, y1 - 18, "Tap to change", 12, MUTED)
    areas.append((x0, y0, x1, y1, ("hold",)))
    return areas


# -- shapes -------------------------------------------------------------------

def _arc(cx, cy, r, start, end, steps=12):
    """Points along a circle, angles in degrees clockwise from east."""
    out = []
    for i in range(steps + 1):
        a = math.radians(start + (end - start) * i / steps)
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def _rounded(x0, y0, x1, y1, r):
    return (_arc(x1 - r, y0 + r, r, -90, 0, 4) + _arc(x1 - r, y1 - r, r, 0, 90, 4)
            + _arc(x0 + r, y1 - r, r, 90, 180, 4) + _arc(x0 + r, y0 + r, r, 180, 270, 4))
