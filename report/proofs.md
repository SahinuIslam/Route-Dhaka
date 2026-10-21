# Proofs for the report

Each proof below is short enough to present on one slide. Under each one, a
"Checked on our data" line tells you where the program confirms the statement
on the real numbers (see `results/<dataset>/summary.md`). A check on data is
not a proof — it only shows the code agrees with the theorem — but it is a
good way to connect the mathematics to the project.

Notation: G = (V, E) is a finite undirected simple graph, n = |V|, m = |E|,
deg(v) = number of edges at v.

---

## 1. Handshaking theorem (direct proof) — Section 10.2

**Theorem.** Σ_{v ∈ V} deg(v) = 2m.

**Proof.** Count the pairs (v, e) where v is a vertex, e is an edge and v is an
end point of e. Counting by vertices: vertex v appears in exactly deg(v) such
pairs, so the count is Σ deg(v). Counting by edges: every edge {u, w} has exactly
two end points, so it appears in exactly 2 pairs, and the count is 2m. Both
counts describe the same set, so they are equal. ∎

**Corollary.** The number of stops with odd degree is even. (Σ deg(v) is even;
the even degrees add up to an even number, so the odd degrees must also add up
to an even number, which needs an even count of odd terms.)

*Checked on our data:* Section 2 of the summary — sum of degrees = 2|E|
(sample 22 = 22; Dhaka 238 = 238).

---

## 2. A tree with n vertices has n − 1 edges (induction) — Section 11.1

**Lemma.** Every tree with n ≥ 2 vertices has a leaf (a vertex of degree 1).

*Proof of the lemma.* Take a path P = v₀ v₁ … v_k in the tree with as many edges
as possible (a longest path; one exists because the graph is finite, and k ≥ 1
because a tree with n ≥ 2 vertices is connected and so has an edge). Suppose
v_k had a neighbour x other than v_{k−1}. If x is on P, then x … v_k x is a cycle,
which a tree does not have. If x is not on P, then v₀ … v_k x is a longer path,
contradicting the choice of P. So v_k has degree 1. ∎

**Theorem.** For every n ≥ 1, a tree with n vertices has exactly n − 1 edges.

**Proof (induction on n).**
*Base case n = 1:* the only tree is a single vertex with 0 = 1 − 1 edges.
*Inductive step:* assume every tree with n vertices has n − 1 edges, and let T be
a tree with n + 1 ≥ 2 vertices. By the lemma, T has a leaf ℓ. Delete ℓ and its one
edge. The result T′ is still connected (no path between two other vertices passed
through ℓ, since a path entering ℓ could not leave it) and still has no cycle
(deleting cannot create one), so T′ is a tree with n vertices. By the hypothesis
T′ has n − 1 edges, so T has (n − 1) + 1 = n edges. ∎

**Corollary (spanning forest).** A forest whose c trees contain n vertices in
total has n − c edges: add n_i − 1 over the c trees.

*Checked on our data:* Section 8 — Kruskal returns |V| − c edges
(sample 11 − 1 = 10; Dhaka 101 − 2 = 99, because Jinjira is isolated).

---

## 3. Cycle property of minimum spanning trees (contradiction) — Section 11.5

**Theorem.** Let C be a cycle in a connected weighted graph and let e be an edge of
C that is strictly heavier than every other edge of C. Then no minimum spanning
tree contains e.

**Proof.** Suppose, for contradiction, that a minimum spanning tree T contains e =
{u, v}. Removing e from T splits T into two pieces, one containing u and one
containing v. The rest of the cycle, C − e, is a path from u to v, so it must
cross between the two pieces through some edge f ≠ e. Then T′ = T − e + f is
connected and has n − 1 edges, so it is a spanning tree. Its weight is
w(T) − w(e) + w(f) < w(T), because w(f) < w(e). That contradicts the minimality
of T. ∎

This is exactly why Kruskal's algorithm may skip an edge that would close a
cycle: when it is considered, every other edge on that cycle is already in the
tree and is no heavier.

*Checked on our data:* Section 8 — "Cycle property check: True". Every link left
out of the tree is at least as heavy as every tree link on the cycle it would
close. In the sample, the only cycle loses Mirpur 10 – Agargaon (3.40 km, its
heaviest link).

---

## 4. Dijkstra's algorithm is correct (induction on |S|) — Section 10.6

