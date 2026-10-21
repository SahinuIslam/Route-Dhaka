"""The main window: sidebar (data set, quick facts, navigation, light/dark) + one page at a time."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")   # figures saved by "Run full analysis" go to files; the app draws with its own canvases

import tkinter as tk

import customtkinter as ctk

from . import model, theme
from .pages import DataCheckPage, OverviewPage, RouteFinderPage, WeakPointsPage
from .steppers import DijkstraPage, SpanningTreePage
from .theme import C

PAGES = [OverviewPage, RouteFinderPage, WeakPointsPage, SpanningTreePage, DijkstraPage, DataCheckPage]
NAV_LABELS = {"overview": "Overview", "route": "Route finder", "weak": "Weak points",
              "mst": "Spanning tree", "dijkstra": "Dijkstra steps", "data": "Data check"}


class App(ctk.CTk):
    def __init__(self, dataset: str | None = None, mode: str = "System"):
        ctk.set_appearance_mode(mode)
        super().__init__()
        self.title("Dhaka Bus Network as a Graph — CSE173")
        self._size_window()
        self.configure(fg_color=C("bg"))
        theme.style_tables(self)
        self.ds: model.Dataset | None = None
        self.current = None
        self._theme_mode = ctk.get_appearance_mode()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self.mode_menu.set(mode)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=22, pady=(18, 18))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        head = ctk.CTkFrame(main, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        self.page_title = theme.label(head, "", size=24, weight="bold")
        self.page_title.pack(anchor="w")
        self.page_sub = theme.label(head, "", size=13, color="ink2")
        self.page_sub.pack(anchor="w", pady=(2, 0))
        holder = ctk.CTkFrame(main, fg_color="transparent")
        holder.grid(row=1, column=0, sticky="nsew")
        holder.grid_columnconfigure(0, weight=1)
        holder.grid_rowconfigure(0, weight=1)
        self.pages = {P.key: P(holder, self) for P in PAGES}

        for seq, key in (("<Right>", "next"), ("<Left>", "back"), ("<space>", "play"),
                         ("<Home>", "home"), ("<End>", "end")):
            self.bind(seq, lambda e, k=key: self._key(e, k))
        self.protocol("WM_DELETE_WINDOW", self._close)

        names = model.available_datasets()
        self.ds_names = names
        if not names:
            self.page_title.configure(text="No data found")
            self.page_sub.configure(text=f"Expected folders like data/sample/raw/ inside {model.ROOT}")
            return
        start = dataset if dataset in names else ("dhaka" if "dhaka" in names else names[0])
        self.ds_switch.configure(values=[model.LABELS.get(n, n.title()) for n in names])
        self.after(10, lambda: self.load(start))
        self.after(1500, self._watch_mode)

    # ------------------------------------------------------------ layout

    def _size_window(self):
        try:
            scale = ctk.ScalingTracker.get_window_scaling(self)
        except Exception:
            scale = 1.0
        sw, sh = self.winfo_screenwidth() / scale, self.winfo_screenheight() / scale
        w, h = int(min(1440, sw * 0.94)), int(min(900, sh * 0.88))
        self.geometry(f"{w}x{h}+{int((sw - w) / 2)}+{int(max(0, (sh - h) / 2 - 20))}")
        self.minsize(min(1180, w), min(720, h))

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=C("panel"), corner_radius=0, width=244)
        sb.grid(row=0, column=0, sticky="nsw")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        sb.grid_rowconfigure(6, weight=1)
        ctk.CTkFrame(self, fg_color=C("border"), width=1, corner_radius=0).grid(row=0, column=0, sticky="nse")

        brand = ctk.CTkFrame(sb, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=20, pady=(22, 18))
        theme.label(brand, "Dhaka Bus Graph", size=19, weight="bold").pack(anchor="w")
        theme.label(brand, "CSE173 · Discrete Mathematics", size=12, color="muted").pack(anchor="w")

        theme.overline(sb, "Data set").grid(row=1, column=0, sticky="w", padx=20, pady=(0, 6))
        self.ds_switch = theme.segmented(sb, ["Sample", "Dhaka"], self._switch_dataset)
        self.ds_switch.grid(row=2, column=0, sticky="ew", padx=16)

        facts = ctk.CTkFrame(sb, fg_color=C("panel_alt"), corner_radius=10)
        facts.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 18))
        facts.grid_columnconfigure((0, 1), weight=1, uniform="facts")
        self.facts = {}
        for i, (key, text) in enumerate([("V", "stops"), ("E", "links"), ("routes", "routes"),
                                         ("components", "components")]):
            cell = ctk.CTkFrame(facts, fg_color="transparent")
            cell.grid(row=i // 2, column=i % 2, sticky="w", padx=14, pady=(10 if i < 2 else 0, 10 if i >= 2 else 0))
            v = theme.label(cell, "–", size=17, weight="bold")
            v.pack(anchor="w")
            theme.label(cell, text, size=11, color="muted").pack(anchor="w")
            self.facts[key] = v

        theme.overline(sb, "Pages").grid(row=4, column=0, sticky="w", padx=20, pady=(0, 6))
        nav = ctk.CTkFrame(sb, fg_color="transparent")
        nav.grid(row=5, column=0, sticky="ew", padx=12)
        nav.grid_columnconfigure(0, weight=1)
        self.nav = {}
        for i, (key, text) in enumerate(NAV_LABELS.items()):
            b = ctk.CTkButton(nav, text=text, anchor="w", height=38, corner_radius=8, font=theme.font(14),
                              fg_color="transparent", hover_color=C("hover"), text_color=C("ink2"),
                              text_color_disabled=C("muted"), command=lambda k=key: self.show(k))
            b.grid(row=i, column=0, sticky="ew", pady=1)
            self.nav[key] = b

        bottom = ctk.CTkFrame(sb, fg_color="transparent")
        bottom.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 18))
        bottom.grid_columnconfigure(0, weight=1)
        self.warn = ctk.CTkButton(bottom, text="", anchor="w", height=30, corner_radius=8, fg_color="transparent",
                                  hover_color=C("hover"), text_color=C("warn"), font=theme.font(12, "bold"),
                                  command=lambda: self.show("data"))
        self.warn.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        theme.overline(bottom, "Appearance").grid(row=1, column=0, sticky="w", padx=4, pady=(0, 6))
        self.mode_menu = ctk.CTkOptionMenu(
            bottom, values=["System", "Light", "Dark"], command=self.set_mode, height=32, corner_radius=8,
            fg_color=C("panel_alt"), button_color=C("panel_alt"), button_hover_color=C("hover"),
            text_color=C("ink"), dropdown_fg_color=C("panel"), dropdown_hover_color=C("hover"),
            dropdown_text_color=C("ink"), font=theme.font(13))
        self.mode_menu.set("System")
        self.mode_menu.grid(row=2, column=0, sticky="ew")

    # ------------------------------------------------------------ data

    def _switch_dataset(self, label):
        for n in self.ds_names:
            if model.LABELS.get(n, n.title()) == label:
                if self.ds is None or n != self.ds.name:
                    self.load(n)
                return

    def reload(self):
        if self.ds is not None:
            self.load(self.ds.name)

    def load(self, name):
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            ds = model.load_dataset(name)
        finally:
            self.configure(cursor="")
        self.ds = ds
        self.ds_switch.set(model.LABELS.get(name, name.title()))
        st = ds.stats
        for key in self.facts:
            self.facts[key].configure(text=str(st[key]) if ds.ok else "–")
        if ds.ok and st.get("unverified"):
            self.warn.configure(text=f"!  {st['unverified']} of {st['routes']} routes unverified")
            self.warn.grid()
        elif not ds.ok:
            self.warn.configure(text="!  Data problem — see Data check")
            self.warn.grid()
        else:
            self.warn.grid_remove()
        for key, b in self.nav.items():
            b.configure(state="normal" if ds.ok or key == "data" else "disabled")
        for page in self.pages.values():
            page.on_dataset()
        self.show("data" if not ds.ok else (self.current or "overview"), force=True)

    def stop_tip(self, sid):
        G = self.ds.G
        deg = len(G.adj[sid])
        routes = sorted(r for r, seq in G.route_seq.items() if sid in seq)
        text = f"{G.name(sid)}  ({sid})\n{deg} link{'s' if deg != 1 else ''} · {len(routes)} route{'s' if len(routes) != 1 else ''}"
        if routes:
            text += "\n" + ", ".join(routes[:8]) + (" …" if len(routes) > 8 else "")
        return text

    # ------------------------------------------------------------ pages

    def show(self, key, force=False):
        if self.ds is None or (not self.ds.ok and key != "data"):
            return
        if key == self.current and not force:
            return
        if self.current and self.current != key:
            old = self.pages[self.current]
            old.on_hide()
            old.grid_forget()
        page = self.pages[key]
        page.grid(row=0, column=0, sticky="nsew")
        self.current = key
        self.page_title.configure(text=page.title)
        self.page_sub.configure(text=page.subtitle)
        for k, b in self.nav.items():
            active = k == key
            b.configure(fg_color=C("select") if active else "transparent",
                        text_color=C("ink") if active else C("ink2"),
                        font=theme.font(14, "bold" if active else "normal"))
        self.update_idletasks()
        page.on_show()

    def _key(self, event, key):
        if isinstance(event.widget, (tk.Entry, tk.Text)) or event.widget.winfo_class() in ("Entry", "Text"):
            return
        if self.current:
            self.pages[self.current].on_key(key)

    # ------------------------------------------------------------ light / dark

    def set_mode(self, mode):
        ctk.set_appearance_mode(mode)
        self.after(60, self._apply_theme)

    def _apply_theme(self):
        self._theme_mode = ctk.get_appearance_mode()
        theme.style_tables(self)
        for page in self.pages.values():
            page.on_theme()
        if self.current:
            self.pages[self.current].on_show()

    def _watch_mode(self):
        if ctk.get_appearance_mode() != self._theme_mode:   # the computer switched light/dark
            self._apply_theme()
        self.after(1500, self._watch_mode)

    def _close(self):
        for page in self.pages.values():
            page.on_hide()
        self.quit()
        self.destroy()


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="Dhaka bus network app")
    p.add_argument("--data", default=None, help="data set to open first (sample, dhaka, osm)")
    p.add_argument("--mode", default="System", choices=["System", "Light", "Dark"])
    args = p.parse_args(argv)
    app = App(dataset=args.data, mode=args.mode)
    app.mainloop()
