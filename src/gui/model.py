"""The logic behind the desktop app.

Nothing in this file uses tkinter, so it can be tested without a screen
(see tests/test_gui_model.py). The app only asks this module for answers
and draws them.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from math import inf
from pathlib import Path

import pandas as pd

from .. import algorithms as alg
from ..analysis import changes_from
from ..data_prep import MAX_HOP_KM, DataError, clean, read_raw, save_processed, validate
from ..graph_build import BusGraph, build_graph, route_graph, save_edges

ROOT = Path(__file__).resolve().parents[2]
LABELS = {"sample": "Sample", "dhaka": "Dhaka", "osm": "OSM"}


def available_datasets(root: Path = ROOT) -> list[str]:
    """Every folder data/<name>/ that has raw/stops.csv. Sample first, then Dhaka, then the rest."""
    data = Path(root) / "data"
    if not data.exists():
        return []
    found = [p.name for p in data.iterdir() if (p / "raw" / "stops.csv").exists()]
    order = {"sample": 0, "dhaka": 1, "osm": 2}
    return sorted(found, key=lambda n: (order.get(n, 9), n))


@dataclass
class Dataset:
    name: str
    folder: Path
    rules: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    error: str | None = None
    data: object = None
    G: BusGraph | None = None
    comps: list = field(default_factory=list)
    cuts: list = field(default_factory=list)
    bridges: list = field(default_factory=list)
    cut_info: dict = field(default_factory=dict)
    radj: dict = field(default_factory=dict)
    ktrace: list = field(default_factory=list)
    mst: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    pairs: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def label(self) -> str:
        return LABELS.get(self.name, self.name.title())

    def stop_names(self) -> list[str]:
        return sorted(self.G.stops["name_en"]) if self.G is not None else []


# ------------------------------------------------------------------ loading

def load_dataset(name: str, root: Path = ROOT, max_hop_km: float = MAX_HOP_KM) -> Dataset:
    """Clean + validate + build + analyse one data set. Never raises for data problems:
    a problem is returned in Dataset.error so the app can show it."""
    folder = Path(root) / "data" / name
    try:
        data = clean(read_raw(folder / "raw"))
    except DataError as e:
        return Dataset(name, folder, error=str(e))
    rules = validate(data, max_hop_km=max_hop_km)
    data.rule_results = rules
    failed = [r.code for r in rules if not r.holds and not r.is_warning]
    if failed:
        return Dataset(name, folder, rules=rules, notes=data.notes, data=data,
                       error=f"Validation failed: rule {', '.join(failed)}. Fix the files in "
                             f"data/{name}/raw/ and press Reload data.")
    save_processed(data, folder / "processed")
    G = build_graph(data)
    save_edges(G, folder / "processed")

    ds = Dataset(name, folder, rules=rules, notes=data.notes, data=data, G=G)
    adj = G.adj
    ds.comps = alg.connected_components(adj)
    ds.cuts = alg.cut_vertices(adj)
    ds.bridges = alg.bridges(adj)
    ds.cut_info = {v: removal_effect(adj, v) for v in ds.cuts}
    ds.cuts.sort(key=lambda v: (-len(ds.cut_info[v]["cut_off"]), G.name(v)))
    ds.radj = route_graph(G)
    ds.ktrace = []
    ds.mst = alg.kruskal(adj, trace=ds.ktrace)
    ds.stats = _stats(ds)
    ds.pairs = _pairs(folder, G)
    return ds


def _pairs(folder: Path, G: BusGraph) -> list[tuple[str, str]]:
    f = folder / "pairs.csv"
    out = []
    if f.exists():
        for _, row in pd.read_csv(f, dtype=str).iterrows():
            try:
                out.append((G.stop_id(row["from_stop"]), G.stop_id(row["to_stop"])))
            except KeyError:
                pass
    return out


def _stats(ds: Dataset) -> dict:
    G, adj = ds.G, ds.G.adj
    V, E = G.n_vertices, G.n_edges
    largest = ds.comps[0]
    hs = alg.hop_summary(adj, largest)
    dsum = alg.distance_summary(adj, largest)
    changes = Counter()
    for s in sorted(largest):
        best = changes_from(ds.radj, G.route_seq, s)
        for t in largest:
            if t > s and t in best:
                changes[best[t]] += 1
    serving = Counter(s for seq in G.route_seq.values() for s in set(seq))
    busiest = sorted(adj, key=lambda s: (-len(adj[s]), -serving.get(s, 0), G.name(s)))
    conf = Counter(G.routes["confidence"]) if "confidence" in G.routes else Counter()
    total_km = sum(w for _, _, w in G.edges())
    return {
        "V": V, "E": E, "routes": len(G.routes), "density": E / (V * (V - 1) / 2) if V > 1 else 0,
        "components": len(ds.comps), "largest": len(largest),
        "cut_vertices": len(ds.cuts), "bridges": len(ds.bridges),
        "total_km": total_km, "mst_km": alg.total_weight(ds.mst),
        "prim_km": alg.total_weight(alg.prim(adj)),
        "avg_hops": hs["average_hops"], "diameter_hops": hs["diameter_hops"],
        "diameter_ends": hs["diameter_ends"], "centre": hs["centre"],
        "avg_km": dsum["average_km"], "diameter_km": dsum["diameter_km"],
        "changes": dict(sorted(changes.items())),
        "busiest": [(s, len(adj[s]), serving.get(s, 0)) for s in busiest[:12]],
        "serving": dict(serving),
        "unverified": conf.get("unverified", 0),
    }


# ------------------------------------------------------------------ route finder

def _positions(seq: list[str], stop: str) -> list[int]:
    return [i for i, s in enumerate(seq) if s == stop]


def route_segment(seq: list[str], a: str, b: str) -> list[str]:
    """The stops a route passes between a and b (either direction), shortest choice for loop routes."""
    best = None
    for i in _positions(seq, a):
        for j in _positions(seq, b):
            if best is None or abs(i - j) < abs(best[0] - best[1]):
                best = (i, j)
    i, j = best
    return seq[i:j + 1] if i <= j else seq[j:i + 1][::-1]


def plan_legs(G: BusGraph, radj: dict, routes: list[str], s: str, t: str) -> list[dict]:
    """Turn a sequence of routes into rider instructions: where to board and get off each bus.
    Change points are chosen to ride the fewest stops in total (a small dynamic programme)."""
    states = {s: (0, [])}                     # current stop -> (stops ridden so far, legs)
    for i, r in enumerate(routes):
        seq = G.route_seq[r]
        targets = sorted(radj[r][routes[i + 1]]) if i + 1 < len(routes) else [t]
        new: dict = {}
        for board in sorted(states):
            cost, legs = states[board]
            for x in targets:
                seg = route_segment(seq, board, x)
                c = cost + len(seg) - 1
                if x not in new or c < new[x][0]:
                    new[x] = (c, legs + [{"route": r, "board": board, "alight": x, "stops": seg}])
        states = new
    return states[t][1]


def find_route(ds: Dataset, s: str, t: str) -> dict:
    G, adj = ds.G, ds.G.adj
    hp = alg.fewest_hops_path(adj, s, t)
    if hp is None:
        return {"reachable": False, "s": s, "t": t}
    dkm, dp = alg.shortest_distance_path(adj, s, t)
    bc = alg.fewest_bus_changes(ds.radj, G.route_seq, s, t)
    legs = plan_legs(G, ds.radj, bc[1], s, t) if bc else []
    return {"reachable": True, "s": s, "t": t,
            "hop_path": hp, "hop_km": alg.path_length_km(adj, hp),
            "dist_path": dp, "dist_km": dkm,
            "changes": bc[0] if bc else None, "legs": legs, "same": hp == dp}


# ------------------------------------------------------------------ weak points

def removal_effect(adj: dict, v: str) -> dict:
    """What happens to v's part of the network if stop v is closed.
    pieces = the parts it falls into (largest first); cut_off = every stop not in the largest part."""
    sub = {u: {w: d for w, d in nb.items() if w != v} for u, nb in adj.items() if u != v}
    seen: set[str] = set()
    pieces = []
    for n in sorted(adj[v]):
        if n in seen:
            continue
        reach, _ = alg.bfs(sub, n)
        seen |= set(reach)
        pieces.append(set(reach))
    pieces.sort(key=lambda p: (-len(p), min(p)))
    cut_off = set().union(*pieces[1:]) if len(pieces) > 1 else set()
    return {"pieces": pieces, "cut_off": cut_off, "main": pieces[0] if pieces else set()}


def detour_cost(adj: dict, v: str, keep: set[str]) -> tuple[float, float]:
    """Average shortest distance between stops in `keep`, with v open and with v closed."""
    sub = {u: {w: d for w, d in nb.items() if w != v} for u, nb in adj.items() if u != v}
    before = after = 0.0
    pairs = 0
    for s in sorted(keep):
        d0, _ = alg.dijkstra(adj, s)
        d1, _ = alg.dijkstra(sub, s)
        for t in keep:
            if t > s and t in d1:
                before += d0[t]
                after += d1[t]
                pairs += 1
    return (before / pairs, after / pairs) if pairs else (0.0, 0.0)


# ------------------------------------------------------------------ step-by-step algorithms

def kruskal_step(ds: Dataset, k: int) -> dict:
    """State of Kruskal's algorithm after it has looked at the first k links (0 <= k <= |E|)."""
    trace = ds.ktrace
    k = max(0, min(k, len(trace)))
    tree = [(u, v, w) for u, v, w, added in trace[:k] if added]
    cur = trace[k - 1] if k else None
    cycle = None
    if cur and not cur[3]:
        tadj: dict = {}
        for u, v, _ in tree:
            tadj.setdefault(u, {})[v] = 1
            tadj.setdefault(v, {})[u] = 1
        _, parent = alg.bfs(tadj, cur[0])
        cycle = alg.reconstruct_path(parent, cur[1])
    return {"k": k, "n_steps": len(trace), "tree": tree, "current": cur, "cycle": cycle,
            "total_km": sum(w for *_, w in tree), "target_edges": ds.G.n_vertices - len(ds.comps)}


def dijkstra_states(adj: dict, source: str) -> list[dict]:
    """Every state of Dijkstra's algorithm from `source`, one per step, for the step-through view.

    State 0 is the start (nothing final yet). In state i, stop `u` has just been moved into S
    (its distance is final) and its links have been relaxed; `updated` lists (stop, new, old)."""
    dist = {v: inf for v in adj}
    dist[source] = 0.0
    parent: dict = {source: None}
    final: list[str] = []
    states = [{"step": 0, "u": None, "final": [], "dist": {source: 0.0}, "parent": {source: None},
               "updated": []}]
    while True:
        cand = [(dist[v], v) for v in adj if v not in final and dist[v] < inf]
        if not cand:
            break
        d, u = min(cand)
        final.append(u)
        updated = []
        for v in sorted(adj[u]):
            if v in final:
                continue
            nd = d + adj[u][v]
            if nd < dist[v] - 1e-12:
                updated.append((v, nd, dist[v]))
                dist[v] = nd
                parent[v] = u
        states.append({"step": len(final), "u": u, "d": d, "final": list(final),
                       "dist": {x: y for x, y in dist.items() if y < inf},
                       "parent": dict(parent), "updated": updated})
    return states
