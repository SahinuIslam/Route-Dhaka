"""Tests for cleaning and validation: each rule must catch the error it describes."""
import json
from pathlib import Path

import pytest

from src.data_prep import DataError, clean, prepare, read_raw, validate
from src.fetch_osm import convert
from src.graph_build import build_graph

STOPS = """stop_id,name_en,lat,lon,aliases
A,Alpha,23.75,90.39,Alfa|ALPHA Stop
B,Bravo,23.76,90.39,
C,Charlie,23.77,90.40,
D,Delta,23.78,90.40,
"""
ROUTES = """route_id,route_name,operator,source,confidence
X,Alpha - Charlie,op,test,high
Y,Bravo - Delta,op,test,high
"""


def make(tmp_path: Path, route_stops: str, stops: str = STOPS, routes: str = ROUTES) -> Path:
    raw = tmp_path / "ds" / "raw"
    raw.mkdir(parents=True)
    (raw / "stops.csv").write_text(stops)
    (raw / "routes.csv").write_text(routes)
    (raw / "route_stops_raw.csv").write_text("route_id,seq,stop_name\n" + route_stops)
    return tmp_path / "ds"


def rules(ds: Path):
    return {r.code: r for r in validate(clean(read_raw(ds / "raw")))}


def test_good_data_and_alias_mapping(tmp_path):
    ds = make(tmp_path, "X,1,alfa\nX,2,  Bravo \nX,3,Charlie\nY,1,B\nY,2,Delta\n")
    data = prepare(ds, verbose=False)
    assert data.route_stops["stop_id"].tolist() == ["A", "B", "C", "B", "D"]
    assert (ds / "processed" / "route_stops.csv").exists()
    G = build_graph(data)
    assert G.n_edges == 3            # A-B, B-C, B-D
    assert len(G.adj["B"]) == 3


def test_unknown_name_is_reported(tmp_path):
    ds = make(tmp_path, "X,1,Alpha\nX,2,Zulu\nY,1,Bravo\nY,2,Delta\n")
    with pytest.raises(DataError, match="Zulu"):
        prepare(ds, verbose=False)


def test_R1_route_with_one_stop(tmp_path):
    ds = make(tmp_path, "X,1,Alpha\nY,1,Bravo\nY,2,Delta\n")
    assert not rules(ds)["R1"].holds
    with pytest.raises(DataError):
        prepare(ds, verbose=False)


def test_R3_stop_twice_in_a_row(tmp_path):
    ds = make(tmp_path, "X,1,Alpha\nX,2,Alpha\nX,3,Bravo\nY,1,Bravo\nY,2,Delta\n")
    assert not rules(ds)["R3"].holds


def test_R4_far_apart(tmp_path):
    far = STOPS.replace("D,Delta,23.78,90.40", "D,Delta,23.90,90.40")
    ds = make(tmp_path, "X,1,Alpha\nX,2,Bravo\nY,1,Bravo\nY,2,Delta\n", stops=far)
    assert not rules(ds)["R4"].holds


def test_R5_outside_dhaka(tmp_path):
    out = STOPS.replace("C,Charlie,23.77,90.40", "C,Charlie,22.35,91.80")   # Chattogram
    ds = make(tmp_path, "X,1,Alpha\nX,2,Bravo\nY,1,Bravo\nY,2,Delta\n", stops=out)
    assert not rules(ds)["R5"].holds


def test_loop_and_isolated_are_warnings(tmp_path):
    ds = make(tmp_path, "X,1,Alpha\nX,2,Bravo\nX,3,Alpha\nY,1,Bravo\nY,2,Delta\n")
    r = rules(ds)
    assert not r["W1"].holds and r["W1"].is_warning      # loop route
    assert not r["W2"].holds and r["W2"].is_warning      # Charlie is unused
    data = prepare(ds, verbose=False)                    # warnings do not stop the pipeline
    assert build_graph(data).adj["C"] == {}              # isolated vertex kept


def test_alias_clash_is_an_error(tmp_path):
    clash = STOPS.replace("B,Bravo,23.76,90.39,", "B,Bravo,23.76,90.39,Alfa")
    ds = make(tmp_path, "X,1,Alpha\nX,2,Bravo\nY,1,Bravo\nY,2,Delta\n", stops=clash)
    with pytest.raises(DataError, match="Alias"):
        prepare(ds, verbose=False)


def test_osm_conversion_on_a_tiny_example():
    osm = {"elements": [
        {"type": "relation", "id": 1, "tags": {"route": "bus", "name": "Test line"},
         "members": [{"type": "node", "ref": 10, "role": "stop"},
                     {"type": "node", "ref": 11, "role": "platform"},   # same stop, other side
                     {"type": "way", "ref": 99, "role": ""},
                     {"type": "node", "ref": 12, "role": "stop"}]},
        {"type": "relation", "id": 2, "tags": {"route": "bus"},
         "members": [{"type": "node", "ref": 12, "role": "stop"}]},     # one stop only: dropped
        {"type": "node", "id": 10, "lat": 23.75, "lon": 90.39, "tags": {"name": "Farmgate"}},
        {"type": "node", "id": 11, "lat": 23.7502, "lon": 90.3901, "tags": {"name": "Farmgate", "name:bn": "ফার্মগেট"}},
        {"type": "node", "id": 12, "lat": 23.74, "lon": 90.40, "tags": {"name": "Shahbag"}},
    ]}
    stops, routes, rs = convert(osm)
    assert [r["route_id"] for r in routes] == ["OSM1"]
    assert [s["name_en"] for s in stops] == ["Farmgate", "Shahbag"]
    assert [r["stop_name"] for r in rs] == ["S0001", "S0002"]
    json.dumps(stops)  # plain data
