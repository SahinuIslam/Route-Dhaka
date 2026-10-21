"""Step 4: run every analysis on one graph and write the results.

`run_analysis` prints a readable report to the terminal and writes the same
report to results/<dataset>/summary.md, plus CSV tables and figures.
Every number in your report should come from these files.
"""
from __future__ import annotations

from collections import Counter
from math import comb, inf
from pathlib import Path

import pandas as pd

from . import algorithms as alg
from . import relations_logic as rl
from . import visualize as viz
from .graph_build import BusGraph, edges_table, handshake_check, route_graph, to_networkx


class Report:
    """Collects markdown lines; prints them as it goes."""

    def __init__(self, echo: bool = True):
        self.lines: list[str] = []
        self.echo = echo

    def __call__(self, text: str = ""):
        self.lines.append(text)
        if self.echo:
            print(text)

    def table(self, df: pd.DataFrame, max_rows: int = 30):
        shown = df.head(max_rows)
        cols = list(shown.columns)
        self("| " + " | ".join(cols) + " |")
        self("|" + "---|" * len(cols))
        for _, row in shown.iterrows():
            self("| " + " | ".join(_fmt(row[c]) for c in cols) + " |")
        if len(df) > max_rows:
            self(f"\n_({len(df) - max_rows} more rows in the CSV file)_")
        self()

    def save(self, path: Path):
        Path(path).write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def _fmt(x):
    if isinstance(x, float):
        return f"{x:.2f}"
    return str(x)


def _pieces_after_removal(adj, v):
    """Sizes of the pieces that v's neighbours fall into once v is deleted."""
    sub = {u: {w: d for w, d in nb.items() if w != v} for u, nb in adj.items() if u != v}
    pieces = []
    seen = set()
    for n in sorted(adj[v]):
        if n in seen:
            continue
        reach, _ = alg.bfs(sub, n)
        seen |= set(reach)
        pieces.append(set(reach))
    return sorted(pieces, key=len, reverse=True)


def _tree_path_max(tree_adj, u, v):
    """Largest edge weight on the unique tree path u -> v (None if not in the same tree)."""
    _, parent = alg.bfs(tree_adj, u)
    path = alg.reconstruct_path(parent, v)
    if path is None:
        return None
    return max(tree_adj[a][b] for a, b in zip(path, path[1:]))


def changes_from(radj, route_seq, s):
    """Fewest bus changes from stop s to every stop (multi-source BFS on the route graph)."""
    start = [r for r, seq in route_seq.items() if s in seq]
    if not start:
        return {}
    rdist = {r: 0 for r in start}
    q = list(start)
    i = 0
    while i < len(q):
        r = q[i]
        i += 1
        for nxt in radj[r]:
            if nxt not in rdist:
                rdist[nxt] = rdist[r] + 1
                q.append(nxt)
    best = {}
    for r, d in rdist.items():
        for t in route_seq[r]:
            if d < best.get(t, inf):
                best[t] = d
    return best


