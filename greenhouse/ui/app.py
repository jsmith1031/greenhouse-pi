"""The window: reads sensors in the background, redraws once a second."""

import threading
import time
import tkinter
from datetime import datetime, timedelta

from ..automation import Controller
from ..readings import History
from . import dashboard
from .surface import TkSurface


class App:
    def __init__(self, cfg, sensors, relays, fullscreen=True, prefill=False):
        self.cfg = cfg
        self.sensors = sensors
        self.relays = relays
        self.controller = Controller(cfg, relays)
        self.history = History()
        self.areas = []

        self.root = tkinter.Tk()
        self.root.title("Greenhouse")
        if fullscreen:
            self.root.attributes("-fullscreen", True)
            self.root.config(cursor="none")
            width, height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        else:
            width, height = dashboard.WIDTH, dashboard.HEIGHT
            self.root.geometry(f"{width}x{height}")
        # Screens that are not 1024x600 get the same picture, scaled to fit.
        self.scale = min(width / dashboard.WIDTH, height / dashboard.HEIGHT)
        canvas = tkinter.Canvas(self.root, width=width, height=height,
                                highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Button-1>", self.on_tap)
        self.root.bind("<Escape>", lambda event: self.root.destroy())
        self.surface = TkSurface(canvas, self.scale)

        now = datetime.now()
        if prefill:
            for minutes in range(359, 0, -1):
                self.history.add(sensors.read(now - timedelta(minutes=minutes)))
        self.snap = sensors.read()
        threading.Thread(target=self.read_forever, daemon=True).start()

    def read_forever(self):
        # Some sensors take most of a second to answer, so keep them off the
        # thread that draws.
        while True:
            time.sleep(self.cfg.read_seconds)
            self.snap = self.sensors.read()

    def tick(self):
        now = datetime.now()
        self.history.add(self.snap)
        self.controller.step(self.snap, now)
        self.redraw(now)
        self.root.after(1000, self.tick)

    def redraw(self, now):
        self.areas = dashboard.draw(self.surface, self.cfg, self.snap,
                                    self.history, self.controller, now)

    def on_tap(self, event):
        x, y = event.x / self.scale, event.y / self.scale
        for x0, y0, x1, y1, action in self.areas:
            if x0 <= x <= x1 and y0 <= y <= y1:
                now = datetime.now()
                if action[0] == "tap":
                    self.controller.tap(action[1], now)
                else:
                    self.controller.next_hold_length()
                self.controller.step(self.snap, now)
                self.redraw(now)
                return

    def run(self):
        self.tick()
        try:
            self.root.mainloop()
        finally:
            for key in self.controller.on:
                self.relays.set(key, False)
