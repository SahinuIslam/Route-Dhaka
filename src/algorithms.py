"""Step 3: the algorithms, written by hand (Chapters 10 and 11).

Every function takes a graph as an adjacency dict  adj[u] -> {v: weight}
and returns a plain result, so the same code runs on the 11-stop sample
and on the Dhaka network. Neighbours are visited in sorted order so the
output is the same on every run.
"""
from __future__ import annotations

import heapq
from collections import deque
from math import inf

Adj = dict  # adj[u][v] = weight


# =====================================================================
# Breadth-first search (Section 10.4) — connectivity and fewest hops
# =====================================================================

def bfs(adj: Adj, source: str) -> tuple[dict[str, int], dict[str, str | None]]:
    """Return (hops, parent). hops[v] = number of edges on a fewest-edge path source -> v.

    Every edge counts as 1, so the first time BFS reaches v is along a fewest-hop path.
    Time O(V + E): each vertex enters the queue once and each edge is looked at twice.
    """
    hops = {source: 0}
    parent: dict[str, str | None] = {source: None}
    queue = deque([source])
    while queue:
        u = queue.popleft()
        for v in sorted(adj[u]):
            if v not in hops:
                hops[v] = hops[u] + 1
                parent[v] = u
                queue.append(v)
    return hops, parent


def reconstruct_path(parent: dict, target: str) -> list[str] | None:
    """Follow parent pointers back from target to the source."""
    if target not in parent:
        return None
    path = []
    v = target
    while v is not None:
        path.append(v)
        v = parent[v]
    return path[::-1]


def fewest_hops_path(adj: Adj, s: str, t: str) -> list[str] | None:
    _, parent = bfs(adj, s)
    return reconstruct_path(parent, t)


def connected_components(adj: Adj) -> list[set[str]]:
    """Run BFS from each unvisited vertex; each run collects one component.

    Components are the equivalence classes of the relation "can reach" (Chapter 9).
    Returned largest first.
    """
    seen: set[str] = set()
    comps: list[set[str]] = []
    for s in sorted(adj):
        if s in seen:
            continue
        hops, _ = bfs(adj, s)
        comp = set(hops)
        seen |= comp
        comps.append(comp)
    comps.sort(key=lambda c: (-len(c), min(c)))
    return comps


def dfs_recursive(adj: Adj, u: str, visited: set[str] | None = None) -> set[str]:
    """Depth-first search written recursively (Chapter 5): visit u, then recurse on
    each unvisited neighbour. Returns the set of vertices reachable from u."""
    if visited is None:
        visited = set()
    visited.add(u)
    for v in sorted(adj[u]):
        if v not in visited:
            dfs_recursive(adj, v, visited)
    return visited


def _count_components(adj: Adj, skip_vertex: str | None = None,
                      skip_edge: frozenset | None = None) -> int:
    """Number of components after deleting one vertex or one edge (BFS that ignores it)."""
    seen: set[str] = set()
    count = 0
    for s in adj:
        if s == skip_vertex or s in seen:
            continue
        count += 1
        seen.add(s)
        queue = deque([s])
        while queue:
            u = queue.popleft()
            for v in adj[u]:
                if v == skip_vertex or v in seen:
                    continue
                if skip_edge is not None and frozenset((u, v)) == skip_edge:
                    continue
                seen.add(v)
                queue.append(v)
    return count


def cut_vertices(adj: Adj) -> list[str]:
    """Stops whose removal increases the number of components.
    Simple method: delete each vertex in turn and recount. O(V (V + E))."""
    base = _count_components(adj)
    return [v for v in sorted(adj) if _count_components(adj, skip_vertex=v) > base]


def bridges(adj: Adj) -> list[tuple[str, str]]:
    """Edges whose removal increases the number of components. O(E (V + E))."""
    base = _count_components(adj)
    out = []
    for u in sorted(adj):
        for v in sorted(adj[u]):
            if u < v and _count_components(adj, skip_edge=frozenset((u, v))) > base:
                out.append((u, v))
    return out


# =====================================================================
# Dijkstra's algorithm (Section 10.6) — shortest distance
# =====================================================================