**Setting.** Weights are non-negative. S is the set of stops whose distance is
"final"; d(v) is the tentative distance; δ(v) is the true shortest distance from
the source s.

**Claim.** Whenever a vertex u is moved into S, d(u) = δ(u).

**Proof (induction on |S|).**
*Base case:* the first vertex moved into S is s with d(s) = 0 = δ(s).
*Inductive step:* assume every vertex already in S has d = δ, and let u be the
next vertex chosen (smallest d outside S). Suppose, for contradiction, that some
path P from s to u is shorter than d(u). P starts in S and ends outside S, so it
has a first edge (x, y) with x ∈ S and y ∉ S. When x entered S, the algorithm
relaxed (x, y), so d(y) ≤ δ(x) + w(x, y) = length of P up to y. Weights are
non-negative, so the length of P up to y is at most the length of P. Hence
d(y) ≤ length(P) < d(u). If y = u this says d(u) < d(u), which is impossible.
Otherwise y, not u, had the smallest tentative distance outside S and would have
been chosen — a contradiction. So d(u) = δ(u). ∎

The proof breaks if a weight is negative (the step "a prefix of P is no longer
than P" fails). That is why the code checks that every weight is positive, and
why a zero-length edge is treated as a data error.

*Checked on our data:* Section 10 — our Dijkstra distances equal NetworkX's for
every stop, and the step-by-step table in Section 6 lets you compare with a hand
trace on the sample.

---

## 5. Connected components are equivalence classes — Sections 9.5 and 10.4

Define u ~ v ("u can reach v") if there is a path from u to v (a path of length
0 counts, so u ~ u).

- **Reflexive:** u ~ u by the path of length 0.
- **Symmetric:** if u = x₀, x₁, …, x_k = v is a path, then x_k, …, x₀ is a path from v
  to u, because every edge {x_i, x_{i+1}} is unordered.
- **Transitive:** if there is a path u → v and a path v → w, joining them gives a
  walk from u to w; a walk always contains a path between its end points
  (cut out any closed loop between two visits to the same vertex).

So ~ is an equivalence relation. Its equivalence classes partition V, and each
class is a maximal set of mutually reachable stops — by definition a connected
component. The relation ~ is the reflexive-transitive closure of "directly
linked", which is what Warshall's algorithm computes.

*Checked on our data:* Section 4 — the Warshall closure is reflexive, symmetric
and transitive, and its classes equal the BFS components.

---

## 6. Connectivity in predicate logic — Section 1.4

Let P(u, v) mean "there is a path from u to v". Then

- "The network is connected" is **∀u ∀v P(u, v)**.
- Its negation is ¬∀u ∀v P(u, v) ≡ **∃u ∃v ¬P(u, v)**.

To show the network is NOT connected, one witness pair is enough; to show it IS
connected, the statement must be checked for every pair. The program does
exactly this and prints the witness. In the Dhaka data the witness is
(Tongi, Jinjira): Jinjira is recorded as a stop but no route in the data serves
it yet — a property of the data, not necessarily of the city.

---

## 7. Pigeonhole: shortest paths never repeat a stop — Section 6.2

**Claim.** A shortest path (in hops or in km with positive weights) visits no stop
twice, so it has at most n − 1 edges.

**Proof.** A walk with k edges lists k + 1 stops. If k + 1 > n, then by the
pigeonhole principle (k + 1 pigeons, n holes) some stop appears twice. Cutting
out the part of the walk between its two visits gives a walk with the same end
points and strictly fewer edges and strictly smaller positive length, so a walk
with a repeated stop is never shortest. ∎

The same principle explains rule W1: route R12 lists 5 positions but only 4
distinct stops, so a repeat is forced — it is a loop route.

---

## 8. Counting — Section 6.4

- Possible stop pairs: C(n, 2) = n(n − 1)/2. Density = m / C(n, 2).
  Dhaka core: C(101, 2) = 5050 possible pairs, 119 links, density ≈ 0.024.
  This is why an adjacency list (O(n + m) space) beats an adjacency matrix
  (O(n²) space) here.
- Product rule: at a stop served by k routes, a rider can change from any of
  k routes to any of the other k − 1, giving k(k − 1) ordered changes
  (Gulistan in the Dhaka data: k = 6, 30 choices).
