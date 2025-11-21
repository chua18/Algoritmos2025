import os
import logging
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

from Dominio.Chat import Chat
from utils.get_message_type import get_message_type

# -----------------------------------
# CONFIGURACIÓN BÁSICA
# -----------------------------------
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Instancia de tu Chat anteriora
chat = Chat()

# --- CREDENCIALES Y CONFIGURACIÓN ---
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
VERSION = os.getenv("VERSION", "v22.0")

GRAPH_SEND_URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"

logging.info(f"ACCESS_TOKEN cargado? {bool(ACCESS_TOKEN)}")
logging.info(f"PHONE_NUMBER_ID: {PHONE_NUMBER_ID!r}")
logging.info(f"GRAPH_SEND_URL: {GRAPH_SEND_URL}")

estado_usuarios: Dict[str, Dict[str, Any]] = {}

# --------------------------------------------------------
# FUNCIONES AUXILIARES PARA ENVIAR MENSAJES A WHATSAPP
# --------------------------------------------------------
async def send_to_whatsapp(payload: Dict[str, Any]) -> None:
    """
    Envía un payload crudo a la API de WhatsApp.
    """
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
    """
    Envía el menú actual (paginado) al usuario usando tu Chat.
    """
    
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


# --------------------------------------------------------
# ENDPOINTS
# --------------------------------------------------------

@app.get("/welcome")
def index():
    return {"mensaje": "welcome developer"}


# ✅ VERIFICACIÓN DEL WEBHOOK (GET /whatsapp)
@app.get("/whatsapp", response_class=PlainTextResponse)
async def verify_token_endpoint(request: Request):
    params = request.query_params
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    mode = params.get("hub.mode")

    logging.info(
        f"[WEBHOOK VERIFY] mode={mode!r}, token_param={token!r}, env_token={VERIFY_TOKEN!r}, challenge={challenge!r}"
    )

    # Meta manda hub.mode=subscribe cuando verifica
    if token == VERIFY_TOKEN and challenge is not None:
        return PlainTextResponse(challenge)

    raise HTTPException(status_code=400, detail="Token de verificación inválido")


