"""OPTIONAL: try OpenStreetMap as a data source (Section 4 of the plan).

Run on your own computer (it needs the internet):

    python -m src.fetch_osm            # download + convert
    python -m src.fetch_osm --offline  # only convert an overpass.json you already saved
    python run_all.py --data osm

It downloads every bus-route relation in the Dhaka box from the Overpass API,
keeps the stops (members with role stop/platform), and writes the project's raw
format to data/osm/raw/. Stops with the same name less than 600 m apart are
clustered into one vertex (the plan's "one cluster of stops with the same name").

OpenStreetMap coverage of Dhaka buses is uncertain. If you get only a few routes,
or routes with missing stops, use the hand-built data set instead and say so in
your report. OSM data is © OpenStreetMap contributors (ODbL): credit it if you use it.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from .data_prep import DHAKA_BBOX, normalise
from .geo import haversine_km

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
QUERY = """[out:json][timeout:120];
rel["route"="bus"](23.65,90.30,23.95,90.50);
out body;
node(r);
out body;
"""
CLUSTER_KM = 0.6
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "osm" / "raw"


def download(query: str = QUERY) -> dict:
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data,
                                 headers={"User-Agent": "CSE173-student-project (dhaka-bus-graph)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def _is_stop(member: dict, node: dict | None) -> bool:
    role = member.get("role", "")
    if role.startswith("stop") or role.startswith("platform"):
        return True
    tags = (node or {}).get("tags", {})
    return tags.get("highway") == "bus_stop" or tags.get("public_transport") in ("platform", "stop_position")


def convert(osm: dict):
    """Overpass JSON -> (stops rows, routes rows, route_stops rows) in the raw format."""
    nodes = {el["id"]: el for el in osm.get("elements", []) if el.get("type") == "node"}
    rels = [el for el in osm.get("elements", []) if el.get("type") == "relation"]
    la0, la1, lo0, lo1 = DHAKA_BBOX

    clusters: list[dict] = []          # {name, key, lat, lon, n, spellings}

    def stop_for(node) -> int:
        tags = node.get("tags", {})
        name = tags.get("name:en") or tags.get("name") or f"OSM node {node['id']}"
        key = normalise(name)
        for i, c in enumerate(clusters):
            if c["key"] == key and haversine_km(c["lat"], c["lon"], node["lat"], node["lon"]) <= CLUSTER_KM:
                c["lat"] = (c["lat"] * c["n"] + node["lat"]) / (c["n"] + 1)
                c["lon"] = (c["lon"] * c["n"] + node["lon"]) / (c["n"] + 1)
                c["n"] += 1
                c["spellings"] |= {v for k, v in tags.items() if k.startswith("name")}
                return i
        clusters.append({"name": name, "key": key, "lat": node["lat"], "lon": node["lon"], "n": 1,
                         "spellings": {v for k, v in tags.items() if k.startswith("name")}})
        return len(clusters) - 1

    routes, route_stops = [], []
    for rel in sorted(rels, key=lambda r: r["id"]):
        seq: list[int] = []
        for m in rel.get("members", []):
            if m.get("type") != "node":
                continue
            node = nodes.get(m.get("ref"))
            if node is None or not _is_stop(m, node):
                continue
            if not (la0 <= node["lat"] <= la1 and lo0 <= node["lon"] <= lo1):
                continue                       # outside the study area
            c = stop_for(node)
            if not seq or seq[-1] != c:        # stop_position + platform of one stop -> once
                seq.append(c)
        if len(seq) < 2:
            continue
        tags = rel.get("tags", {})
        rid = f"OSM{rel['id']}"
        routes.append({"route_id": rid,
                       "route_name": tags.get("name") or tags.get("ref") or rid,
                       "operator": tags.get("operator", ""),
                       "source": f"OpenStreetMap relation {rel['id']} (© OpenStreetMap contributors)",
                       "confidence": "medium"})
        route_stops += [{"route_id": rid, "seq": i + 1, "stop_name": f"S{c + 1:04d}"}
                        for i, c in enumerate(seq)]

    # duplicate names (same name, far apart) get a suffix so every name is unique
    seen: dict[str, int] = {}
    stops = []
    taken = {c["key"] for c in clusters}       # every spelling may point to one stop only
    for i, c in enumerate(clusters):
        seen[c["key"]] = seen.get(c["key"], 0) + 1
        name = c["name"] if seen[c["key"]] == 1 else f"{c['name']} ({seen[c['key']]})"
        aliases = []
        if seen[c["key"]] == 1:
            for s in sorted(c["spellings"]):
                k = normalise(s)
                if k and k not in taken and "|" not in s:
                    aliases.append(s)
                    taken.add(k)
        stops.append({"stop_id": f"S{i + 1:04d}", "name_en": name, "lat": round(c["lat"], 6),
                      "lon": round(c["lon"], 6), "aliases": "|".join(aliases)})
    used = {r["stop_name"] for r in route_stops}
    stops = [s for s in stops if s["stop_id"] in used]
    return stops, routes, route_stops


def _write(path: Path, rows: list[dict], cols: list[str]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true", help="convert data/osm/raw/overpass.json only")
    args = p.parse_args(argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_json = OUT_DIR / "overpass.json"
    if not args.offline:
        print("Downloading bus routes from the Overpass API (this can take a minute)...")
        try:
            osm = download()
        except Exception as e:  # network errors, timeouts, server busy
            print(f"Download failed: {e}\nTry again later, or keep using the hand-built data.")
            return 1
        raw_json.write_text(json.dumps(osm), encoding="utf-8")
    else:
        osm = json.loads(raw_json.read_text(encoding="utf-8"))
    n_rel = sum(1 for e in osm.get("elements", []) if e.get("type") == "relation")
    stops, routes, route_stops = convert(osm)
    print(f"Overpass returned {n_rel} bus relations; {len(routes)} have 2 or more stops inside Dhaka; "
          f"{len(stops)} stops after clustering.")
    if not routes:
        print("Nothing usable. Use the hand-built data set (data/dhaka).")
        return 1
    _write(OUT_DIR / "stops.csv", stops, ["stop_id", "name_en", "lat", "lon", "aliases"])
    _write(OUT_DIR / "routes.csv", routes, ["route_id", "route_name", "operator", "source", "confidence"])
    _write(OUT_DIR / "route_stops_raw.csv", route_stops, ["route_id", "seq", "stop_name"])
    print(f"Written to {OUT_DIR}. Next: python run_all.py --data osm "
          "(if rule R4 fails, the route has gaps; try --max-hop-km 6 and look at those routes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
