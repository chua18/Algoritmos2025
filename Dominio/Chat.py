# Dominio/Chat.py
import logging
from typing import Any, Dict, List, Optional

from Menu import menuCompleto  # tu menú completo de productos
from Dominio.Modelos import Pedido, ItemCarrito
from Dominio import Rutas
import osmnx as ox
from Dominio.Rutas import G

PAGE_SIZE = 5

LAT_LOCAL = -31.387591856643436
LON_LOCAL = -57.962891374932944

NODO_LOCAL = ox.nearest_nodes(G, LON_LOCAL, LAT_LOCAL)

def get_nodo_mas_cercano(lat: float, lng: float) -> int:
    """
    Devuelve el id de nodo del grafo G más cercano a las coordenadas (lat, lng).
    """
    return ox.nearest_nodes(G, lng, lat)


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

def calcular_zona(lat_cliente: float, lon_cliente: float) -> str:
    """
    Divide el plano en 4 zonas con el local como origen:
    - Noroeste (NO)
    - Noreste (NE)
    - Suroeste (SO)
    - Sureste (SE)

    OJO: estamos en hemisferio sur, las latitudes son negativas.
    - lat_cliente > LAT_LOCAL => está más al NORTE
    - lat_cliente < LAT_LOCAL => está más al SUR
    - lon_cliente > LON_LOCAL => está más al ESTE
    - lon_cliente < LON_LOCAL => está más al OESTE
    """
    es_norte = lat_cliente > LAT_LOCAL
    es_este = lon_cliente > LON_LOCAL

    if es_norte and not es_este:
        return "NO"   # Noroeste
    if es_norte and es_este:
        return "NE"   # Noreste
    if not es_norte and not es_este:
        return "SO"   # Suroeste
    return "SE"        # Sureste


# ------------------ CLASE CHAT ------------------ #

