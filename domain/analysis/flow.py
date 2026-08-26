"""Flusso massimo bipartito (Dinic) e lato sorgente del taglio minimo, senza
dipendenze. Serve al violatore di Hall: in una rete con gli archi centrali
infiniti, il taglio minimo *e'* l'insieme di Hall deficitario (hall.py, §3.2
della spec). Algoritmo generico — non sa niente di orari."""

from collections import deque

INF = 10 ** 9


class MaxFlow:
    def __init__(self, n):
        self.n = n
        self.graph = [[] for _ in range(n)]   # nodo → [[dest, capacita', indice inverso]]

    def add_edge(self, u, v, cap):
        self.graph[u].append([v, cap, len(self.graph[v])])
        self.graph[v].append([u, 0, len(self.graph[u]) - 1])

    def _levels(self, s, t):
        self.level = [-1] * self.n
        self.level[s] = 0
        queue = deque([s])
        while queue:
            u = queue.popleft()
            for v, cap, _ in self.graph[u]:
                if cap > 0 and self.level[v] < 0:
                    self.level[v] = self.level[u] + 1
                    queue.append(v)
        return self.level[t] >= 0

    def _augment(self, u, t, limit):
        if u == t:
            return limit
        while self.seen[u] < len(self.graph[u]):
            edge = self.graph[u][self.seen[u]]
            v, cap, rev = edge
            if cap > 0 and self.level[v] == self.level[u] + 1:
                pushed = self._augment(v, t, min(limit, cap))
                if pushed > 0:
                    edge[1] -= pushed
                    self.graph[v][rev][1] += pushed
                    return pushed
            self.seen[u] += 1
        return 0

    def max_flow(self, s, t):
        total = 0
        while self._levels(s, t):
            self.seen = [0] * self.n
            while True:
                pushed = self._augment(s, t, INF)
                if pushed == 0:
                    break
                total += pushed
        return total

    def source_side(self, s):
        """I nodi raggiungibili dalla sorgente nel grafo residuo, dopo il
        flusso massimo: il lato sorgente del taglio minimo."""
        seen = {s}
        queue = deque([s])
        while queue:
            u = queue.popleft()
            for v, cap, _ in self.graph[u]:
                if cap > 0 and v not in seen:
                    seen.add(v)
                    queue.append(v)
        return seen
