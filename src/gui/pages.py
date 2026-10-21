"""The app's pages: Overview, Route finder, Weak points and Data check.
(The two step-by-step pages are in steppers.py.)

Every page follows the same pattern:
    render()      draw everything for the current data set (called when the page is shown
                  and something changed: new data set or light/dark switch)
    on_click(id)  what happens when a stop on the map is clicked (optional)
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading

import customtkinter as ctk
import pandas as pd

from . import model, theme
from .mapview import MapView
from .theme import C, P


def open_path(path) -> None:
    """Open a file or folder with the computer's default program."""
    path = str(path)
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606 (Windows only)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


class Page(ctk.CTkFrame):
    key = ""
    title = ""
    subtitle = ""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.dirty = True

    @property
    def ds(self) -> model.Dataset:
        return self.app.ds

    def on_dataset(self):
        self.dirty = True

    def on_theme(self):
        self.dirty = True

    def on_show(self):
        if self.dirty and self.ds is not None:
            self.dirty = False
            self.render()

    def on_hide(self):
        pass

    def on_key(self, key):
        pass

    def render(self):
        pass


def _clear(frame):
    for w in frame.winfo_children():
        w.destroy()


def _branch_points(a, b):
    """Stops on both paths where the two paths split or join again."""
    def nb(path):
        return {x: (path[i - 1] if i else None, path[i + 1] if i + 1 < len(path) else None)
                for i, x in enumerate(path)}
    na, nbb = nb(a), nb(b)
    return [x for x in a[1:-1] if x in nbb and na[x] != nbb[x]]


