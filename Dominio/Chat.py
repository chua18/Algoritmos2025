# Dominio/Chat.py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from Menu import menuCompleto  # <-- tu menú de productos

PAGE_SIZE = 5


@dataclass
class Pedido:
    cliente: str
    items: List[Dict[str, Any]] = field(default_factory=list)


def get_paginated_menu(page: int = 1, categoria: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Devuelve una “página” de productos desde menuCompleto.
    Si se pasa categoría, filtra por ese campo.
    """
    productos = menuCompleto

    if categoria:
        productos = [
            p for p in menuCompleto
            if p.get("categoria", "").lower() == categoria.lower()
        ]

    inicio = (page - 1) * PAGE_SIZE
    fin = inicio + PAGE_SIZE
    return productos[inicio:fin]


class Chat:
    def __init__(self) -> None:
        # Estado para el paginado / filtros
        self.pagina_actual: int = 1
        self.categoria_actual: Optional[str] = None
        self.orden_por_precio: Optional[str] = None  # "asc", "desc" o None

        # Si más adelante querés, aquí podrías guardar pedidos por teléfono, etc.
        self.pedidos: Dict[str, Pedido] = {}

    # ----------------- MENÚ PAGINADO ----------------- #

    def _obtener_menu_actual(self) -> List[Dict[str, Any]]:
        productos = get_paginated_menu(self.pagina_actual, self.categoria_actual)

        if self.orden_por_precio == "asc":
            productos = sorted(productos, key=lambda p: p["precio"])
        elif self.orden_por_precio == "desc":
            productos = sorted(productos, key=lambda p: p["precio"], reverse=True)

        return productos

    def generar_mensaje_menu(self) -> Dict[str, Any]:
        """
        Construye el objeto 'interactive' para WhatsApp List
        en base a la página y categoría actuales.
        ES EXACTAMENTE lo que main.py espera que devuelva.
        """
        productos = self._obtener_menu_actual()

        rows: List[Dict[str, Any]] = []

        # Filas de productos
        for producto in productos:
            rows.append({
                "id": f"producto_{producto['id']}",
                "title": f"{producto['nombre']} - ${producto['precio']}",
                "description": producto["descripcion"],
            })

        # Filas de navegación / acciones
        if self.pagina_actual > 1:
            rows.append({
                "id": "prev_page",
                "title": "⬅️ Página anterior",
                "description": "Volver a la página anterior",
            })

        rows.append({
            "id": "next_page",
            "title": "➡️ Siguiente página",
            "description": "Ver más productos",
        })

        # Opcionales (los nombres matchean con lo que usás en main.py)
        rows.append({
            "id": "ordenar",
            "title": "↕️ Ordenar por precio",
            "description": "Alternar entre más barato y más caro",
        })
        rows.append({
            "id": "go_first_page",
            "title": "⏮ Volver al inicio",
            "description": "Ir a la primera página del menú",
        })
        # Si después querés filtrar por categoría, podés usar "filtrar_categoria"

        mensaje_interactivo: Dict[str, Any] = {
            "type": "list",
            "header": {
                "type": "text",
                "text": "Menú de productos",
            },
            "body": {
                "text": "🍔 *Menú disponible:*\nSeleccioná un producto o una acción.\n",
            },
            "footer": {
                "text": f"📄 Página {self.pagina_actual}",
            },
            "action": {
                "button": "Ver opciones",
                "sections": [
                    {
                        "title": "Productos disponibles",
                        "rows": rows,
                    }
                ],
            },
        }

        return mensaje_interactivo

    def manejar_accion(self, accion_id: str) -> Dict[str, Any]:
        """
        Maneja IDs como 'next_page', 'prev_page', 'ordenar', 'go_first_page', etc.
        Devuelve de nuevo un 'interactive' para que main.py lo envíe.
        """
        if accion_id == "next_page":
            self.pagina_actual += 1

        elif accion_id == "prev_page":
            if self.pagina_actual > 1:
                self.pagina_actual -= 1

        elif accion_id == "go_first_page":
            self.pagina_actual = 1

        elif accion_id == "ordenar":
            # Alternar modo de orden
            if self.orden_por_precio == "asc":
                self.orden_por_precio = "desc"
            else:
                self.orden_por_precio = "asc"
            # Opcional: volver a la primera página
            self.pagina_actual = 1

        elif accion_id == "filtrar_categoria":
            # Por ahora no implementamos el filtro real.
            # Podés más adelante pedirle al usuario la categoría deseada.
            # Ejemplo: self.categoria_actual = "Hamburguesas"
            pass

        # Después de cambiar el estado, devolvemos el nuevo menú
        return self.generar_mensaje_menu()
