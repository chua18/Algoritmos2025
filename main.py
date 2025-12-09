import os
import logging
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

import random
from Dominio.Chat import Chat
from Dominio.Reparto import GestorReparto
from Dominio import Rutas
from Dominio.Modelos import Pedido, Cliente
from utils.get_message_type import get_message_type

# -----------------------------------
# CONFIGURACIÓN BÁSICA
# -----------------------------------

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Instancia de tu Chat anterior
chat = Chat()

clientes: Dict[str, Cliente] = {}
codigos_pedidos: Dict[str, Pedido] = {}
estado_usuarios: Dict[str, Dict[str, Any]] = {}

CELULAR_REPARTIDOR = {
    "NO": os.getenv("REPARTIDOR_NO", "59891307359"),
    "NE": os.getenv("REPARTIDOR_NE", "59896964635"),
    "SO": os.getenv("REPARTIDOR_SO", "59896964635"),
    "SE": os.getenv("REPARTIDOR_SE", "59891307359"),
}

gestor_reparto = GestorReparto.desde_config(CELULAR_REPARTIDOR)

# --- CREDENCIALES Y CONFIGURACIÓN ---
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
VERSION = os.getenv("VERSION", "v22.0")

GRAPH_SEND_URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"

logging.info(f"ACCESS_TOKEN cargado? {bool(ACCESS_TOKEN)}")
logging.info(f"PHONE_NUMBER_ID: {PHONE_NUMBER_ID!r}")
logging.info(f"GRAPH_SEND_URL: {GRAPH_SEND_URL}")


# --------------------------------------------------------
# HELPERS DE SERIALIZACIÓN
# --------------------------------------------------------

def cliente_to_dict(cliente: Cliente) -> Dict[str, Any]:
    """Convierte un Cliente en un diccionario simple para JSON."""
    return {
        "telefono": cliente.telefono,
        "nombre": cliente.nombre,
        "cantidad_pedidos": len(cliente.pedidos),
        "pedidos": [
            {
                "total": p.total,
                "zona": getattr(p, "zona", None),
                "direccion": p.direccion_texto,
            }
            for p in cliente.pedidos
        ],
    }


def pedido_to_dict(pedido: Pedido) -> Dict[str, Any]:
    """Convierte un Pedido a JSON para debug."""
    lat = None
    lng = None
    if pedido.ubicacion:
        lat, lng = pedido.ubicacion

    return {
        "telefono_cliente": pedido.telefono_cliente,
        "zona": getattr(pedido, "zona", None),
        "total": pedido.total,
        "direccion": pedido.direccion_texto,
        "ubicacion": {"lat": lat, "lng": lng} if lat is not None else None,
        "distancia_km": getattr(pedido, "distancia_km", None),
        "tiempo_estimado_min": getattr(pedido, "tiempo_estimado_min", None),
        "cantidad_items": len(pedido.items),
    }


# --------------------------------------------------------
# WHATSAPP HELPERS
# --------------------------------------------------------

async def send_to_whatsapp(payload: Dict[str, Any]) -> None:
    """Envía un payload crudo a la API de WhatsApp."""
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        logging.warning(
            f"Falta ACCESS_TOKEN o PHONE_NUMBER_ID. "
            f"(ACCESS_TOKEN={bool(ACCESS_TOKEN)}, PHONE_NUMBER_ID={bool(PHONE_NUMBER_ID)})"
        )
        logging.info(f"MOCK SEND => {payload}")
        return

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(GRAPH_SEND_URL, headers=headers, json=payload)
        logging.info(f"Respuesta WhatsApp: {resp.status_code} {resp.text}")
        resp.raise_for_status()


async def send_menu(to: str, nombre: str = "Cliente") -> None:
    """Envía menú paginado."""
    msg = chat.generar_mensaje_menu()
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": msg,
    }
    print(f"payload del menú paginado:\n{payload}")
    await send_to_whatsapp(payload)


async def send_text(to: str, body: str) -> None:
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    await send_to_whatsapp(payload)


