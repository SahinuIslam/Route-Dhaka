"""Tests for the app's logic (src/gui/model.py). No screen needed."""
from math import isclose

from src import algorithms as alg
from src.gui import model


def _sample():
    ds = model.load_dataset("sample")
    assert ds.ok, ds.error
    return ds


def test_available_datasets():
    names = model.available_datasets()
    assert names[:2] == ["sample", "dhaka"]


def test_stats_sample():
    st = _sample().stats
    assert (st["V"], st["E"], st["components"], st["cut_vertices"], st["bridges"]) == (11, 11, 1, 4, 4)
    assert isclose(st["mst_km"], st["prim_km"])


def test_route_finder_and_legs():
    ds = _sample()
    G = ds.G
    r = model.find_route(ds, G.stop_id("Mirpur 1"), G.stop_id("Farmgate"))
    assert len(r["hop_path"]) - 1 == 3 and len(r["dist_path"]) - 1 == 4 and not r["same"]
    assert r["dist_km"] < r["hop_km"]

    r = model.find_route(ds, G.stop_id("Technical"), G.stop_id("Sadarghat"))
    assert r["changes"] == 2
    legs = [(l["route"], G.name(l["board"]), G.name(l["alight"])) for l in r["legs"]]
    # change points chosen to ride the fewest stops: T2 to Farmgate, T1 to Shahbag, T3 to the end
    assert legs == [("T2", "Technical", "Farmgate"), ("T1", "Farmgate", "Shahbag"),
                    ("T3", "Shahbag", "Sadarghat")]
    for l in r["legs"]:                       # every leg really is part of its route
        seq = G.route_seq[l["route"]]
        assert all(s in seq for s in l["stops"])


def test_unreachable_pair_in_dhaka():
    ds = model.load_dataset("dhaka")
    G = ds.G
    r = model.find_route(ds, G.stop_id("Tongi"), G.stop_id("Jinjira"))
    assert r["reachable"] is False


def test_legs_cover_trip_in_dhaka():
    ds = model.load_dataset("dhaka")
    for s, t in ds.pairs:
        r = model.find_route(ds, s, t)
        legs = r["legs"]
        assert legs[0]["board"] == s and legs[-1]["alight"] == t
        assert len(legs) == r["changes"] + 1
        for a, b in zip(legs, legs[1:]):
            assert a["alight"] == b["board"]


def test_removal_effect():
    ds = _sample()
    G = ds.G
    eff = model.removal_effect(G.adj, G.stop_id("Farmgate"))
    assert sorted(G.name(s) for s in eff["cut_off"]) == ["Gulistan", "Karwan Bazar", "Sadarghat", "Shahbag"]
    eff = model.removal_effect(G.adj, G.stop_id("Agargaon"))       # on the only cycle
    assert eff["cut_off"] == set()
    before, after = model.detour_cost(G.adj, G.stop_id("Agargaon"), eff["main"])
    assert after >= before


def test_kruskal_steps():
    ds = _sample()
    G = ds.G
    end = model.kruskal_step(ds, len(ds.ktrace))
    assert isclose(end["total_km"], ds.stats["mst_km"]) and len(end["tree"]) == 10
    last = end["current"]                      # the 11th link is the one that closes the cycle
    assert not last[3]
    names = [G.name(s) for s in end["cycle"]]
    assert names[0] in ("Mirpur 10", "Agargaon") and names[-1] in ("Mirpur 10", "Agargaon")
    assert len(end["cycle"]) == 7
    assert model.kruskal_step(ds, 0)["tree"] == []


def test_dijkstra_states_match_dijkstra():
    ds = model.load_dataset("dhaka")
    adj = ds.G.adj
    s = ds.G.stop_id("Mirpur 12")
    states = model.dijkstra_states(adj, s)
    dist, _ = alg.dijkstra(adj, s)
    final = states[-1]
    assert len(final["final"]) == len(dist)
    for v, d in dist.items():
        assert isclose(final["dist"][v], d, abs_tol=1e-9)
    # distances leave S in non-decreasing order
    order = [st["d"] for st in states[1:]]
    assert order == sorted(order)
