"""Step-by-step pages: Kruskal's algorithm (spanning tree) and Dijkstra's algorithm.

Keyboard while one of these pages is open:
    →  next step     ←  previous step     space  play / pause     Home / End  first / last step
"""
from __future__ import annotations

import customtkinter as ctk

from . import model, theme
from .mapview import MapView
from .pages import Page
from .theme import C, P


class Stepper(ctk.CTkFrame):
    """Reset / Back / Play / Next / Finish buttons, a step counter and a speed slider."""

    def __init__(self, parent, on_change):
        super().__init__(parent, fg_color="transparent")
        self.on_change = on_change
        self.k = 0
        self.n = 0
        self._job = None
        b = theme.button
        b(self, "Reset", lambda: self.go(0), kind="ghost", width=70).pack(side="left", padx=(0, 6))
        b(self, "◀  Back", lambda: self.go(self.k - 1), kind="ghost", width=84).pack(side="left", padx=6)
        self.play_btn = b(self, "Play", self.toggle, width=84)
        self.play_btn.pack(side="left", padx=6)
        b(self, "Next  ▶", lambda: self.go(self.k + 1), kind="ghost", width=84).pack(side="left", padx=6)
        b(self, "Finish", lambda: self.go(self.n), kind="ghost", width=70).pack(side="left", padx=6)
        self.counter = theme.label(self, "", size=13, weight="bold", width=130)
        self.counter.pack(side="left", padx=(14, 6))
        theme.label(self, "Speed", size=12, color="ink2").pack(side="left", padx=(10, 6))
        self.speed = ctk.CTkSlider(self, from_=1, to=10, number_of_steps=9, width=110,
                                   button_color=C("accent"), button_hover_color=C("accent_hover"),
                                   progress_color=C("accent"), fg_color=C("border"))
        self.speed.set(5)
        self.speed.pack(side="left")

    def setup(self, n, k=0):
        self.stop()
        self.n = n
        self.go(k)

    def go(self, k):
        k = max(0, min(k, self.n))
        self.k = k
        self.counter.configure(text=f"Step {k} of {self.n}")
        self.on_change(k)
        if k >= self.n:
            self.stop()

    def toggle(self):
        if self._job:
            self.stop()
        else:
            if self.k >= self.n:
                self.go(0)
            self.play_btn.configure(text="Pause")
            self._tick()

    def _tick(self):
        if self.k >= self.n:
            self.stop()
            return
        self.go(self.k + 1)
        delay = int(1500 / float(self.speed.get()))
        self._job = self.after(delay, self._tick)

    def stop(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        self.play_btn.configure(text="Play")

    def key(self, key):
        if key == "next":
            self.stop()
            self.go(self.k + 1)
        elif key == "back":
            self.stop()
            self.go(self.k - 1)
        elif key == "play":
            self.toggle()
        elif key == "home":
            self.stop()
            self.go(0)
        elif key == "end":
            self.stop()
            self.go(self.n)


class _StepPage(Page):
    """Shared layout: controls on top, map on the left, explanation + step table on the right."""

    side_title = ""

    def __init__(self, master, app, table_columns):
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        bar = theme.card(self)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        self.stepper = Stepper(bar, self.draw)
        self.stepper.pack(side="left", padx=16, pady=12)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2, minsize=380)
        self.map = MapView(body, hover_text=self.tip)
        self.map.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.side = ctk.CTkFrame(body, fg_color="transparent")
        self.side.grid(row=0, column=1, sticky="nsew")
        self.side.grid_columnconfigure(0, weight=1)
        self.side.grid_rowconfigure(3, weight=1)

        self.top = ctk.CTkFrame(self.side, fg_color="transparent", width=1, height=1)   # optional extra controls
        self.top.grid(row=0, column=0, sticky="ew")
        self.top.grid_columnconfigure(0, weight=1)

        c = theme.card(self.side)
        c.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        c.grid_columnconfigure(0, weight=1)
        theme.overline(c, "This step").grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
        self.explain = theme.label(c, "", size=13, wraplength=360)
        self.explain.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 14))

        self.status_card = theme.card(self.side)
        self.status_card.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self.status_card.grid_columnconfigure(0, weight=1)
        self.status_title = theme.overline(self.status_card, "")
        self.status_title.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
        self.status_value = theme.label(self.status_card, "", size=18, weight="bold")
        self.status_value.grid(row=1, column=0, sticky="w", padx=16)
        self.status_bar = ctk.CTkProgressBar(self.status_card, height=10, corner_radius=5,
                                             fg_color=C("panel_alt"), progress_color=C("aqua"))
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 4))
        self.status_note = theme.label(self.status_card, "", size=12, color="ink2", wraplength=360)
        self.status_note.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 14))

        c4 = theme.card(self.side)
        c4.grid(row=3, column=0, sticky="nsew")
        c4.grid_columnconfigure(0, weight=1)
        c4.grid_rowconfigure(0, weight=1)
        self.table = theme.Table(c4, table_columns, height=6, on_select=lambda i: self.stepper.go(i + 1))
        self.table.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

    def tip(self, sid):
        return self.app.stop_tip(sid)

    def on_hide(self):
        self.stepper.stop()

    def on_key(self, key):
        self.stepper.key(key)

    def _select_row(self, k):
        if k > 0:
            self.table.select_row(k - 1)
        else:
            self.table.clear_selection()


