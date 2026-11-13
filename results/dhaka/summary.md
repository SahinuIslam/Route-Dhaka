# Results: dhaka

## 1. Data

- 101 stops, 18 routes, 210 route-stop entries.
- Route confidence: unverified: 18.
- **18 routes are still unverified.** Results describe this data set; check the routes before claiming they describe the city.
- Cleaning mapped 27 written names to their official stop (see cleaning_log.txt).

Validation rules (each is a proposition the program checks):

- R1: ∀ route r: r has at least 2 stops — **holds**
- R2: ∀ (r, i, s) in route_stops: r ∈ Routes ∧ s ∈ Stops — **holds**
- R3: ∀ r, ∀ i: s_i ≠ s_(i+1)  (no stop twice in a row) — **holds**
- R4: ∀ r, ∀ i: d(s_i, s_(i+1)) ≤ 4.0 km — **holds**
- R5: ∀ stop s: s lies inside the Dhaka bounding box — **holds**
- R6: ∀ r: the seq numbers of r are distinct — **holds**
- R7: ∀ given road distance: 0 < road_km(u,v) and road_km(u,v) ≥ haversine(u,v) — **holds**
- W1: ∀ r: no stop repeats within r  (a repeat = a loop route; allowed) — **warning**
    - R12: 5 positions but 4 distinct stops; repeats ['S081']
- W2: ∀ stop s: some route serves s  (otherwise s is an isolated vertex) — **warning**
    - S101 Jinjira

## 2. Size of the graph

- |V| = 101 stops, |E| = 119 links.
- Links used by more than one route (parallel routes merged into one edge): 58.
- Handshaking theorem: sum of degrees = 238, 2|E| = 238 → holds.
- Possible stop pairs C(101, 2) = 5050; density = |E| / C(|V|, 2) = 0.0236 (a sparse graph, so an adjacency list is the right structure).
- Total length of all links = 118.43 km (0 road distances, 119 straight-line distances).

## 3. Degrees

- Degree: min 0, max 6, mean 2.36, median 2; 8 end stops (degree 1), 1 isolated stops.

Busiest stops (most directly linked stops):

| stop_id | name | degree | routes_serving |
|---|---|---|---|
| S024 | Gulistan | 6 | 6 |
| S014 | Mohakhali | 5 | 4 |
| S027 | Paltan | 5 | 4 |
| S054 | Science Lab | 5 | 3 |
| S031 | Mirpur 10 | 4 | 4 |
| S050 | Asad Gate | 4 | 4 |
| S012 | Kakoli | 4 | 3 |
| S074 | Malibagh | 4 | 3 |
| S076 | Mogbazar | 4 | 3 |
| S019 | Bangla Motor | 3 | 5 |

## 4. Connectivity

- Statement checked: ∀u ∀v (there is a path from u to v). Result: **False**.
- Witness for the negation ∃u ∃v ¬path(u, v): Tongi and Jinjira.
- Connected components: **2**. Largest: 100 stops (99.0% of all stops).
- Component 2: Jinjira
- "Directly linked" relation is symmetric: True.
- Warshall closure of "can reach": reflexive True, symmetric True, transitive True → an equivalence relation with 2 class(es); classes equal the BFS components: True.

## 5. Weak points: cut vertices and bridges

- **23 cut vertices** (a stop whose removal disconnects part of the network) and **25 bridges** (a link with the same effect).

Cut vertices, by how many stops they would cut off:

| name | pieces_after_removal | stops_cut_off | cut_off_stops |
|---|---|---|---|
| Gulistan | 3 | 12 | Jatrabari, Jurain, Kajla, Postogola, Ray Saheb Bazar, Rayerbag, Sadarghat, Saidabad ... |
| Kuril Bishwa Road | 2 | 8 | Abdullahpur, Airport, Azampur, House Building, Jasimuddin, Kawla, Khilkhet, Tongi |
| Tikatuli | 2 | 8 | Jatrabari, Jurain, Kajla, Postogola, Rayerbag, Saidabad, Shonir Akhra, Signboard |
| Khilkhet | 2 | 7 | Abdullahpur, Airport, Azampur, House Building, Jasimuddin, Kawla, Tongi |
| Saidabad | 2 | 7 | Jatrabari, Jurain, Kajla, Postogola, Rayerbag, Shonir Akhra, Signboard |
| Kawla | 2 | 6 | Abdullahpur, Airport, Azampur, House Building, Jasimuddin, Tongi |
| Jatrabari | 3 | 6 | Jurain, Kajla, Postogola, Rayerbag, Shonir Akhra, Signboard |
| Airport | 2 | 5 | Abdullahpur, Azampur, House Building, Jasimuddin, Tongi |
| Jasimuddin | 2 | 4 | Abdullahpur, Azampur, House Building, Tongi |
| Azampur | 2 | 3 | Abdullahpur, House Building, Tongi |
| Kajla | 2 | 3 | Rayerbag, Shonir Akhra, Signboard |
| House Building | 2 | 2 | Abdullahpur, Tongi |
| Science Lab | 2 | 2 | Azimpur, New Market |
| Shonir Akhra | 2 | 2 | Rayerbag, Signboard |
| Ray Saheb Bazar | 2 | 2 | Sadarghat, Victoria Park |

