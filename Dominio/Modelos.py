from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class Cliente:
    #Representa un cliente del sistema.
   
    telefono: str
    nombre: str
    pedidos: List["Pedido"] = field(default_factory=list)

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
        #Agrega 'cantidad' unidades con el mismo detalle.
        
        for _ in range(cantidad):
            self.unidades.append(UnidadCarrito(detalle=detalle))


@dataclass
class Pedido:
    telefono_cliente: str
    ubicacion: Optional[Tuple[float, float]] = None
    direccion_texto: Optional[str] = None
    items: List[ItemCarrito] = field(default_factory=list)

    zona: Optional[str] = None  # "NO", "NE", "SO", "SE"

    nodo_origen: Optional[int] = None
    nodo_destino: Optional[int] = None
    distancia_km: float = 0.0
    tiempo_estimado_min: float = 0.0
    path_nodos: List[int] = field(default_factory=list)

    codigo_validacion: Optional[str] = None
    entregado: bool = False
    calificacion: Optional[int] = None

    @property
    def total(self) -> int:
        return sum(item.precio * item.cantidad for item in self.items)

    def obtener_item(self, id_producto: str, nombre: str, precio: int) -> ItemCarrito:
        
       # Devuelve el ItemCarrito del producto si ya existe en el pedido, o lo crea y lo agrega a la lista de items.
        
        for item in self.items:
            if item.id_producto == id_producto:
                return item

        nuevo = ItemCarrito(
            id_producto=id_producto,
            nombre=nombre,
            precio=precio,
        )
        self.items.append(nuevo)
        return nuevo

    def vaciar(self) -> None:
        self.items.clear()

    def agregar_item(
        self,
        id_producto: str,
        nombre: str,
        precio: int,
        detalle: str,
        cantidad: int = 1,
    ) -> None:
        
        #Agrega 'cantidad' unidades de un producto al pedido, cada una con su 'detalle'.  El detalle se guarda en UnidadCarrito.detalle, no en ItemCarrito.
       
        item = self.obtener_item(id_producto=id_producto, nombre=nombre, precio=precio)
        item.agregar_unidades(detalle=detalle, cantidad=cantidad)