def _names(G, stops, limit=None):
    names = [G.name(s) for s in stops]
    if limit and len(names) > limit:
        return " → ".join(names[:limit // 2]) + " → … → " + " → ".join(names[-(limit // 2):])
    return " → ".join(names)


# =====================================================================
# Overview
# =====================================================================

class OverviewPage(Page):
    key = "overview"
    title = "Overview"
    subtitle = "Stops are vertices; two stops that follow each other on a route are joined by an edge."

    def __init__(self, master, app):
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        kpis = ctk.CTkFrame(self, fg_color="transparent")
        kpis.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        self.kpi = {}
        for i, (key, title) in enumerate([("V", "Stops |V|"), ("E", "Links |E|"), ("comp", "Components"),
                                          ("cut", "Cut vertices"), ("mst", "Spanning tree")]):
            kpis.grid_columnconfigure(i, weight=1, uniform="kpi")
            card = theme.KpiCard(kpis, title)
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0 if i == 4 else 6))
            self.kpi[key] = card

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2, minsize=340)
        self.map = MapView(body, hover_text=lambda s: self.app.stop_tip(s))
        self.map.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        side = ctk.CTkFrame(body, fg_color="transparent")
        side.grid(row=0, column=1, sticky="nsew")
        side.grid_columnconfigure(0, weight=1)
        side.grid_rowconfigure(0, weight=1)

        c1 = theme.card(side)
        c1.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        c1.grid_columnconfigure(0, weight=1)
        c1.grid_rowconfigure(1, weight=1)
        theme.overline(c1, "Busiest stops").grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))
        self.table = theme.Table(c1, [("name", "Stop", 170, "w"), ("deg", "Links", 60, "center"),
                                      ("routes", "Routes", 70, "center")], height=7)
        self.table.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        c2 = theme.card(side)
        c2.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        c2.grid_columnconfigure(1, weight=1)
        theme.overline(c2, "How far apart are stops?").grid(row=0, column=0, columnspan=2, sticky="w",
                                                             padx=16, pady=(14, 4))
        self.facts = {}
        for i, (key, text) in enumerate([("avg", "Average trip"), ("diam", "Longest trip"),
                                         ("km", "Longest distance"), ("centre", "Most central")]):
            theme.label(c2, text, size=12, color="ink2").grid(row=i + 1, column=0, sticky="nw", padx=(16, 10), pady=2)
            v = theme.label(c2, "", size=12, wraplength=250)
            v.grid(row=i + 1, column=1, sticky="w", padx=(0, 16), pady=2)
            self.facts[key] = v
        ctk.CTkFrame(c2, fg_color="transparent", width=1, height=10).grid(row=9, column=0)

        self.c3 = theme.card(side)
        self.c3.grid(row=2, column=0, sticky="ew")
        self.c3.grid_columnconfigure(1, weight=1)

    def render(self):
        ds, G, st = self.ds, self.ds.G, self.ds.stats
        self.kpi["V"].set(str(st["V"]), f"{st['routes']} routes")
        self.kpi["E"].set(str(st["E"]), f"density {st['density']:.3f}")
        self.kpi["comp"].set(str(st["components"]), f"largest has {st['largest']} stops")
        self.kpi["cut"].set(str(st["cut_vertices"]), f"{st['bridges']} bridges")
        self.kpi["mst"].set(f"{st['mst_km']:.1f} km", f"of {st['total_km']:.1f} km of links")

        p = P()
        m = self.map
        m.start(G)
        m.edges(G.edges())
        small = st["V"] <= 20
        items = []
        for i, comp in enumerate(ds.comps):
            col = theme.series(i) if i < 8 else p["muted"]
            ids = sorted(comp)
            sizes = [10 + 9 * len(G.adj[s]) for s in ids]
            xs = [m.pos[s][0] for s in ids]
            ys = [m.pos[s][1] for s in ids]
            m.ax.scatter(xs, ys, s=sizes, c=col, zorder=3, edgecolors=p["panel"], linewidths=0.8)
            if i < 4:
                items.append(("dot", col, f"component {i + 1} · {len(comp)} stop{'s' if len(comp) != 1 else ''}"))
        hubs = list(G.adj) if small else [s for s in G.adj if len(G.adj[s]) >= 4 or not G.adj[s]]
        m.labels(sorted(hubs, key=lambda s: -len(G.adj[s])))
        m.legend.set(items + [("line", p["edge"], "link")])
        m.show()

        self.table.set_rows([(G.name(s), d, r) for s, d, r in st["busiest"]])
        a, b = st["diameter_ends"]
        self.facts["avg"].configure(text=f"{st['avg_hops']:.1f} hops · {st['avg_km']:.2f} km")
        self.facts["diam"].configure(text=f"{st['diameter_hops']} hops · {G.name(a)} ↔ {G.name(b)}")
        self.facts["km"].configure(text=f"{st['diameter_km']:.2f} km")
        centre = [G.name(s) for s in st["centre"]]
        self.facts["centre"].configure(text=", ".join(centre[:4]) + (" …" if len(centre) > 4 else ""))

        _clear(self.c3)
        theme.overline(self.c3, "Bus changes needed (all stop pairs)").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(14, 6))
        total = sum(st["changes"].values()) or 1
        for i, (k, n) in enumerate(sorted(st["changes"].items())):
            share = n / total
            theme.label(self.c3, f"{k} change{'s' if k != 1 else ''}", size=12, color="ink2", width=80).grid(
                row=i + 1, column=0, sticky="w", padx=(16, 8), pady=3)
            bar = ctk.CTkProgressBar(self.c3, height=10, corner_radius=5, fg_color=C("panel_alt"),
                                     progress_color=C("accent"))
            bar.set(share)
            bar.grid(row=i + 1, column=1, sticky="ew", pady=3)
            theme.label(self.c3, f"{100 * share:.1f}%", size=12, width=56, anchor="e").grid(
                row=i + 1, column=2, sticky="e", padx=(8, 16), pady=3)
        ctk.CTkFrame(self.c3, fg_color="transparent", width=1, height=10).grid(row=20, column=0)


# =====================================================================
# Route finder
# =====================================================================

