# Dominio/Pedidos.py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from Menu import menuCompleto  # usamos tu menuCompleto con 'nombre', 'precio', 'categoria', 'descripcion'

PAGE_SIZE = 5

# ------------------ MODELOS ------------------ #

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
        """
        Si el producto ya está en el carrito, solo aumenta cantidad.
        Si no está, lo agrega.
        """
        for existente in self.items:
            if existente.id_producto == item.id_producto:
                existente.cantidad += item.cantidad
                return
        self.items.append(item)


# ------------------ LÓGICA DE MENÚ (REUTILIZABLE) ------------------ #

def get_paginated_menu(page: int = 1, categoria: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Devuelve una página de productos desde menuCompleto.
    Si pasás categoría, filtra por ese campo.
    """
    productos = menuCompleto

    if categoria is not None:
        productos = [
            item for item in menuCompleto
            if item.get("categoria", "").lower() == categoria.lower()
        ]

    inicio = (page - 1) * PAGE_SIZE
    fin = inicio + PAGE_SIZE
    return productos[inicio:fin]
