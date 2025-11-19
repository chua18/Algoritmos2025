from typing import Any, Dict, List
from Dominio.Chat import bot
from Dominio.Modelos import Pedido, ItemCarrito
from Menu import menu_items  # tu menú original: dict por categoría

# Si querés paginar 5 productos
PAGE_SIZE = 5


def get_paginated_menu(categoria: str, pagina: int) -> List[Dict[str, Any]]:
    productos = menu_items.get(categoria, [])
    inicio = (pagina - 1) * PAGE_SIZE
    fin = inicio + PAGE_SIZE
    return productos[inicio:fin]


@bot.register_function("/inicio")
def cmd_inicio(mensaje: str) -> None:
    """Comando para empezar la conversación / pedido."""
    # Crear pedido vacío para este usuario
    pedido = Pedido(telefono_cliente=bot.user_phone)
    bot.set_conversation_data("pedido_actual", pedido)
    bot.set_conversation_data("categoria_actual", "Hamburguesas")
    bot.set_conversation_data("pagina_actual", 1)

    bot.enviar(
        "👋 Hola, bienvenido al local.\n"
        "Te voy a mostrar el menú de *Hamburguesas*.\n"
        "Escribí cualquier cosa para ver la primera página."
    )

    # El próximo mensaje lo maneja esta función:
    bot.set_waiting_for(funcion_mostrar_menu)


def funcion_mostrar_menu(mensaje: str) -> None:
    """Muestra productos de la categoría actual (paginado simple, texto plano)."""
    categoria = bot.get_conversation_data("categoria_actual")
    pagina = bot.get_conversation_data("pagina_actual") or 1

    productos = get_paginated_menu(categoria, pagina)

    if not productos:
        bot.enviar("⚠️ No hay más productos en esta categoría.")
        return

    texto = [f"📄 Página {pagina} - {categoria}"]
    for idx, prod in enumerate(productos, start=1):
        texto.append(
            f"{idx}. {prod['title']} - ${prod['precio']}\n{prod['description']}"
        )

    texto.append("\nResponde con el número del producto para agregarlo al carrito.")
    texto.append("O escribe 'siguiente' para ver más productos.")
    bot.enviar("\n\n".join(texto))

    bot.set_waiting_for(funcion_procesar_seleccion_producto)


def funcion_procesar_seleccion_producto(mensaje: str) -> None:
    """Procesa '1', '2', 'siguiente', etc."""
    mensaje_limpio = mensaje.strip().lower()

    if mensaje_limpio == "siguiente":
        pagina = bot.get_conversation_data("pagina_actual") or 1
        bot.set_conversation_data("pagina_actual", pagina + 1)
        funcion_mostrar_menu(mensaje="")
        return

    # Intentar convertir a número de ítem
    try:
        numero = int(mensaje_limpio)
    except ValueError:
        bot.enviar("❌ Opción inválida. Escribe un número o 'siguiente'.")
        bot.set_waiting_for(funcion_procesar_seleccion_producto)
        return

    categoria = bot.get_conversation_data("categoria_actual")
    pagina = bot.get_conversation_data("pagina_actual") or 1
    productos = get_paginated_menu(categoria, pagina)

    if numero < 1 or numero > len(productos):
        bot.enviar("❌ Número fuera de rango. Intenta de nuevo.")
        bot.set_waiting_for(funcion_procesar_seleccion_producto)
        return

    producto = productos[numero - 1]

    # Recuperar pedido y agregar ítem
    pedido: Pedido = bot.get_conversation_data("pedido_actual")
    item = ItemCarrito(
        id_producto=producto["id"],
        nombre=producto["title"],
        precio=producto["precio"],
        cantidad=1
    )
    pedido.agregar_item(item)
    bot.set_conversation_data("pedido_actual", pedido)

    bot.enviar(
        f"✅ Agregué *{producto['title']}* al carrito.\n"
        f"Total actual: ${pedido.total}\n\n"
        "¿Querés seguir viendo el menú? Escribe 'siguiente' o un número nuevo.\n"
        "También podés escribir 'ver carrito' para ver el detalle."
    )

    bot.set_waiting_for(funcion_procesar_post_producto)


def funcion_procesar_post_producto(mensaje: str) -> None:
    mensaje_limpio = mensaje.strip().lower()
    pedido: Pedido = bot.get_conversation_data("pedido_actual")

    if mensaje_limpio == "ver carrito":
        if not pedido.items:
            bot.enviar("🛒 Tu carrito está vacío.")
        else:
            lineas = ["🛒 *Carrito actual:*"]
            for item in pedido.items:
                lineas.append(
                    f"- {item.nombre} x{item.cantidad} = ${item.precio * item.cantidad}"
                )
            lineas.append(f"\nTotal: ${pedido.total}")
            bot.enviar("\n".join(lineas))

        bot.enviar("Escribe 'siguiente' para seguir o '/confirmar' para finalizar.")
        bot.set_waiting_for(funcion_procesar_post_producto)
        return

    if mensaje_limpio == "siguiente":
        pagina = bot.get_conversation_data("pagina_actual") or 1
        bot.set_conversation_data("pagina_actual", pagina + 1)
        funcion_mostrar_menu(mensaje="")
        return

    if mensaje_limpio == "/confirmar":
        bot.enviar(
            "✅ Pedido confirmado.\n"
            "Ahora podríamos pedirte la ubicación, nombre, etc."
        )
        # Acá podrías cambiar el waiting_for a otra función:
        # bot.set_waiting_for(funcion_pedir_datos_cliente)
        return

    bot.enviar("No entendí. Escribe 'siguiente', 'ver carrito' o '/confirmar'.")
    bot.set_waiting_for(funcion_procesar_post_producto)
