"""Step 1 of the pipeline: read the raw notes, clean them, and validate them.

Raw files (data/<dataset>/raw/) are NEVER edited by this code:
    stops.csv            stop_id, name_en, lat, lon, aliases   (aliases separated by "|")
    routes.csv           route_id, route_name, operator, source, confidence
    route_stops_raw.csv  route_id, seq, stop_name   (names as you wrote them down)
    road_km.csv          optional: stop_u, stop_v, distance_km, source  (real road distances)

Cleaning writes data/<dataset>/processed/:
    stops.csv, routes.csv, route_stops.csv (route_id, seq, stop_id), road_km.csv

Each validation rule is a proposition (Chapter 1). The program evaluates it
and reports "holds" or the counterexamples that make it false.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .geo import haversine_km

# Rough Dhaka box (lat_min, lat_max, lon_min, lon_max). Slightly wider than the
# Overpass query box so that stops on the edge of the city still pass.
DHAKA_BBOX = (23.60, 24.00, 90.25, 90.55)
MAX_HOP_KM = 4.0   # two consecutive stops further apart than this are suspicious


class DataError(Exception):
    """Raised when the raw data cannot be cleaned or fails a validation rule."""


@dataclass
class CleanData:
    stops: pd.DataFrame                  # index: stop_id; columns name_en, lat, lon, aliases
    routes: pd.DataFrame                 # index: route_id
    route_stops: pd.DataFrame            # columns route_id, seq, stop_id
    road_km: pd.DataFrame                # columns stop_u, stop_v, distance_km, source
    notes: list[str] = field(default_factory=list)   # what cleaning changed
    rule_results: list = field(default_factory=list)  # filled in by prepare()


@dataclass
class RuleResult:
    code: str
    statement: str          # the proposition, written with quantifiers
    holds: bool
    counterexamples: list[str]
    is_warning: bool = False   # warnings are reported but do not stop the pipeline


# ---------------------------------------------------------------- reading

def normalise(name) -> str:
    """Trim, collapse inner spaces and ignore case: '  Farm  gate ' -> 'farm gate'."""
    return " ".join(str(name).strip().split()).casefold()


def read_raw(raw_dir: Path) -> dict[str, pd.DataFrame]:
    raw_dir = Path(raw_dir)
    need = ["stops.csv", "routes.csv", "route_stops_raw.csv"]
    missing = [f for f in need if not (raw_dir / f).exists()]
    if missing:
        raise DataError(f"Missing raw files in {raw_dir}: {missing}")
    tables = {
        "stops": pd.read_csv(raw_dir / "stops.csv", dtype=str, keep_default_na=False),
        "routes": pd.read_csv(raw_dir / "routes.csv", dtype=str, keep_default_na=False),
        "route_stops_raw": pd.read_csv(raw_dir / "route_stops_raw.csv", dtype=str,
                                       keep_default_na=False),
    }
    road = raw_dir / "road_km.csv"
    tables["road_km"] = (pd.read_csv(road, dtype=str, keep_default_na=False) if road.exists()
                         else pd.DataFrame(columns=["stop_u", "stop_v", "distance_km", "source"]))
    return tables


# ---------------------------------------------------------------- cleaning

def build_alias_map(stops: pd.DataFrame) -> dict[str, str]:
    """Map every spelling (official name + aliases, normalised) to one stop_id.

    A spelling that points to two different stops is an error: the program
    could not know which stop you meant.
    """
    alias_map: dict[str, str] = {}
    clashes = []
    for _, row in stops.iterrows():
        sid = row["stop_id"].strip()
        spellings = [row["name_en"]] + [a for a in str(row.get("aliases", "")).split("|") if a.strip()]
        for s in spellings:
            key = normalise(s)
            if key in alias_map and alias_map[key] != sid:
                clashes.append(f"'{s}' -> {alias_map[key]} and {sid}")
            alias_map[key] = sid
    if clashes:
        raise DataError("Alias used for two different stops: " + "; ".join(clashes))
    return alias_map


def clean(raw: dict[str, pd.DataFrame]) -> CleanData:
    notes: list[str] = []

    # stops: trim text, convert coordinates to numbers
    stops = raw["stops"].copy()
    for c in stops.columns:
        stops[c] = stops[c].str.strip()
    if stops["stop_id"].duplicated().any():
        dup = stops.loc[stops["stop_id"].duplicated(), "stop_id"].tolist()
        raise DataError(f"Duplicate stop_id in stops.csv: {dup}")
    try:
        stops["lat"] = stops["lat"].astype(float)
        stops["lon"] = stops["lon"].astype(float)
    except ValueError as e:
        raise DataError(f"A latitude or longitude in stops.csv is not a number: {e}")
    if "aliases" not in stops.columns:
        stops["aliases"] = ""
    alias_map = build_alias_map(stops)
    stop_ids = set(stops["stop_id"])
    stops = stops.set_index("stop_id")

    routes = raw["routes"].copy()
    for c in routes.columns:
        routes[c] = routes[c].str.strip()
    if routes["route_id"].duplicated().any():
        raise DataError("Duplicate route_id in routes.csv")
    routes = routes.set_index("route_id")

    # route stops: map each written name to a stop_id
    rs = raw["route_stops_raw"].copy()
    rs["route_id"] = rs["route_id"].str.strip()
    try:
        rs["seq"] = rs["seq"].astype(int)
    except ValueError as e:
        raise DataError(f"A seq value in route_stops_raw.csv is not a whole number: {e}")

    unknown = []
    ids = []
    for _, row in rs.iterrows():
        written = row["stop_name"]
        if written.strip() in stop_ids:            # the notes may already use an ID
            ids.append(written.strip())
            continue
        sid = alias_map.get(normalise(written))
        if sid is None:
            unknown.append(f"{row['route_id']} seq {row['seq']}: '{written}'")
        else:
            if written != stops.loc[sid, "name_en"]:
                notes.append(f"{row['route_id']} seq {row['seq']}: '{written}' -> "
                             f"{sid} {stops.loc[sid, 'name_en']}")
        ids.append(sid)
    if unknown:
        raise DataError("These stop names are not in stops.csv (add them, or add the spelling "
                        "to that stop's aliases):\n  " + "\n  ".join(unknown))
    rs["stop_id"] = ids
    rs = rs[["route_id", "seq", "stop_id"]].sort_values(["route_id", "seq"]).reset_index(drop=True)

    # road distances (optional): map names or IDs to IDs, numbers to float
    road = raw["road_km"].copy()
    if len(road):
        for col in ("stop_u", "stop_v"):
            mapped = []
            for v in road[col]:
                v2 = v.strip() if v.strip() in stop_ids else alias_map.get(normalise(v))
                if v2 is None:
                    raise DataError(f"road_km.csv: unknown stop '{v}'")
                mapped.append(v2)
            road[col] = mapped
        road["distance_km"] = road["distance_km"].astype(float)

    return CleanData(stops=stops, routes=routes, route_stops=rs, road_km=road, notes=notes)


# ---------------------------------------------------------------- validation

def _sequences(route_stops: pd.DataFrame) -> dict[str, list[str]]:
    return {rid: g.sort_values("seq")["stop_id"].tolist()
            for rid, g in route_stops.groupby("route_id", sort=True)}


def validate(data: CleanData, max_hop_km: float = MAX_HOP_KM,
             bbox: tuple = DHAKA_BBOX) -> list[RuleResult]:
    """Evaluate every data rule. Each rule is a universally quantified proposition;
    a counterexample is a witness to its negation."""
    stops, routes, rs = data.stops, data.routes, data.route_stops
    seqs = _sequences(rs)
    results: list[RuleResult] = []

    def add(code, statement, bad, warning=False):
        results.append(RuleResult(code, statement, len(bad) == 0, bad, warning))

    # R1: every route (in routes.csv) has at least two stops
    bad = [f"{r}: {len(seqs.get(r, []))} stop(s)" for r in routes.index if len(seqs.get(r, [])) < 2]
    add("R1", "∀ route r: r has at least 2 stops", bad)

    # R2: every route_id used in route_stops exists in routes.csv (stop IDs were checked in cleaning)
    bad = sorted(set(rs["route_id"]) - set(routes.index))
    add("R2", "∀ (r, i, s) in route_stops: r ∈ Routes ∧ s ∈ Stops", [f"unknown route {b}" for b in bad])

    # R3: no stop is listed twice in a row
    bad = []
    for r, seq in seqs.items():
        for i in range(len(seq) - 1):
            if seq[i] == seq[i + 1]:
                bad.append(f"{r}: {seq[i]} at positions {i + 1},{i + 2}")
    add("R3", "∀ r, ∀ i: s_i ≠ s_(i+1)  (no stop twice in a row)", bad)

    # R4: consecutive stops are not implausibly far apart
    bad = []
    for r, seq in seqs.items():
        for a, b in zip(seq, seq[1:]):
            d = haversine_km(stops.loc[a, "lat"], stops.loc[a, "lon"], stops.loc[b, "lat"], stops.loc[b, "lon"])
            if d > max_hop_km:
                bad.append(f"{r}: {stops.loc[a, 'name_en']} -> {stops.loc[b, 'name_en']} = {d:.2f} km")
    add("R4", f"∀ r, ∀ i: d(s_i, s_(i+1)) ≤ {max_hop_km} km", bad)

    # R5: every stop lies inside the Dhaka box
    la0, la1, lo0, lo1 = bbox
    bad = [f"{s} {row.name_en} ({row.lat}, {row.lon})" for s, row in stops.iterrows()
           if not (la0 <= row.lat <= la1 and lo0 <= row.lon <= lo1)]
    add("R5", "∀ stop s: s lies inside the Dhaka bounding box", bad)

    # R6: no two entries of one route share a position number
    bad = [f"{r}: seq {q} used twice" for (r, q), n in rs.groupby(["route_id", "seq"]).size().items() if n > 1]
    add("R6", "∀ r: the seq numbers of r are distinct", bad)

    # R7: road distances are positive and never shorter than the straight line
    bad = []
    for _, row in data.road_km.iterrows():
        a, b, d = row["stop_u"], row["stop_v"], row["distance_km"]
        hv = haversine_km(stops.loc[a, "lat"], stops.loc[a, "lon"], stops.loc[b, "lat"], stops.loc[b, "lon"])
        if d <= 0 or d < hv - 1e-9:
            bad.append(f"{a}-{b}: road {d} km < straight line {hv:.2f} km")
    add("R7", "∀ given road distance: 0 < road_km(u,v) and road_km(u,v) ≥ haversine(u,v)", bad)

    # W1 (warning): loop routes — a stop appears twice, not consecutively
    bad = []
    for r, seq in seqs.items():
        if len(seq) > len(set(seq)):   # pigeonhole: more positions than distinct stops
            rep = sorted({s for s in seq if seq.count(s) > 1})
            bad.append(f"{r}: {len(seq)} positions but {len(set(seq))} distinct stops; repeats {rep}")
    add("W1", "∀ r: no stop repeats within r  (a repeat = a loop route; allowed)", bad, warning=True)

    # W2 (warning): stops that no route uses become isolated vertices
    used = set(rs["stop_id"])
    bad = [f"{s} {stops.loc[s, 'name_en']}" for s in stops.index if s not in used]
    add("W2", "∀ stop s: some route serves s  (otherwise s is an isolated vertex)", bad, warning=True)

    return results


def print_rules(results: list[RuleResult]) -> None:
    for r in results:
        status = "holds" if r.holds else ("WARNING" if r.is_warning else "FAILS")
        print(f"  {r.code} {r.statement:<72} {status}")
        for c in r.counterexamples[:10]:
            print(f"       - {c}")
        if len(r.counterexamples) > 10:
            print(f"       ... and {len(r.counterexamples) - 10} more")


def save_processed(data: CleanData, processed_dir: Path) -> None:
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    data.stops.reset_index().to_csv(processed_dir / "stops.csv", index=False)
    data.routes.reset_index().to_csv(processed_dir / "routes.csv", index=False)
    data.route_stops.to_csv(processed_dir / "route_stops.csv", index=False)
    data.road_km.to_csv(processed_dir / "road_km.csv", index=False)


def prepare(dataset_dir: Path, max_hop_km: float = MAX_HOP_KM, verbose: bool = True) -> CleanData:
    """Read raw -> clean -> validate -> save processed. Raises DataError if a rule fails."""
    dataset_dir = Path(dataset_dir)
    data = clean(read_raw(dataset_dir / "raw"))
    if verbose:
        print(f"Cleaning: {len(data.notes)} written names were mapped to a different official name")
        for n in data.notes[:8]:
            print(f"  {n}")
        if len(data.notes) > 8:
            print(f"  ... ({len(data.notes) - 8} more; all listed in results/cleaning_log.txt)")
    results = validate(data, max_hop_km=max_hop_km)
    if verbose:
        print("Validation rules:")
        print_rules(results)
    failed = [r for r in results if not r.holds and not r.is_warning]
    if failed:
        raise DataError("Validation failed: " + ", ".join(r.code for r in failed)
                        + ". Fix the raw notes (not the processed files) and run again.")
    save_processed(data, dataset_dir / "processed")
    data.rule_results = results   # kept for the summary report
    return data
