from dataclasses import dataclass, field
from typing import List, Dict

from Dominio.Modelos import Pedido

MAX_PEDIDOS_POR_LOTE = 7
ZONAS_VALIDAS = ("NO", "NE", "SO", "SE")


@dataclass
class LoteReparto:
    """
    Representa un lote de pedidos para un repartidor.
    """
    pedidos: List[Pedido] = field(default_factory=list)

    def esta_completo(self) -> bool:
        return len(self.pedidos) >= MAX_PEDIDOS_POR_LOTE

    def agregar_pedido(self, pedido: Pedido) -> None:
        self.pedidos.append(pedido)

    def vaciar(self) -> None:
        self.pedidos.clear()


@dataclass
class RepartidorZona:
    """
    Repartidor identificado por una etiqueta (NO, NE, SO, SE).
    AHORA puede entregar pedidos de cualquier zona geográfica del cliente.
    La 'zona' acá funciona como ID lógico del repartidor.
    """
    zona: str
    telefono_whatsapp: str
    lote_actual: LoteReparto = field(default_factory=LoteReparto)
    cola_espera: List[Pedido] = field(default_factory=list)
    pedidos_entregados: List[Pedido] = field(default_factory=list)

    def asignar_pedido(self, pedido: Pedido) -> bool:
        """
        Asigna el pedido al lote actual si hay lugar.
        Si el lote está completo, lo manda a la cola de espera.
        Devuelve True si DESPUÉS de asignar el pedido, el lote quedó completo.
        """
        if not self.lote_actual.esta_completo():
            self.lote_actual.agregar_pedido(pedido)
            return self.lote_actual.esta_completo()

        # Lote ya lleno → pasa a cola de espera
        self.cola_espera.append(pedido)
        return False

    def obtener_lote_actual(self) -> List[Pedido]:
        """
        Devuelve los pedidos del lote actual ORDENADOS
        por distancia desde el local (distancia_km ascendente).
        """
        pedidos = list(self.lote_actual.pedidos)
        pedidos.sort(key=lambda p: getattr(p, "distancia_km", 0.0))
        return pedidos

    def obtener_pedidos_pendientes(self) -> List[Pedido]:
        """
        Devuelve todos los pedidos que aún no se marcaron como entregados:
        - los del lote actual
        - los de la cola de espera
        """
        return list(self.lote_actual.pedidos) + list(self.cola_espera)

    def registrar_entrega(self, pedido: Pedido) -> None:
        """
        Registra un pedido como entregado.
        """
        self.pedidos_entregados.append(pedido)

    def marcar_lote_enviado(self) -> List[Pedido]:
        """
        Se llama luego de enviar la imagen al repartidor.
        Vacía el lote actual y lo rellena con la siguiente tanda (si hay).
        Devuelve la lista de pedidos que formaban el lote enviado.
        """
        enviados = list(self.lote_actual.pedidos)
        self.lote_actual.vaciar()

        # Si hay pedidos en cola, cargamos hasta 7 para el próximo lote
        while self.cola_espera and not self.lote_actual.esta_completo():
            p = self.cola_espera.pop(0)
            self.lote_actual.agregar_pedido(p)

        return enviados


@dataclass
class GestorReparto:
    """
    Maneja la asignación de pedidos a varios repartidores.
    Cada repartidor puede recibir pedidos de cualquier zona;
    los nuevos pedidos se asignan al repartidor con el lote más vacío.
    """
    repartidores: Dict[str, RepartidorZona] = field(default_factory=dict)

    @classmethod
    def desde_config(cls, mapa_telefonos: Dict[str, str]) -> "GestorReparto":
        """
        Crea un GestorReparto a partir de un dict {id_repartidor: telefono_wpp}.
        Por compatibilidad se usan labels NO, NE, SO, SE como IDs.
        """
        reps: Dict[str, RepartidorZona] = {}
        for zona, tel in mapa_telefonos.items():
            if zona not in ZONAS_VALIDAS:
                continue
            reps[zona] = RepartidorZona(zona=zona, telefono_whatsapp=tel)
        return cls(repartidores=reps)

    def asignar_pedido(self, pedido: Pedido) -> tuple[bool, str]:
        """
        Asigna el pedido al repartidor que tenga MENOS pedidos
        en su lote_actual, sin importar la zona del cliente.

        Devuelve (lote_lleno, repartidor_id).
        """
        if not self.repartidores:
            raise RuntimeError("No hay repartidores configurados en el GestorReparto.")

        # Elegimos el repartidor cuyo lote_actual tenga MENOS pedidos
        mejor_repartidor = min(
            self.repartidores.values(),
            key=lambda r: len(r.lote_actual.pedidos)
        )

        # Guardamos en el pedido a qué repartidor fue asignado
        pedido.repartidor_id = mejor_repartidor.zona

        lote_lleno = mejor_repartidor.asignar_pedido(pedido)

        return lote_lleno, mejor_repartidor.zona

    def obtener_lote_actual(self, repartidor_id: str) -> List[Pedido]:
        if repartidor_id not in self.repartidores:
            return []
        return self.repartidores[repartidor_id].obtener_lote_actual()

    def marcar_lote_enviado(self, repartidor_id: str) -> List[Pedido]:
        if repartidor_id not in self.repartidores:
            return []
        return self.repartidores[repartidor_id].marcar_lote_enviado()
