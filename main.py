from fastapi import FastAPI, HTTPException, Request
from utils.get_message_type import get_message_type
import os
import logging
import httpx
from typing import Any, Dict, List
from Dominio.Chat import Chat

logging.basicConfig(level=logging.INFO)

chat = Chat()

app = FastAPI()

# --- CREDENCIALES Y CONFIGURACIÓN ---
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
VERSION = os.getenv("VERSION", "v22.0")

GRAPH_SEND_URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"

logging.info(f"ACCESS_TOKEN cargado? {bool(ACCESS_TOKEN)}")
logging.info(f"PHONE_NUMBER_ID: {PHONE_NUMBER_ID!r}")
logging.info(f"GRAPH_SEND_URL: {GRAPH_SEND_URL}")
# --------------------------------------------------------
# FUNCIONES AUXILIARES PARA ENVIAR MENSAJES A WHATSAPP
# --------------------------------------------------------
async def send_to_whatsapp(payload: Dict[str, Any]) -> None:
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        logging.warning(
            f"Falta ACCESS_TOKEN o PHONE_NUMBER_ID. "
            f"(ACCESS_TOKEN={bool(ACCESS_TOKEN)}, PHONE_NUMBER_ID={bool(PHONE_NUMBER_ID)})"
        )
        logging.info(f"MOCK SEND => {payload}")
        return

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(GRAPH_SEND_URL, headers=headers, json=payload)
        logging.info(f"Respuesta WhatsApp: {resp.status_code} {resp.text}")
        resp.raise_for_status()

async def send_menu(to: str, nombre: str = "Cliente") -> None:
    """Envía el menú actual (paginado) al usuario."""
    msg = chat.generar_mensaje_menu()
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": msg
    }
    print(f"payload del menú paginado:\n{payload}")
    await send_to_whatsapp(payload)


# --------------------------------------------------------
# ENDPOINTS
# --------------------------------------------------------
@app.get("/welcome")
def index():
    return {"mensaje": "welcome developer"}


ACCESS_TOKEN = "EAATMVR8dZCWcBP28NQcW8hJfXjPqSwwdwP923Ko34BnRbYYJOejUvDIS1ac7ux8DEDLuiepKxuuTsHgzomdebv4T0AGfZCSgHgU6ZCjHIV6KGRe6BfVEc1ktQZC4zcBSU7bPR8VxOSOu9OUdrV5PFbhnVkgEXzy8m0QRq1RbZBdIPGLWRha55Tq92dZAOwCRe9CZCeq9tatLgdTzN2tQo3DCBCPpFxHwSm7iSHwvT2dOeTjNZBJt37yO7LAzICueAcacP2JZCWh6E7PMHOqr6LiiAwwZDZD"


@app.get("/whatsapp")
async def verify_token(request: Request):
    try:
        query_params = request.query_params
        verify_token = query_params.get("hub.verify_token")
        challenge = query_params.get("hub.challenge")

        if verify_token is not None and challenge is not None and verify_token == ACCESS_TOKEN:
            return int(challenge)
        else:
            raise HTTPException(status_code=400, detail="Token de verificación inválido o parámetros faltantes")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en la verificación: {e}")


@app.post("/whatsapp")
async def received_message(request: Request):
    try:
        body = await request.json()
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" in value and len(value["messages"]) > 0:
            message = value["messages"][0]
            type_message, content = get_message_type(message)
            number = message["from"]
            contacts = value.get("contacts", [])
            name = contacts[0].get("profile", {}).get("name", "Cliente") if contacts else "Cliente"

            print(f"Mensaje recibido de {number}: {content}")

            # --- NUEVA LÓGICA CORREGIDA ---
            # WhatsApp List devuelve el ID del row (no el texto)
            if content in ["next_page", "prev_page", "ordenar", "filtrar_categoria", "go_first_page"]:

                nuevo_mensaje = chat.manejar_accion(content)
                payload = {
                    "messaging_product": "whatsapp",
                    "to": number,
                    "type": "interactive",
                    "interactive": nuevo_mensaje
                }
                await send_to_whatsapp(payload)

            else:
                # Primer mensaje o texto cualquiera → mostrar menú inicial
                await send_menu(number, name)

        return "EVENT_RECEIVED"

    except Exception as e:
        print("Error en /whatsapp:", e)
        return "EVENT_RECEIVED"


# --------------------------------------------------------
# MAIN SERVER
# --------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

