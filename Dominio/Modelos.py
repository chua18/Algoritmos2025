from dataclasses import dataclass, field
from typing import List, Tuple, Optional

@dataclass
class ItemCarrito:
    id_producto: str
    nombre: str
    precio: int
    cantidad: int = 1
    detalle: str = ""   # 👈 “sin panceta”, “completa”, etc.


@dataclass
class Pedido:
    telefono_cliente: str
    ubicacion: Optional[Tuple[float, float]] = None
    direccion_texto: Optional[str] = None  # NUEVO
    items: List[ItemCarrito] = field(default_factory=list)

    @property
    def total(self) -> int:
        """
        Total con descuento:
        - Para cada producto (id_producto), si la suma de cantidades >= 3,
          aplica 5% de descuento sobre el subtotal de ese producto.
        """
        # Agrupamos por producto
        productos = {}  # id_producto -> {"cantidad": int, "subtotal": int}
        for item in self.items:
            key = item.id_producto
            subtotal_item = item.precio * item.cantidad
            if key not in productos:
                productos[key] = {"cantidad": 0, "subtotal": 0}
            productos[key]["cantidad"] += item.cantidad
            productos[key]["subtotal"] += subtotal_item

        total = 0
        for data in productos.values():
            if data["cantidad"] >= 3:
                # 5% de descuento para ese grupo
                total += int(round(data["subtotal"] * 0.95))
            else:
                total += data["subtotal"]

        return total

    def agregar_item(self, item: ItemCarrito) -> None:
        """
        Si el producto ya está en el carrito con el mismo 'detalle',
        solo aumenta la cantidad. Si el detalle cambia, es otra “sub-línea”.
        """
        for existente in self.items:
            if (existente.id_producto == item.id_producto
                    and existente.detalle == item.detalle):
                existente.cantidad += item.cantidad
                return
        self.items.append(item)
