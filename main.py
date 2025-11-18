from fastapi import FastAPI, HTTPException, Request
from utils.get_message_type import get_message_type
import os
import logging
import httpx
from typing import Any, Dict, List
from Dominio.Chat import Chat
from fastapi.responses import PlainTextResponse

logging.basicConfig(level=logging.INFO)

chat = Chat()

app = FastAPI()

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


#ACCESS_TOKEN = "EAATMVR8dZCWcBP4DBhxLgO5zaSg6r3USZAikV8SCZA0y1Aeo3g0CISgFm1C9QXyWJaWAcBnqsw3Ca7aZA2bU5ASxH0YyLojyTDKYw8jEtDp7lHnwZC7tkYU3Dfa3v36qjDjlZA0kIX658tHBmzJ3Eqse44JvkcZCeht9aS2wpgdpEZBLQOKmUBHwcJDMnL1ZAZCU3Az7w0criorYcx7gMDaSTaefDDO8PqOLaxtCyxvZCeImpodbTtLEuo3ODnZCZA6NDyDOcsjGlZAqaGhNgThTEY9XaE"

@app.get("/whatsapp")
async def verify_token_endpoint(request: Request):
    params = request.query_params
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    mode = params.get("hub.mode")

    logging.info(f"[WEBHOOK VERIFY] mode={mode!r}, token_param={token!r}, env_token={VERIFY_TOKEN!r}, challenge={challenge!r}")

    # Meta suele mandar hub.mode=subscribe, pero para la prueba desde el navegador
    # lo importante es que el token y el challenge estén
    if token == VERIFY_TOKEN and challenge is not None:
        # Devolver el challenge tal cual, como texto plano
        return PlainTextResponse(challenge)

    raise HTTPException(status_code=400, detail="Token de verificación inválido")
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

