"""Cross-checks: every hand-written algorithm must agree with NetworkX.

Run with:  pytest            (from the project folder)
Each test builds graphs three ways: the 11-stop sample, the Dhaka data set,
and random graphs (connected and disconnected) so that edge cases are covered.
"""
import random
from math import isclose
from pathlib import Path

import networkx as nx
import pytest

from src import algorithms as alg
from src import relations_logic as rl
from src.data_prep import prepare
from src.graph_build import build_graph, handshake_check, route_graph, to_networkx

ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    G = build_graph(prepare(ROOT / "data" / name, verbose=False))
    return G.adj, to_networkx(G)


def _random(seed, n=30, m=40):
    rnd = random.Random(seed)
    H = nx.gnm_random_graph(n, m, seed=seed)
    H = nx.relabel_nodes(H, {i: f"v{i:02d}" for i in H})
    for u, v in H.edges():
        H[u][v]["weight"] = round(rnd.uniform(0.2, 5.0), 3)
    adj = {u: {v: H[u][v]["weight"] for v in H[u]} for u in H}
    return adj, H


CASES = [("sample",), ("dhaka",)] + [(f"random{s}",) for s in range(6)]


@pytest.fixture(params=[c[0] for c in CASES])
def graph(request):
    name = request.param
    if name.startswith("random"):
        s = int(name[6:])
        # seeds 0-2: sparse (usually disconnected); seeds 3-5: denser
        return _random(s, n=30, m=25 if s < 3 else 60)
    return _load(name)


def test_handshake(graph):
    adj, H = graph
    sum_deg, two_e, ok = handshake_check(adj)
    assert ok and sum_deg == 2 * H.number_of_edges()


def test_components(graph):
    adj, H = graph
    ours = sorted(map(sorted, alg.connected_components(adj)))
    theirs = sorted(map(sorted, nx.connected_components(H)))
    assert ours == theirs


def test_recursive_dfs_matches_bfs(graph):
    adj, _ = graph
    for s in list(adj)[:10]:
        hops, _ = alg.bfs(adj, s)
        assert alg.dfs_recursive(adj, s) == set(hops)


def test_bfs_hops(graph):
    adj, H = graph
    for s in sorted(adj)[:15]:
        hops, _ = alg.bfs(adj, s)
        assert hops == nx.single_source_shortest_path_length(H, s)


def test_dijkstra(graph):
    adj, H = graph
    for s in sorted(adj)[:15]:
        ours, parent = alg.dijkstra(adj, s)
        theirs = nx.single_source_dijkstra_path_length(H, s)
        assert set(ours) == set(theirs)
        for v in theirs:
            assert isclose(ours[v], theirs[v], abs_tol=1e-9)
            path = alg.reconstruct_path(parent, v)
            assert isclose(alg.path_length_km(adj, path), ours[v], abs_tol=1e-9)


def test_cut_vertices_and_bridges(graph):
    adj, H = graph
    assert set(alg.cut_vertices(adj)) == set(nx.articulation_points(H))
    assert {frozenset(e) for e in alg.bridges(adj)} == {frozenset(e) for e in nx.bridges(H)}


def test_mst(graph):
    adj, H = graph
    c = nx.number_connected_components(H)
    nx_total = sum(d["weight"] for *_, d in nx.minimum_spanning_edges(H, data=True))
    k, p = alg.kruskal(adj), alg.prim(adj)
    assert isclose(alg.total_weight(k), nx_total, abs_tol=1e-9)
    assert isclose(alg.total_weight(p), nx_total, abs_tol=1e-9)
    # a spanning forest has |V| - c edges and no cycle
    assert len(k) == len(p) == H.number_of_nodes() - c
    assert alg.is_forest(H.number_of_nodes(), k, c)
    assert nx.is_forest(nx.Graph([(u, v) for u, v, _ in k]))


def test_warshall_is_reachability(graph):
    adj, H = graph
    order = sorted(adj)
    W = rl.warshall(rl.adjacency_matrix(adj, order))
    assert rl.is_reflexive(W) and rl.is_symmetric(W) and rl.is_transitive(W)
    classes = sorted(map(sorted, rl.equivalence_classes(W, order)))
    assert classes == sorted(map(sorted, nx.connected_components(H)))


def test_quantifier_check(graph):
    adj, H = graph
    holds, witness = rl.connectivity_by_quantifiers(adj)
    assert holds == nx.is_connected(H)
    if witness:
        u, v = witness
        assert not nx.has_path(H, u, v)


# ---------------------------------------------------------------- known answers on the sample

def test_sample_known_answers():
    G = build_graph(prepare(ROOT / "data" / "sample", verbose=False))
    adj = G.adj
    assert (G.n_vertices, G.n_edges) == (11, 11)
    assert sorted(G.name(v) for v in alg.cut_vertices(adj)) == ["Farmgate", "Gulistan", "Karwan Bazar", "Shahbag"]
    assert len(alg.bridges(adj)) == 4
    # hops and distance disagree for Mirpur 1 -> Farmgate
    s, t = G.stop_id("Mirpur 1"), G.stop_id("Farmgate")
    assert len(alg.fewest_hops_path(adj, s, t)) - 1 == 3
    km, path = alg.shortest_distance_path(adj, s, t)
    assert len(path) - 1 == 4 and km < alg.path_length_km(adj, alg.fewest_hops_path(adj, s, t))
    # the only cycle loses its heaviest edge, Mirpur 10 - Agargaon
    tree = {frozenset((u, v)) for u, v, _ in alg.kruskal(adj)}
    assert frozenset((G.stop_id("Mirpur 10"), G.stop_id("Agargaon"))) not in tree
    # Technical -> Sadarghat needs two changes: T2 -> T1 -> T3
    radj = route_graph(G)
    n, routes = alg.fewest_bus_changes(radj, G.route_seq, G.stop_id("Technical"), G.stop_id("Sadarghat"))
    assert n == 2 and routes == ["T2", "T1", "T3"]


def test_dijkstra_rejects_negative_weights():
    with pytest.raises(ValueError):
        alg.dijkstra({"a": {"b": -1.0}, "b": {"a": -1.0}}, "a")
