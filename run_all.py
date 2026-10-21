"""Run the whole project from one command.

    python run_all.py                  # sample first, then Dhaka
    python run_all.py --data sample    # only the 11-stop sample
    python run_all.py --data dhaka     # only the Dhaka core network
    python run_all.py --data osm       # data fetched with  python -m src.fetch_osm

Pipeline for each data set:
  raw CSVs -> clean + validate -> processed CSVs -> graph -> edges.csv
           -> analyses -> results/<dataset>/summary.md, tables, figures, map
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # write figures to files; no window needed

import pandas as pd

from src.analysis import run_analysis
from src.data_prep import MAX_HOP_KM, DataError, prepare
from src.graph_build import build_graph, save_edges

ROOT = Path(__file__).resolve().parent

# The report prints symbols such as ∀ and →. On a terminal that cannot show them,
# print a "?" instead of crashing.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass


def run_one(dataset: str, max_hop_km: float, figures: bool) -> dict:
    ds_dir = ROOT / "data" / dataset
    print("=" * 78)
    print(f"DATA SET: {dataset}   ({ds_dir})")
    print("=" * 78)
    data = prepare(ds_dir, max_hop_km=max_hop_km)
    G = build_graph(data)
    edges_path = save_edges(G, ds_dir / "processed")
    print(f"Graph built: {G.n_vertices} vertices, {G.n_edges} edges -> {edges_path.relative_to(ROOT)}")
    print()
    pairs_file = ds_dir / "pairs.csv"
    pairs = pd.read_csv(pairs_file) if pairs_file.exists() else pd.DataFrame(columns=["from_stop", "to_stop"])
    out = ROOT / "results" / dataset
    res = run_analysis(G, data, dataset, pairs, out, make_figures=figures)
    print(f"\nEverything for '{dataset}' is in {out.relative_to(ROOT)}/  (start with summary.md)\n")
    return res


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Dhaka bus network as a graph (CSE173)")
    p.add_argument("--data", choices=["sample", "dhaka", "osm", "all"], default="all")
    p.add_argument("--max-hop-km", type=float, default=MAX_HOP_KM,
                   help="rule R4: largest believable distance between consecutive stops")
    p.add_argument("--no-figures", action="store_true", help="skip figures and the map (faster)")
    args = p.parse_args(argv)
    sets = ["sample", "dhaka"] if args.data == "all" else [args.data]
    try:
        for ds in sets:
            run_one(ds, args.max_hop_km, not args.no_figures)
    except DataError as e:
        print(f"\nDATA PROBLEM: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
