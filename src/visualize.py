"""Step 5: figures for the report and slides (Matplotlib) and an optional map (Folium).

Stops are drawn at their real coordinates (x = longitude, y = latitude), with the
aspect ratio corrected so the map is not stretched.
"""
from __future__ import annotations

from math import cos, radians
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# colours (a colour-blind-checked categorical order; text always in ink colours)
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
EDGE = "#c3c2b7"
SURFACE = "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BLUE, ORANGE, AQUA, RED = SERIES[0], SERIES[1], SERIES[2], SERIES[7]

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9, "axes.edgecolor": EDGE,
    "axes.labelcolor": INK_2, "xtick.color": MUTED, "ytick.color": MUTED,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})


def _pos(G):
    return {s: (r["lon"], r["lat"]) for s, r in G.stops.iterrows()}


def _new_axes(G, title, size=(9, 9)):
    fig, ax = plt.subplots(figsize=size)
    lat0 = G.stops["lat"].mean()
    ax.set_aspect(1 / cos(radians(lat0)))
    ax.set_title(title, color=INK, fontsize=12, loc="left", pad=10)
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return fig, ax


def _draw_edges(ax, G, pos, edges=None, color=EDGE, lw=1.2, ls="-", z=1, alpha=1.0):
    edges = G.edges() if edges is None else edges
    for u, v, *_ in edges:
        (x1, y1), (x2, y2) = pos[u], pos[v]
        ax.plot([x1, x2], [y1, y2], color=color, lw=lw, ls=ls, zorder=z, alpha=alpha,
                solid_capstyle="round")


def _draw_nodes(ax, G, pos, nodes=None, color=INK_2, size=14, z=3, edgecolor=SURFACE):
    nodes = list(G.adj) if nodes is None else list(nodes)
    if not nodes:
        return
    xs = [pos[n][0] for n in nodes]
    ys = [pos[n][1] for n in nodes]
    ax.scatter(xs, ys, s=size, c=color, zorder=z, edgecolors=edgecolor, linewidths=0.8)


def _label(ax, G, pos, nodes, fontsize=7.5, color=INK):
    for n in nodes:
        x, y = pos[n]
        ax.annotate(G.name(n), (x, y), xytext=(4, 3), textcoords="offset points",
                    fontsize=fontsize, color=color, zorder=5)


def _default_labels(G):
    if G.n_vertices <= 20:
        return list(G.adj)
    return [s for s in G.adj if len(G.adj[s]) >= 4 or len(G.adj[s]) == 0]


def _save(fig, out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)          # free the memory (matters when the app re-runs the analysis)
    return out


def plot_network(G, components, out, title="Bus stop graph"):
    """Whole network; stop size grows with degree; colour = connected component."""
    pos = _pos(G)
    fig, ax = _new_axes(G, title)
    _draw_edges(ax, G, pos)
    handles = []
    for i, comp in enumerate(components[:8]):
        col = SERIES[i]
        sizes = [12 + 9 * len(G.adj[n]) for n in comp]
        nodes = sorted(comp)
        ax.scatter([pos[n][0] for n in nodes], [pos[n][1] for n in nodes], s=sizes, c=col,
                   zorder=3, edgecolors=SURFACE, linewidths=0.8)
        handles.append(Line2D([], [], marker="o", ls="", color=col,
                              label=f"component {i + 1} ({len(comp)} stop{'s' if len(comp) != 1 else ''})"))
    if len(components) > 8:
        rest = set().union(*components[8:])
        _draw_nodes(ax, G, pos, rest, color=MUTED)
        handles.append(Line2D([], [], marker="o", ls="", color=MUTED, label="other components"))
    _label(ax, G, pos, _default_labels(G))
    ax.legend(handles=handles, loc="best", frameon=False, labelcolor=INK_2)
    return _save(fig, out)


def plot_paths(G, hop_path, dist_path, out, title):
    """Fewest-hop path (orange, dashed) against shortest-distance path (blue, solid)."""
    pos = _pos(G)
    fig, ax = _new_axes(G, title)
    _draw_edges(ax, G, pos, alpha=0.8)
    _draw_nodes(ax, G, pos, color=EDGE, size=10)
    if hop_path:
        _draw_edges(ax, G, pos, list(zip(hop_path, hop_path[1:])), color=ORANGE, lw=3.2, ls=(0, (4, 2)), z=4)
    if dist_path:
        _draw_edges(ax, G, pos, list(zip(dist_path, dist_path[1:])), color=BLUE, lw=2.4, z=4)
    on_path = set(hop_path or []) | set(dist_path or [])
    _draw_nodes(ax, G, pos, on_path, color=INK, size=22, z=6)
    _label(ax, G, pos, on_path)
    ax.legend(handles=[
        Line2D([], [], color=ORANGE, lw=3, ls=(0, (4, 2)), label=f"fewest stops ({len(hop_path) - 1} hops)"),
        Line2D([], [], color=BLUE, lw=2.4, label=f"shortest distance ({len(dist_path) - 1} hops)"),
    ], loc="best", frameon=False, labelcolor=INK_2)
    return _save(fig, out)


