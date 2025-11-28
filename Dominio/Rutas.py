from typing import List, Optional

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

def _parse_maxspeed(raw) -> float:
    if raw is None:
        return 40.0
    if isinstance(raw, (list, tuple)):
        raw = raw[0]
    if isinstance(raw, str):
        digits = "".join(ch for ch in raw if ch.isdigit())
        if digits:
            return float(digits)
        return 40.0
    try:
        return float(raw)
    except Exception:
        return 40.0

# -----------------------------------------------------------
# A* PARA LÓGICA (DISTANCIA / TIEMPO)
# -----------------------------------------------------------


def coordenadas_a_nodo(lat: float, lon: float) -> int:
    
   # Convierte lat/lon a nodo más cercano del grafo.
  
    
    return ox.distance.nearest_nodes(G, lon, lat)


def a_star_ruta(nodo_origen: int, nodo_destino: int):
   
   # Calcula ruta más corta por 'length' entre nodo_origen y nodo_destino.
   # Devuelve: path (lista de nodos), dist_km, tiempo_min.
  
    try:
        path = nx.shortest_path(G, nodo_origen, nodo_destino, weight="length")
    except nx.NetworkXNoPath:
        return [nodo_origen], 0.0, 0.0

    if not path or len(path) == 1:
        return path, 0.0, 0.0

    dist_m = 0.0
    speeds = []

    for u, v in zip(path, path[1:]):
        edge_data = G.get_edge_data(u, v)
        if not edge_data:
            continue

        e0 = list(edge_data.values())[0]
        length = float(e0.get("length", 0.0))
        maxspeed = _parse_maxspeed(e0.get("maxspeed", 40.0))

        dist_m += length
        speeds.append(maxspeed)

    dist_km = dist_m / 1000.0

    if speeds:
        vel_prom = sum(speeds) / len(speeds)
        tiempo_min = dist_km / vel_prom * 60.0
    else:
        vel_prom = 40.0
        tiempo_min = dist_km / vel_prom * 60.0 if dist_km > 0 else 0.0

    return path, dist_km, tiempo_min

# -----------------------------------------------------------
# GIF PARA LOTE DE PEDIDOS (USANDO coordenadas_gifs)
# -----------------------------------------------------------

def generar_gif_ruta_lote(pedidos: List[Pedido]) -> Optional[str]:
 
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

    gif_path, png_path = create_gif("pathfinding_lote_reparto_salto.gif")

    if not png_path:
        return None

    return png_path
