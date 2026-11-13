# Results: sample

## 1. Data

- 11 stops, 3 routes, 15 route-stop entries.
- Route confidence: sample: 3.
- Cleaning mapped 3 written names to their official stop (see cleaning_log.txt).

Validation rules (each is a proposition the program checks):

- R1: ∀ route r: r has at least 2 stops — **holds**
- R2: ∀ (r, i, s) in route_stops: r ∈ Routes ∧ s ∈ Stops — **holds**
- R3: ∀ r, ∀ i: s_i ≠ s_(i+1)  (no stop twice in a row) — **holds**
- R4: ∀ r, ∀ i: d(s_i, s_(i+1)) ≤ 4.0 km — **holds**
- R5: ∀ stop s: s lies inside the Dhaka bounding box — **holds**
- R6: ∀ r: the seq numbers of r are distinct — **holds**
- R7: ∀ given road distance: 0 < road_km(u,v) and road_km(u,v) ≥ haversine(u,v) — **holds**
- W1: ∀ r: no stop repeats within r  (a repeat = a loop route; allowed) — **holds**
- W2: ∀ stop s: some route serves s  (otherwise s is an isolated vertex) — **holds**

## 2. Size of the graph

- |V| = 11 stops, |E| = 11 links.
- Links used by more than one route (parallel routes merged into one edge): 1.
- Handshaking theorem: sum of degrees = 22, 2|E| = 22 → holds.
- Possible stop pairs C(11, 2) = 55; density = |E| / C(|V|, 2) = 0.2000 (a sparse graph, so an adjacency list is the right structure).
- Total length of all links = 21.06 km (0 road distances, 11 straight-line distances).

## 3. Degrees

- Degree: min 1, max 3, mean 2.00, median 2; 1 end stops (degree 1), 0 isolated stops.

Busiest stops (most directly linked stops):

| stop_id | name | degree | routes_serving |
|---|---|---|---|
| S04 | Farmgate | 3 | 2 |
| S01 | Mirpur 1 | 2 | 2 |
| S05 | Karwan Bazar | 2 | 2 |
| S06 | Shahbag | 2 | 2 |
| S02 | Mirpur 10 | 2 | 1 |
| S03 | Agargaon | 2 | 1 |
| S07 | Technical | 2 | 1 |
| S08 | Shyamoli | 2 | 1 |
| S09 | Asad Gate | 2 | 1 |
| S10 | Gulistan | 2 | 1 |

## 4. Connectivity

- Statement checked: ∀u ∀v (there is a path from u to v). Result: **True**.
- Connected components: **1**. Largest: 11 stops (100.0% of all stops).
- "Directly linked" relation is symmetric: True.
- Warshall closure of "can reach": reflexive True, symmetric True, transitive True → an equivalence relation with 1 class(es); classes equal the BFS components: True.

## 5. Weak points: cut vertices and bridges

- **4 cut vertices** (a stop whose removal disconnects part of the network) and **4 bridges** (a link with the same effect).

Cut vertices, by how many stops they would cut off:

| name | pieces_after_removal | stops_cut_off | cut_off_stops |
|---|---|---|---|
| Farmgate | 2 | 4 | Gulistan, Karwan Bazar, Sadarghat, Shahbag |
| Karwan Bazar | 2 | 3 | Gulistan, Sadarghat, Shahbag |
| Shahbag | 2 | 2 | Gulistan, Sadarghat |
| Gulistan | 2 | 1 | Sadarghat |

## 6. Shortest paths for chosen stop pairs

Fewest stops = BFS (every link counts 1). Shortest distance = Dijkstra (weights in km). Fewest bus changes = BFS on the route graph.

### Mirpur 1 → Farmgate

- Fewest stops: 3 hops, 7.69 km: Mirpur 1 -> Mirpur 10 -> Agargaon -> Farmgate
- Shortest distance: 4 hops, 6.76 km: Mirpur 1 -> Technical -> Shyamoli -> Asad Gate -> Farmgate
- Same path? no.
- Fewest bus changes: **0** (routes T1); one bus does the whole trip

### Mirpur 10 → Sadarghat

- Fewest stops: 6 hops, 12.50 km: Mirpur 10 -> Agargaon -> Farmgate -> Karwan Bazar -> Shahbag -> Gulistan -> Sadarghat
- Shortest distance: 6 hops, 12.50 km: Mirpur 10 -> Agargaon -> Farmgate -> Karwan Bazar -> Shahbag -> Gulistan -> Sadarghat
- Same path? yes.
- Fewest bus changes: **1** (routes T1 → T3); change T1→T3 at Shahbag

### Technical → Sadarghat