class RouteFinderPage(Page):
    key = "route"
    title = "Route finder"
    subtitle = ("Fewest stops (BFS), shortest distance (Dijkstra) and fewest bus changes "
                "(BFS on the route graph) between two stops.")

    def __init__(self, master, app):
        super().__init__(master, app)
        self.s = self.t = None
        self.result = None
        self.mode = "Compare paths"
        self.picking_to = False
        self._all_names: list[str] = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        bar = theme.card(self)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        bar.grid_columnconfigure(6, weight=1)
        theme.label(bar, "From", size=12, color="ink2").grid(row=0, column=0, padx=(16, 8), pady=14)
        self.from_box = theme.combo(bar, [], command=lambda _v: self._picked())
        self.from_box.grid(row=0, column=1, pady=14)
        theme.button(bar, "↔", self.swap, kind="ghost", width=40).grid(row=0, column=2, padx=8)
        theme.label(bar, "To", size=12, color="ink2").grid(row=0, column=3, padx=(0, 8))
        self.to_box = theme.combo(bar, [], command=lambda _v: self._picked())
        self.to_box.grid(row=0, column=4)
        theme.button(bar, "Find route", self.find, width=110).grid(row=0, column=5, padx=12)
        self.hint = theme.label(bar, "or click two stops on the map", size=12, color="muted")
        self.hint.grid(row=0, column=6, sticky="w")
        self.mode_btn = theme.segmented(bar, ["Compare paths", "Bus trip"], self._set_mode)
        self.mode_btn.set(self.mode)
        self.mode_btn.grid(row=0, column=7, padx=16)
        for box in (self.from_box, self.to_box):
            entry = getattr(box, "_entry", None)
            if entry is not None:
                entry.bind("<KeyRelease>", lambda e, b=box: self._filter(e, b), add="+")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2, minsize=360)
        self.map = MapView(body, hover_text=lambda s: self.app.stop_tip(s), on_click=self.on_click)
        self.map.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.results = ctk.CTkScrollableFrame(body, fg_color="transparent",
                                              scrollbar_button_color=C("border"),
                                              scrollbar_button_hover_color=C("muted"))
        self.results.grid(row=0, column=1, sticky="nsew")
        self.results.grid_columnconfigure(0, weight=1)

    # ---- data set changes
    def on_dataset(self):
        super().on_dataset()
        self.s = self.t = self.result = None

    def render(self):
        G = self.ds.G
        names = self.ds.stop_names()
        self._all_names = names
        for box in (self.from_box, self.to_box):
            box.configure(values=names)
        if self.s is None:
            s, t = (self.ds.pairs[0] if self.ds.pairs else (G.stops.index[0], G.stops.index[-1]))
            self.s, self.t = s, t
            self.result = model.find_route(self.ds, s, t)
        self.from_box.set(G.name(self.s))
        self.to_box.set(G.name(self.t) if self.t else "")
        self._paint()
        self._show_results()

    # ---- input
    def _filter(self, event, box):
        if event.keysym in ("Return", "KP_Enter"):
            self.find()
            return
        text = box.get().strip().casefold()
        vals = [n for n in self._all_names if text in n.casefold()] if text else self._all_names
        box.configure(values=vals or self._all_names)

    def _picked(self):
        for box in (self.from_box, self.to_box):
            box.configure(values=self._all_names)
        if self.from_box.get() and self.to_box.get():
            self.find()

    def swap(self):
        a, b = self.from_box.get(), self.to_box.get()
        self.from_box.set(b)
        self.to_box.set(a)
        self.find()

    def _set_mode(self, mode):
        self.mode = mode
        self._paint()

    def on_click(self, sid):
        G = self.ds.G
        if not self.picking_to:
            self.s, self.t, self.result = sid, None, None
            self.picking_to = True
            self.from_box.set(G.name(sid))
            self.to_box.set("")
            self.hint.configure(text="now click the destination stop")
            self._paint()
            self._show_results()
        else:
            self.picking_to = False
            self.to_box.set(G.name(sid))
            self.find()

    def find(self):
        G = self.ds.G
        self.picking_to = False
        self.hint.configure(text="or click two stops on the map")
        try:
            s = G.stop_id(self.from_box.get())
            t = G.stop_id(self.to_box.get())
        except KeyError as e:
            self._message("Unknown stop", str(e).strip("'\"") + ". Pick a name from the list.")
            return
        if s == t:
            self._message("Same stop", "Choose two different stops.")
            return
        self.s, self.t = s, t
        self.result = model.find_route(self.ds, s, t)
        self._paint()
        self._show_results()

    # ---- drawing
    def _paint(self):
        G, m, p = self.ds.G, self.map, P()
        m.start(G)
        m.base(node_size=10)
        r = self.result
        if r is None or not r.get("reachable"):
            ends = [x for x in (self.s, self.t) if x]
            m.nodes(ends, color=p["ink"], size=80, z=8, lw=1.5)
            m.labels(ends, size=9.5, weight="bold", force=True)
            m.legend.set([("dot", p["ink"], "chosen stop")])
            m.show()
            return
        s, t = r["s"], r["t"]
        if self.mode == "Compare paths":
            m.path(r["hop_path"], p["orange"], lw=3.6, ls=(0, (4, 2)), z=5)
            m.path(r["dist_path"], p["blue"], lw=2.6, z=6)
            on = set(r["hop_path"]) | set(r["dist_path"])
            m.nodes(on, color=p["ink"], size=16, z=7)
            m.nodes([s, t], color=p["ink"], size=80, z=8, lw=1.5)
            m.labels([s, t], size=9.5, weight="bold", force=True)
            m.labels(_branch_points(r["hop_path"], r["dist_path"]), size=8.5, color=p["ink2"])
            m.legend.set([("dash", p["orange"], f"fewest stops ({len(r['hop_path']) - 1} hops)"),
                          ("line", p["blue"], f"shortest distance ({r['dist_km']:.2f} km)"),
                          ("dot", p["ink"], "start / end")])
        else:
            items = []
            for i, leg in enumerate(r["legs"]):
                col = theme.series(i)
                m.path(leg["stops"], col, lw=3.8, z=5 + i)
                m.nodes(leg["stops"], color=col, size=14, z=7)
                items.append(("line", col, leg["route"]))
            transfers = [leg["alight"] for leg in r["legs"][:-1]]
            m.nodes([s, t], color=p["ink"], size=80, z=9, lw=1.5)
            m.nodes(transfers, color=p["panel"], size=95, z=9, edge=p["ink"], lw=2.2)
            m.labels([s, t] + transfers, size=9.5, weight="bold", force=True)
            m.legend.set(items + [("ring", p["ink"], "change bus"), ("dot", p["ink"], "start / end")])
        m.show()

    # ---- result cards
    def _card(self, row, glyph, color, title, big, small_text, body=None):
        c = theme.card(self.results)
        c.grid(row=row, column=0, sticky="ew", pady=(0, 12), padx=(0, 4))
        c.grid_columnconfigure(1, weight=1)
        theme.glyph(c, glyph, color).grid(row=0, column=0, sticky="w", padx=(14, 6), pady=(14, 0))
        theme.label(c, title, size=12, weight="bold", color="ink2").grid(row=0, column=1, sticky="w", pady=(14, 0))
        line = ctk.CTkFrame(c, fg_color="transparent")
        line.grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(2, 0))
        theme.label(line, big, size=22, weight="bold").pack(side="left")
        theme.label(line, small_text, size=13, color="ink2").pack(side="left", padx=(10, 0), pady=(6, 0))
        if body:
            theme.label(c, body, size=12, color="ink2", wraplength=300).grid(
                row=2, column=0, columnspan=2, sticky="w", padx=16, pady=(6, 0))
        ctk.CTkFrame(c, fg_color="transparent", width=1, height=12).grid(row=9, column=0)
        return c

    def _message(self, title, text):
        _clear(self.results)
        c = theme.card(self.results)
        c.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        theme.label(c, title, size=14, weight="bold").pack(anchor="w", padx=16, pady=(14, 2))
        theme.label(c, text, size=12, color="ink2", wraplength=300).pack(anchor="w", padx=16, pady=(0, 14))

    def _show_results(self):
        G, r, p = self.ds.G, self.result, P()
        if r is None:
            self._message("Pick the destination", f"From: {G.name(self.s)}. Now click the stop you want to go to, "
                                                  "or choose it in the To box.")
            return
        if not r["reachable"]:
            self._message("No path",
                          f"{G.name(r['s'])} and {G.name(r['t'])} are in different connected components "
                          "of this data set, so no sequence of links joins them. That describes the data, "
                          "not necessarily the city — a route may simply be missing.")
            return
        _clear(self.results)
        hp, dp = r["hop_path"], r["dist_path"]
        self._card(0, "line", p["blue"], "SHORTEST DISTANCE  ·  Dijkstra", f"{r['dist_km']:.2f} km",
                   f"{len(dp) - 1} hops", _names(G, dp, 16))
        same = "Same path as the shortest distance." if r["same"] else _names(G, hp, 16)
        extra = r["hop_km"] - r["dist_km"]
        self._card(1, "dash", p["orange"], "FEWEST STOPS  ·  BFS", f"{len(hp) - 1} hops",
                   f"{r['hop_km']:.2f} km" + (f"  (+{extra:.2f} km)" if extra > 1e-9 else ""), same)
        n = r["changes"]
        c = self._card(2, "ring", p["ink"], "FEWEST BUS CHANGES  ·  route graph",
                       f"{n} change{'s' if n != 1 else ''}", f"{len(r['legs'])} bus{'es' if len(r['legs']) != 1 else ''}")
        legs = ctk.CTkFrame(c, fg_color="transparent")
        legs.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 0))
        for i, leg in enumerate(r["legs"]):
            name = str(G.routes.loc[leg["route"], "route_name"]) if leg["route"] in G.routes.index else ""
            chip = ctk.CTkLabel(legs, text=leg["route"], fg_color=theme.series(i), text_color="#ffffff",
                                corner_radius=6, font=theme.font(12, "bold"), width=46, height=24)
            chip.grid(row=2 * i, column=0, sticky="nw", pady=(4, 0))
            theme.label(legs, f"{G.name(leg['board'])} → {G.name(leg['alight'])}", size=13).grid(
                row=2 * i, column=1, sticky="w", padx=10, pady=(4, 0))
            theme.label(legs, f"{len(leg['stops']) - 1} hops · {name}", size=11, color="muted",
                        wraplength=270).grid(row=2 * i + 1, column=1, sticky="w", padx=10)
        tip = theme.label(self.results, "Switch the map to “Bus trip” (top right) to see each bus.", size=11,
                          color="muted", wraplength=300)
        tip.grid(row=3, column=0, sticky="w", padx=4)