_(8 more rows in the CSV file)_

## 6. Shortest paths for chosen stop pairs

Fewest stops = BFS (every link counts 1). Shortest distance = Dijkstra (weights in km). Fewest bus changes = BFS on the route graph.

### Mirpur 12 → Motijheel

- Fewest stops: 13 hops, 15.38 km: Mirpur 12 -> Mirpur 11 -> Mirpur 10 -> Mirpur 14 -> Kochukhet -> Jahangir Gate -> Mohakhali -> Nabisco -> Satrasta -> Mogbazar -> Kakrail -> Paltan -> Gulistan -> Motijheel
- Shortest distance: 15 hops, 13.42 km: Mirpur 12 -> Mirpur 11 -> Mirpur 10 -> Kazipara -> Shewrapara -> Taltola -> Agargaon -> Bijoy Sarani -> Farmgate -> Karwan Bazar -> Bangla Motor -> Mogbazar -> Kakrail -> Paltan -> Fakirapool -> Motijheel
- Same path? no.
- Fewest bus changes: **0** (routes R02); one bus does the whole trip

### Abdullahpur → Sadarghat

- Fewest stops: 20 hops, 21.43 km: Abdullahpur -> House Building -> Azampur -> Jasimuddin -> Airport -> Kawla -> Khilkhet -> Kuril Bishwa Road -> MES -> Sainik Club -> Kakoli -> Mohakhali -> Nabisco -> Satrasta -> Mogbazar -> Kakrail -> Paltan -> Gulistan -> Ray Saheb Bazar -> Victoria Park -> Sadarghat
- Shortest distance: 20 hops, 20.48 km: Abdullahpur -> House Building -> Azampur -> Jasimuddin -> Airport -> Kawla -> Khilkhet -> Kuril Bishwa Road -> Bashundhara -> Natun Bazar -> Uttar Badda -> Badda -> Merul Badda -> Rampura -> Malibagh -> Shantinagar -> Paltan -> Gulistan -> Ray Saheb Bazar -> Victoria Park -> Sadarghat
- Same path? no.
- Fewest bus changes: **1** (routes R01 → R04); change R01→R04 at GPO, Gulistan, Matsya Bhaban ...

### Gabtoli → Signboard

- Fewest stops: 20 hops, 19.15 km: Gabtoli -> Technical -> Kallyanpur -> Shyamoli -> College Gate -> Asad Gate -> Khamarbari -> Farmgate -> Karwan Bazar -> Bangla Motor -> Mogbazar -> Kakrail -> Paltan -> Gulistan -> Tikatuli -> Saidabad -> Jatrabari -> Kajla -> Shonir Akhra -> Rayerbag -> Signboard
- Shortest distance: 21 hops, 18.34 km: Gabtoli -> Technical -> Kallyanpur -> Shyamoli -> College Gate -> Asad Gate -> Dhanmondi 27 -> Russell Square -> Kalabagan -> Science Lab -> Nilkhet -> Palashi -> Bakshi Bazar -> Chankharpul -> Gulistan -> Tikatuli -> Saidabad -> Jatrabari -> Kajla -> Shonir Akhra -> Rayerbag -> Signboard
- Same path? no.
- Fewest bus changes: **2** (routes R03 → R04 → R16); change R03→R04 at Asad Gate, College Gate, Dhanmondi 27 ...; R04→R16 at Gulistan

### Mohammadpur → Banasree

- Fewest stops: 11 hops, 10.02 km: Mohammadpur -> Town Hall -> Asad Gate -> Khamarbari -> Farmgate -> Karwan Bazar -> Bangla Motor -> Mogbazar -> Mouchak -> Malibagh -> Rampura -> Banasree
- Shortest distance: 11 hops, 10.02 km: Mohammadpur -> Town Hall -> Asad Gate -> Khamarbari -> Farmgate -> Karwan Bazar -> Bangla Motor -> Mogbazar -> Mouchak -> Malibagh -> Rampura -> Banasree
- Same path? yes.
- Fewest bus changes: **1** (routes R08 → R18); change R08→R18 at Asad Gate, Bangla Motor, Karwan Bazar