async def send_botones_siguiente_paso(to: str) -> None:
    """Envía botones: seguir, quitar, finalizar."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "¿Qué querés hacer ahora?",
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": "seguir_comprando", "title": "🛒 Seguir comprando"},
                    },
                    {
                        "type": "reply",
                        "reply": {"id": "quitar_producto", "title": "🗑 Quitar producto"},
                    },
                    {
                        "type": "reply",
                        "reply": {"id": "finalizar_pedido", "title": "✅ Finalizar pedido"},
                    },
                ]
            },
        },
    }
    await send_to_whatsapp(payload)


async def upload_media(file_path: str, mime_type: str = "image/gif") -> str:
    """Sube un archivo y devuelve media_id."""
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        logging.warning("No hay ACCESS_TOKEN o PHONE_NUMBER_ID para subir media.")
        return ""

    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/media"

    async with httpx.AsyncClient(timeout=30) as client:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, mime_type)}
            data = {"messaging_product": "whatsapp"}
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

            resp = await client.post(url, data=data, files=files, headers=headers)

        logging.info(f"Subida de media: {resp.status_code} {resp.text}")
        resp.raise_for_status()
        return resp.json().get("id", "")


# --------------------------------------------------------
# ENVÍO DE LOTES
# --------------------------------------------------------

async def enviar_lote_zona_al_repartidor(zona: str) -> None:
    repartidor = gestor_reparto.repartidores.get(zona)
    if not repartidor:
        logging.warning(f"[REPARTO] No hay repartidor para zona={zona}")
        return

    pedidos_lote: List[Pedido] = gestor_reparto.obtener_lote_actual(zona)
    if not pedidos_lote:
        logging.info(f"[REPARTO] Lote vacío en zona={zona}")
        return

    png_path = Rutas.generar_gif_ruta_lote(pedidos_lote)
    if not png_path:
        logging.warning(f"[REPARTO] No se pudo generar PNG para zona={zona}")
        return

    media_id = await upload_media(png_path, "image/png")
    if not media_id:
        logging.warning(f"[REPARTO] No se pudo subir PNG para zona={zona}")
        return

    # Armar resumen
    lineas: List[str] = []
    lineas.append(f"🛵 *Nuevo lote de pedidos (hasta 7) - Zona {zona}*")

    for idx, p in enumerate(pedidos_lote, start=1):
        if p.direccion_texto:
            direccion = p.direccion_texto
        elif p.ubicacion:
            lat, lng = p.ubicacion
            direccion = f"{lat:.5f}, {lng:.5f}"
        else:
            direccion = "Sin dirección"

        lineas.append(f"\n#{idx} 📱 {p.telefono_cliente}")
        lineas.append(f"📍 {direccion}")
        if getattr(p, "zona", None):
            lineas.append(f"🗺 Zona: {p.zona}")
        lineas.append(f"💵 Total: ${p.total}")

    caption = "\n".join(lineas)
    if len(caption) > 1024:
        caption = caption[:1020] + "..."

    payload = {
        "messaging_product": "whatsapp",
        "to": repartidor.telefono_whatsapp,
        "type": "image",
        "image": {"id": media_id, "caption": caption},
    }

    await send_to_whatsapp(payload)
    gestor_reparto.marcar_lote_enviado(zona)


async def intentar_cerrar_lote(telefono: str) -> None:
    pedido = chat.pedidos.get(telefono)
    if not pedido:
        logging.warning(f"[LOTE] No hay pedido para tel={telefono}")
        return

    cliente = clientes.get(telefono)
    if cliente and pedido not in cliente.pedidos:
        cliente.pedidos.append(pedido)

    lote_lleno, zona = gestor_reparto.asignar_pedido(pedido)

    chat.pedidos.pop(telefono, None)

    if lote_lleno:
        await enviar_lote_zona_al_repartidor(zona)


# --------------------------------------------------------
# ENDPOINTS
# --------------------------------------------------------

@app.get("/welcome")
def index():
    return {"mensaje": "welcome developer"}


# ---- VERIFICACIÓN WEBHOOK ----
@app.get("/whatsapp", response_class=PlainTextResponse)
async def verify_token_endpoint(request: Request):
    params = request.query_params
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    mode = params.get("hub.mode")

    logging.info(
        f"[WEBHOOK VERIFY] mode={mode!r}, token_param={token!r}, "
        f"env_token={VERIFY_TOKEN!r}, challenge={challenge!r}"
    )

    if token == VERIFY_TOKEN and challenge is not None:
        return PlainTextResponse(challenge)

    raise HTTPException(status_code=400, detail="Token de verificación inválido")


# ---- RECEPCIÓN DE MENSAJES ----
@app.post("/whatsapp")
async def received_message(request: Request):
    try:
        body = await request.json()
        logging.info(f"Payload recibido: {body}")

        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value or len(value["messages"]) == 0:
            return "EVENT_RECEIVED"

        message = value["messages"][0]
        type_message, content = get_message_type(message)
        number = message["from"]

        contacts = value.get("contacts", [])
        name = contacts[0].get("profile", {}).get("name", "Cliente") if contacts else "Cliente"

        if number not in clientes:
            clientes[number] = Cliente(telefono=number, nombre=name)
            logging.info(f"[CLIENTE] Nuevo cliente registrado: {name} ({number})")

        print(f"Mensaje recibido de {number}: {content} (tipo: {type_message})")

        texto_normalizado = content.strip().lower() if isinstance(content, str) else ""

        estado = estado_usuarios.get(number)

        # ------------------------------------------------
        # FASE: CANTIDAD
        # ------------------------------------------------
        if estado and estado.get("fase") == "esperando_cantidad" and type_message == "text":
            try:
                cantidad = int(texto_normalizado)
                if cantidad <= 0:
                    raise ValueError()
            except ValueError:
                await send_text(number, "❌ Cantidad inválida. Ej: *2*.")
                return "EVENT_RECEIVED"

            estado["fase"] = "detalles_por_unidad"
            estado["cantidad_total"] = cantidad
            estado["indice_actual"] = 1
            estado["detalles"] = []

            prod = chat._buscar_producto_por_row_id(estado["row_id"])
            nombre_prod = prod["nombre"] if prod else "el producto"

            await send_text(
                number,
                f"📝 Para la unidad 1 de *{nombre_prod}*, "
                "¿completa o con alguna modificación?"
            )
            return "EVENT_RECEIVED"

        # ------------------------------------------------
        # FASE: DETALLES
        # ------------------------------------------------
        if estado and estado.get("fase") == "detalles_por_unidad" and type_message == "text":
            detalle_texto = content.strip()

            if detalle_texto.lower() in ("completa", "normal", "no"):
                detalle_texto = ""

            detalles = estado["detalles"]
            detalles.append(detalle_texto)

            cantidad_total = estado["cantidad_total"]
            ya_tengo = len(detalles)

            prod = chat._buscar_producto_por_row_id(estado["row_id"])
            nombre_prod = prod["nombre"] if prod else "el producto"

            if ya_tengo < cantidad_total:
                siguiente_n = ya_tengo + 1
                await send_text(
                    number,
                    f"📝 Para la unidad {siguiente_n} de *{nombre_prod}*, "
                    "¿completa o modificada?"
                )
                return "EVENT_RECEIVED"

            # Todas las unidades cargadas
            from collections import Counter

            contador = Counter(detalles)

            for detalle_valor, cant in contador.items():
                chat.agregar_producto_al_carrito(
                    telefono=number,
                    row_id=estado["row_id"],
                    cantidad=cant,
                    detalle=detalle_valor,
                )

            estado_usuarios.pop(number, None)

            resumen = chat.resumen_carrito(number)
            await send_text(number, resumen)
            await send_botones_siguiente_paso(number)
            return "EVENT_RECEIVED"

        # ------------------------------------------------
        # FASE: UBICACIÓN
        # ------------------------------------------------
        if estado and estado.get("fase") == "esperando_ubicacion":
            if message.get("type") == "location":
                loc = message["location"]
                lat = loc.get("latitude")
                lng = loc.get("longitude")

                chat.guardar_ubicacion(
                    number,
                    lat,
                    lng,
                    loc.get("address") or loc.get("name") or ""
                )
                estado_usuarios.pop(number, None)

                pedido = chat.pedidos.get(number)
                extra = ""
                codigo = None

                if pedido:
                    if not getattr(pedido, "codigo_validacion", None):
                        codigo = f"{random.randint(0, 999999):06d}"
                        pedido.codigo_validacion = codigo
                        codigos_pedidos[codigo] = pedido

                    if getattr(pedido, "distancia_km", 0) > 0:
                        extra += (
                            f"\n\n🛣 Distancia estimada: {pedido.distancia_km:.2f} km"
                            f"\n⏱ Tiempo aprox: {pedido.tiempo_estimado_min:.1f} min"
                        )
                    if getattr(pedido, "zona", None):
                        extra += f"\n📍 Zona de reparto: {pedido.zona}"

                mensaje = (
                    "📍 ¡Gracias! Ya registramos tu ubicación.\n"
                    "Tu pedido está en preparación. 🙌" + extra
                )

                if codigo:
                    mensaje += (
                        f"\n\n🔑 Código de validación: *{codigo}*.\n"
                        "Mostraselo al repartidor."
                    )

                await send_text(number, mensaje)
                await intentar_cerrar_lote(number)
                return "EVENT_RECEIVED"

            await send_text(
                number,
                "🚫 No puedo leer esa dirección.\n"
                "Usá el clip 📎 ➜ *Ubicación* ➜ *Enviar ubicación actual*."
            )
            return "EVENT_RECEIVED"

        # ------------------------------------------------
        # FASE: CALIFICACIÓN
        # ------------------------------------------------
        estado = estado_usuarios.get(number)
        if estado and estado.get("fase") == "esperando_calificacion" and type_message == "text":
            try:
                valor = int(texto_normalizado)
            except ValueError:
                await send_text(number, "❌ Enviá un número del 1 al 5.")
                return "EVENT_RECEIVED"

            if valor < 1 or valor > 5:
                await send_text(number, "⚠️ La calificación debe ser entre 1 y 5.")
                return "EVENT_RECEIVED"

            pedido = chat.pedidos.get(number)

            if not pedido:
                cliente = clientes.get(number)
                if cliente and cliente.pedidos:
                    pedido = cliente.pedidos[-1]

            if pedido:
                pedido.calificacion = valor

            estado_usuarios.pop(number, None)

            await send_text(
                number,
                f"✨ ¡Gracias por tu valoración de *{valor}/5*! 🙌"
            )
            return "EVENT_RECEIVED"

        # ------------------------------------------------
        # SELECCIÓN DE PRODUCTO
        # ------------------------------------------------
        es_producto = isinstance(content, str) and content.startswith("producto_")
        if es_producto:
            estado_usuarios[number] = {"fase": "esperando_cantidad", "row_id": content}

            prod = chat._buscar_producto_por_row_id(content)
            nombre_prod = prod["nombre"] if prod else "el producto elegido"

            await send_text(
                number,
                f"🍽 ¿Cuántas unidades de *{nombre_prod}* querés?\n"
                "Ejemplo: *1* o *3*."
            )
            return "EVENT_RECEIVED"

        # ------------------------------------------------
        # ACCIONES DEL MENÚ
        # ------------------------------------------------
        es_accion_menu = (
            isinstance(content, str)
            and (
                content in [
                    "next_page",
                    "prev_page",
                    "ordenar",
                    "filtrar_categoria",
                    "go_first_page",
                ]
                or content.startswith("categoria_")
            )
        )

        if es_accion_menu:
            nuevo_mensaje = chat.manejar_accion(content)
            payload = {
                "messaging_product": "whatsapp",
                "to": number,
                "type": "interactive",
                "interactive": nuevo_mensaje,
            }
            await send_to_whatsapp(payload)
            return "EVENT_RECEIVED"

        # ------------------------------------------------
        # COMANDOS DEL CARRITO
        # ------------------------------------------------

        if texto_normalizado == "seguir_comprando":
            await send_menu(number, name)
            return "EVENT_RECEIVED"

        if texto_normalizado == "quitar_producto":
            menu_quitar = chat.generar_menu_quitar_producto(number)
            if not menu_quitar:
                await send_text(number, "🧺 Tu carrito está vacío.")
                return "EVENT_RECEIVED"

            payload = {
                "messaging_product": "whatsapp",
                "to": number,
                "type": "interactive",
                "interactive": menu_quitar,
            }
            await send_to_whatsapp(payload)
            return "EVENT_RECEIVED"

        if texto_normalizado in ("carrito", "/carrito"):
            await send_text(number, chat.resumen_carrito(number))
            return "EVENT_RECEIVED"

        if texto_normalizado in ("borrar", "vaciar", "/borrar"):
            chat.vaciar_carrito(number)
            await send_text(number, "🧺 Carrito vaciado.")
            return "EVENT_RECEIVED"

        if texto_normalizado in ("/reset", "reset", "/salir", "salir"):
            chat.reset_estado()
            estado_usuarios.pop(number, None)
            chat.vaciar_carrito(number)
            await send_text(
                number,
                "🔄 Conversación reiniciada.\n"
                "Escribí algo para ver el menú."
            )
            return "EVENT_RECEIVED"

        if texto_normalizado in ("confirmar", "/confirmar", "finalizar_pedido"):
            pedido = chat.pedidos.get(number)

            if not pedido or not pedido.items:
                await send_text(
                    number,
                    "No tenés un pedido activo. Escribí algo para ver el menú."
                )
                return "EVENT_RECEIVED"

            resumen = chat.resumen_carrito(number)
            await send_text(
                number,
                resumen + "\n\n📍 Enviame tu ubicación (clip ➜ Ubicación)."
            )

            estado_usuarios[number] = {"fase": "esperando_ubicacion"}
            return "EVENT_RECEIVED"

        # ------------------------------------------------
        # QUITAR UNIDAD DEL CARRITO
        # ------------------------------------------------
        if isinstance(content, str) and content.startswith("quitar_unidad_"):
            resto = content[len("quitar_unidad_"):]
            try:
                idx_item_str, idx_unidad_str = resto.split("_", 1)
                idx_item = int(idx_item_str)
                idx_unidad = int(idx_unidad_str)
            except Exception:
                await send_text(number, "❌ No pude identificar la unidad.")
                return "EVENT_RECEIVED"

            ok = chat.quitar_unidad_del_carrito(number, idx_item, idx_unidad)
            if not ok:
                await send_text(number, "❌ No se pudo quitar la unidad.")
                return "EVENT_RECEIVED"

            resumen = chat.resumen_carrito(number)
            await send_text(number, "🗑 Unidad quitada.\n\n" + resumen)
            await send_botones_siguiente_paso(number)
            return "EVENT_RECEIVED"

        # ------------------------------------------------
        # ÚLTIMA OPCIÓN: MOSTRAR MENÚ
        # ------------------------------------------------
        await send_menu(number, name)
        return "EVENT_RECEIVED"

    except Exception as e:
        print("Error en /whatsapp:", e)
        return "EVENT_RECEIVED"


# --------------------------------------------------------
# ENDPOINTS ADMIN
# --------------------------------------------------------

@app.get("/clientesnuevos")
def clientes_nuevos():
    """Devuelve todos los clientes registrados."""
    lista_clientes = [cliente_to_dict(c) for c in clientes.values()]
    return {
        "cantidad_clientes": len(lista_clientes),
        "clientes": lista_clientes,
    }


@app.get("/pedidosporrepartidor")
def pedidos_por_repartidor():
    """Devuelve los pedidos pendientes de cada repartidor."""
    data: Dict[str, Any] = {}

    for zona, repartidor in gestor_reparto.repartidores.items():
        pendientes = repartidor.obtener_pedidos_pendientes()

        data[zona] = {
            "telefono_repartidor": repartidor.telefono_whatsapp,
            "cantidad_pendientes": len(pendientes),
            "pedidos": [pedido_to_dict(p) for p in pendientes],
        }

    return data


@app.get("/pedidosentregados")
def pedidos_entregados():
    """Pedidos entregados + estrellas + distancia + gasto nafta."""
    data: Dict[str, Any] = {}

    for zona, repartidor in gestor_reparto.repartidores.items():
        entregados = repartidor.pedidos_entregados

        calificaciones = [
            p.calificacion
            for p in entregados
            if getattr(p, "calificacion", None) is not None
        ]

        promedio = sum(calificaciones) / len(calificaciones) if calificaciones else None

        distancia_total_km = sum(getattr(p, "distancia_km", 0.0) or 0.0 for p in entregados)

        litros_nafta = distancia_total_km / 10.0

        data[zona] = {
            "telefono_repartidor": repartidor.telefono_whatsapp,
            "cantidad_entregados": len(entregados),
            "cantidad_calificados": len(calificaciones),
            "promedio_estrellas": promedio,
            "distancia_total_km": distancia_total_km,
            "litros_nafta_estimados": litros_nafta,
            "pedidos": [pedido_to_dict(p) for p in entregados],
        }

    return data


@app.get("/entregarpedido/{codigo}")
async def entregar_pedido(codigo: str):
    """
    Marca un pedido como entregado a partir de su código de validación
    y le pide al cliente que califique al repartidor.
    """
    pedido = codigos_pedidos.get(codigo)
    if not pedido:
        raise HTTPException(status_code=404, detail="Código inválido o pedido no encontrado.")

    if pedido.entregado:
        return {"status": "already_delivered", "mensaje": "El pedido ya estaba entregado."}

    pedido.entregado = True

    zona = getattr(pedido, "zona", None) or "SO"
    repartidor = gestor_reparto.repartidores.get(zona)

    if repartidor:
        repartidor.registrar_entrega(pedido)

        if pedido in repartidor.lote_actual.pedidos:
            repartidor.lote_actual.pedidos.remove(pedido)
        elif pedido in repartidor.cola_espera:
            repartidor.cola_espera.remove(pedido)

    codigos_pedidos.pop(codigo, None)

    texto = (
        "✅ Marcamos tu pedido como *entregado*.\n\n"
        "Por favor valorá al repartidor con una nota del *1 al 5*.\n\n"
        "Enviá solo el número. Ej: *5*."
    )

    await send_text(pedido.telefono_cliente, texto)

    estado_usuarios[pedido.telefono_cliente] = {"fase": "esperando_calificacion"}

    return {"status": "ok", "telefono_cliente": pedido.telefono_cliente, "zona": zona}


# --------------------------------------------------------
# MAIN LOCAL
# --------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
