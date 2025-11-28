# Dominio/Reparto.py
from dataclasses import dataclass, field
from typing import List, Dict
from Dominio.Modelos import Pedido


MAX_PEDIDOS_POR_LOTE = 7


@dataclass
class LoteReparto:
    pedidos_telefonos: List[str] = field(default_factory=list)

    def esta_completo(self) -> bool:
        return len(self.pedidos_telefonos) >= MAX_PEDIDOS_POR_LOTE

    def agregar_pedido(self, telefono: str) -> None:
        self.pedidos_telefonos.append(telefono)

    def vaciar(self) -> None:
        self.pedidos_telefonos.clear()


@dataclass
class GestorReparto:
    """
    Maneja la asignación de pedidos a un único repartidor.
    - lote_actual: hasta 7 pedidos
    - cola_espera: pedidos que esperan a que el lote actual se libere
    """
    lote_actual: LoteReparto = field(default_factory=LoteReparto)
    cola_espera: List[str] = field(default_factory=list)

    def asignar_pedido(self, telefono: str) -> bool:
        """
        Asigna el pedido al lote actual si hay lugar.
        Si el lote está completo, lo manda a la cola de espera.
        Devuelve True si DESPUÉS de asignar el pedido el lote quedó completo.
        """
        if not self.lote_actual.esta_completo():
            self.lote_actual.agregar_pedido(telefono)
            return self.lote_actual.esta_completo()

        # Lote ya lleno → pasa a cola de espera
        self.cola_espera.append(telefono)
        return False

    def obtener_lote_actual(self) -> List[str]:
        return list(self.lote_actual.pedidos_telefonos)

    def marcar_lote_enviado(self) -> List[str]:
        """
        Se llama luego de enviar el GIF al repartidor.
        Vacía el lote actual y lo rellena con la siguiente tanda (si hay).
        Devuelve la lista de teléfonos que formaban el lote enviado.
        """
        enviados = list(self.lote_actual.pedidos_telefonos)
        self.lote_actual.vaciar()

        # Si hay pedidos en cola, cargamos hasta 7 para el próximo lote
        while self.cola_espera and not self.lote_actual.esta_completo():
            tel = self.cola_espera.pop(0)
            self.lote_actual.agregar_pedido(tel)

        return enviados
