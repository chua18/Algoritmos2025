# Dominio/rutas.py
from typing import List, Tuple
import heapq

import osmnx as ox
import networkx as nx  # por si querés usar funciones de networkx también


# Cargar el grafo de Salto UNA sola vez
G = ox.graph_from_place("Salto, Uruguay", network_type="drive")

# Configurar atributos de las aristas: maxspeed y weight (tiempo aproximado)
for edge in G.edges:
    maxspeed = 40  # valor por defecto

    if "maxspeed" in G.edges[edge]:
        raw = G.edges[edge]["maxspeed"]
        if isinstance(raw, list):
            # tomamos la menor velocidad de la lista
            try:
                speeds = [int(str(s).split()[0]) for s in raw]
                maxspeed = min(speeds)
            except Exception:
                maxspeed = 40
        elif isinstance(raw, str):
            try:
                maxspeed = int(raw.split()[0])
            except Exception:
                maxspeed = 40

    G.edges[edge]["maxspeed"] = maxspeed
    # weight ≈ tiempo = longitud / velocidad
    G.edges[edge]["weight"] = G.edges[edge]["length"] / maxspeed


def heuristica(n1: int, n2: int) -> float:
    """
    Heurística para A*: distancia euclídea entre dos nodos (en coordenadas x,y).
    """
    x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
    x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def coordenadas_a_nodo(lat: float, lon: float) -> int:
    """
    Convierte lat/lon a nodo más cercano del grafo.
    Ojo: osmnx usa (x = lon, y = lat).
    """
    return ox.distance.nearest_nodes(G, lon, lat)


def a_star_ruta(orig: int, dest: int) -> Tuple[List[int], float, float]:
    """
    Implementación de A* para el proyecto.

    Devuelve:
      - path: lista de nodos (int) desde orig hasta dest
      - distancia_km: distancia total aproximada en km
      - tiempo_min: tiempo aproximado en minutos
    """

    # Inicializar todos los nodos
    for n in G.nodes:
        G.nodes[n]["g_score"] = float("inf")   # coste desde el origen
        G.nodes[n]["f_score"] = float("inf")   # g + heurística
        G.nodes[n]["previous"] = None          # para reconstruir camino

    G.nodes[orig]["g_score"] = 0.0
    G.nodes[orig]["f_score"] = heuristica(orig, dest)

    # cola de prioridad con (f_score, nodo)
    pq: List[Tuple[float, int]] = [(G.nodes[orig]["f_score"], orig)]

    while pq:
        _, node = heapq.heappop(pq)

        if node == dest:
            # ya encontramos el mejor camino hacia dest
            break

        # recorrer vecinos
        for u, v, k in G.out_edges(node, keys=True):
            edge_data = G.edges[(u, v, k)]
            w = edge_data["weight"]  # coste (tiempo aproximado)

            tentative_g = G.nodes[node]["g_score"] + w

            if tentative_g < G.nodes[v]["g_score"]:
                G.nodes[v]["g_score"] = tentative_g
                G.nodes[v]["f_score"] = tentative_g + heuristica(v, dest)
                G.nodes[v]["previous"] = node
                heapq.heappush(pq, (G.nodes[v]["f_score"], v))

    # Reconstruir camino
    if G.nodes[dest]["previous"] is None and dest != orig:
        # no se encontró camino válido
        return [], 0.0, 0.0

    path: List[int] = []
    curr = dest
    dist_m = 0.0
    speeds = []

    while curr != orig:
        prev = G.nodes[curr]["previous"]
        path.append(curr)

        edge_data = G.get_edge_data(prev, curr)
        if edge_data:
            # get_edge_data devuelve dict de claves (keys) → tomamos la primera
            e0 = list(edge_data.values())[0]
            dist_m += e0["length"]
            speeds.append(e0["maxspeed"])

        curr = prev

    path.append(orig)
    path.reverse()

    dist_km = dist_m / 1000.0
    vel_prom = (sum(speeds) / len(speeds)) if speeds else 30.0
    tiempo_min = dist_km / vel_prom * 60.0

    return path, dist_km, tiempo_min
