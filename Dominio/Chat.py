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
        Menú de productos (list) respetando los límites de WhatsApp.
        - Si NO hay filtro de categoría: menú normal paginado.
        - Si HAY filtro y esa categoría tiene <= PAGE_SIZE productos:
            * No muestra 'Siguiente página' ni 'Volver al inicio'
            * Muestra 'Ver todos' (usa la misma lógica que categoria_Todos)
        """
        productos = self._obtener_menu_actual()

        rows_productos: List[Dict[str, Any]] = []

        # --------- FILAS DE PRODUCTOS --------- #
        for producto in productos:
            # Título: nombre recortado (máx 24 chars)
            titulo = producto["nombre"]
            if len(titulo) > 24:
                titulo = titulo[:24]

            # Descripción: precio + descripción
            descripcion = f"${producto['precio']} - {producto['descripcion']}"

            rows_productos.append({
                "id": f"producto_{producto['id']}",
                "title": titulo,
                "description": descripcion,
            })

        # --------- LÓGICA DE VALIDACIÓN POR CATEGORÍA --------- #
        esta_filtrado = self.categoria_actual is not None

        if esta_filtrado:
            total_categoria = sum(
                1
                for p in menuCompleto
                if p.get("categoria", "").lower() == self.categoria_actual.lower()
            )
        else:
            total_categoria = len(menuCompleto)

        hay_multiples_paginas = total_categoria > PAGE_SIZE

        # --------- FILAS DE ACCIONES --------- #
        rows_acciones: List[Dict[str, Any]] = []

        # Página anterior solo si hay más de una página
        if self.pagina_actual > 1 and hay_multiples_paginas:
            rows_acciones.append({
                "id": "prev_page",
                "title": "⬅️ Página anterior",
                "description": "Volver a la página anterior",
            })

        # Caso paginado normal (sin filtro o filtro con muchas filas)
        if (not esta_filtrado) or (esta_filtrado and hay_multiples_paginas):
            rows_acciones.append({
                "id": "next_page",
                "title": "➡️ Siguiente página",
                "description": "Ver más productos",
            })
            rows_acciones.append({
                "id": "go_first_page",
                "title": "⏮ Volver al inicio",
                "description": "Ir a la primera página del menú",
            })

        # Caso filtrado con pocos productos (<= PAGE_SIZE):
        # mostramos "Ver todos" que usa la misma lógica que categoria_Todos
        if esta_filtrado and not hay_multiples_paginas:
            rows_acciones.append({
                "id": "categoria_Todos",       # 👈 IMPORTANTE: mismo ID que en el menú de categorías
                "title": "Ver todos",
                "description": "Mostrar todos los productos",
            })

        # Ordenar siempre
        rows_acciones.append({
            "id": "ordenar",
            "title": "↕️ Ordenar precio",
            "description": "Alternar entre barato y caro",
        })

        # Solo mostramos "Filtrar categoría" cuando NO estamos filtrando
        if not esta_filtrado:
            rows_acciones.append({
                "id": "filtrar_categoria",
                "title": "🔎 Filtrar categoría",
                "description": "Elegir una categoría de productos",
            })

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
                        "rows": rows_productos,
                    },
                    {
                        "title": "Acciones",
                        "rows": rows_acciones,
                    },
                ],
            },
        }

        return mensaje_interactivo


    
    
   #---------- MENÚ DE CATEGORÍAS ---------- #

    def generar_mensaje_categorias(self) -> Dict[str, Any]:
        """
        Menú list SOLO con categorías para que el usuario elija una.
        """
        # Sacar categorías únicas del menú
        categorias_set = {p["categoria"] for p in menuCompleto}
        categorias = sorted(list(categorias_set))

        rows: List[Dict[str, Any]] = []

        # Opción "Todos"
        rows.append({
            "id": "categoria_Todos",
            "title": "Todos",
            "description": "Ver todos los productos",
        })

        for cat in categorias:
            titulo = cat
            if len(titulo) > 24:
                titulo = titulo[:24]

            rows.append({
                "id": f"categoria_{cat}",
                "title": titulo,
                "description": "Ver solo esta categoría",
            })

        mensaje_interactivo: Dict[str, Any] = {
            "type": "list",
            "header": {
                "type": "text",
                "text": "Filtrar por categoría",
            },
            "body": {
                "text": "📂 Elegí una categoría para filtrar el menú.",
            },
            "footer": {
                "text": "Podés volver al menú general luego.",
            },
            "action": {
                "button": "Ver categorías",
                "sections": [
                    {
                        "title": "Categorías",
                        "rows": rows,
                    }
                ],
            },
        }

        return mensaje_interactivo

    # ----------------- ACCIONES ----------------- #

    def manejar_accion(self, accion_id: str) -> Dict[str, Any]:
        """
        Maneja IDs como:
        - 'next_page', 'prev_page', 'go_first_page', 'ordenar'
        - 'filtrar_categoria'
        - 'categoria_<Nombre>'
        """
        # Navegación entre páginas
        if accion_id == "next_page":
            self.pagina_actual += 1

        elif accion_id == "prev_page":
            if self.pagina_actual > 1:
                self.pagina_actual -= 1

        elif accion_id == "go_first_page":
            self.pagina_actual = 1

        # Orden por precio
        elif accion_id == "ordenar":
            if self.orden_por_precio == "asc":
                self.orden_por_precio = "desc"
            else:
                self.orden_por_precio = "asc"
            self.pagina_actual = 1

        # Mostrar menú de categorías
        elif accion_id == "filtrar_categoria":
            return self.generar_mensaje_categorias()

        # ✅ Cualquier botón que empiece con 'categoria_'
        elif accion_id.startswith("categoria_"):
            categoria = accion_id[len("categoria_"):]
            if categoria == "Todos":
                self.categoria_actual = None
            else:
                self.categoria_actual = categoria
            self.pagina_actual = 1
            return self.generar_mensaje_menu()

        # Cualquier otra cosa: devolvemos el menú actual
        return self.generar_mensaje_menu()