def plot_mst(G, mst_edges, out, title):
    """The minimum spanning tree (thick) over the full network (thin, dashed)."""
    pos = _pos(G)
    fig, ax = _new_axes(G, title)
    _draw_edges(ax, G, pos, color=EDGE, lw=1.0, ls=(0, (2, 2)))
    _draw_edges(ax, G, pos, mst_edges, color=AQUA, lw=2.6, z=2)
    _draw_nodes(ax, G, pos, size=14)
    _label(ax, G, pos, _default_labels(G))
    ax.legend(handles=[
        Line2D([], [], color=AQUA, lw=2.6, label=f"spanning tree edge ({len(mst_edges)})"),
        Line2D([], [], color=EDGE, lw=1.2, ls=(0, (2, 2)),
               label=f"left out = redundancy ({G.n_edges - len(mst_edges)})"),
    ], loc="best", frameon=False, labelcolor=INK_2)
    return _save(fig, out)


def plot_cut_points(G, cuts, bridge_edges, out, title):
    """Cut vertices (large red dots) and bridges (thick red lines)."""
    pos = _pos(G)
    fig, ax = _new_axes(G, title)
    _draw_edges(ax, G, pos)
    _draw_edges(ax, G, pos, bridge_edges, color=RED, lw=2.6, z=2)
    _draw_nodes(ax, G, pos, size=12)
    _draw_nodes(ax, G, pos, cuts, color=RED, size=60, z=4)
    _label(ax, G, pos, cuts)
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="", color=RED, markersize=8, label=f"cut vertex ({len(cuts)})"),
        Line2D([], [], color=RED, lw=2.6, label=f"bridge ({len(bridge_edges)})"),
    ], loc="best", frameon=False, labelcolor=INK_2)
    return _save(fig, out)


def plot_degree_histogram(G, out, title="How many neighbours each stop has"):
    degs = [len(n) for n in G.adj.values()]
    values = list(range(0, max(degs) + 1))
    counts = [degs.count(d) for d in values]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.bar(values, counts, width=0.72, color=BLUE, zorder=2)
    for x, c in zip(values, counts):
        if c:
            ax.annotate(str(c), (x, c), xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=8, color=INK_2)
    ax.set_xticks(values)
    ax.set_xlabel("degree (number of directly linked stops)")
    ax.set_ylabel("number of stops")
    ax.set_title(title, color=INK, fontsize=12, loc="left")
    ax.grid(axis="y", color="#e1e0d9", lw=0.6, zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return _save(fig, out)


def build_map(G, mst_edges=None, path=None, cuts=None):
    """Interactive Leaflet map as a folium.Map (shows inline in a notebook). None if folium is missing."""
    try:
        import folium
    except ImportError:
        print("  (folium not installed: skipping the interactive map)")
        return None
    lat0, lon0 = G.stops["lat"].mean(), G.stops["lon"].mean()
    m = folium.Map(location=[lat0, lon0], zoom_start=12, tiles="OpenStreetMap")
    coord = {s: (r["lat"], r["lon"]) for s, r in G.stops.iterrows()}

    net = folium.FeatureGroup(name="All links")
    for u, v, w in G.edges():
        routes = ", ".join(sorted(G.edge_routes[frozenset((u, v))]))
        folium.PolyLine([coord[u], coord[v]], color=MUTED, weight=2, opacity=0.7,
                        tooltip=f"{G.name(u)} - {G.name(v)}: {w:.2f} km ({routes})").add_to(net)
    net.add_to(m)
    if mst_edges:
        fg = folium.FeatureGroup(name="Minimum spanning tree")
        for u, v, w in mst_edges:
            folium.PolyLine([coord[u], coord[v]], color=AQUA, weight=5, opacity=0.9).add_to(fg)
        fg.add_to(m)
    if path:
        fg = folium.FeatureGroup(name="Shortest path example")
        folium.PolyLine([coord[s] for s in path], color=BLUE, weight=6,
                        tooltip=G.names(path)).add_to(fg)
        fg.add_to(m)
    stops = folium.FeatureGroup(name="Stops")
    cuts = set(cuts or [])
    for s, (la, lo) in coord.items():
        is_cut = s in cuts
        folium.CircleMarker([la, lo], radius=6 if is_cut else 4,
                            color=RED if is_cut else INK_2, fill=True, fill_opacity=0.9,
                            tooltip=f"{G.name(s)} ({s}), degree {len(G.adj[s])}"
                                    + (" - cut vertex" if is_cut else "")).add_to(stops)
    stops.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m


def make_map(G, out_html, mst_edges=None, path=None, cuts=None):
    """Save the interactive map as an HTML file you can open in any browser."""
    m = build_map(G, mst_edges=mst_edges, path=path, cuts=cuts)
    if m is None:
        return None
    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))
    return out_html