# =====================================================================
# Kruskal
# =====================================================================

class SpanningTreePage(_StepPage):
    key = "mst"
    title = "Spanning tree"
    subtitle = ("Kruskal's algorithm, one link at a time: the cheapest set of links that keeps "
                "every stop reachable (Ch 11.5). Use ← → or Play.")

    def __init__(self, master, app):
        super().__init__(master, app, [("i", "#", 44, "center"), ("link", "Link", 220, "w"),
                                       ("km", "km", 60, "center"), ("res", "Result", 80, "center")])
        self._for = None

    def render(self):
        ds, G = self.ds, self.ds.G
        rows = [(i + 1, f"{G.name(u)} – {G.name(v)}", f"{w:.2f}", "added" if a else "skipped")
                for i, (u, v, w, a) in enumerate(ds.ktrace)]
        self.table.set_rows(rows)
        self.status_bar.configure(progress_color=C("aqua"))
        k = self.stepper.k if self._for is ds else 0
        self._for = ds
        self.stepper.setup(len(ds.ktrace), k)

    def draw(self, k):
        ds, G, m, p = self.ds, self.ds.G, self.map, P()
        st = model.kruskal_step(ds, k)
        m.start(G)
        m.edges(G.edges(), lw=1.1)
        m.nodes(G.adj, size=11)
        m.edges(st["tree"], color=p["aqua"], lw=3.0, z=3)
        cur = st["current"]
        ends = []
        if cur:
            u, v, w, added = cur
            ends = [u, v]
            if added:
                m.edges([(u, v)], color=p["orange"], lw=5.0, z=6)
            else:
                m.path(st["cycle"], p["violet"], lw=3.4, z=5)
                m.edges([(u, v)], color=p["red"], lw=3.6, ls=(0, (3, 2)), z=6)
            m.nodes(ends, color=p["ink"], size=46, z=8, lw=1.2)
            m.labels(ends, size=9.5, weight="bold", force=True)
        if G.n_vertices <= 20:
            m.labels([s for s in G.adj if s not in ends])
        m.legend.set([("line", p["aqua"], "tree so far"), ("line", p["orange"], "link just added"),
                      ("dash", p["red"], "link skipped"), ("line", p["violet"], "cycle it would close")])
        m.show()

        n, target = st["n_steps"], st["target_edges"]
        if k == 0:
            text = (f"Kruskal's algorithm sorts all {n} links from shortest to longest and looks at them "
                    f"in that order. A link joins the tree unless the tree already connects its two ends "
                    f"(then it would close a cycle).\n\nPress Next ▶ or the → key.")
        else:
            u, v, w, added = cur
            a, b = G.name(u), G.name(v)
            if added:
                text = (f"Link {k}: {a} – {b} ({w:.2f} km).\nIts two ends are in different pieces of the "
                        f"tree, so it is added and joins them.")
            else:
                text = (f"Link {k}: {a} – {b} ({w:.2f} km) is skipped.\nThe tree already connects "
                        f"{a} and {b} (purple path), so this link would close a cycle. Every link on that "
                        f"path is at most {w:.2f} km — the cycle property.")
        self.explain.configure(text=text)

        self.status_title.configure(text="TREE SO FAR")
        self.status_value.configure(text=f"{len(st['tree'])} of {target} links · {st['total_km']:.2f} km")
        self.status_bar.set(len(st["tree"]) / target if target else 1)
        if k >= n:
            left_out = ds.stats["total_km"] - st["total_km"]
            note = (f"Finished. The {n - len(st['tree'])} links left out ({left_out:.2f} km) are the "
                    f"network's redundancy. Prim's algorithm gives the same total: "
                    f"{ds.stats['prim_km']:.2f} km.")
        else:
            c = len(ds.comps)
            note = (f"A spanning forest on {G.n_vertices} stops in {c} component{'s' if c != 1 else ''} "
                    f"has |V| − c = {target} links.")
        self.status_note.configure(text=note)
        self._select_row(k)