def run_analysis(G: BusGraph, data, dataset: str, pairs: pd.DataFrame, out_dir: Path,
                 make_figures: bool = True, echo: bool = True) -> dict:
    out_dir = Path(out_dir)
    fig_dir = out_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    R = Report(echo)
    res: dict = {}
    adj = G.adj
    small = G.n_vertices <= 20

    R(f"# Results: {dataset}")
    R()

    # ------------------------------------------------------------ 1. data
    R("## 1. Data")
    R()
    n_entries = len(data.route_stops)
    R(f"- {len(G.stops)} stops, {len(G.routes)} routes, {n_entries} route-stop entries.")
    conf = Counter(G.routes["confidence"]) if "confidence" in G.routes else Counter()
    if conf:
        R("- Route confidence: " + ", ".join(f"{k}: {v}" for k, v in sorted(conf.items())) + ".")
    if conf.get("unverified"):
        R(f"- **{conf['unverified']} routes are still unverified.** Results describe this data set; "
          "check the routes before claiming they describe the city.")
    R(f"- Cleaning mapped {len(data.notes)} written names to their official stop (see cleaning_log.txt).")
    (out_dir / "cleaning_log.txt").write_text("\n".join(data.notes) + "\n", encoding="utf-8")
    R()
    R("Validation rules (each is a proposition the program checks):")
    R()
    for r in data.rule_results:
        status = "holds" if r.holds else ("warning" if r.is_warning else "FAILS")
        R(f"- {r.code}: {r.statement} — **{status}**")
        for c in r.counterexamples[:5]:
            R(f"    - {c}")
    R()

    # ------------------------------------------------------------ 2. size
    V, E = G.n_vertices, G.n_edges
    sum_deg, two_e, ok = handshake_check(adj)
    possible = comb(V, 2)
    parallel = sum(1 for rs in G.edge_routes.values() if len(rs) > 1)
    R("## 2. Size of the graph")
    R()
    R(f"- |V| = {V} stops, |E| = {E} links.")
    R(f"- Links used by more than one route (parallel routes merged into one edge): {parallel}.")
    R(f"- Handshaking theorem: sum of degrees = {sum_deg}, 2|E| = {two_e} → "
      f"{'holds' if ok else 'FAILS (bug!)'}.")
    R(f"- Possible stop pairs C({V}, 2) = {possible}; density = |E| / C(|V|, 2) = {E / possible:.4f} "
      f"(a sparse graph, so an adjacency list is the right structure).")
    edge_df = edges_table(G)
    total_km = float(edge_df["distance_km"].sum())
    R(f"- Total length of all links = {total_km:.2f} km "
      f"({(edge_df['weight_source'] == 'road').sum()} road distances, "
      f"{(edge_df['weight_source'] == 'haversine').sum()} straight-line distances).")
    R()
    res.update(V=V, E=E, density=E / possible, handshake=ok, total_km=total_km)

    # ------------------------------------------------------------ 3. degrees
    ds = alg.degree_stats(adj)
    n_routes_at = Counter(s for seq in G.route_seq.values() for s in set(seq))
    deg_df = pd.DataFrame([{"stop_id": s, "name": G.name(s), "degree": len(adj[s]),
                            "routes_serving": n_routes_at.get(s, 0)} for s in adj])
    deg_df = deg_df.sort_values(["degree", "routes_serving", "stop_id"], ascending=[False, False, True])
    deg_df.to_csv(out_dir / "degrees.csv", index=False)
    R("## 3. Degrees")
    R()
    R(f"- Degree: min {ds['min']}, max {ds['max']}, mean {ds['mean']:.2f}, median {ds['median']}; "
      f"{ds['leaves (degree 1)']} end stops (degree 1), {ds['isolated (degree 0)']} isolated stops.")
    R()
    R("Busiest stops (most directly linked stops):")
    R()
    R.table(deg_df.head(10))
    res["degree_stats"] = ds

    # ------------------------------------------------------------ 4. connectivity
    comps = alg.connected_components(adj)
    holds, witness = rl.connectivity_by_quantifiers(adj)
    largest = comps[0]
    R("## 4. Connectivity")
    R()
    R(f"- Statement checked: ∀u ∀v (there is a path from u to v). Result: **{holds}**.")
    if witness:
        R(f"- Witness for the negation ∃u ∃v ¬path(u, v): {G.name(witness[0])} and {G.name(witness[1])}.")
    R(f"- Connected components: **{len(comps)}**. Largest: {len(largest)} stops "
      f"({100 * len(largest) / V:.1f}% of all stops).")
    for i, c in enumerate(comps[1:], start=2):
        R(f"- Component {i}: " + ", ".join(G.name(s) for s in sorted(c)))
    rows = [{"component": i + 1, "stop_id": s, "name": G.name(s)}
            for i, c in enumerate(comps) for s in sorted(c)]
    pd.DataFrame(rows).to_csv(out_dir / "components.csv", index=False)

    if V <= 150:
        order = sorted(adj)
        M = rl.adjacency_matrix(adj, order)
        W = rl.warshall(M)
        refl, sym, trans = rl.is_reflexive(W), rl.is_symmetric(W), rl.is_transitive(W)
        classes = rl.equivalence_classes(W, order)
        same = sorted(map(sorted, classes)) == sorted(map(sorted, comps))
        R(f"- \"Directly linked\" relation is symmetric: {rl.is_symmetric(M)}.")
        R(f"- Warshall closure of \"can reach\": reflexive {refl}, symmetric {sym}, transitive {trans} "
          f"→ an equivalence relation with {len(classes)} class(es); "
          f"classes equal the BFS components: {same}.")
    R()
    res.update(components=len(comps), largest=len(largest), connected=holds)

    # ------------------------------------------------------------ 5. resilience
    cuts = alg.cut_vertices(adj)
    brs = alg.bridges(adj)
    R("## 5. Weak points: cut vertices and bridges")
    R()
    R(f"- **{len(cuts)} cut vertices** (a stop whose removal disconnects part of the network) and "
      f"**{len(brs)} bridges** (a link with the same effect).")
    cut_rows = []
    for v in cuts:
        pieces = _pieces_after_removal(adj, v)
        cut_off = sum(len(p) for p in pieces[1:])
        small_side = sorted({G.name(s) for p in pieces[1:] for s in p})
        cut_rows.append({"stop_id": v, "name": G.name(v), "pieces_after_removal": len(pieces),
                         "stops_cut_off": cut_off,
                         "cut_off_stops": ", ".join(small_side[:8]) + (" ..." if len(small_side) > 8 else "")})
    cut_df = pd.DataFrame(cut_rows, columns=["stop_id", "name", "pieces_after_removal",
                                             "stops_cut_off", "cut_off_stops"])
    if len(cut_df):
        cut_df = cut_df.sort_values(["stops_cut_off", "stop_id"], ascending=[False, True])
    cut_df.to_csv(out_dir / "cut_vertices.csv", index=False)
    br_df = pd.DataFrame([{"u": u, "v": v, "u_name": G.name(u), "v_name": G.name(v),
                           "distance_km": round(adj[u][v], 3)} for u, v in brs])
    br_df.to_csv(out_dir / "bridges.csv", index=False)
    if len(cut_df):
        R()
        R("Cut vertices, by how many stops they would cut off:")
        R()
        R.table(cut_df[["name", "pieces_after_removal", "stops_cut_off", "cut_off_stops"]], max_rows=15)
    res.update(cut_vertices=len(cuts), bridges=len(brs))

    # ------------------------------------------------------------ 6. shortest paths
    radj = route_graph(G)
    R("## 6. Shortest paths for chosen stop pairs")
    R()
    R("Fewest stops = BFS (every link counts 1). Shortest distance = Dijkstra (weights in km). "
      "Fewest bus changes = BFS on the route graph.")
    R()
    sp_rows = []
    showcase = None
    for _, row in pairs.iterrows():
        try:
            s, t = G.stop_id(row["from_stop"]), G.stop_id(row["to_stop"])
        except KeyError as e:
            R(f"- Skipped pair {row['from_stop']} → {row['to_stop']}: {e}")
            continue
        hp = alg.fewest_hops_path(adj, s, t)
        dkm, dp = alg.shortest_distance_path(adj, s, t)
        R(f"### {G.name(s)} → {G.name(t)}")
        R()
        if hp is None:
            R("- No path: the two stops are in different components.")
            R()
            sp_rows.append({"from": G.name(s), "to": G.name(t), "reachable": False})
            continue
        hkm = alg.path_length_km(adj, hp)
        bc = alg.fewest_bus_changes(radj, G.route_seq, s, t)
        R(f"- Fewest stops: {len(hp) - 1} hops, {hkm:.2f} km: {G.names(hp)}")
        R(f"- Shortest distance: {len(dp) - 1} hops, {dkm:.2f} km: {G.names(dp)}")
        same = hp == dp
        R(f"- Same path? {'yes' if same else 'no'}.")
        if bc:
            n_ch, rseq = bc
            hops_txt = []
            for a, b in zip(rseq, rseq[1:]):
                shared = sorted(G.name(x) for x in radj[a][b])
                hops_txt.append(f"{a}→{b} at " + (", ".join(shared[:3]) + (" ..." if len(shared) > 3 else "")))
            R(f"- Fewest bus changes: **{n_ch}** (routes {' → '.join(rseq)})"
              + (f"; change {'; '.join(hops_txt)}" if hops_txt else "; one bus does the whole trip"))
        R()
        sp_rows.append({"from": G.name(s), "to": G.name(t), "reachable": True,
                        "fewest_hops": len(hp) - 1, "fewest_hops_km": round(hkm, 3),
                        "shortest_km": round(dkm, 3), "shortest_km_hops": len(dp) - 1,
                        "same_path": same, "bus_changes": bc[0] if bc else None,
                        "routes": " > ".join(bc[1]) if bc else "",
                        "hop_path": " > ".join(G.name(x) for x in hp),
                        "distance_path": " > ".join(G.name(x) for x in dp)})
        if showcase is None or (not same and showcase[3]):
            showcase = (s, t, (hp, dp), same)
    pd.DataFrame(sp_rows).to_csv(out_dir / "shortest_paths.csv", index=False)

    # automatic examples where the two criteria disagree
    ex = alg.hops_vs_distance_examples(adj, largest, k=5)
    R("### Where \"fewest stops\" and \"shortest distance\" disagree")
    R()
    if not ex:
        R("- In this graph the fewest-stop path is never longer in km than necessary.")
    for e in ex[:3]:
        R(f"- {G.name(e['from'])} → {G.name(e['to'])}: fewest stops = {len(e['hop_path']) - 1} hops but "
          f"{e['hop_km']:.2f} km; shortest = {len(e['dist_path']) - 1} hops, {e['dist_km']:.2f} km "
          f"(+{e['extra_km']:.2f} km for the fewest-stop path).")
    R()
    if ex and (showcase is None or showcase[3]):
        e = ex[0]
        showcase = (e["from"], e["to"], (e["hop_path"], e["dist_path"]), False)

    # hand-trace table of Dijkstra for the first pair (useful for the sample)
    if len(pairs):
        try:
            s0 = G.stop_id(pairs.iloc[0]["from_stop"])
            trace = pd.DataFrame(alg.dijkstra_trace(adj, s0, G.name))
            trace.to_csv(out_dir / "dijkstra_trace.csv", index=False)
            if small:
                R(f"### Dijkstra step by step from {G.name(s0)} (compare with your hand trace)")
                R()
                R.table(trace)
        except KeyError:
            pass

    # ------------------------------------------------------------ 7. network-wide
    hs = alg.hop_summary(adj, largest)
    dsum = alg.distance_summary(adj, largest)
    R("## 7. How compact is the network? (largest component)")
    R()
    R(f"- Average shortest path: {hs['average_hops']:.2f} hops, {dsum['average_km']:.2f} km.")
    a, b = hs["diameter_ends"]
    R(f"- Diameter: {hs['diameter_hops']} hops (e.g. {G.name(a)} ↔ {G.name(b)}).")
    a, b = dsum["diameter_ends"]
    R(f"- Longest shortest distance: {dsum['diameter_km']:.2f} km ({G.name(a)} ↔ {G.name(b)}).")
    R(f"- Centre (smallest eccentricity, {hs['radius_hops']} hops): "
      + ", ".join(G.name(s) for s in hs["centre"]) + ".")
    # bus changes over all pairs
    dist_changes = Counter()
    for s in sorted(largest):
        best = changes_from(radj, G.route_seq, s)
        for t in largest:
            if t > s and t in best:
                dist_changes[best[t]] += 1
    tot = sum(dist_changes.values())
    if tot:
        R("- Bus changes needed over all stop pairs: "
          + ", ".join(f"{k} change{'s' if k != 1 else ''}: {100 * v / tot:.1f}%"
                      for k, v in sorted(dist_changes.items())) + ".")
    R(f"- Route graph: {len(radj)} routes, {sum(len(n) for n in radj.values()) // 2} pairs of routes "
      f"that share at least one stop.")
    R()
    res.update(avg_hops=hs["average_hops"], diameter_hops=hs["diameter_hops"],
               avg_km=dsum["average_km"], changes=dict(dist_changes))

    # ------------------------------------------------------------ 8. MST
    ktrace: list = []
    k_edges = alg.kruskal(adj, trace=ktrace)
    p_edges = alg.prim(adj)
    kw, pw = alg.total_weight(k_edges), alg.total_weight(p_edges)
    forest_ok = alg.is_forest(V, k_edges, len(comps))
    tree_adj = {v: {} for v in adj}
    for u, v, w in k_edges:
        tree_adj[u][v] = tree_adj[v][u] = w
    tree_set = {frozenset((u, v)) for u, v, _ in k_edges}
    non_tree = [(u, v, w) for u, v, w in G.edges() if frozenset((u, v)) not in tree_set]
    cycle_ok = all(w >= _tree_path_max(tree_adj, u, v) - 1e-9 for u, v, w in non_tree)
    R("## 8. Minimum spanning tree (the backbone)")
    R()
    R(f"- Kruskal: {len(k_edges)} edges, total {kw:.2f} km. Prim: {len(p_edges)} edges, total {pw:.2f} km. "
      f"Same total: {abs(kw - pw) < 1e-6}.")
    R(f"- Edge count = |V| − c = {V} − {len(comps)} = {V - len(comps)}: {len(k_edges) == V - len(comps)}; "
      f"acyclic forest: {forest_ok}.")
    R(f"- Full network {total_km:.2f} km vs tree {kw:.2f} km: the {len(non_tree)} links left out "
      f"({total_km - kw:.2f} km, {100 * (total_km - kw) / total_km:.1f}% of the length) are redundancy.")
    R(f"- Cycle property check: every left-out link is at least as heavy as every tree link on the cycle "
      f"it would close: {cycle_ok}.")
    heavy = sorted(k_edges, key=lambda e: -e[2])[:3]
    R("- Longest tree links: " + "; ".join(f"{G.name(u)}–{G.name(v)} {w:.2f} km" for u, v, w in heavy) + ".")
    R("- Reading: the tree is the cheapest set of links that keeps every stop reachable. "
      "It is not a proposal for bus routes: trips along the tree can be much longer than on the full network.")
    R()
    mst_df = pd.DataFrame([{"u": u, "v": v, "u_name": G.name(u), "v_name": G.name(v),
                            "distance_km": round(w, 3)} for u, v, w in k_edges])
    mst_df.to_csv(out_dir / "mst_edges.csv", index=False)
    kt_df = pd.DataFrame([{"order": i + 1, "edge": f"{G.name(u)} – {G.name(v)}", "km": round(w, 2),
                           "decision": "added" if added else "skipped (would close a cycle)"}
                          for i, (u, v, w, added) in enumerate(ktrace)])
    kt_df.to_csv(out_dir / "kruskal_trace.csv", index=False)
    if small:
        R("### Kruskal step by step")
        R()
        R.table(kt_df)
    res.update(mst_km=kw, prim_km=pw, mst_edges=len(k_edges))

    # ------------------------------------------------------------ 9. counting
    R("## 9. Counting (Chapter 6)")
    R()
    R(f"- Stop pairs: C({V}, 2) = {possible}; actual links {E}; so {100 * E / possible:.2f}% of pairs are linked.")
    multi = sorted(((n, s) for s, n in n_routes_at.items() if n >= 2), reverse=True)
    if multi:
        top = multi[:3]
        R("- Product rule: at a stop served by k routes a rider can change from any route to any other, "
          "k·(k−1) ordered choices. " + "; ".join(f"{G.name(s)}: k={n}, {n * (n - 1)} choices" for n, s in top) + ".")
        R(f"- Transfer stops (served by 2 or more routes): {len(multi)} of {V}.")
    loops = [r for r, seq in G.route_seq.items() if len(seq) > len(set(seq))]
    if loops:
        r = loops[0]
        R(f"- Pigeonhole: route {r} lists {len(G.route_seq[r])} stops but only {len(set(G.route_seq[r]))} "
          "distinct ones, so some stop must repeat (it is a loop route).")
    R()

    # ------------------------------------------------------------ 10. cross-check
    import networkx as nx
    H = to_networkx(G)
    checks = {
        "components": sorted(map(sorted, nx.connected_components(H))) == sorted(map(sorted, comps)),
        "cut vertices": set(nx.articulation_points(H)) == set(cuts),
        "bridges": {frozenset(e) for e in nx.bridges(H)} == {frozenset(e) for e in brs},
        "MST weight": abs(sum(d["weight"] for *_, d in nx.minimum_spanning_edges(H, data=True)) - kw) < 1e-6,
    }
    s_any = sorted(largest)[0]
    nd = nx.single_source_dijkstra_path_length(H, s_any)
    md, _ = alg.dijkstra(adj, s_any)
    checks["Dijkstra distances"] = all(abs(nd[v] - md[v]) < 1e-9 for v in nd) and set(nd) == set(md)
    nh = nx.single_source_shortest_path_length(H, s_any)
    mh, _ = alg.bfs(adj, s_any)
    checks["BFS hop counts"] = nh == mh
    R("## 10. Cross-check against NetworkX")
    R()
    for k, v in checks.items():
        R(f"- {k}: {'matches' if v else 'DIFFERENT — look for a bug'}")
    R()
    res["crosscheck"] = checks

    # ------------------------------------------------------------ figures
    if make_figures:
        label = {"sample": "Sample", "dhaka": "Dhaka core", "osm": "OSM"}.get(dataset, dataset)
        figs = [viz.plot_network(G, comps, fig_dir / "network.png", f"{label}: stop graph "
                                 f"({V} stops, {E} links)"),
                viz.plot_degree_histogram(G, fig_dir / "degree_histogram.png"),
                viz.plot_cut_points(G, cuts, brs, fig_dir / "cut_points.png",
                                    f"{label}: cut vertices and bridges"),
                viz.plot_mst(G, k_edges, fig_dir / "mst.png",
                             f"{label}: minimum spanning tree ({kw:.1f} km of {total_km:.1f} km)")]
        if showcase:
            s, t, (hp, dp), _ = showcase
            figs.append(viz.plot_paths(G, hp, dp, fig_dir / "shortest_path.png",
                                       f"{G.name(s)} → {G.name(t)}: fewest stops vs shortest distance"))
        m = viz.make_map(G, out_dir / "map.html", mst_edges=k_edges,
                         path=showcase[2][1] if showcase else None, cuts=cuts)
        R("## Figures")
        R()
        for f in figs:
            R(f"- figures/{Path(f).name}")
        if m:
            R("- map.html (open in a browser)")
        R()

    R.save(out_dir / "summary.md")
    res["report_path"] = out_dir / "summary.md"
    return res
