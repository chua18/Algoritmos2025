# Dominio/rutas.py
from typing import List, Tuple, Optional
import heapq

import osmnx as ox
import networkx as nx  # por si querés usar funciones de networkx también

from Dominio.Modelos import Pedido

# 👇 IMPORTAMOS LAS FUNCIONES DEL MÓDULO DE GIFS
# Asegurate de que el archivo se llame exactamente `coordenadas_gifs.py`
from Algoritmos.coordenadas_gifs import (
    frames,
    a_star_gif,          # algoritmo A* que pinta el grafo y llena frames
    reconstruct_path_gif,
    create_gif,
)

# -----------------------------------------------------------
# GRAFO DE SALTO (una sola vez)
# -----------------------------------------------------------

# Cargar el grafo de Salto, Uruguay
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


# -----------------------------------------------------------
# A* PARA LÓGICA (DISTANCIA / TIEMPO)
# -----------------------------------------------------------

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
    Implementación de A* para el proyecto (solo lógica).

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


# -----------------------------------------------------------
# GIF PARA LOTE DE PEDIDOS (USANDO coordenadas_gifs)
# -----------------------------------------------------------

def generar_gif_ruta_lote(pedidos: List[Pedido]) -> Optional[str]:
    """
    Genera un GIF para un lote de pedidos, encadenando
    la ruta local -> pedido1 -> pedido2 -> ... en orden.

    Para el GIF usamos las funciones de `coordenadas_gifs`:
    - a_star_gif (que recalcula la ruta y pinta el grafo)
    - reconstruct_path_gif
    - create_gif

    Devuelve el path del GIF o None si falla.
    """

    # Filtramos pedidos que tengan nodos válidos
    pedidos_validos = [
        p for p in pedidos
        if p.nodo_origen is not None and p.nodo_destino is not None
    ]
    if not pedidos_validos:
        return None

    # En este ejemplo todos usan el mismo nodo_origen (el del local)
    nodo_inicio = pedidos_validos[0].nodo_origen

    # Orden simple: por distancia_km ascendente (más cercanos primero)
    pedidos_ordenados = sorted(
        pedidos_validos,
        key=lambda p: p.distancia_km
    )

    # Limpiamos los frames globales del módulo de GIFs
    frames.clear()

    nodo_actual = nodo_inicio
    hay_algo = False

    for idx, p in enumerate(pedidos_ordenados, start=1):
        # Para el GIF usamos el A* propio del módulo de GIFs
        a_star_gif(nodo_actual, p.nodo_destino)
        ok = reconstruct_path_gif(nodo_actual, p.nodo_destino, f"Lote #{idx}")
        if not ok:
            continue

        nodo_actual = p.nodo_destino
        hay_algo = True

    if not hay_algo:
        return None

    gif_file = create_gif("Lote_Reparto", duration=600)
    return gif_file