class Chat:
    def __init__(self, nombre_restaurante: str = "Restaurante"):
        self.nombre_restaurante = nombre_restaurante
        self.pagina_Actual = 1
        self.categoria_Actual = None
        self.orden_por_precio = None
        # 👇 diccionario de pedidos activos por teléfono
        self.pedidos: Dict[str, Pedido] = {}

    # --- NUEVO ---
    def obtener_o_crear_pedido(self, telefono: str) -> Pedido:
        """
        Devuelve el Pedido asociado a este teléfono si existe,
        o crea uno nuevo, lo guarda en self.pedidos y lo devuelve.
        """
        pedido = self.pedidos.get(telefono)
        if pedido is None:
            pedido = Pedido(telefono_cliente=telefono)
            self.pedidos[telefono] = pedido
        return pedido

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
        cantidad: int,
        detalle: str,
    ) -> tuple[ItemCarrito, int]:
        """
        Agrega 'cantidad' unidades de un producto (row_id tipo 'producto_6')
        al carrito de ese teléfono, con el mismo detalle.
        Devuelve (item_modificado, total_actual).
        """
        producto = self._buscar_producto_por_row_id(row_id)
        if not producto:
            raise ValueError(f"No se encontró producto para row_id={row_id!r}")

        if telefono not in self.pedidos:
            self.pedidos[telefono] = Pedido(telefono_cliente=telefono)

        pedido = self.pedidos[telefono]

        item = pedido.obtener_item(
            id_producto=str(producto["id"]),
            nombre=producto["nombre"],
            precio=int(producto["precio"]),
        )

        # 👇 acá se crean las unidades individuales
        item.agregar_unidades(detalle=detalle, cantidad=cantidad)

        total = pedido.total

        logging.info(
            f"[CARRITO] Tel={telefono} agregó {cantidad}x {item.nombre} "
            f"(detalle={detalle!r}), total={total}"
        )

        return item, total

    def resumen_carrito(self, telefono: str) -> str:
        """
        Devuelve un texto con el contenido del carrito de ese teléfono,
        mostrando las unidades agrupadas por detalle.
        """
        pedido = self.pedidos.get(telefono)
        if not pedido or not pedido.items:
            return "🧺 Tu carrito está vacío por ahora."

        from collections import Counter

        lineas: List[str] = ["🧺 *Tu carrito actual:*"]

        for idx, item in enumerate(pedido.items, start=1):
            # Contamos cuántas unidades hay de cada detalle
            detalles = [u.detalle for u in item.unidades]
            contador = Counter(detalles)

            lineas.append(f"{idx}. *{item.nombre}* x{item.cantidad}")

            for detalle_valor, cant in contador.items():
                if detalle_valor:
                    lineas.append(f"   - x{cant} ({detalle_valor})")
                else:
                    lineas.append(f"   - x{cant} completas")

        lineas.append(f"\n💵 *Total:* ${pedido.total}")
        lineas.append("\nEscribí *confirmar* para finalizar o *borrar* para vaciar el carrito.")
        return "\n".join(lineas)
    
    def generar_menu_quitar_producto(self, telefono: str) -> Optional[Dict[str, Any]]:
        """
        Genera un mensaje interactivo (list) con CADA UNIDAD del carrito
        para que el usuario pueda elegir exactamente cuál quitar.
        Ejemplo:
          - Hamburguesa - $300 - sin panceta
          - Hamburguesa - $300 - completa
        Devuelve el dict 'interactive' o None si el carrito está vacío.
        """
        pedido = self.pedidos.get(telefono)
        if not pedido or not pedido.items:
            return None

        rows: List[Dict[str, Any]] = []

        for idx_item, item in enumerate(pedido.items):
            for idx_unidad, unidad in enumerate(item.unidades):
                titulo = item.nombre
                if len(titulo) > 24:
                    titulo = titulo[:24]

                detalle = unidad.detalle or "completa"
                descripcion = f"${item.precio} - {detalle}"

                # id codifica el índice del item y de la unidad
                rows.append({
                    "id": f"quitar_unidad_{idx_item}_{idx_unidad}",
                    "title": titulo,
                    "description": descripcion,
                })

        if not rows:
            return None

        mensaje_interactivo: Dict[str, Any] = {
            "type": "list",
            "header": {
                "type": "text",
                "text": "Quitar producto",
            },
            "body": {
                "text": "Elegí la unidad que querés quitar del carrito.",
            },
            "footer": {
                "text": "Cada línea es una unidad distinta.",
            },
            "action": {
                "button": "Ver unidades",
                "sections": [
                    {
                        "title": "Unidades en tu carrito",
                        "rows": rows,
                    }
                ],
            },
        }

        return mensaje_interactivo

    
  
    def quitar_unidad_del_carrito(self, telefono: str, idx_item: int, idx_unidad: int) -> bool:
        """
        Quita UNA unidad específica del carrito, indicada por
        (idx_item, idx_unidad), ambos índices 0-based.
        Si el item se queda sin unidades, lo elimina del pedido.
        Devuelve True si se quitó algo, False si no.
        """
        pedido = self.pedidos.get(telefono)
        if not pedido or not pedido.items:
            return False

        if idx_item < 0 or idx_item >= len(pedido.items):
            return False

        item = pedido.items[idx_item]

        if idx_unidad < 0 or idx_unidad >= len(item.unidades):
            return False

        unidad = item.unidades.pop(idx_unidad)
        logging.info(
            f"[CARRITO] Tel={telefono} quitó 1x {item.nombre} (detalle={unidad.detalle!r}) del carrito."
        )

        # Si ya no quedan unidades de ese item, lo sacamos del carrito
        if not item.unidades:
            pedido.items.pop(idx_item)
            logging.info(
                f"[CARRITO] Item {item.nombre} eliminado del carrito (sin unidades restantes)."
            )

        return True


    def vaciar_carrito(self, telefono: str) -> None:
        pedido = self.pedidos.get(telefono)
        if pedido:
            pedido.vaciar()
            logging.info(f"[CARRITO] Tel={telefono} vació su carrito.")


    def guardar_ubicacion(self, telefono: str, lat: float, lng: float, direccion: str):
        pedido = self.obtener_o_crear_pedido(telefono)
        if not pedido:
            logging.warning(f"[UBICACION] No hay pedido para tel={telefono}")
            return

        pedido.ubicacion = (lat, lng)

        try:
            # Usamos las constantes definidas en ESTE archivo (Chat.py)
            nodo_local = NODO_LOCAL
            nodo_cliente = get_nodo_mas_cercano(lat, lng)

            path, dist_km, tiempo_min = Rutas.a_star_ruta(nodo_local, nodo_cliente)
            

            pedido.ubicacion = (lat, lng)
            pedido.direccion_texto = direccion
            pedido.nodo_origen = nodo_local
            pedido.nodo_destino = nodo_cliente
            pedido.distancia_km = dist_km
            pedido.tiempo_estimado_min = tiempo_min
            pedido.path_nodos = path

            # 🔽 NUEVO: calcular zona
            pedido.zona = calcular_zona(lat, lng)

            logging.info(
                f"[RUTA] tel={telefono} zona={pedido.zona} "
                f"dist={dist_km:.2f}km tiempo={tiempo_min:.1f}min nodos={len(path)}"
            )
        except Exception as e:
            logging.error(f"[RUTA] Error calculando ruta para tel={telefono}: {e}")


    def guardar_direccion_texto(self, telefono: str, direccion: str) -> None:
        """
        Guarda direccion escrita por el usuario en el Pedido (por si no manda ubicación).
        No calcula ruta porque no hay lat/lon, pero queda la dirección registrada.
        """
        pedido = self.pedidos.get(telefono)
        if not pedido:
            logging.warning(f"[DIRECCION] No hay pedido para tel={telefono}")
            return

        pedido.direccion_texto = direccion
        logging.info(f"[DIRECCION] tel={telefono} -> {direccion!r}")
