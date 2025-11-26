from dataclasses import dataclass, field
from typing import List, Tuple, Optional

@dataclass
class UnidadCarrito:
    #representa la unidad del producto en el carrito guardando su detalle
    detalle: str = ""  # "" = completa


@dataclass
class ItemCarrito:
    id_producto: str
    nombre: str
    precio: int
    unidades: List[UnidadCarrito] = field(default_factory=list)
    #la cantidad de producto en el carrito se guarda como una lista de unidades de ese producto


    @property
    def cantidad(self) -> int:
        return len(self.unidades)

    def agregar_unidades(self, detalle: str, cantidad: int) -> None:
        """
        Agrega 'cantidad' unidades con el mismo detalle.
        """
        for _ in range(cantidad):
            self.unidades.append(UnidadCarrito(detalle=detalle))


@dataclass
class Pedido:
    telefono_cliente: str
    ubicacion: Optional[Tuple[float, float]] = None
    direccion_texto: Optional[str] = None
    items: List[ItemCarrito] = field(default_factory=list)


    # 🔽 NUEVO: datos de ruta / entrega
    nodo_origen: Optional[int] = None
    nodo_destino: Optional[int] = None
    distancia_km: float = 0.0
    tiempo_estimado_min: float = 0.0
    path_nodos: List[int] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(item.precio * item.cantidad for item in self.items)

    def obtener_item(self, id_producto: str, nombre: str, precio: int) -> ItemCarrito:
        """
        Devuelve el ItemCarrito de ese producto si ya existe,
        si no, lo crea y lo agrega a la lista.
        """
        for it in self.items:
            if it.id_producto == id_producto:
                return it

        nuevo = ItemCarrito(id_producto=id_producto, nombre=nombre, precio=precio)
        self.items.append(nuevo)
        return nuevo

    def vaciar(self) -> None:
        self.items.clear()

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
