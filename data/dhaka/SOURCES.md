# Where the Dhaka core data comes from — read before you report results

**Status: constructed, not yet verified.** This is the plan's fallback option
("semi-synthetic data: real stop names and coordinates, route sequences
assembled from corridors"), prepared as a starting point.

## What is real and what is assumed

| Part | Status | What to do |
|---|---|---|
| Stop names (101) | Real, well-known stops and junctions | Keep; add Bengali names to `aliases` if you like |
| Coordinates | Approximate (typically within a few hundred metres) | Check each on Google Maps (right-click → coordinates) and correct `lat`, `lon` |
| Route stop orders (18 routes) | Built along real road corridors (Airport Road, Progoti Sarani, Mirpur Road, Begum Rokeya Sarani, Kazi Nazrul Islam Avenue, Dhaka–Chittagong Highway, …) | Check each against a real operator route (Google Maps transit view, a conductor, your own ride). Fix the order, then change `confidence` |
| Operators | Not filled in | Fill in when you verify a route |
| Jinjira (S101) | Deliberately left with no route | It demonstrates an isolated vertex. Either add a verified route that serves it, or keep it and explain it |
| Road distances | None yet (`road_km.csv` is empty) | Optional: add road distances from Google Maps for important links |

All 18 routes have `confidence = unverified`. The summary report prints this so
you never mistake the data set for the city.

## Spellings in the raw notes

`route_stops_raw.csv` deliberately uses mixed spellings (Farm Gate / Farmgate,
Kawran Bazar / Karwan Bazar, Mirpur-10, extra spaces) so that the cleaning step
has something to do. The cleaning log (`results/dhaka/cleaning_log.txt`) lists
every mapping.

## How to record a verified route

1. Edit `raw/route_stops_raw.csv` (never the files in `processed/`).
2. In `raw/routes.csv` set `operator`, `source` (e.g. "Google Maps transit view,
   checked 2026-10-25 + rode it") and `confidence` (`high` / `medium` / `low`).
3. Run `python run_all.py --data dhaka` and read the validation rules.
