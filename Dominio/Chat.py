# Dominio/Chat.py
import logging
from typing import Any, Dict, List, Optional

from Menu import menuCompleto  # tu menú completo de productos
from Dominio.Pedidos import Pedido, ItemCarrito  # modelos de dominio (carrito/pedido)

PAGE_SIZE = 5


# ------------------ HELPER DE PAGINADO ------------------ #

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


# ------------------ CLASE CHAT ------------------ #

class Chat:
    def __init__(self) -> None:
        # Estado para el paginado / filtros
        self.pagina_actual: int = 1
        self.categoria_actual: Optional[str] = None
        self.orden_por_precio: Optional[str] = None  # "asc", "desc" o None

        # Carritos por teléfono: tel -> Pedido (de Dominio.Pedidos)
        self.pedidos: Dict[str, Pedido] = {}

    # ----------------- ESTADO DEL MENÚ ----------------- #

    def reset_estado(self) -> None:
        """
        Deja el menú en estado 'limpio':
        - Página 1
        - Sin categoría filtrada
        - Sin orden especial por precio
        (NO toca el carrito ni pedidos).
        """
        self.pagina_actual = 1
        self.categoria_actual = None
        self.orden_por_precio = None
        logging.info(">>> RESET de estado de menú (pagina=1, sin categoria, sin orden)")

    def _obtener_menu_actual(self) -> List[Dict[str, Any]]:
        """
        Devuelve la página actual de productos, aplicando orden por precio si corresponde.
        """
        productos = get_paginated_menu(self.pagina_actual, self.categoria_actual)

        if self.orden_por_precio == "asc":
            productos = sorted(productos, key=lambda p: p["precio"])
        elif self.orden_por_precio == "desc":
            productos = sorted(productos, key=lambda p: p["precio"], reverse=True)

        return productos

    # ----------------- MENÚ PAGINADO PRINCIPAL ----------------- #

    def generar_mensaje_menu(self) -> Dict[str, Any]:
        """
        Menú de productos (list) respetando los límites de WhatsApp.

        - Si NO hay filtro de categoría: menú normal paginado.
        - Si HAY filtro:
            * 'Siguiente página' solo si hay otra página real.
            * 'Volver al inicio' aparece recién desde la página 3.
            * 'Ver todos' (categoria_Todos) SIEMPRE aparece mientras haya filtro.
        """
        productos = self._obtener_menu_actual()

        rows_productos: List[Dict[str, Any]] = []

        # --------- FILAS DE PRODUCTOS --------- #
        for producto in productos:
            # Título: nombre recortado (máx 24 chars para WhatsApp)
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

        # --------- INFO GLOBAL PARA PAGINADO --------- #
        esta_filtrado = self.categoria_actual is not None

        if esta_filtrado:
            productos_totales = [
                p for p in menuCompleto
                if p.get("categoria", "").lower() == self.categoria_actual.lower()
            ]
        else:
            productos_totales = menuCompleto

        total_items = len(productos_totales)
        total_paginas = (total_items + PAGE_SIZE - 1) // PAGE_SIZE if total_items > 0 else 1

        tiene_siguiente = self.pagina_actual < total_paginas
        tiene_anterior = self.pagina_actual > 1

        # --------- FILAS DE ACCIONES --------- #
        rows_acciones: List[Dict[str, Any]] = []

        # Botón "Página anterior" si hay página anterior
        if tiene_anterior:
            rows_acciones.append({
                "id": "prev_page",
                "title": "⬅️ Página anterior",
                "description": "Volver a la página anterior",
            })

        # Botón "Siguiente página" solo si hay otra página real
        if tiene_siguiente:
            rows_acciones.append({
                "id": "next_page",
                "title": "➡️ Siguiente página",
                "description": "Ver más productos",
            })

        # Botón "Volver al inicio" recién desde página 3 en adelante
        if self.pagina_actual >= 3:
            rows_acciones.append({
                "id": "go_first_page",
                "title": "⏮ Volver al inicio",
                "description": "Ir a la primera página del menú",
            })

        # Si estamos filtrando por categoría, SIEMPRE mostrar "Ver todos"
        # que usa la misma lógica que categoria_Todos del menú de categorías
        if esta_filtrado:
            rows_acciones.append({
                "id": "categoria_Todos",       # mismo ID que en el menú de categorías
                "title": "Ver todos",
                "description": "Mostrar todos los productos",
            })

        # Ordenar por precio (siempre)
        rows_acciones.append({
            "id": "ordenar",
            "title": "↕️ Ordenar precio",
            "description": "Alternar entre barato y caro",
        })

        # Solo mostrar "Filtrar categoría" cuando NO estamos filtrando
        if not esta_filtrado:
            rows_acciones.append({
                "id": "filtrar_categoria",
                "title": "🔎 Filtrar categoría",
                "description": "Elegir una categoría de productos",
            })

        # --------- ARMAR MENSAJE INTERACTIVO --------- #
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

    # ---------- MENÚ DE CATEGORÍAS ---------- #

    def generar_mensaje_categorias(self) -> Dict[str, Any]:
        """
        Menú list SOLO con categorías para que el usuario elija una.
        """
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

    # ----------------- ACCIONES DE MENÚ ----------------- #

    def manejar_accion(self, accion_id: str) -> Dict[str, Any]:
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

        # Cualquier botón que empiece con 'categoria_'
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

    # ----------------- CARRITO ----------------- #

    def _buscar_producto_por_row_id(self, row_id: str) -> Optional[Dict[str, Any]]:
        """
        row_id viene del menú, ej: 'producto_6'.
        Devuelve el dict del producto correspondiente en menuCompleto.
        """
        if not row_id.startswith("producto_"):
            return None

        id_producto = row_id.split("_", 1)[1]  # "6", "10", etc.

        for p in menuCompleto:
            if str(p["id"]) == str(id_producto):
                return p
        return None

    def agregar_producto_al_carrito(
        self,
        telefono: str,
        row_id: str,
        cantidad: int = 1,
        detalle: str = "",
    ) -> tuple[ItemCarrito, int]:
        """
        Agrega un producto (por row_id tipo 'producto_6') al carrito de ese teléfono.
        Devuelve (item_agregado, total_actual_del_carrito).
        """
        producto = self._buscar_producto_por_row_id(row_id)
        if not producto:
            raise ValueError(f"No se encontró producto para row_id={row_id!r}")

        # 👇 Asegurate que el Pedido de Dominio/Pedidos tenga 'telefono_cliente'
        if telefono not in self.pedidos:
            self.pedidos[telefono] = Pedido(telefono_cliente=telefono)

        pedido = self.pedidos[telefono]

        item = ItemCarrito(
            id_producto=str(producto["id"]),
            nombre=producto["nombre"],
            precio=int(producto["precio"]),
            cantidad=cantidad,
            detalle=detalle,
        )

        pedido.agregar_item(item)
        total = pedido.total

        logging.info(
            f"[CARRITO] Tel={telefono} agregó {item.nombre} x{item.cantidad} "
            f"(${item.precio} c/u, detalle='{item.detalle}'), total={total}"
        )

        return item, total

    def resumen_carrito(self, telefono: str) -> str:
        """
        Devuelve un texto con el contenido del carrito de ese teléfono,
        agrupando por producto y luego por detalle.
        """
        pedido = self.pedidos.get(telefono)
        if not pedido or not pedido.items:
            return "🧺 Tu carrito está vacío por ahora."

        # Agrupamos por producto
        productos: Dict[str, Dict[str, Any]] = {}
        for item in pedido.items:
            key = item.id_producto
            if key not in productos:
                productos[key] = {
                    "nombre": item.nombre,
                    "precio": item.precio,
                    "detalles": {},   # detalle -> cantidad
                    "cantidad_total": 0,
                }
            prod = productos[key]
            prod["cantidad_total"] += item.cantidad
            detalle_clave = item.detalle or "completa"
            prod["detalles"][detalle_clave] = prod["detalles"].get(detalle_clave, 0) + item.cantidad

        lineas: List[str] = ["🧺 *Tu carrito actual:*"]

        for prod in productos.values():
            nombre = prod["nombre"]
            cant_total = prod["cantidad_total"]
            lineas.append(f"\n• {nombre} x{cant_total}")

            # Subdetalles: "x2 completas, x1 sin panceta"
            subpartes = []
            for detalle, cant in prod["detalles"].items():
                if detalle == "completa":
                    subpartes.append(f"x{cant} completas")
                else:
                    subpartes.append(f"x{cant} {detalle}")
            lineas.append("   " + ", ".join(subpartes))

        lineas.append(f"\n💵 *Total (con descuentos):* ${pedido.total}")
        lineas.append("\nEscribí *confirmar* para finalizar o *borrar* para vaciar el carrito.")

        return "\n".join(lineas)


    def vaciar_carrito(self, telefono: str) -> None:
        """
        Vacía el carrito de ese teléfono.
        """
        pedido = self.pedidos.get(telefono)
        if pedido:
            pedido.items.clear()
            logging.info(f"[CARRITO] Tel={telefono} vació su carrito.")

    def guardar_ubicacion(self, telefono: str, lat: float, lng: float) -> None:
        pedido = self.pedidos.get(telefono)
        if not pedido:
            return
        pedido.ubicacion = (lat, lng)

    def guardar_direccion_texto(self, telefono: str, direccion: str) -> None:
        pedido = self.pedidos.get(telefono)
        if not pedido:
            return
        pedido.direccion_texto = direccion
