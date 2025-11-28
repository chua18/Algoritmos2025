from dataclasses import dataclass, field
from typing import List
from Dominio.Modelos import Pedido

MAX_PEDIDOS_POR_LOTE = 7


@dataclass
class LoteReparto:
    # Ahora guardamos directamente los pedidos (no solo teléfonos)
    pedidos: List[Pedido] = field(default_factory=list)

    def esta_completo(self) -> bool:
        return len(self.pedidos) >= MAX_PEDIDOS_POR_LOTE

    def agregar_pedido(self, pedido: Pedido) -> None:
        """
        Agrega un pedido al lote si no está repetido.
        """
        if any(p.telefono_cliente == pedido.telefono_cliente for p in self.pedidos):
            # ya estaba agregado este teléfono
            return
        self.pedidos.append(pedido)

    def vaciar(self) -> None:
        self.pedidos.clear()


@dataclass
class GestorReparto:
    """
    Maneja la asignación de pedidos a un único repartidor.
    - lote_actual: hasta 7 pedidos
    - cola_espera: pedidos que esperan a que el lote actual se libere
    """
    lote_actual: LoteReparto = field(default_factory=LoteReparto)
    cola_espera: List[Pedido] = field(default_factory=list)

    def asignar_pedido(self, pedido: Pedido) -> bool:
        """
        Asigna el pedido al lote actual si hay lugar.
        Si el lote está completo, lo manda a la cola de espera.
        Devuelve True si DESPUÉS de asignar el pedido el lote quedó completo.
        """
        # Evitar duplicar por teléfono
        if any(p.telefono_cliente == pedido.telefono_cliente for p in self.lote_actual.pedidos):
            return self.lote_actual.esta_completo()

        if not self.lote_actual.esta_completo():
            self.lote_actual.agregar_pedido(pedido)
            return self.lote_actual.esta_completo()

        # Si el lote ya estaba lleno, va a cola de espera (sin duplicar)
        if not any(p.telefono_cliente == pedido.telefono_cliente for p in self.cola_espera):
            self.cola_espera.append(pedido)
        return False

    def obtener_lote_actual(self) -> List[Pedido]:
        return list(self.lote_actual.pedidos)

    def marcar_lote_enviado(self) -> List[Pedido]:
        """
        Se llama luego de enviar el GIF al repartidor.
        Vacía el lote actual y lo rellena con la siguiente tanda (si hay).
        Devuelve la lista de pedidos que formaban el lote enviado.
        """
        enviados = list(self.lote_actual.pedidos)
        self.lote_actual.vaciar()

        # Si hay pedidos en cola, cargamos hasta 7 para el próximo lote
        while self.cola_espera and not self.lote_actual.esta_completo():
            pedido = self.cola_espera.pop(0)
            self.lote_actual.agregar_pedido(pedido)

        return enviados