### Tongi → Azimpur

- Fewest stops: 21 hops, 22.59 km: Tongi -> Abdullahpur -> House Building -> Azampur -> Jasimuddin -> Airport -> Kawla -> Khilkhet -> Kuril Bishwa Road -> MES -> Sainik Club -> Kakoli -> Mohakhali -> Nabisco -> Satrasta -> Mogbazar -> Bangla Motor -> Shahbag -> Kataban -> Science Lab -> New Market -> Azimpur
- Shortest distance: 21 hops, 22.59 km: Tongi -> Abdullahpur -> House Building -> Azampur -> Jasimuddin -> Airport -> Kawla -> Khilkhet -> Kuril Bishwa Road -> MES -> Sainik Club -> Kakoli -> Mohakhali -> Nabisco -> Satrasta -> Mogbazar -> Bangla Motor -> Shahbag -> Kataban -> Science Lab -> New Market -> Azimpur
- Same path? yes.
- Fewest bus changes: **2** (routes R01 → R04 → R03); change R01→R04 at GPO, Gulistan, Matsya Bhaban ...; R04→R03 at Asad Gate, College Gate, Dhanmondi 27 ...

### Mirpur 1 → Kamalapur

- Fewest stops: 14 hops, 15.56 km: Mirpur 1 -> Mirpur 2 -> Mirpur 10 -> Mirpur 14 -> Kochukhet -> Jahangir Gate -> Mohakhali -> Nabisco -> Satrasta -> Mogbazar -> Kakrail -> Paltan -> Gulistan -> Motijheel -> Kamalapur
- Shortest distance: 17 hops, 12.63 km: Mirpur 1 -> Ansar Camp -> Bangla College -> Technical -> Kallyanpur -> Shyamoli -> College Gate -> Asad Gate -> Khamarbari -> Farmgate -> Karwan Bazar -> Bangla Motor -> Mogbazar -> Kakrail -> Paltan -> Fakirapool -> Motijheel -> Kamalapur
- Same path? no.
- Fewest bus changes: **1** (routes R04 → R08); change R04→R08 at Asad Gate, Matsya Bhaban, Press Club ...

### Where "fewest stops" and "shortest distance" disagree

- Mirpur 1 → Chankharpul: fewest stops = 13 hops but 15.11 km; shortest = 15 hops, 10.17 km (+4.94 km for the fewest-stop path).
- Mugda → Mazar Road: fewest stops = 15 hops but 17.76 km; shortest = 17 hops, 13.34 km (+4.42 km for the fewest-stop path).
- Motijheel → Ansar Camp: fewest stops = 14 hops but 15.51 km; shortest = 15 hops, 11.47 km (+4.04 km for the fewest-stop path).

## 7. How compact is the network? (largest component)

- Average shortest path: 8.35 hops, 8.35 km.
- Diameter: 25 hops (e.g. Tongi ↔ Signboard).
- Longest shortest distance: 28.08 km (Tongi ↔ Signboard).
- Centre (smallest eccentricity, 13 hops): Mohakhali, Badda, Merul Badda, Nabisco.
- Bus changes needed over all stop pairs: 0 changes: 23.7%, 1 change: 61.1%, 2 changes: 14.9%, 3 changes: 0.2%.
- Route graph: 18 routes, 71 pairs of routes that share at least one stop.

## 8. Minimum spanning tree (the backbone)

- Kruskal: 99 edges, total 90.83 km. Prim: 99 edges, total 90.83 km. Same total: True.
- Edge count = |V| − c = 101 − 2 = 99: True; acyclic forest: True.
- Full network 118.43 km vs tree 90.83 km: the 20 links left out (27.60 km, 23.3% of the length) are redundancy.
- Cycle property check: every left-out link is at least as heavy as every tree link on the cycle it would close: True.
- Longest tree links: Rayerbag–Signboard 2.16 km; Tongi–Abdullahpur 1.99 km; Jahangir Gate–Kochukhet 1.93 km.
- Reading: the tree is the cheapest set of links that keeps every stop reachable. It is not a proposal for bus routes: trips along the tree can be much longer than on the full network.

## 9. Counting (Chapter 6)

- Stop pairs: C(101, 2) = 5050; actual links 119; so 2.36% of pairs are linked.
- Product rule: at a stop served by k routes a rider can change from any route to any other, k·(k−1) ordered choices. Gulistan: k=6, 30 choices; Bangla Motor: k=5, 20 choices; Asad Gate: k=4, 12 choices.
- Transfer stops (served by 2 or more routes): 64 of 101.
- Pigeonhole: route R12 lists 5 stops but only 4 distinct ones, so some stop must repeat (it is a loop route).

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

