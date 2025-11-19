from dataclasses import dataclass, field
from typing import List, Tuple, Optional

@dataclass
class ItemCarrito:
    id_producto: str
    nombre: str
    precio: int
    cantidad: int = 1


@dataclass
class Pedido:
    telefono_cliente: str
    ubicacion: Optional[Tuple[float, float]] = None
    items: List[ItemCarrito] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(item.precio * item.cantidad for item in self.items)

    def agregar_item(self, item: ItemCarrito) -> None:
        """Si el producto ya está en el carrito, solo aumenta la cantidad."""
        for existente in self.items:
            if existente.id_producto == item.id_producto:
                existente.cantidad += item.cantidad
                return
        self.items.append(item)