# =====================================================================
# Dijkstra
# =====================================================================

class DijkstraPage(_StepPage):
    key = "dijkstra"
    title = "Dijkstra steps"
    subtitle = ("Shortest distances from one stop, one stop at a time. S is the set of stops whose "
                "distance is final (Ch 10.6). Use ← → or Play.")

    def __init__(self, master, app):
        super().__init__(master, app, [("i", "#", 44, "center"), ("stop", "Moved into S", 160, "w"),
                                       ("km", "km", 60, "center"), ("upd", "Improved", 140, "w")])
        self.source = None
        self.states = []
        src = theme.card(self.top)
        src.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        src.grid_columnconfigure(1, weight=1)
        theme.label(src, "Start at", size=12, color="ink2").grid(row=0, column=0, padx=(16, 8), pady=12)
        self.box = theme.combo(src, [], width=200, command=lambda _v: self.restart())
        self.box.grid(row=0, column=1, sticky="ew", pady=12)
        theme.button(src, "Start", self.restart, width=74).grid(row=0, column=2, padx=12)
        entry = getattr(self.box, "_entry", None)
        if entry is not None:
            entry.bind("<Return>", lambda e: self.restart(), add="+")

    def on_dataset(self):
        super().on_dataset()
        self.source = None

    def render(self):
        ds, G = self.ds, self.ds.G
        self.box.configure(values=ds.stop_names())
        self.status_bar.configure(progress_color=C("blue"))
        if self.source is None:
            self.source = ds.pairs[0][0] if ds.pairs else G.stops.index[0]
            self._compute(keep_step=False)
        else:
            self._compute(keep_step=True)

    def restart(self):
        try:
            self.source = self.ds.G.stop_id(self.box.get())
        except KeyError:
            self.explain.configure(text=f"No stop called '{self.box.get()}'. Pick one from the list.")
            return
        self._compute(keep_step=False)

    def _compute(self, keep_step):
        G = self.ds.G
        self.box.set(G.name(self.source))
        self.states = model.dijkstra_states(G.adj, self.source)
        rows = []
        for st in self.states[1:]:
            upd = ", ".join(G.name(v) for v, _, _ in st["updated"]) or "–"
            rows.append((st["step"], G.name(st["u"]), f"{st['d']:.2f}", upd))
        self.table.set_rows(rows)
        k = self.stepper.k if keep_step else 0
        self.stepper.setup(len(self.states) - 1, k)

    def tip(self, sid):
        text = self.app.stop_tip(sid)
        if self.states:
            st = self.states[self.stepper.k]
            if sid in st["final"]:
                text += f"\ndistance {st['dist'][sid]:.2f} km (final)"
            elif sid in st["dist"]:
                text += f"\ndistance {st['dist'][sid]:.2f} km so far"
            else:
                text += "\ndistance ∞ (not reached yet)"
        return text

    def draw(self, k):
        if not self.states:
            return
        G, m, p = self.ds.G, self.map, P()
        st = self.states[k]
        final, dist, parent = set(st["final"]), st["dist"], st["parent"]
        frontier = [v for v in dist if v not in final]
        m.start(G)
        m.edges(G.edges(), lw=1.1)
        m.edges([(parent[v], v) for v in frontier if parent.get(v)], color=p["orange"], lw=1.8,
                ls=(0, (3, 2)), z=2)
        m.edges([(parent[v], v) for v in final if parent.get(v)], color=p["blue"], lw=2.8, z=3)
        m.nodes([v for v in G.adj if v not in dist], size=10)
        m.nodes(frontier, color=p["orange"], size=38, z=5)
        m.nodes(final, color=p["blue"], size=38, z=5)
        if st["u"]:
            m.nodes([st["u"]], color=p["blue"], size=150, z=8, edge=p["ink"], lw=2)
        if self.source != st["u"]:
            m.nodes([self.source], color=p["blue"] if self.source in final else p["orange"], size=90, z=7,
                    edge=p["ink"], lw=1.5)
        if G.n_vertices <= 20:
            show = sorted(G.adj, key=lambda v: v not in dist)
        else:
            show = [x for x in [self.source, st["u"]] + [v for v, _, _ in st["updated"]] if x]
            show = list(dict.fromkeys(show))
        m.labels(show, texts=[f"{G.name(v)} · {dist[v]:.2f}" if v in dist else f"{G.name(v)} · ∞" for v in show],
                 force=G.n_vertices <= 20)
        m.legend.set([("dot", p["blue"], "in S (final)"), ("dot", p["orange"], "reached, not final"),
                      ("line", p["blue"], "shortest-path tree"), ("dash", p["orange"], "best link so far")])
        m.show()

        src = G.name(self.source)
        if k == 0:
            text = (f"Start at {src}: its distance is 0 and every other stop is ∞. S, the set of stops "
                    f"whose shortest distance is known for sure, is empty.\n\nPress Next ▶ or the → key.")
        else:
            u = G.name(st["u"])
            text = (f"Step {k}: of all stops not in S, {u} has the smallest distance so far "
                    f"({st['d']:.2f} km), so it joins S. No other path can beat it, because every "
                    f"link has a positive length.\n\n")
            if st["updated"]:
                parts = [f"{G.name(v)} {'∞' if old == float('inf') else f'{old:.2f}'} → {new:.2f} km"
                         for v, new, old in st["updated"]]
                text += "Its links improve: " + "; ".join(parts) + "."
            else:
                text += "None of its links gives a shorter way to any stop."
        self.explain.configure(text=text)

        n = len(self.states) - 1
        self.status_title.configure(text="THE SET S")
        self.status_value.configure(text=f"{len(final)} of {n} reachable stops final")
        self.status_bar.set(len(final) / n if n else 1)
        unreached = G.n_vertices - n
        if k >= n:
            note = f"Finished. The blue lines are the shortest-path tree from {src}."
            if unreached:
                note += f" {unreached} stop{'s are' if unreached != 1 else ' is'} never reached (another component)."
        else:
            note = f"{len(frontier)} stop{'s' if len(frontier) != 1 else ''} reached but not final yet (orange)."
        self.status_note.configure(text=note)
        self._select_row(k)
