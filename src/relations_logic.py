"""Chapters 1 and 9: connectivity as a quantified statement, and reachability as a relation.

- "Directly linked" is the relation D = {(u, v) : {u, v} ∈ E}. It is symmetric.
- "Can reach" is the reflexive-transitive closure of D, computed with Warshall's algorithm.
- "Can reach" is an equivalence relation; its equivalence classes are the connected components.

Warshall's algorithm costs O(V^3), so use it on the sample (and, if you like, on Dhaka:
about 1 million steps for 100 stops, still only a second or two).
"""
from __future__ import annotations

from .algorithms import bfs


def adjacency_matrix(adj: dict, order: list[str]) -> list[list[int]]:
    """M[i][j] = 1 if order[i] and order[j] are directly linked."""
    idx = {v: i for i, v in enumerate(order)}
    n = len(order)
    M = [[0] * n for _ in range(n)]
    for u in adj:
        for v in adj[u]:
            M[idx[u]][idx[v]] = 1
    return M


def warshall(M: list[list[int]], reflexive: bool = True) -> list[list[int]]:
    """Transitive closure (Section 9.4). W_k[i][j] = W_(k-1)[i][j] or (W_(k-1)[i][k] and W_(k-1)[k][j]).
    With reflexive=True the diagonal is set to 1 first ("every stop can reach itself")."""
    n = len(M)
    W = [row[:] for row in M]
    if reflexive:
        for i in range(n):
            W[i][i] = 1
    for k in range(n):
        Wk = W[k]
        for i in range(n):
            if W[i][k]:
                Wi = W[i]
                for j in range(n):
                    if Wk[j]:
                        Wi[j] = 1
    return W


def is_reflexive(M) -> bool:
    return all(M[i][i] for i in range(len(M)))


def is_symmetric(M) -> bool:
    n = len(M)
    return all(M[i][j] == M[j][i] for i in range(n) for j in range(n))


def is_transitive(M) -> bool:
    n = len(M)
    return all(not (M[i][k] and M[k][j]) or M[i][j]
               for i in range(n) for k in range(n) for j in range(n))


def equivalence_classes(M, order: list[str]) -> list[set[str]]:
    """Class of x = { y : x R y }. For an equivalence relation the classes partition the set."""
    classes, seen = [], set()
    for i, x in enumerate(order):
        if x in seen:
            continue
        cls = {order[j] for j in range(len(order)) if M[i][j]}
        seen |= cls
        classes.append(cls)
    classes.sort(key=lambda c: (-len(c), min(c)))
    return classes


def connectivity_by_quantifiers(adj: dict):
    """Evaluate  ∀u ∀v  path(u, v)  directly.

    The negation is  ∃u ∃v  ¬path(u, v).  If the statement is false we return a witness
    (u, v) for the negation — two stops with no path between them.
    Returns (holds: bool, witness: tuple | None).
    """
    vertices = sorted(adj)
    for u in vertices:
        reach, _ = bfs(adj, u)
        for v in vertices:
            if v not in reach:
                return False, (u, v)
    return True, None