# ✅ RECEPCIÓN DE MENSAJES (POST /whatsapp)
@app.post("/whatsapp")
async def received_message(request: Request):
    try:
        body = await request.json()
        logging.info(f"Payload recibido: {body}")

        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        # A veces llegan solo "statuses", sin mensajes nuevos
        if "messages" not in value or len(value["messages"]) == 0:
            return "EVENT_RECEIVED"

        message = value["messages"][0]
        type_message, content = get_message_type(message)
        number = message["from"]

        contacts = value.get("contacts", [])
        name = contacts[0].get("profile", {}).get("name", "Cliente") if contacts else "Cliente"

        print(f"Mensaje recibido de {number}: {content} (tipo: {type_message})")

        texto_normalizado = ""
        if isinstance(content, str):
            texto_normalizado = content.strip().lower()

        # ==========================
        # 0) MANEJO DE FASES (CANTIDAD / DETALLES)
        # ==========================
        estado = estado_usuarios.get(number)

        # FASE: esperar cantidad
        if estado and estado.get("fase") == "esperando_cantidad" and type_message == "text":
            try:
                cantidad = int(texto_normalizado)
                if cantidad <= 0:
                    raise ValueError()
            except ValueError:
                await send_text(
                    number,
                    "❌ No entendí la cantidad. Escribí un número mayor a 0, por ejemplo *2*."
                )
                return "EVENT_RECEIVED"

            # Pasamos a fase de detalle unitario
            estado["fase"] = "detalles_por_unidad"
            estado["cantidad_total"] = cantidad
            estado["indice_actual"] = 1
            estado["detalles"] = []

            prod = chat._buscar_producto_por_row_id(estado["row_id"])
            nombre_prod = prod["nombre"] if prod else "el producto"

            await send_text(
                number,
                f"📝 Para la unidad 1 de *{nombre_prod}*, "
                "¿la querés *completa* o con alguna modificación?\n"
                "Ejemplo: *completa* o *sin panceta*."
            )
            return "EVENT_RECEIVED"

        # FASE: pedir detalle por cada unidad
        if estado and estado.get("fase") == "detalles_por_unidad" and type_message == "text":
            detalle_texto = content.strip()

            if detalle_texto.lower() in ("completa", "normal", "no"):
                detalle_texto = ""

            estado["detalles"].append(detalle_texto)

            cantidad_total = estado["cantidad_total"]
            indice_actual = estado["indice_actual"] + 1
            estado["indice_actual"] = indice_actual

            prod = chat._buscar_producto_por_row_id(estado["row_id"])
            nombre_prod = prod["nombre"] if prod else "el producto"

            if indice_actual <= cantidad_total:
                await send_text(
                    number,
                    f"📝 Para la unidad {indice_actual} de *{nombre_prod}*, "
                    "¿la querés *completa* o con alguna modificación?"
                )
                return "EVENT_RECEIVED"

            # Ya tenemos todos los detalles → agrupamos por tipo de detalle
            from collections import Counter
            detalles = estado["detalles"]  # lista de strings ("" para completas)
            contador = Counter(detalles)

            total = None
            items_creados = []

            for detalle_valor, cant in contador.items():
                item, total = chat.agregar_producto_al_carrito(
                    telefono=number,
                    row_id=estado["row_id"],
                    cantidad=cant,
                    detalle=detalle_valor,
                )
                items_creados.append(item)

            del estado_usuarios[number]

            lineas = []
            nombre_base = items_creados[0].nombre if items_creados else "Producto"
            cantidad_total = sum(it.cantidad for it in items_creados)
            lineas.append(f"✅ *{nombre_base}* x{cantidad_total} agregado al carrito:")

            for it in items_creados:
                if it.detalle:
                    lineas.append(f"   - x{it.cantidad} ({it.detalle})")
                else:
                    lineas.append(f"   - x{it.cantidad} completas")

            if total is not None:
                lineas.append(f"\n💵 Total actual (con descuentos aplicados): ${total}")

            lineas.append("\nEscribí *carrito* para ver todo lo que llevás.")

            await send_text(number, "\n".join(lineas))
            await send_menu(number, name)
            return "EVENT_RECEIVED"


        # ==========================
        # 1) SELECCIÓN DE PRODUCTO (LISTA)
        # ==========================
        es_producto = isinstance(content, str) and content.startswith("producto_")
        if es_producto:
            # Iniciamos flujo: primero cantidad
            estado_usuarios[number] = {
                "fase": "esperando_cantidad",
                "row_id": content,
            }

            prod = chat._buscar_producto_por_row_id(content)
            nombre_prod = prod["nombre"] if prod else "el producto elegido"

            await send_text(
                number,
                f"🍽 ¿Cuántas unidades de *{nombre_prod}* querés?\n"
                "Escribí un número, por ejemplo *1* o *3*."
            )
            return "EVENT_RECEIVED"

        # ==========================
        # 2) ACCIONES DEL MENÚ (next_page, ordenar, filtrar_categoria, etc.)
        # ==========================
        es_accion_menu = (
            isinstance(content, str)
            and (
                content in ["next_page", "prev_page", "ordenar", "filtrar_categoria", "go_first_page"]
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

        # ==========================
        # 3) COMANDOS DE TEXTO (carrito, borrar, reset, confirmar)
        # ==========================
        if texto_normalizado in ("carrito", "/carrito"):
            resumen = chat.resumen_carrito(number)
            await send_text(number, resumen)
            return "EVENT_RECEIVED"

        if texto_normalizado in ("borrar", "vaciar", "/borrar"):
            chat.vaciar_carrito(number)
            await send_text(number, "🧺 Carrito vaciado.")
            return "EVENT_RECEIVED"

        if texto_normalizado in ("/reset", "reset", "/salir", "salir"):
            # limpiamos estado de menú y carrito de ese user
            chat.reset_estado()
            estado_usuarios.pop(number, None)
            chat.vaciar_carrito(number)
            await send_text(
                number,
                "🔄 Se reinició la conversación y el carrito. "
                "Escribí cualquier cosa para ver el menú desde cero."
            )
            return "EVENT_RECEIVED"

         # ✅ CONFIRMAR PEDIDO
        if texto_normalizado in ("confirmar", "/confirmar"):
            pedido = chat.pedidos.get(number)

            if not pedido or not pedido.items:
                await send_text(
                    number,
                    "🧺 Tu carrito está vacío, todavía no puedo confirmar nada.\n"
                    "Elegí algún producto del menú primero."
                )
                return "EVENT_RECEIVED"

            resumen = chat.resumen_carrito(number)

            await send_text(
                number,
                resumen
                + "\n\n✅ *Pedido confirmado.*\n"
                  "En la siguiente etapa te voy a pedir tu ubicación para calcular el envío."
            )
        # ==========================
        # 4) CUALQUIER OTRO TEXTO → MOSTRAR MENÚ
        # ==========================
        await send_menu(number, name)
        return "EVENT_RECEIVED"

    except Exception as e:
        print("Error en /whatsapp:", e)
        # Siempre devolver EVENT_RECEIVED para que Meta no reintente infinitamente
        return "EVENT_RECEIVED"


# --------------------------------------------------------
# MAIN LOCAL
# --------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
