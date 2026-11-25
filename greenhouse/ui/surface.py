"""Two things the dashboard can be drawn on: a Tk canvas, or an SVG file.

The dashboard only ever calls the handful of methods below, so the picture in
the README is the same drawing the touchscreen shows.
"""

from xml.sax.saxutils import escape

from . import theme


class TkSurface:
    def __init__(self, canvas, scale=1.0):
        from tkinter import font

        self.canvas = canvas
        self.scale = scale
        installed = set(font.families(canvas))
        self.sans = _first(theme.SANS, installed, "TkDefaultFont")
        self.serif = _first(theme.SERIF, installed, "TkDefaultFont")

    def _p(self, values):
        return [v * self.scale for v in values]

    def clear(self, color):
        self.canvas.delete("all")
        self.canvas.configure(bg=color)

    def rect(self, x0, y0, x1, y1, fill="", outline="", width=1):
        self.canvas.create_rectangle(*self._p((x0, y0, x1, y1)), fill=fill,
                                     outline=outline, width=width * self.scale)

    def oval(self, x0, y0, x1, y1, fill="", outline="", width=1):
        self.canvas.create_oval(*self._p((x0, y0, x1, y1)), fill=fill,
                                outline=outline, width=width * self.scale)

    def polygon(self, points, fill="", outline="", width=1):
        flat = [v for point in points for v in point]
        self.canvas.create_polygon(*self._p(flat), fill=fill, outline=outline,
                                   width=width * self.scale)

    def line(self, points, color, width=1, dash=None):
        flat = [v for point in points for v in point]
        self.canvas.create_line(*self._p(flat), fill=color, dash=dash,
                                width=width * self.scale, capstyle="round",
                                joinstyle="round")

    def text(self, x, y, string, size, color, anchor="w", bold=False,
             italic=False, serif=False):
        style = " ".join(filter(None, ("bold" if bold else "",
                                       "italic" if italic else ""))) or "normal"
        family = self.serif if serif else self.sans
        self.canvas.create_text(
            x * self.scale, y * self.scale, text=string, fill=color, anchor=anchor,
            font=(family, -max(1, round(size * self.scale)), style))


class SvgSurface:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.parts = []

    def clear(self, color):
        self.parts = [f'<rect width="{self.width}" height="{self.height}" fill="{color}"/>']

    def _paint(self, fill, outline, width):
        stroke = f' stroke="{outline}" stroke-width="{width}"' if outline else ""
        return f'fill="{fill or "none"}"{stroke}'

    def rect(self, x0, y0, x1, y1, fill="", outline="", width=1):
        self.parts.append(
            f'<rect x="{_n(x0)}" y="{_n(y0)}" width="{_n(x1 - x0)}" '
            f'height="{_n(y1 - y0)}" {self._paint(fill, outline, width)}/>')

    def oval(self, x0, y0, x1, y1, fill="", outline="", width=1):
        self.parts.append(
            f'<ellipse cx="{_n((x0 + x1) / 2)}" cy="{_n((y0 + y1) / 2)}" '
            f'rx="{_n((x1 - x0) / 2)}" ry="{_n((y1 - y0) / 2)}" '
            f'{self._paint(fill, outline, width)}/>')

    def polygon(self, points, fill="", outline="", width=1):
        self.parts.append(f'<polygon points="{_points(points)}" '
                          f'{self._paint(fill, outline, width)}/>')

    def line(self, points, color, width=1, dash=None):
        dashes = f' stroke-dasharray="{" ".join(map(str, dash))}"' if dash else ""
        self.parts.append(
            f'<polyline points="{_points(points)}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" '
            f'stroke-linejoin="round"{dashes}/>')

    def text(self, x, y, string, size, color, anchor="w", bold=False,
             italic=False, serif=False):
        side = "" if anchor == "center" else anchor
        align = "end" if "e" in side else "start" if "w" in side else "middle"
        # Tk places text by its box; SVG by its baseline.
        drop = 0.78 if "n" in side else -0.22 if "s" in side else 0.34
        family = ",".join(f"'{name}'" for name in (theme.SERIF if serif else theme.SANS))
        family += ",Georgia,serif" if serif else ",'Arial Narrow',sans-serif"
        style = (' font-weight="700"' if bold else "") + \
                (' font-style="italic"' if italic else "")
        self.parts.append(
            f'<text x="{_n(x)}" y="{_n(y + drop * size)}" font-family="{family}" '
            f'font-size="{size}"{style} fill="{color}" text-anchor="{align}">'
            f'{escape(string)}</text>')

    def to_string(self):
        body = "\n".join(self.parts)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'viewBox="0 0 {self.width} {self.height}" '
                f'width="{self.width}" height="{self.height}">\n{body}\n</svg>\n')


def _first(wanted, installed, fallback):
    return next((name for name in wanted if name in installed), fallback)


def _n(value):
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _points(points):
    return " ".join(f"{_n(x)},{_n(y)}" for x, y in points)
