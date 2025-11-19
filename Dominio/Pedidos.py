from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from Dominio.Chat import bot
from Menu import menuCompleto  # IMPORTANTE: usamos menuCompleto, no menu_items

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
        for existente in self.items:
            if existente.id_producto == item.id_producto:
                existente.cantidad += item.cantidad
                return
        self.items.append(item)


# ------------------ LÓGICA DE MENÚ ------------------ #

def get_paginated_menu(page: int = 1, categoria: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Si pasás categoría, filtra por ese campo en los items de menuCompleto.
    Si no, pagina sobre todo el menú.
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


# ------------------ FLUJO DEL BOT ------------------ #

@bot.register_function("/inicio")
def cmd_inicio(mensaje: str) -> None:
    """
    Comando para empezar la conversación / pedido.
    """
    pedido = Pedido(telefono_cliente=bot.user_phone)
    bot.set_conversation_data("pedido_actual", pedido)
    bot.set_conversation_data("pagina_actual", 1)
    bot.set_conversation_data("categoria_actual", None)  # o "Hamburguesas" si querés

    bot.print_ayuda = False  # si tenés algo similar, si no, lo ignorás

    bot.set_waiting_for(funcion_mostrar_menu)

    bot.print_ayuda = True
    bot.waiting_for = funcion_mostrar_menu

    bot.set_conversation_data("pagina_actual", 1)
    bot.set_conversation_data("categoria_actual", None)  # o "Hamburguesas"

    bot.print_ayuda = False
    bot.waiting_for = None

    bot.set_waiting_for(funcion_mostrar_menu)

    bot.set_conversation_data("pagina_actual", 1)
    bot.set_conversation_data("categoria_actual", None)

    bot.set_waiting_for(funcion_mostrar_menu)

    bot.set_conversation_data("pagina_actual", 1)
    bot.set_conversation_data("categoria_actual", None)

    bot.set_waiting_for(funcion_mostrar_menu)

    bot.set_conversation_data("pagina_actual", 1)
    bot.set_conversation_data("categoria_actual", None)

    bot.set_waiting_for(funcion_mostrar_menu)

    bot.set_conversation_data("pagina_actual", 1)
    bot.set_conversation_data("categoria_actual", None)

    bot.set_waiting_for(funcion_mostrar_menu)

    # Mensaje de bienvenida y aviso al usuario
    print("👋 Hola, bienvenido al local. Te voy a mostrar el menú (texto plano).")
    funcion_mostrar_menu("")


def funcion_mostrar_menu(mensaje: str) -> None:
    pagina = bot.get_conversation_data("pagina_actual") or 1
    categoria = bot.get_conversation_data("categoria_actual")

    productos = get_paginated_menu(pagina, categoria)

    if not productos:
        print("⚠️ No hay más productos para mostrar.")
        return

    lineas: List[str] = [f"📄 Página {pagina}"]

    for indice, prod in enumerate(productos, start=1):
        nombre = prod.get("title", "Producto sin nombre")
        precio = prod.get("precio", 0)
        desc = prod.get("description", "")
        lineas.append(f"{indice}. {nombre} - ${precio}\n{desc}")

    lineas.append("\nResponde con el número del producto para agregarlo al carrito.")
    lineas.append("O escribe 'siguiente' para ver más productos.")

    print("\n\n".join(lineas))
    bot.set_waiting_for(funcion_procesar_seleccion_producto)


def funcion_procesar_seleccion_producto(mensaje: str) -> None:
    mensaje_limpio = mensaje.strip().lower()

    if mensaje_limpio == "siguiente":
        pagina = bot.get_conversation_data("pagina_actual") or 1
        bot.set_conversation_data("pagina_actual", pagina + 1)
        funcion_mostrar_menu("")
        return

    try:
        numero = int(mensaje_limpio)
    except ValueError:
        print("❌ Opción inválida. Escribe un número o 'siguiente'.")
        bot.set_waiting_for(funcion_procesar_seleccion_producto)
        return

    pagina = bot.get_conversation_data("pagina_actual") or 1
    categoria = bot.get_conversation_data("categoria_actual")
    productos = get_paginated_menu(pagina, categoria)

    if numero < 1 or numero > len(productos):
        print("❌ Número fuera de rango. Intenta de nuevo.")
        bot.set_waiting_for(funcion_procesar_seleccion_producto)
        return

    producto = productos[numero - 1]
    pedido: Pedido = bot.get_conversation_data("pedido_actual")

    item = ItemCarrito(
        id_producto=str(producto.get("id", "")),
        nombre=producto.get("title", "Producto"),
        precio=int(producto.get("precio", 0)),
        cantidad=1,
    )
    pedido.agregar_item(item)
    bot.set_conversation_data("pedido_actual", pedido)

    print(
        f"✅ Agregué {item.nombre} al carrito.\n"
        f"Total actual: ${pedido.total}\n\n"
        "Escribe 'siguiente' para seguir viendo productos, "
        "o escribe 'ver carrito' para ver el detalle."
    )

    bot.set_waiting_for(funcion_post_producto)


def funcion_post_producto(mensaje: str) -> None:
    mensaje_limpio = mensaje.strip().lower()
    pedido: Pedido = bot.get_conversation_data("pedido_actual")

    if mensaje_limpio == "ver carrito":
        if not pedido.items:
            print("🛒 Tu carrito está vacío.")
        else:
            lineas = ["🛒 Carrito actual:"]
            for item in pedido.items:
                subtotal = item.precio * item.cantidad
                lineas.append(f"- {item.nombre} x{item.cantidad} = ${subtotal}")
            lineas.append(f"\nTotal: ${pedido.total}")
            print("\n".join(lineas))

        print("Escribe 'siguiente' para seguir o '/confirmar' para finalizar.")
        bot.set_waiting_for(funcion_post_producto)
        return

    if mensaje_limpio == "siguiente":
        pagina = bot.get_conversation_data("pagina_actual") or 1
        bot.set_conversation_data("pagina_actual", pagina + 1)
        funcion_mostrar_menu("")
        return

    if mensaje_limpio == "/confirmar":
        print("✅ Pedido confirmado. (Acá podrías pedir ubicación, nombre, etc.)")
        return

    print("No entendí. Escribe 'siguiente', 'ver carrito' o '/confirmar'.")
    bot.set_waiting_for(funcion_post_producto)