def dijkstra(adj: Adj, source: str) -> tuple[dict[str, float], dict[str, str | None]]:
    """Return (dist, parent). Requires non-negative weights.

    S = set of vertices whose distance is final. Each step moves the outside vertex
    with the smallest tentative distance into S (heap pop), then relaxes its edges:
    if dist[u] + w(u, v) < dist[v], improve dist[v].  Time O((V + E) log V).
    """
    dist = {source: 0.0}
    parent: dict[str, str | None] = {source: None}
    final: set[str] = set()                      # the set S
    heap = [(0.0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if u in final:
            continue                             # an old, out-of-date heap entry
        final.add(u)
        for v in sorted(adj[u]):
            w = adj[u][v]
            if w < 0:
                raise ValueError("Dijkstra's algorithm needs non-negative weights")
            nd = d + w
            if nd < dist.get(v, inf) - 1e-12:
                dist[v] = nd
                parent[v] = u
                heapq.heappush(heap, (nd, v))
    return dist, parent


def shortest_distance_path(adj: Adj, s: str, t: str) -> tuple[float, list[str] | None]:
    dist, parent = dijkstra(adj, s)
    return dist.get(t, inf), reconstruct_path(parent, t)


def path_length_km(adj: Adj, path: list[str]) -> float:
    """Cost of a path = sum of w over its edges (a summation, Chapter 2)."""
    return sum(adj[a][b] for a, b in zip(path, path[1:]))


def dijkstra_trace(adj: Adj, source: str, name=lambda s: s) -> list[dict]:
    """Same algorithm, but records each step, so you can compare with a hand trace."""
    dist = {v: inf for v in adj}
    dist[source] = 0.0
    final: list[str] = []
    steps = []
    while len(final) < len(adj):
        candidates = [(dist[v], v) for v in adj if v not in final and dist[v] < inf]
        if not candidates:
            break
        d, u = min(candidates)
        final.append(u)
        updated = []
        for v in sorted(adj[u]):
            if v not in final and d + adj[u][v] < dist[v] - 1e-12:
                dist[v] = d + adj[u][v]
                updated.append(f"{name(v)}={dist[v]:.2f}")
        steps.append({"step": len(final), "moved_into_S": name(u), "distance_km": round(d, 2),
                      "updated": ", ".join(updated) or "-"})
    return steps


# =====================================================================
# Network-wide numbers
# =====================================================================

def degree_stats(adj: Adj) -> dict:
    degs = sorted(len(n) for n in adj.values())
    n = len(degs)
    return {"min": degs[0], "max": degs[-1], "mean": sum(degs) / n,
            "median": (degs[n // 2] if n % 2 else (degs[n // 2 - 1] + degs[n // 2]) / 2),
            "leaves (degree 1)": degs.count(1), "isolated (degree 0)": degs.count(0)}


def hop_summary(adj: Adj, component: set[str]) -> dict:
    """BFS from every stop of one component: average shortest-path length (in hops),
    diameter (longest shortest path), its end points, and the centre (smallest eccentricity)."""
    sub = {u: {v: w for v, w in adj[u].items() if v in component} for u in component}
    total, pairs = 0, 0
    ecc = {}
    best = (-1, None, None)
    for s in sorted(sub):
        hops, _ = bfs(sub, s)
        ecc[s] = max(hops.values())
        for t, h in hops.items():
            if t > s:
                total += h
                pairs += 1
                if h > best[0]:
                    best = (h, s, t)
    radius = min(ecc.values())
    return {"average_hops": total / pairs if pairs else 0.0, "diameter_hops": best[0],
            "diameter_ends": (best[1], best[2]), "radius_hops": radius,
            "centre": sorted(v for v, e in ecc.items() if e == radius)}


def distance_summary(adj: Adj, component: set[str]) -> dict:
    """Dijkstra from every stop: average shortest distance and weighted diameter (km)."""
    sub = {u: {v: w for v, w in adj[u].items() if v in component} for u in component}
    total, pairs = 0.0, 0
    best = (-1.0, None, None)
    for s in sorted(sub):
        dist, _ = dijkstra(sub, s)
        for t, d in dist.items():
            if t > s:
                total += d
                pairs += 1
                if d > best[0]:
                    best = (d, s, t)
    return {"average_km": total / pairs if pairs else 0.0, "diameter_km": best[0],
            "diameter_ends": (best[1], best[2])}


def hops_vs_distance_examples(adj: Adj, component: set[str], k: int = 5) -> list[dict]:
    """Pairs where the fewest-hop path (BFS) is strictly shorter in stops but longer in km
    than the shortest-distance path (Dijkstra). Sorted by the extra km, largest first."""
    out = []
    for s in sorted(component):
        hops, hpar = bfs(adj, s)
        dist, dpar = dijkstra(adj, s)
        for t in sorted(component):
            if t <= s:
                continue
            hp = reconstruct_path(hpar, t)
            dp = reconstruct_path(dpar, t)
            h_km = path_length_km(adj, hp)
            if len(hp) < len(dp) and h_km > dist[t] + 1e-9:
                out.append({"from": s, "to": t, "hop_path": hp, "hop_km": h_km,
                            "dist_path": dp, "dist_km": dist[t], "extra_km": h_km - dist[t]})
    out.sort(key=lambda r: -r["extra_km"])
    return out[:k]


# =====================================================================
# Route graph — fewest bus changes
# =====================================================================

def fewest_bus_changes(radj: dict, route_seq: dict[str, list[str]], s: str, t: str):
    """BFS on the route graph, starting from every route that serves s at once.

    Returns (changes, [r1, r2, ...]) or None. Taking routes r1, r2, ..., rk means
    k - 1 changes of bus. 0 changes means one bus goes from s to t.
    """
    start = sorted(r for r, seq in route_seq.items() if s in seq)
    goal = {r for r, seq in route_seq.items() if t in seq}
    if not start or not goal:
        return None
    parent: dict[str, str | None] = {r: None for r in start}
    queue = deque(start)
    while queue:
        r = queue.popleft()
        if r in goal:
            path = reconstruct_path(parent, r)
            return len(path) - 1, path
        for nxt in sorted(radj[r]):
            if nxt not in parent:
                parent[nxt] = r
                queue.append(nxt)
    return None


# =====================================================================
# Minimum spanning tree (Sections 11.4, 11.5)
# =====================================================================

class UnionFind:
    """Disjoint sets with union by rank and path halving. find(x) gives the set's root."""

    def __init__(self, items):
        self.parent = {x: x for x in items}
        self.rank = {x: 0 for x in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b) -> bool:
        """Join the sets of a and b. Returns False if they were already one set
        (adding the edge a-b would then close a cycle)."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True


def kruskal(adj: Adj, trace: list | None = None) -> list[tuple[str, str, float]]:
    """Sort edges by weight; add each edge unless it closes a cycle.
    On a disconnected graph this gives a minimum spanning FOREST with V - c edges.
    Time O(E log E)."""
    edges = sorted(((w, u, v) for u in adj for v, w in adj[u].items() if u < v))
    uf = UnionFind(adj)
    tree = []
    for w, u, v in edges:
        added = uf.union(u, v)
        if added:
            tree.append((u, v, w))
        if trace is not None:
            trace.append((u, v, w, added))
    return tree


def prim(adj: Adj) -> list[tuple[str, str, float]]:
    """Grow a tree from one stop by always adding the cheapest edge that leaves it.
    Restarts from an unvisited stop for each further component (spanning forest).
    Time O(E log V)."""
    in_tree: set[str] = set()
    tree = []
    for start in sorted(adj):
        if start in in_tree:
            continue
        in_tree.add(start)
        heap = [(w, start, v) for v, w in adj[start].items()]
        heapq.heapify(heap)
        while heap:
            w, u, v = heapq.heappop(heap)
            if v in in_tree:
                continue
            in_tree.add(v)
            tree.append((u, v, w) if u < v else (v, u, w))
            for x, wx in adj[v].items():
                if x not in in_tree:
                    heapq.heappush(heap, (wx, v, x))
    return tree


def total_weight(edges) -> float:
    return sum(w for _, _, w in edges)


def is_forest(n_vertices: int, edges, n_components: int) -> bool:
    """A forest on n vertices with c trees has exactly n - c edges and no cycle."""
    uf = UnionFind({x for e in edges for x in e[:2]})
    for u, v, _ in edges:
        if not uf.union(u, v):
            return False
    return len(edges) == n_vertices - n_components