# =====================================================================
# Weak points
# =====================================================================

class WeakPointsPage(Page):
    key = "weak"
    title = "Weak points"
    subtitle = ("Cut vertices and bridges: stops and links whose loss disconnects part of the network. "
                "Click any stop to simulate closing it.")

    def __init__(self, master, app):
        super().__init__(master, app)
        self.sel = None
        self.grid_columnconfigure(0, minsize=360)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        c1 = theme.card(left)
        c1.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        c1.grid_columnconfigure(0, weight=1)
        c1.grid_rowconfigure(2, weight=1)
        top = ctk.CTkFrame(c1, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))
        top.grid_columnconfigure(0, weight=1)
        self.count = theme.label(top, "", size=16, weight="bold")
        self.count.grid(row=0, column=0, sticky="w")
        theme.button(top, "Show all", self.clear, kind="ghost", width=84).grid(row=0, column=1, sticky="e")
        theme.label(c1, "Cut vertices, by how many stops they would cut off", size=12, color="ink2").grid(
            row=1, column=0, sticky="w", padx=16, pady=(2, 8))
        self.table = theme.Table(c1, [("name", "Stop", 160, "w"), ("off", "Cuts off", 84, "center"),
                                      ("pieces", "Pieces", 64, "center")], height=9,
                                 on_select=self._row)
        self.table.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        self.info_card = theme.card(left)
        self.info_card.grid(row=1, column=0, sticky="ew")
        self.info_card.grid_columnconfigure(0, weight=1)
        self.info_title = theme.label(self.info_card, "", size=14, weight="bold")
        self.info_title.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
        self.info_text = theme.label(self.info_card, "", size=12, color="ink2", wraplength=320)
        self.info_text.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 14))

        self.map = MapView(self, hover_text=lambda s: self.app.stop_tip(s), on_click=self.on_click)
        self.map.grid(row=0, column=1, sticky="nsew")

    def on_dataset(self):
        super().on_dataset()
        self.sel = None

    def render(self):
        ds, G = self.ds, self.ds.G
        self.count.configure(text=f"{len(ds.cuts)} cut vertices · {len(ds.bridges)} bridges")
        self.table.set_rows([(G.name(v), len(ds.cut_info[v]["cut_off"]), len(ds.cut_info[v]["pieces"]))
                             for v in ds.cuts])
        self._refresh()

    def _row(self, i):
        self.sel = self.ds.cuts[i]
        self._refresh(select_row=False, focus=True)

    def on_click(self, sid):
        self.sel = sid
        self._refresh()

    def clear(self):
        self.sel = None
        self.table.clear_selection()
        self.map._view = None
        self._refresh()

    def _refresh(self, select_row=True, focus=False):
        ds, G, m, p = self.ds, self.ds.G, self.map, P()
        m.start(G)
        if self.sel is None:
            m.base(node_size=12)
            m.edges(ds.bridges, color=p["red"], lw=2.8, z=2)
            m.nodes(ds.cuts, color=p["red"], size=60, z=4)
            m.labels(ds.cuts)
            m.legend.set([("dot", p["red"], f"cut vertex ({len(ds.cuts)})"),
                          ("line", p["red"], f"bridge ({len(ds.bridges)})")])
            self.info_title.configure(text="What is a cut vertex?")
            self.info_text.configure(text=(
                "A stop whose removal splits its part of the network into two or more pieces. "
                "A bridge is a link with the same effect. The program finds them by deleting each "
                "stop (or link) in turn and counting the components again.\n\n"
                "Select a stop in the list, or click any stop on the map, to see what closing it would do."))
            m.show()
            return

        v = self.sel
        if select_row and v in ds.cuts:
            self.table.select_row(ds.cuts.index(v))
        elif v not in ds.cuts:
            self.table.clear_selection()
        eff = ds.cut_info.get(v) or model.removal_effect(G.adj, v)
        off = eff["cut_off"]
        lost = [(v, n) for n in G.adj[v]]
        inside = [(a, b, w) for a, b, w in G.edges() if a in off and b in off]
        others = [(a, b, w) for a, b, w in G.edges() if v not in (a, b) and not (a in off and b in off)]
        m.edges(others)
        m.edges(inside, color=p["red"], lw=2.2, z=2)
        m.edges(lost, color=p["muted"], lw=1.6, ls=(0, (3, 2)), z=2)
        m.nodes([s for s in G.adj if s not in off and s != v], size=12)
        m.nodes(off, color=p["red"], size=34, z=4)
        m.nodes([v], color=p["red"], size=170, z=9, marker="X", lw=1.2)
        m.labels([v], size=10, weight="bold", force=True)
        m.labels(sorted(off))
        m.legend.set([("cross", p["red"], "closed stop"), ("dot", p["red"], f"cut off ({len(off)})"),
                      ("dash", p["muted"], "links lost")])
        if focus and off:
            m.focus(off | {v} | set(G.adj[v]))
        m.show()

        name = G.name(v)
        self.info_title.configure(text=f"Closing {name}")
        if not G.adj[v]:
            text = "This stop has no links in the data, so closing it changes nothing for the others."
        elif off:
            names = ", ".join(sorted(G.name(s) for s in off))
            text = (f"Its part of the network splits into {len(eff['pieces'])} pieces. "
                    f"{len(off)} stop{'s' if len(off) != 1 else ''} can no longer reach the rest: {names}.\n\n"
                    f"{name} is a cut vertex: every path from these stops to the rest passes through it.")
        else:
            self.info_text.configure(text="Working out the detours…")
            self.update_idletasks()
            before, after = model.detour_cost(G.adj, v, eff["main"])
            pct = 100 * (after - before) / before if before else 0.0
            text = (f"Nothing is disconnected: every other stop can still reach every other stop, "
                    f"because there is another way around {name}.\n\n"
                    f"The detours have a cost: the average shortest trip between the remaining stops "
                    f"goes from {before:.2f} km to {after:.2f} km (+{pct:.1f}%).")
        self.info_text.configure(text=text)


