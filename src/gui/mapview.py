"""An interactive map of the bus graph, drawn with Matplotlib inside the app.

    scroll        zoom in / out around the mouse
    drag          move the map
    hover a stop  show its name and details
    click a stop  calls on_click(stop_id) if the page gave one
    + / − / Fit   buttons in the top-right corner
"""
from __future__ import annotations

from math import cos, radians

import customtkinter as ctk
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure

from . import theme
from .theme import C, P

HIT_PX = 13   # how close (in pixels) the mouse must be to a stop to pick it


class MapView(ctk.CTkFrame):
    def __init__(self, master, hover_text=None, on_click=None):
        super().__init__(master, fg_color=C("panel"), corner_radius=12, border_width=1, border_color=C("border"))
        self.hover_text = hover_text
        self.on_click = on_click
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.fig = Figure(figsize=(6, 5), dpi=100)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.widget = self.canvas.get_tk_widget()
        self.widget.configure(highlightthickness=0, borderwidth=0, background=P()["panel"])
        self.widget.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 0))

        self.legend = theme.Legend(self)
        self.legend.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 10))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        for text, cmd in (("+", lambda: self.zoom(1 / 1.4)), ("−", lambda: self.zoom(1.4)),
                          ("Fit", self.reset_view)):
            ctk.CTkButton(bar, text=text, command=cmd, width=40, height=30, corner_radius=8,
                          fg_color=C("panel_alt"), hover_color=C("hover"), text_color=C("ink"),
                          border_width=1, border_color=C("border"),
                          font=theme.font(14 if text != "Fit" else 12, "bold")).pack(pady=2)
        bar.place(relx=1.0, x=-18, y=18, anchor="ne")

        self.G = None
        self.pos: dict = {}
        self._ids: list = []
        self._xy = None
        self._home = None
        self._view = None
        self._press = None
        self._hover_id = None
        self._tip = None
        self._k = 1.0
        self._label_reqs: list = []
        self._label_artists: list = []
        for ev, fn in (("scroll_event", self._mpl_scroll), ("button_press_event", self._mpl_press),
                       ("button_release_event", self._mpl_release), ("motion_notify_event", self._mpl_motion),
                       ("figure_leave_event", lambda e: self._show_tip(None)),
                       ("resize_event", self._mpl_resize)):
            self.canvas.mpl_connect(ev, fn)

    # -------------------------------------------------------------- drawing API

    def start(self, G):
        """Clear the map and get ready to draw graph G (keeps the zoom if G is the same graph)."""
        if G is not self.G:
            self.G = G
            self._ids = list(G.stops.index)
            self.pos = {s: (r["lon"], r["lat"]) for s, r in G.stops.iterrows()}
            self._xy = np.array([self.pos[s] for s in self._ids])
            x0, y0 = self._xy.min(axis=0)
            x1, y1 = self._xy.max(axis=0)
            px, py = (x1 - x0) * 0.06 + 1e-3, (y1 - y0) * 0.06 + 1e-3
            self._home = ((x0 - px, x1 + px), (y0 - py, y1 + py))
            self._view = None
        p = P()
        self.ax.clear()
        self.ax.set_axis_off()
        self.fig.patch.set_facecolor(p["panel"])
        self.ax.set_facecolor(p["panel"])
        self.widget.configure(background=p["panel"])
        self._k = cos(radians(float(self._xy[:, 1].mean())))   # 1° of longitude is shorter than 1° of latitude
        self._tip = self.ax.annotate(
            "", (0, 0), xytext=(12, 12), textcoords="offset points", fontsize=9, color=p["ink"],
            zorder=200, visible=False, va="bottom",
            bbox=dict(boxstyle="round,pad=0.5", fc=p["panel_alt"], ec=p["border"], lw=1))
        self._hover_id = None
        self._label_reqs = []
        self._label_artists = []

    def edges(self, pairs, color=None, lw=1.3, ls="solid", z=1, alpha=1.0):
        segs = [(self.pos[u], self.pos[v]) for u, v, *_ in pairs]
        if segs:
            self.ax.add_collection(LineCollection(segs, colors=color or P()["edge"], linewidths=lw,
                                                  linestyles=ls, zorder=z, alpha=alpha, capstyle="round"))

    def path(self, stops, color, lw=3.0, ls="solid", z=5, alpha=1.0):
        self.edges(list(zip(stops, stops[1:])), color=color, lw=lw, ls=ls, z=z, alpha=alpha)

    def nodes(self, ids, color=None, size=16, z=3, edge=None, lw=0.8, marker="o"):
        ids = list(ids)
        if not ids:
            return
        xy = np.array([self.pos[s] for s in ids])
        self.ax.scatter(xy[:, 0], xy[:, 1], s=size, c=color or P()["node"], zorder=z, marker=marker,
                        edgecolors=edge or P()["panel"], linewidths=lw)

    def labels(self, ids, size=8.5, weight="normal", color=None, texts=None, force=False):
        """Ask for stop names on the map. They are placed in show(): a label that would overlap
        one already placed is moved to another corner of its stop, or left out (unless force=True).
        Zooming in makes room, so more labels appear."""
        for i, s in enumerate(ids):
            text = texts[i] if texts else self.G.name(s)
            self._label_reqs.append((s, text, size, weight, color, force))

    def focus(self, ids, pad=0.45):
        """Zoom to the given stops (with some margin)."""
        xy = np.array([self.pos[s] for s in ids])
        (x0, y0), (x1, y1) = xy.min(axis=0), xy.max(axis=0)
        hx, hy = self._home[0][1] - self._home[0][0], self._home[1][1] - self._home[1][0]
        dx, dy = max(x1 - x0, hx * 0.18), max(y1 - y0, hy * 0.18)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self._view = ((cx - dx * (0.5 + pad), cx + dx * (0.5 + pad)), (cy - dy * (0.5 + pad), cy + dy * (0.5 + pad)))

    def _place_labels(self):
        for a in self._label_artists:
            a.remove()
        self._label_artists = []
        p = P()
        box = self.ax.bbox
        dpi = self.fig.dpi
        placed: list = []
        reqs = sorted(self._label_reqs, key=lambda r: not r[5])          # forced labels first
        for sid, text, size, weight, color, force in reqs:
            px, py = self.ax.transData.transform(self.pos[sid])
            if not (box.x0 <= px <= box.x1 and box.y0 <= py <= box.y1):
                continue
            fpx = size * dpi / 72
            lines = text.split("\n")
            w = max(len(t) for t in lines) * fpx * (0.64 if weight == "bold" else 0.58)
            h = fpx * 1.3 * len(lines)
            chosen = None
            for ox, oy, ha in ((7, 4, "left"), (7, -4 - h, "left"), (-7, 4, "right"), (-7, -4 - h, "right")):
                x0 = px + ox if ha == "left" else px + ox - w
                cand = (x0, py + oy, x0 + w, py + oy + h)
                if cand[0] < box.x0 or cand[2] > box.x1:
                    continue
                if not any(cand[0] < b[2] and b[0] < cand[2] and cand[1] < b[3] and b[1] < cand[3] for b in placed):
                    chosen = (ox, oy, ha, cand)
                    break
            if chosen is None:
                if not force:
                    continue
                chosen = (7, 4, "left", (px + 7, py + 4, px + 7 + w, py + 4 + h))
            ox, oy, ha, cand = chosen
            placed.append(cand)
            self._label_artists.append(self.ax.annotate(
                text, self.pos[sid], xytext=(ox, oy), textcoords="offset pixels", ha=ha, va="bottom",
                fontsize=size, fontweight=weight, color=color or p["ink"], zorder=60,
                path_effects=[pe.withStroke(linewidth=3.2, foreground=p["panel"])]))

    def base(self, alpha=1.0, node_size=14):
        """The whole network, quiet, as a background for highlights."""
        self.edges(self.G.edges(), alpha=alpha)
        self.nodes(self._ids, size=node_size)

    def show(self):
        """Apply the current view, widened so the map is not stretched, and redraw."""
        (x0, x1), (y0, y1) = self._view or self._home
        w, h = max(self.ax.bbox.width, 1), max(self.ax.bbox.height, 1)
        cx, cy, dx, dy = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        if dx * self._k / dy < w / h:
            dx = dy * (w / h) / self._k
        else:
            dy = dx * self._k * (h / w)
        self.ax.set_xlim(cx - dx / 2, cx + dx / 2)
        self.ax.set_ylim(cy - dy / 2, cy + dy / 2)
        self._place_labels()
        self.canvas.draw_idle()

    def _mpl_resize(self, _e):
        if self._home is not None:
            self.show()

    # -------------------------------------------------------------- zoom and pan

    def zoom(self, factor, cx=None, cy=None):
        if self._home is None:
            return
        (x0, x1), (y0, y1) = self.ax.get_xlim(), self.ax.get_ylim()
        cx = (x0 + x1) / 2 if cx is None else cx
        cy = (y0 + y1) / 2 if cy is None else cy
        hx = self._home[0][1] - self._home[0][0]
        if factor > 1 and (x1 - x0) * factor > 3 * hx:
            return                               # do not zoom out further than 3x the city
        self._view = ((cx - (cx - x0) * factor, cx + (x1 - cx) * factor),
                      (cy - (cy - y0) * factor, cy + (y1 - cy) * factor))
        self.show()

    def reset_view(self):
        self._view = None
        if self._home is not None:
            self.show()

    def _mpl_scroll(self, e):
        if e.xdata is None:
            return
        self.zoom(1 / 1.25 if e.button == "up" else 1.25, e.xdata, e.ydata)

    def _mpl_press(self, e):
        if e.button == 1 and e.inaxes is self.ax:
            self._press = (e.x, e.y, self.ax.get_xlim(), self.ax.get_ylim(), False)

    def _mpl_release(self, e):
        press, self._press = self._press, None
        self.widget.configure(cursor="")
        if press is None or e.button != 1:
            return
        if not press[4] and self.on_click:
            sid = self._nearest(e)
            if sid is not None:
                self.on_click(sid)

    def _mpl_motion(self, e):
        if self._press:
            x0, y0, xlim, ylim, moved = self._press
            dx, dy = e.x - x0, e.y - y0
            if not moved and abs(dx) + abs(dy) < 4:
                return
            self._press = (x0, y0, xlim, ylim, True)
            self.widget.configure(cursor="fleur")
            sx = (xlim[1] - xlim[0]) / max(self.ax.bbox.width, 1)
            sy = (ylim[1] - ylim[0]) / max(self.ax.bbox.height, 1)
            self._view = ((xlim[0] - dx * sx, xlim[1] - dx * sx), (ylim[0] - dy * sy, ylim[1] - dy * sy))
            self._show_tip(None, draw=False)
            self.show()
            return
        self._show_tip(self._nearest(e))

    def _nearest(self, e):
        if self._xy is None or e.inaxes is not self.ax:
            return None
        disp = self.ax.transData.transform(self._xy)
        d2 = (disp[:, 0] - e.x) ** 2 + (disp[:, 1] - e.y) ** 2
        i = int(np.argmin(d2))
        return self._ids[i] if d2[i] <= HIT_PX ** 2 else None

    def _show_tip(self, sid, draw=True):
        if sid == self._hover_id or self._tip is None:
            return
        self._hover_id = sid
        if sid is None:
            self._tip.set_visible(False)
            self.widget.configure(cursor="")
        else:
            text = self.hover_text(sid) if self.hover_text else self.G.name(sid)
            self._tip.xy = self.pos[sid]
            right = self.ax.transData.transform(self.pos[sid])[0] > self.ax.bbox.x0 + self.ax.bbox.width * 0.62
            top = self.ax.transData.transform(self.pos[sid])[1] > self.ax.bbox.y0 + self.ax.bbox.height * 0.75
            self._tip.set_text(text)
            self._tip.set_position((-12 if right else 12, -12 if top else 12))
            self._tip.set_ha("right" if right else "left")
            self._tip.set_va("top" if top else "bottom")
            self._tip.set_visible(True)
            if self.on_click:
                self.widget.configure(cursor="hand2")
        if draw:
            self.canvas.draw_idle()
