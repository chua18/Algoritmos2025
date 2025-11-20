import os
import logging
from typing import Any, Dict

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

        # A veces llegan solo "statuses" sin messages
        if "messages" not in value or len(value["messages"]) == 0:
            return "EVENT_RECEIVED"

        message = value["messages"][0]
        type_message, content = get_message_type(message)
        number = message["from"]

        contacts = value.get("contacts", [])
        name = contacts[0].get("profile", {}).get("name", "Cliente") if contacts else "Cliente"

        print(f"Mensaje recibido de {number}: {content} (tipo: {type_message})")

        # Normalizamos el texto para comandos
        texto_normalizado = ""
        if isinstance(content, str):
            texto_normalizado = content.strip().lower()

        # 1) ¿Seleccionó un PRODUCTO del menú? (row id: 'producto_X')
        es_producto = isinstance(content, str) and content.startswith("producto_")

        if es_producto:
            try:
                item, total = chat.agregar_producto_al_carrito(number, content)
                mensaje = (
                    f"✅ *{item.nombre}* agregado al carrito (${item.precio}).\n"
                    f"💵 Total actual: ${total}\n\n"
                    "Escribí *carrito* para ver todo lo que llevás."
                )
            except ValueError:
                mensaje = "❌ No pude identificar ese producto. Probá de nuevo."

            await send_text(number, mensaje)
            # Opcional: volver a mostrar el menú actual (manteniendo filtro/página)
            await send_menu(number, name)
            return "EVENT_RECEIVED"

        # 2) ¿Es una acción del MENÚ (paginado / filtros / categorías)?
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

        # 3) COMANDOS DE TEXTO: reset, ver carrito, vaciar carrito

        # Reset de menú (sin tocar carrito)
        if texto_normalizado in ("/reset", "/inicio", "menu"):
            chat.reset_estado()
            await send_menu(number, name)
            return "EVENT_RECEIVED"

        # Ver carrito
        if texto_normalizado in ("carrito", "/carrito"):
            resumen = chat.resumen_carrito(number)
            await send_text(number, resumen)
            return "EVENT_RECEIVED"

        # Vaciar carrito
        if texto_normalizado in ("borrar", "vaciar", "/borrar"):
            chat.vaciar_carrito(number)
            await send_text(number, "🧺 Carrito vaciado.")
            return "EVENT_RECEIVED"

        # 4) Cualquier otro texto (por ahora) → mostrar menú
        await send_menu(number, name)
        return "EVENT_RECEIVED"

    except Exception as e:
        print("Error en /whatsapp:", e)
        return "EVENT_RECEIVED"


# --------------------------------------------------------
# MAIN LOCAL
# --------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