# =====================================================================
# Data check
# =====================================================================

class DataCheckPage(Page):
    key = "data"
    title = "Data check"
    subtitle = "Each rule is a proposition about the data; the program checks it and lists counterexamples."

    def __init__(self, master, app):
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._q: queue.Queue = queue.Queue()

        bar = theme.card(self)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        bar.grid_columnconfigure(4, weight=1)
        theme.button(bar, "Reload data", self.app.reload, kind="ghost", width=120).grid(
            row=0, column=0, padx=(16, 6), pady=14)
        self.run_btn = theme.button(bar, "Run full analysis", self.run_analysis, width=150)
        self.run_btn.grid(row=0, column=1, padx=6)
        theme.button(bar, "Open results folder", self.open_results, kind="ghost", width=160).grid(
            row=0, column=2, padx=6)
        theme.button(bar, "Open summary", self.open_summary, kind="ghost", width=130).grid(row=0, column=3, padx=6)
        self.status = theme.label(bar, "", size=12, color="ink2")
        self.status.grid(row=0, column=4, sticky="w", padx=12)
        self.progress = ctk.CTkProgressBar(bar, mode="indeterminate", width=140, height=8,
                                           fg_color=C("panel_alt"), progress_color=C("accent"))

        self.error = theme.card(self, border_color=C("bad"), border_width=2)
        self.error.grid_columnconfigure(0, weight=1)
        self.error_title = theme.label(self.error, "This data set has a problem", size=15, weight="bold", color="bad")
        self.error_title.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
        self.error_text = theme.label(self.error, "", size=12, wraplength=900)
        self.error_text.grid(row=1, column=0, sticky="w", padx=16)
        self.error_hint = theme.label(self.error, "", size=12, color="ink2")
        self.error_hint.grid(row=2, column=0, sticky="w", padx=16, pady=(6, 14))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        c1 = theme.card(body)
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        c1.grid_columnconfigure(0, weight=1)
        c1.grid_rowconfigure(1, weight=1)
        theme.overline(c1, "Validation rules").grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        self.rules = ctk.CTkScrollableFrame(c1, fg_color="transparent", scrollbar_button_color=C("border"),
                                            scrollbar_button_hover_color=C("muted"))
        self.rules.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 10))
        self.rules.grid_columnconfigure(1, weight=1)
        self._wrapped: list = []
        self._wrap = 380
        c1.bind("<Configure>", self._rewrap, add="+")

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=3)
        right.grid_rowconfigure(1, weight=2)
        c2 = theme.card(right)
        c2.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        c2.grid_columnconfigure(0, weight=1)
        c2.grid_rowconfigure(1, weight=1)
        theme.overline(c2, "Routes").grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))
        self.routes = theme.Table(c2, [("id", "ID", 56, "center"), ("name", "Name", 260, "w"),
                                       ("stops", "Stops", 56, "center"), ("conf", "Confidence", 96, "center")],
                                  height=6)
        self.routes.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        c3 = theme.card(right)
        c3.grid(row=1, column=0, sticky="nsew")
        c3.grid_columnconfigure(0, weight=1)
        c3.grid_rowconfigure(1, weight=1)
        theme.overline(c3, "Spellings fixed by cleaning").grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))
        self.log = ctk.CTkTextbox(c3, fg_color=C("panel_alt"), text_color=C("ink2"), corner_radius=8,
                                  font=ctk.CTkFont(family="Consolas" if sys.platform.startswith("win") else "Courier",
                                                   size=12), wrap="none")
        self.log.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def render(self):
        ds = self.ds
        self.status.configure(text="")
        if ds.error:
            self.error_text.configure(text=ds.error)
            self.error_hint.configure(text=f"Edit the files in data/{ds.name}/raw/ (never the processed/ files), "
                                           "save, then press Reload data.")
            self.error.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        else:
            self.error.grid_forget()
        self.run_btn.configure(state="normal" if ds.ok else "disabled")

        _clear(self.rules)
        self._wrapped = []
        p = P()
        if not ds.rules:
            theme.label(self.rules, "The rules could not be checked because the files could not be read.",
                        size=12, color="ink2", wraplength=420).grid(row=0, column=0, columnspan=2, sticky="w", padx=10)
        for i, r in enumerate(ds.rules):
            if r.holds:
                icon, col, status = "✓", p["good"], "holds"
            elif r.is_warning:
                icon, col, status = "!", p["warn"], "warning"
            else:
                icon, col, status = "✗", p["bad"], "fails"
            ctk.CTkLabel(self.rules, text=icon, width=24, height=24, corner_radius=12, fg_color=col,
                         text_color="#ffffff" if col != DARK_WARN else "#1a1a19",
                         font=theme.font(12, "bold")).grid(row=2 * i, column=0, sticky="n", padx=(10, 10), pady=(10, 0))
            a = theme.label(self.rules, f"{r.code}   {r.statement}", size=12, wraplength=self._wrap)
            a.grid(row=2 * i, column=1, sticky="w", pady=(10, 0))
            detail = status
            if r.counterexamples:
                shown = r.counterexamples[:5]
                detail += ":  " + "\n".join(shown) + (f"\n… and {len(r.counterexamples) - 5} more"
                                                     if len(r.counterexamples) > 5 else "")
            b = theme.label(self.rules, detail, size=11, color="muted", wraplength=self._wrap)
            b.grid(row=2 * i + 1, column=1, sticky="w")
            self._wrapped += [a, b]

        if ds.G is not None:
            G = ds.G
            rows = []
            for rid, row in G.routes.iterrows():
                rows.append((rid, row.get("route_name", ""), len(G.route_seq.get(rid, [])), row.get("confidence", "")))
            self.routes.set_rows(rows)
        else:
            self.routes.set_rows([])
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert("1.0", "\n".join(ds.notes) if ds.notes else "Nothing to fix: every name matched exactly.")
        self.log.configure(state="disabled")

    def _rewrap(self, event):
        wrap = max(200, int(event.width / self._scaling()) - 110)
        if abs(wrap - self._wrap) > 8:
            self._wrap = wrap
            for w in self._wrapped:
                if w.winfo_exists():
                    w.configure(wraplength=wrap)

    def _scaling(self):
        try:
            return ctk.ScalingTracker.get_widget_scaling(self)
        except Exception:
            return 1.0

    # ---- actions
    def run_analysis(self):
        ds = self.ds
        if not ds.ok:
            return
        self.run_btn.configure(state="disabled")
        self.status.configure(text="Running every analysis and saving figures…")
        self.progress.grid(row=0, column=5, padx=16)
        self.progress.start()
        out = model.ROOT / "results" / ds.name

        def work():
            try:
                from ..analysis import run_analysis
                f = ds.folder / "pairs.csv"
                pairs = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["from_stop", "to_stop"])
                run_analysis(ds.G, ds.data, ds.name, pairs, out, make_figures=True, echo=False)
                self._q.put(("ok", out))
            except Exception as e:  # show any error in the app instead of crashing
                self._q.put(("err", f"{type(e).__name__}: {e}"))

        threading.Thread(target=work, daemon=True).start()
        self.after(150, self._poll)

    def _poll(self):
        try:
            kind, payload = self._q.get_nowait()
        except queue.Empty:
            self.after(150, self._poll)
            return
        self.progress.stop()
        self.progress.grid_forget()
        self.run_btn.configure(state="normal")
        if kind == "ok":
            rel = payload.relative_to(model.ROOT)
            self.status.configure(text=f"Done. Summary, tables, figures and map saved in {rel}/")
        else:
            self.status.configure(text=f"Failed: {payload}")

    def open_results(self):
        out = model.ROOT / "results" / self.ds.name
        if not out.exists():
            self.status.configure(text="No results yet: press Run full analysis first.")
            return
        open_path(out)

    def open_summary(self):
        f = model.ROOT / "results" / self.ds.name / "summary.md"
        if not f.exists():
            self.status.configure(text="No summary yet: press Run full analysis first.")
            return
        open_path(f)


DARK_WARN = theme.DARK["warn"]
