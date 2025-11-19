# main.py
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse
import httpx
import os
import logging

from Dominio.Chat import bot               # Clase Chat (bot global)
from Dominio import Pedidos        # Import necesario para registrar comandos (no se usa directo)

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables de entorno necesarias para WhatsApp / Meta
WHATSAPP_URL = os.getenv("GRAPH_SEND_URL")   # p.ej. https://graph.facebook.com/v22.0/<PHONE_ID>/messages
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")     # Token de acceso de Meta
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")     # Token de verificación para el webhook (GET)

app = FastAPI()


# -------------------------------------------------------------------
# Funciones auxiliares para enviar y recibir mensajes
# -------------------------------------------------------------------

def enviar_texto_whatsapp(to: str, body: str) -> None:
    """
    Envía un mensaje de texto simple a través de la API de WhatsApp.
    """
    if not WHATSAPP_URL or not ACCESS_TOKEN:
        logger.error("Faltan WHATSAPP_URL o ACCESS_TOKEN en las variables de entorno.")
        return

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(WHATSAPP_URL, json=payload, headers=headers, timeout=10)
        if response.status_code >= 400:
            logger.error("Error al enviar mensaje a WhatsApp: %s - %s", response.status_code, response.text)
    except Exception as exc:
        logger.error("Excepción enviando mensaje a WhatsApp: %s", exc)


def enviar_texto_para_Bot(body: str) -> None:
    """
    Función que el bot usará como 'enviador'.
    Toma el teléfono desde bot.user_phone (seteado en cada request).
    """
    if not bot.user_phone:
        logger.warning("bot.user_phone está vacío, no se puede enviar el mensaje.")
        return

    enviar_texto_whatsapp(bot.user_phone, body)


def extraer_mensaje_y_telefono(data: dict) -> tuple[str, str]:
    """
    Extrae el texto del mensaje y el número de teléfono
    desde el payload enviado por WhatsApp.
    Adaptar según el formato que estés usando (text, interactive, etc.).
    """
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        mensaje = value["messages"][0]
    except (KeyError, IndexError) as exc:
        logger.error("Formato inesperado del payload de WhatsApp: %s", exc)
        raise HTTPException(status_code=400, detail="Formato inesperado del payload de WhatsApp")

    texto = ""

    tipo = mensaje.get("type")
    if tipo == "text":
        texto = mensaje["text"]["body"]
    elif tipo == "interactive":
        interactive = mensaje["interactive"]
        if "list_reply" in interactive:
            texto = interactive["list_reply"]["id"]
        elif "button_reply" in interactive:
            texto = interactive["button_reply"]["id"]
        else:
            logger.warning("Tipo de mensaje interactivo no manejado: %s", interactive)
            texto = ""
    else:
        logger.warning("Tipo de mensaje no manejado: %s", tipo)
        texto = ""

    telefono = mensaje.get("from", "")

    if not telefono:
        raise HTTPException(status_code=400, detail="No se pudo obtener el teléfono del remitente")

    return texto, telefono


# -------------------------------------------------------------------
# Rutas de FastAPI
# -------------------------------------------------------------------

@app.get("/", response_class=PlainTextResponse)
async def root():
    """
    Endpoint simple para comprobar que la app está corriendo.
    """
    return "API de WhatsApp bot (Obligatorio Algoritmos) funcionando."


@app.get("/webhook", response_class=PlainTextResponse)
async def verificar_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
):
    """
    Verificación del webhook de Meta (GET).
    Meta llama a este endpoint cuando configurás el webhook.
    """
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        # Devolver el challenge que envía Meta
        logger.info("Webhook verificado correctamente.")
        return hub_challenge or ""
    else:
        logger.warning("Intento de verificación de webhook fallido.")
        raise HTTPException(status_code=403, detail="Token de verificación inválido")


@app.post("/webhook")
async def webhook_whatsapp(request: Request):
    """
    Endpoint que recibe los mensajes de WhatsApp (POST).
    Cada mensaje se pasa al 'bot' para que lo procese.
    """
    data = await request.json()
    logger.info("Payload recibido de WhatsApp: %s", data)

    # WhatsApp envía también notificaciones que no son mensajes (ej: status)
    # Filtramos y procesamos solo si hay 'messages'
    try:
        value = data["entry"][0]["changes"][0]["value"]
        if "messages" not in value:
            # No hay mensajes (puede ser una notificación de estado)
            return {"status": "ok"}
    except (KeyError, IndexError):
        return {"status": "ok"}

    # 1. Extraer texto y teléfono
    texto, telefono = extraer_mensaje_y_telefono(data)

    # 2. Configurar el teléfono actual en el bot
    bot.user_phone = telefono

    # 3. Configurar el "enviador" sin usar lambda
    bot.enviador = enviar_texto_para_Bot

    # 4. Pasar el mensaje al cerebro del bot
    bot.process_message(texto)

    return {"status": "ok"}
