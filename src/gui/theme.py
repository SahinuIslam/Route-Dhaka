"""Colours, fonts and small reusable widgets for the app (light and dark mode).

Every colour is given as a (light, dark) pair. CustomTkinter widgets accept the pair
and switch by themselves; Matplotlib and the tables ask for the current palette with P().
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

import customtkinter as ctk

LIGHT = {
    "bg": "#f3f2ee", "panel": "#fcfcfb", "panel_alt": "#f5f4f0", "border": "#e1e0d9",
    "hover": "#ebeae4", "select": "#dceafb",
    "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
    "edge": "#cfcec6", "node": "#6b6a66",
    "accent": "#2a78d6", "accent_hover": "#256abf",
    "blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "red": "#e34948",
    "violet": "#6250d6", "yellow": "#eda100",
    "good": "#0a8a0a", "warn": "#9a6700", "bad": "#d03b3b",
}
DARK = {
    "bg": "#121211", "panel": "#1c1c1b", "panel_alt": "#242423", "border": "#30302e",
    "hover": "#2b2b29", "select": "#1f3a5c",
    "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
    "edge": "#4a4946", "node": "#a3a29b",
    "accent": "#256abf", "accent_hover": "#1c5cab",
    "blue": "#3987e5", "orange": "#d95926", "aqua": "#199e70", "red": "#e66767",
    "violet": "#9085e9", "yellow": "#c98500",
    "good": "#0ca30c", "warn": "#fab219", "bad": "#e66767",
}
SERIES = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
}


def is_dark() -> bool:
    return ctk.get_appearance_mode() == "Dark"


def P() -> dict:
    """The palette for the current mode (for Matplotlib and ttk)."""
    return DARK if is_dark() else LIGHT


def C(key: str) -> tuple[str, str]:
    """A (light, dark) colour pair for CustomTkinter widgets."""
    return LIGHT[key], DARK[key]


def series(i: int) -> str:
    s = SERIES["dark" if is_dark() else "light"]
    return s[i % len(s)]


_fonts: dict = {}


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    key = (size, weight)
    if key not in _fonts:
        _fonts[key] = ctk.CTkFont(size=size, weight=weight)
    return _fonts[key]


# ------------------------------------------------------------------ ttk table style

_tk_fonts: dict = {}


def style_tables(root) -> None:
    """Style ttk.Treeview to match the current mode. Call again after a mode change."""
    p = P()
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    if not _tk_fonts:
        base = tkfont.nametofont("TkDefaultFont")
        _tk_fonts["row"] = base.copy()
        _tk_fonts["row"].configure(size=10)
        _tk_fonts["head"] = base.copy()
        _tk_fonts["head"].configure(size=10, weight="bold")
    line = _tk_fonts["row"].metrics("linespace")
    st.configure("Bus.Treeview", background=p["panel"], fieldbackground=p["panel"],
                 foreground=p["ink"], rowheight=line + 12, borderwidth=0, relief="flat",
                 font=_tk_fonts["row"])
    st.map("Bus.Treeview", background=[("selected", p["select"])], foreground=[("selected", p["ink"])])
    st.configure("Bus.Treeview.Heading", background=p["panel_alt"], foreground=p["ink2"],
                 relief="flat", borderwidth=0, font=_tk_fonts["head"], padding=(8, 6))
    st.map("Bus.Treeview.Heading", background=[("active", p["hover"])], relief=[("active", "flat")])
    st.layout("Bus.Treeview", [("Bus.Treeview.treearea", {"sticky": "nswe"})])


# ------------------------------------------------------------------ widget helpers

def card(parent, **kw) -> ctk.CTkFrame:
    opts = dict(fg_color=C("panel"), corner_radius=12, border_width=1, border_color=C("border"))
    opts.update(kw)
    return ctk.CTkFrame(parent, **opts)


def label(parent, text="", size=13, weight="normal", color="ink", **kw) -> ctk.CTkLabel:
    opts = dict(text=text, font=font(size, weight), text_color=C(color), anchor="w", justify="left")
    opts.update(kw)
    return ctk.CTkLabel(parent, **opts)


def overline(parent, text) -> ctk.CTkLabel:
    return label(parent, text.upper(), size=11, weight="bold", color="muted")


def button(parent, text, command, kind="primary", width=110, **kw) -> ctk.CTkButton:
    if kind == "primary":
        opts = dict(fg_color=C("accent"), hover_color=C("accent_hover"), text_color=("#ffffff", "#ffffff"),
                    border_width=0)
    else:  # ghost
        opts = dict(fg_color=C("panel"), hover_color=C("hover"), text_color=C("ink"),
                    border_width=1, border_color=C("border"))
    opts.update(dict(text=text, command=command, width=width, height=34, corner_radius=8,
                     font=font(13, "bold" if kind == "primary" else "normal")))
    opts.update(kw)
    return ctk.CTkButton(parent, **opts)


def combo(parent, values, command=None, width=220) -> ctk.CTkComboBox:
    return ctk.CTkComboBox(parent, values=values, command=command, width=width, height=34,
                           corner_radius=8, border_width=1, border_color=C("border"),
                           fg_color=C("panel"), button_color=C("border"), button_hover_color=C("muted"),
                           text_color=C("ink"), dropdown_fg_color=C("panel"),
                           dropdown_hover_color=C("hover"), dropdown_text_color=C("ink"), font=font(13))


def segmented(parent, values, command, **kw) -> ctk.CTkSegmentedButton:
    opts = dict(values=values, command=command, height=32, corner_radius=8, font=font(12, "bold"),
                fg_color=C("panel_alt"), selected_color=C("accent"), selected_hover_color=C("accent_hover"),
                unselected_color=C("panel_alt"), unselected_hover_color=C("hover"),
                text_color=(("#0b0b0b"), ("#f0efec")))
    opts.update(kw)
    return ctk.CTkSegmentedButton(parent, **opts)


class Table(ctk.CTkFrame):
    """A ttk.Treeview with a slim scrollbar, styled for the current mode.
    columns: list of (key, heading, width, anchor)."""

    def __init__(self, parent, columns, height=10, on_select=None):
        super().__init__(parent, fg_color="transparent")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._cols = [c[0] for c in columns]
        self.tree = ttk.Treeview(self, columns=self._cols, show="headings", height=height,
                                 style="Bus.Treeview", selectmode="browse")
        for key, head, width, anchor in columns:
            self.tree.heading(key, text=head, anchor=anchor)
            self.tree.column(key, width=width, minwidth=40, anchor=anchor, stretch=(anchor == "w"))
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb = ctk.CTkScrollbar(self, command=self.tree.yview, width=12,
                              button_color=C("border"), button_hover_color=C("muted"))
        sb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)
        self.on_select = on_select
        self._silent = False
        self.tree.bind("<<TreeviewSelect>>", self._selected)
        self.restyle()

    def set_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(rows):
            self.tree.insert("", "end", iid=str(i), values=row, tags=("odd" if i % 2 else "even",))
        self.restyle()

    def select_row(self, index, see=True):
        iid = str(index)
        if self.tree.exists(iid):
            self._silent = True
            self.tree.selection_set(iid)
            if see:
                self.tree.see(iid)
            self.after_idle(lambda: setattr(self, "_silent", False))

    def clear_selection(self):
        self._silent = True
        self.tree.selection_remove(*self.tree.selection())
        self.after_idle(lambda: setattr(self, "_silent", False))

    def _selected(self, _event):
        if self._silent or not self.on_select:
            return
        sel = self.tree.selection()
        if sel:
            self.on_select(int(sel[0]))

    def restyle(self):
        p = P()
        self.tree.tag_configure("odd", background=p["panel_alt"])
        self.tree.tag_configure("even", background=p["panel"])


class KpiCard(ctk.CTkFrame):
    def __init__(self, parent, title):
        super().__init__(parent, fg_color=C("panel"), corner_radius=12, border_width=1, border_color=C("border"))
        self.grid_columnconfigure(0, weight=1)
        label(self, title, size=12, color="ink2").grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
        self.value = label(self, "–", size=26, weight="bold")
        self.value.grid(row=1, column=0, sticky="w", padx=16)
        self.caption = label(self, "", size=12, color="muted")
        self.caption.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))

    def set(self, value, caption=""):
        self.value.configure(text=value)
        self.caption.configure(text=caption)


def glyph(parent, kind, color, bg=None) -> tk.Canvas:
    """A tiny legend symbol: dot, ring, cross, line or dash."""
    p = P()
    bg = bg or p["panel"]
    cv = tk.Canvas(parent, width=24, height=14, highlightthickness=0, bg=bg, borderwidth=0)
    if kind == "dot":
        cv.create_oval(7, 2, 17, 12, fill=color, outline="")
    elif kind == "ring":
        cv.create_oval(6, 1, 18, 13, fill=bg, outline=color, width=2)
    elif kind == "cross":
        cv.create_line(7, 2, 17, 12, fill=color, width=3)
        cv.create_line(7, 12, 17, 2, fill=color, width=3)
    elif kind == "dash":
        cv.create_line(1, 7, 23, 7, fill=color, width=3, dash=(5, 3))
    else:
        cv.create_line(1, 7, 23, 7, fill=color, width=3)
    return cv


class Legend(ctk.CTkFrame):
    """A row of legend entries: (kind, colour, text), kind = dot, ring, cross, line or dash."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent", width=1, height=22)

    def set(self, items):
        for w in self.winfo_children():
            w.destroy()
        for kind, color, text in items:
            glyph(self, kind, color).pack(side="left", padx=(0, 4))
            label(self, text, size=12, color="ink2").pack(side="left", padx=(0, 16))
