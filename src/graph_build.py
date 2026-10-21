"""Step 2 of the pipeline: turn the cleaned tables into the graph G = (V, E, w, L).

    V = stops
    E = { {u, v} : u and v are consecutive stops on some route }
    w : E -> R+   distance in km (road distance if given, otherwise haversine)
    L : E -> P(Routes)   the set of routes that use the edge

The graph is stored as an adjacency list, a dict of dicts:  adj[u][v] = w({u, v}).
Because the graph is undirected, adj[u][v] and adj[v][u] always hold the same value.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .data_prep import CleanData
from .geo import haversine_km


@dataclass
class BusGraph:
    adj: dict[str, dict[str, float]]          # adjacency list with weights (km)
    edge_routes: dict[frozenset, set[str]]    # L: edge {u, v} -> set of route IDs
    edge_source: dict[frozenset, str]         # "haversine" or "road"
    stops: pd.DataFrame                       # index stop_id: name_en, lat, lon
    routes: pd.DataFrame                      # index route_id: route_name, ...
    route_seq: dict[str, list[str]]           # route_id -> ordered list of stop_ids

    # ---- small helpers used everywhere
    def name(self, sid: str) -> str:
        return self.stops.loc[sid, "name_en"]

    def names(self, path) -> str:
        return " -> ".join(self.name(s) for s in path) if path else "(no path)"

    def edges(self) -> list[tuple[str, str, float]]:
        """Each undirected edge once, as (u, v, w) with u < v."""
        return sorted((u, v, w) for u in self.adj for v, w in self.adj[u].items() if u < v)

    @property
    def n_vertices(self) -> int:
        return len(self.adj)

    @property
    def n_edges(self) -> int:
        return sum(len(nbrs) for nbrs in self.adj.values()) // 2

    def stop_id(self, name_or_id: str) -> str:
        """Find a stop by ID, official name or alias (case and spacing ignored)."""
        if name_or_id in self.adj:
            return name_or_id
        key = " ".join(name_or_id.split()).casefold()
        for sid, row in self.stops.iterrows():
            spellings = [row["name_en"]] + str(row.get("aliases", "")).split("|")
            if key in {" ".join(s.split()).casefold() for s in spellings if s}:
                return sid
        raise KeyError(f"No stop called '{name_or_id}'")


def build_graph(data: CleanData) -> BusGraph:
    stops = data.stops
    road = {frozenset((r.stop_u, r.stop_v)): float(r.distance_km) for r in data.road_km.itertuples()}

    route_seq = {rid: g.sort_values("seq")["stop_id"].tolist()
                 for rid, g in data.route_stops.groupby("route_id", sort=True)}

    # every stop is a vertex, even if no route uses it (an isolated vertex)
    adj: dict[str, dict[str, float]] = {sid: {} for sid in stops.index}
    edge_routes: dict[frozenset, set[str]] = {}
    edge_source: dict[frozenset, str] = {}

    for rid, seq in route_seq.items():
        for u, v in zip(seq, seq[1:]):          # consecutive pairs of the route
            e = frozenset((u, v))
            if e in road:
                w, src = road[e], "road"
            else:
                w = haversine_km(stops.loc[u, "lat"], stops.loc[u, "lon"],
                                 stops.loc[v, "lat"], stops.loc[v, "lon"])
                src = "haversine"
            if w <= 0:
                raise ValueError(f"Edge {u}-{v} has weight {w}; weights must be positive "
                                 "(two stops share coordinates?)")
            # parallel routes on the same pair: merge into one edge, keep the smallest weight,
            # and remember every route name in L(e)
            if e in edge_routes:
                edge_routes[e].add(rid)
                if w < adj[u][v]:
                    adj[u][v] = adj[v][u] = w
                    edge_source[e] = src
            else:
                edge_routes[e] = {rid}
                edge_source[e] = src
                adj[u][v] = adj[v][u] = w

    return BusGraph(adj=adj, edge_routes=edge_routes, edge_source=edge_source,
                    stops=stops, routes=data.routes, route_seq=route_seq)


def edges_table(G: BusGraph) -> pd.DataFrame:
    rows = []
    for u, v, w in G.edges():
        e = frozenset((u, v))
        rows.append({"u": u, "v": v, "u_name": G.name(u), "v_name": G.name(v),
                     "distance_km": round(w, 3), "weight_source": G.edge_source[e],
                     "routes": ";".join(sorted(G.edge_routes[e]))})
    return pd.DataFrame(rows)


def save_edges(G: BusGraph, processed_dir: Path) -> Path:
    path = Path(processed_dir) / "edges.csv"
    edges_table(G).to_csv(path, index=False)
    return path


def handshake_check(adj: dict) -> tuple[int, int, bool]:
    """Handshaking theorem: sum of degrees = 2|E|. Returns (sum_deg, 2|E|, holds).

    |E| is counted independently of the degrees (as a set of unordered pairs),
    so the check can catch an adjacency list that is not symmetric.
    """
    sum_deg = sum(len(nbrs) for nbrs in adj.values())
    edge_set = {frozenset((u, v)) for u in adj for v in adj[u]}
    symmetric = all(u in adj[v] for u in adj for v in adj[u])
    return sum_deg, 2 * len(edge_set), (sum_deg == 2 * len(edge_set)) and symmetric


def route_graph(G: BusGraph) -> dict[str, dict[str, set[str]]]:
    """The second view: one vertex per route, an edge when two routes share a stop.

    radj[r1][r2] = set of shared stops = stops(r1) ∩ stops(r2)   (a set intersection, Ch 2)
    """
    stop_sets = {r: set(seq) for r, seq in G.route_seq.items()}
    radj: dict[str, dict[str, set[str]]] = {r: {} for r in stop_sets}
    rids = sorted(stop_sets)
    for i, a in enumerate(rids):
        for b in rids[i + 1:]:
            shared = stop_sets[a] & stop_sets[b]
            if shared:
                radj[a][b] = shared
                radj[b][a] = shared
    return radj


def to_networkx(G: BusGraph):
    """A NetworkX copy of the graph, used only to cross-check our own algorithms and to draw."""
    import networkx as nx
    H = nx.Graph()
    for sid, row in G.stops.iterrows():
        H.add_node(sid, name=row["name_en"], pos=(row["lon"], row["lat"]))
    for u, v, w in G.edges():
        H.add_edge(u, v, weight=w)
    return H
