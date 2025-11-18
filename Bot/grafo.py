
import math

class GrafoPedidos:
    def __init__(self):
        self.grafo = {}

    def agregar_nodo(self, nombre):
        if nombre not in self.grafo:
            self.grafo[nombre] = {}

    def agregar_arista(self, origen, destino, distancia):
        if origen in self.grafo and destino in self.grafo:
            self.grafo[origen][destino] = distancia
            self.grafo[destino][origen] = distancia  # No dirigido

    def calcular_distancia(self, ubicacion1, ubicacion2):
        """Calcula la distancia euclidiana entre dos puntos (lat, lon)"""
        lat1, lon1 = ubicacion1
        lat2, lon2 = ubicacion2
        return round(math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) * 111, 2)  # km aprox.

    def generar_rutas(self, restaurante, pedidos):
        """
        Crea un grafo conectando el restaurante con todos los clientes de la tanda.
        Cada cliente se conecta también con el siguiente más cercano.
        """
        self.agregar_nodo(restaurante)
        for pedido in pedidos:
            self.agregar_nodo(pedido.cliente)
            distancia = self.calcular_distancia(pedido.ubicacion, (0, 0))  # (0,0) = restaurante
            self.agregar_arista(restaurante, pedido.cliente, distancia)

    def mostrar_grafo(self):
        for nodo, conexiones in self.grafo.items():
            print(f"{nodo} -> {conexiones}")

    def obtener_vecinos(self, nodo):
        return self.grafo.get(nodo, {})

    def dijkstra(self, inicio):
        """Calcula la ruta más corta desde el nodo de inicio (restaurante)"""
        distancias = {nodo: float('inf') for nodo in self.grafo}
        distancias[inicio] = 0
        visitados = set()

        while len(visitados) < len(self.grafo):
            nodo_actual = min(
                (n for n in self.grafo if n not in visitados),
                key=lambda n: distancias[n],
                default=None
            )

            if nodo_actual is None:
                break

            visitados.add(nodo_actual)
            for vecino, distancia in self.grafo[nodo_actual].items():
                nueva_dist = distancias[nodo_actual] + distancia
                if nueva_dist < distancias[vecino]:
                    distancias[vecino] = nueva_dist

        return distancias