- Fewest stops: 7 hops, 11.59 km: Technical -> Shyamoli -> Asad Gate -> Farmgate -> Karwan Bazar -> Shahbag -> Gulistan -> Sadarghat
- Shortest distance: 7 hops, 11.59 km: Technical -> Shyamoli -> Asad Gate -> Farmgate -> Karwan Bazar -> Shahbag -> Gulistan -> Sadarghat
- Same path? yes.
- Fewest bus changes: **2** (routes T2 → T1 → T3); change T2→T1 at Farmgate, Karwan Bazar, Mirpur 1; T1→T3 at Shahbag

### Where "fewest stops" and "shortest distance" disagree

- Mirpur 1 → Karwan Bazar: fewest stops = 4 hops but 8.54 km; shortest = 5 hops, 7.61 km (+0.93 km for the fewest-stop path).
- Mirpur 1 → Farmgate: fewest stops = 3 hops but 7.69 km; shortest = 4 hops, 6.76 km (+0.93 km for the fewest-stop path).
- Mirpur 1 → Shahbag: fewest stops = 5 hops but 9.95 km; shortest = 6 hops, 9.02 km (+0.93 km for the fewest-stop path).

### Dijkstra step by step from Mirpur 1 (compare with your hand trace)

| step | moved_into_S | distance_km | updated |
|---|---|---|---|
| 1 | Mirpur 1 | 0.00 | Mirpur 10=1.80, Technical=1.78 |
| 2 | Technical | 1.78 | Shyamoli=3.29 |
| 3 | Mirpur 10 | 1.80 | Agargaon=5.19 |
| 4 | Shyamoli | 3.29 | Asad Gate=5.00 |
| 5 | Asad Gate | 5.00 | Farmgate=6.76 |
| 6 | Agargaon | 5.19 | - |
| 7 | Farmgate | 6.76 | Karwan Bazar=7.61 |
| 8 | Karwan Bazar | 7.61 | Shahbag=9.02 |
| 9 | Shahbag | 9.02 | Gulistan=11.29 |
| 10 | Gulistan | 11.29 | Sadarghat=13.37 |
| 11 | Sadarghat | 13.37 | - |

## 7. How compact is the network? (largest component)

- Average shortest path: 3.09 hops, 5.56 km.
- Diameter: 7 hops (e.g. Mirpur 1 ↔ Sadarghat).
- Longest shortest distance: 13.37 km (Mirpur 1 ↔ Sadarghat).
- Centre (smallest eccentricity, 4 hops): Farmgate, Karwan Bazar.
- Bus changes needed over all stop pairs: 0 changes: 54.5%, 1 change: 34.5%, 2 changes: 10.9%.
- Route graph: 3 routes, 2 pairs of routes that share at least one stop.

## 8. Minimum spanning tree (the backbone)

- Kruskal: 10 edges, total 17.66 km. Prim: 10 edges, total 17.66 km. Same total: True.
- Edge count = |V| − c = 11 − 1 = 10: True; acyclic forest: True.
- Full network 21.06 km vs tree 17.66 km: the 1 links left out (3.40 km, 16.1% of the length) are redundancy.
- Cycle property check: every left-out link is at least as heavy as every tree link on the cycle it would close: True.
- Longest tree links: Agargaon–Farmgate 2.50 km; Shahbag–Gulistan 2.27 km; Gulistan–Sadarghat 2.08 km.
- Reading: the tree is the cheapest set of links that keeps every stop reachable. It is not a proposal for bus routes: trips along the tree can be much longer than on the full network.

### Kruskal step by step

| order | edge | km | decision |
|---|---|---|---|
| 1 | Farmgate – Karwan Bazar | 0.85 | added |
| 2 | Karwan Bazar – Shahbag | 1.41 | added |
| 3 | Technical – Shyamoli | 1.51 | added |
| 4 | Shyamoli – Asad Gate | 1.71 | added |
| 5 | Farmgate – Asad Gate | 1.76 | added |
| 6 | Mirpur 1 – Technical | 1.78 | added |
| 7 | Mirpur 1 – Mirpur 10 | 1.80 | added |
| 8 | Gulistan – Sadarghat | 2.08 | added |
| 9 | Shahbag – Gulistan | 2.27 | added |
| 10 | Agargaon – Farmgate | 2.50 | added |
| 11 | Mirpur 10 – Agargaon | 3.40 | skipped (would close a cycle) |

## 9. Counting (Chapter 6)

- Stop pairs: C(11, 2) = 55; actual links 11; so 20.00% of pairs are linked.
- Product rule: at a stop served by k routes a rider can change from any route to any other, k·(k−1) ordered choices. Shahbag: k=2, 2 choices; Karwan Bazar: k=2, 2 choices; Farmgate: k=2, 2 choices.
- Transfer stops (served by 2 or more routes): 4 of 11.

## 10. Cross-check against NetworkX

- components: matches
- cut vertices: matches
- bridges: matches
- MST weight: matches
- Dijkstra distances: matches
- BFS hop counts: matches

## Figures

- figures/network.png
- figures/degree_histogram.png
- figures/cut_points.png
- figures/mst.png
- figures/shortest_path.png
- map.html (open in a browser)

