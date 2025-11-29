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

# Instancia de tu Chat anteriora
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



def cliente_to_dict(cliente: Cliente) -> Dict[str, Any]:
    
   # Convierte un Cliente en un diccionario simple para JSON.
   
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
   
   # Convierte un Pedido en un diccionario serializable a JSON con los campos más importantes para debug/monitoreo.
   
    lat = None
    lng = None
    if pedido.ubicacion:
        lat, lng = pedido.ubicacion

    return {
        "telefono_cliente": pedido.telefono_cliente,
        "zona": getattr(pedido, "zona", None),
        "total": pedido.total,
        "direccion": pedido.direccion_texto,
        "ubicacion": {"lat": lat, "lng": lng} if lat is not None and lng is not None else None,
        "distancia_km": getattr(pedido, "distancia_km", None),
        "tiempo_estimado_min": getattr(pedido, "tiempo_estimado_min", None),
        "cantidad_items": len(pedido.items),
    }

# --------------------------------------------------------
# FUNCIONES AUXILIARES PARA ENVIAR MENSAJES A WHATSAPP
# --------------------------------------------------------
async def send_to_whatsapp(payload: Dict[str, Any]) -> None:
    
   # Envía un payload crudo a la API de WhatsApp.
   
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
   
   # Envía el menú actual (paginado) al usuario usando tu Chat.
   
    
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
    
   # Envía botones para que el usuario elija si quiere seguir comprando, quitar productos o finalizar el pedido.
    
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
                        "reply": {
                            "id": "seguir_comprando",
                            "title": "🛒 Seguir comprando",
                        },
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "quitar_producto",
                            "title": "🗑 Quitar producto",
                        },
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "finalizar_pedido",
                            "title": "✅ Finalizar pedido",
                        },
                    },
                ]
            },
        },
    }
    await send_to_whatsapp(payload)

    
async def upload_media(file_path: str, mime_type: str = "image/gif") -> str:
    
   # Sube un archivo a la API de WhatsApp y devuelve el media_id.
  
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        logging.warning("No hay ACCESS_TOKEN o PHONE_NUMBER_ID para subir media.")
        return ""

    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/media"

    async with httpx.AsyncClient(timeout=30) as client:
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f, mime_type),
            }
            data = {
                "messaging_product": "whatsapp",
            }
            headers = {
                "Authorization": f"Bearer {ACCESS_TOKEN}",
            }
            resp = await client.post(url, data=data, files=files, headers=headers)

        logging.info(f"Subida de media: {resp.status_code} {resp.text}")
        resp.raise_for_status()
        media_id = resp.json().get("id", "")
        return media_id


async def enviar_lote_repartidor(repartidor_id: str) -> None:
    """
    Toma el lote_actual del repartidor indicado,
    genera la imagen (PNG) con la ruta de todos los pedidos,
    y la envía al repartidor con un resumen de cada pedido.
    Luego marca el lote como enviado (y carga el siguiente si hay cola).
    """
    repartidor = gestor_reparto.repartidores.get(repartidor_id)
    if not repartidor:
        logging.warning(f"[REPARTO] No hay repartidor configurado con id={repartidor_id}")
        return

    pedidos_lote: List[Pedido] = gestor_reparto.obtener_lote_actual(repartidor_id)
    if not pedidos_lote:
        logging.info(f"[REPARTO] No hay pedidos en el lote actual del repartidor {repartidor_id}.")
        return

    # 1) Generar imagen (PNG) para el lote
    png_path = Rutas.generar_gif_ruta_lote(pedidos_lote)
    if not png_path:
        logging.warning(f"[REPARTO] No se pudo generar la imagen del lote (PNG) para repartidor={repartidor_id}.")
        return

    # 2) Subir la imagen PNG
    media_id = await upload_media(png_path, "image/png")
    if not media_id:
        logging.warning(f"[REPARTO] No se pudo subir la imagen PNG a WhatsApp para repartidor={repartidor_id}.")
        return

    # 3) Armar resumen para el repartidor
    lineas: List[str] = []
    lineas.append(f"🛵 *Nuevo lote de pedidos (hasta 7) - Repartidor {repartidor_id}*")

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
            lineas.append(f"🗺 Zona del cliente: {p.zona}")
        lineas.append(f"💵 Total: ${p.total}")

    caption = "\n".join(lineas)
    if len(caption) > 1024:
        caption = caption[:1020] + "..."

    payload = {
        "messaging_product": "whatsapp",
        "to": repartidor.telefono_whatsapp,
        "type": "image",
        "image": {
            "id": media_id,
            "caption": caption,
        },
    }

    await send_to_whatsapp(payload)
    logging.info(f"[REPARTO] Imagen de ruta del lote enviada al repartidor {repartidor_id}.")

    # 4) Marcar lote como enviado y preparar el siguiente
    gestor_reparto.marcar_lote_enviado(repartidor_id)

async def intentar_cerrar_lote(telefono: str) -> None:
    pedido = chat.pedidos.get(telefono)
    if not pedido:
        logging.warning(f"[LOTE] No hay pedido activo para tel={telefono}")
        return

    # Vinculamos el pedido al cliente (si existe)
    cliente = clientes.get(telefono)
    if cliente and pedido not in cliente.pedidos:
        cliente.pedidos.append(pedido)

    # Asignar al repartidor con lote más vacío
    lote_lleno, repartidor_id = gestor_reparto.asignar_pedido(pedido)

    # sacamos el pedido activo del chat
    chat.pedidos.pop(telefono, None)

    if lote_lleno:
        await enviar_lote_repartidor(repartidor_id)

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

        if "messages" not in value or len(value["messages"]) == 0:
            return "EVENT_RECEIVED"

        message = value["messages"][0]
        type_message, content = get_message_type(message)
        number = message["from"]

        contacts = value.get("contacts", [])
        name = contacts[0].get("profile", {}).get("name", "Cliente") if contacts else "Cliente"

        if number not in clientes:
            clientes[number] = Cliente(
                telefono=number,
                nombre=name,
            )
            logging.info(f"[CLIENTE] Nuevo cliente registrado: {name} ({number})")

        print(f"Mensaje recibido de {number}: {content} (tipo: {type_message})")

        texto_normalizado = ""
        if isinstance(content, str):
            texto_normalizado = content.strip().lower()

      
        # 0) MANEJO DE FASES (CANTIDAD / DETALLES)
       
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

              # FASE: pedir detalle por cada unidad (después de que ya mandaste la cantidad)
        if estado and estado.get("fase") == "detalles_por_unidad" and type_message == "text":
            detalle_texto = content.strip()

            # Normalizamos "completa", "normal", "no" como sin detalle extra
            if detalle_texto.lower() in ("completa", "normal", "no"):
                detalle_texto = ""

            # Guardamos detalle de esta unidad
            detalles = estado["detalles"]
            detalles.append(detalle_texto)

            cantidad_total = estado["cantidad_total"]
            ya_tengo = len(detalles)

            prod = chat._buscar_producto_por_row_id(estado["row_id"])
            nombre_prod = prod["nombre"] if prod else "el producto"

            # ¿Todavía faltan unidades por preguntar?
            if ya_tengo < cantidad_total:
                siguiente_n = ya_tengo + 1
                await send_text(
                    number,
                    f"📝 Para la unidad {siguiente_n} de *{nombre_prod}*, "
                    "¿la querés *completa* o con alguna modificación?"
                )
                return "EVENT_RECEIVED"

            # 👇 Si llegamos acá, ya tenemos detalle para TODAS las unidades
            from collections import Counter

            contador = Counter(detalles)  # "" = completas

            # Primero impactamos TODO en el carrito
            for detalle_valor, cant in contador.items():
                chat.agregar_producto_al_carrito(
                    telefono=number,
                    row_id=estado["row_id"],
                    cantidad=cant,
                    detalle=detalle_valor,
                )

            # Limpiamos el estado temporal del usuario
            del estado_usuarios[number]

            # Ahora usamos SIEMPRE el resumen del carrito final
            resumen = chat.resumen_carrito(number)
            await send_text(number, resumen)

            # 👇 después del resumen mostramos botones de siguiente paso
            await send_botones_siguiente_paso(number)
            return "EVENT_RECEIVED"
        
       
        # FASE: esperando ubicación luego de confirmar pedido
      
        if estado and estado.get("fase") == "esperando_ubicacion":
            if message.get("type") == "location":
                loc = message["location"]
                lat = loc.get("latitude")
                lng = loc.get("longitude")

                # Guardar ubicación y calcular ruta
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
                    # Generar código de validación si aún no tiene
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

                mensaje = "📍 ¡Gracias! Ya registramos tu ubicación.\nTu pedido está en preparación. 🙌" + extra

                if codigo:
                    mensaje += (
                        f"\n\n🔑 Tu código de validación para la entrega es: *{codigo}*.\n"
                        "Mostraselo al repartidor cuando llegue."
                    )

                await send_text(number, mensaje)
                await intentar_cerrar_lote(number)
                return "EVENT_RECEIVED"

            # Si manda cualquier otra cosa
            await send_text(
                number,
                "🚫 No puedo leer esa dirección.\n\n"
                "Por favor enviá tu ubicación usando el *clip* 📎 ➜ *Ubicación* "
                "y elegí *Enviar tu ubicación actual*."
            )
            return "EVENT_RECEIVED"
        
      
        # FASE: esperando calificación del repartidor
        
        estado = estado_usuarios.get(number)
        if estado and estado.get("fase") == "esperando_calificacion" and type_message == "text":
            try:
                valor = int(texto_normalizado)
            except ValueError:
                await send_text(
                    number,
                    "❌ No entendí la calificación.\n"
                    "Por favor enviá un número del *1 al 5*."
                )
                return "EVENT_RECEIVED"

            if valor < 1 or valor > 5:
                await send_text(
                    number,
                    "⚠️ La calificación debe ser un número del *1 al 5*.\n"
                    "Intentá de nuevo."
                )
                return "EVENT_RECEIVED"

            pedido = chat.pedidos.get(number)
            # el pedido ya fue sacado de chat.pedidos al cerrar lote,
            # así que lo buscamos en los clientes o repartidores
            if not pedido:
                # Intentamos buscarlo en el cliente
                cliente = clientes.get(number)
                if cliente and cliente.pedidos:
                    # Tomamos el último pedido como el que se está calificando
                    pedido = cliente.pedidos[-1]

            if pedido:
                pedido.calificacion = valor

            estado_usuarios.pop(number, None)

            await send_text(
                number,
                f"✨ ¡Gracias por tu valoración de *{valor}/5*! Nos ayuda a mejorar el servicio. 🙌"
            )
            return "EVENT_RECEIVED"


        # 1) SELECCIÓN DE PRODUCTO (LISTA)
       
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

        
        # 2) ACCIONES DEL MENÚ (next_page, ordenar, filtrar_categoria, etc.)
      
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

       
        # 3) COMANDOS DE TEXTO Y BOTONES
        #    (carrito, borrar, reset, confirmar, seguir_comprando, finalizar_pedido)
       

        # Botón " Seguir comprando"
        if texto_normalizado == "seguir_comprando":
            await send_menu(number, name)
            return "EVENT_RECEIVED"
         # Botón / comando "quitar producto"
        if texto_normalizado == "quitar_producto":
            menu_quitar = chat.generar_menu_quitar_producto(number)
            if not menu_quitar:
                await send_text(
                    number,
                    "🧺 Tu carrito está vacío, no hay productos para quitar."
                )
                return "EVENT_RECEIVED"

            payload = {
                "messaging_product": "whatsapp",
                "to": number,
                "type": "interactive",
                "interactive": menu_quitar,
            }
            await send_to_whatsapp(payload)
            return "EVENT_RECEIVED"
        #texto en chat para ver el carrito
        if texto_normalizado in ("carrito", "/carrito"):
            resumen = chat.resumen_carrito(number)
            await send_text(number, resumen)
            return "EVENT_RECEIVED"
        #texto en chat para borrar, vaciar el carrito
        if texto_normalizado in ("borrar", "vaciar", "/borrar"):
            chat.vaciar_carrito(number)
            await send_text(number, "🧺 Carrito vaciado.")
            return "EVENT_RECEIVED"
        #texto en chat para resetear la conversacion y carrito "cache"
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

        #texto en chat para confrimar y finalizar el pedido
        #boton para finalizar el pedido
        if texto_normalizado in ("confirmar", "/confirmar", "finalizar_pedido"):
            pedido = chat.pedidos.get(number)

            if not pedido or not pedido.items:
                await send_text(
                    number,
                    "Por ahora no tenés un pedido pendiente. ✅\n"
                    "Escribí cualquier cosa para ver el menú y hacer uno nuevo."
                )
                return "EVENT_RECEIVED"

            resumen = chat.resumen_carrito(number)
            await send_text(
                number,
                resumen + "\n\n📍 Ahora enviame tu ubicación (clip ➜ Ubicación)\n"
                
            )

            estado_usuarios[number] = {"fase": "esperando_ubicacion"}
            return "EVENT_RECEIVED"
        
        
        # SELECCIÓN de unidad a quitar del carrito
       
        if isinstance(content, str) and content.startswith("quitar_unidad_"):
            resto = content[len("quitar_unidad_"):]  # algo como "0_2"
            try:
                idx_item_str, idx_unidad_str = resto.split("_", 1)
                idx_item = int(idx_item_str)
                idx_unidad = int(idx_unidad_str)
            except Exception:
                await send_text(
                    number,
                    "❌ No se pudo identificar la unidad a quitar."
                )
                return "EVENT_RECEIVED"

            ok = chat.quitar_unidad_del_carrito(number, idx_item, idx_unidad)
            if not ok:
                await send_text(
                    number,
                    "❌ No se pudo quitar la unidad (puede que el carrito haya cambiado)."
                )
                return "EVENT_RECEIVED"

            # Mostramos el resumen del carrito
            resumen = chat.resumen_carrito(number)
            await send_text(
                number,
                "🗑 Unidad quitada del carrito.\n\n" + resumen
            )

            # Volvemos a ofrecer los botones de siguiente paso
            await send_botones_siguiente_paso(number)
            return "EVENT_RECEIVED"


        # ==========================
        # 4) CUALQUIER OTRO TEXTO → MOSTRAR MENÚ
        # ==========================
        await send_menu(number, name)
        return "EVENT_RECEIVED"

    except Exception as e:
        print("Error en /whatsapp:", e)
        # Siempre devolver EVENT_RECEIVED para que Meta no reintente infinitamente
        return "EVENT_RECEIVED"


@app.get("/clientesnuevos")
def clientes_nuevos():
   
   # Devuelve todos los clientes registrados por el bot desde que la aplicación se inició.
    
    lista_clientes = [cliente_to_dict(c) for c in clientes.values()]

    return {
        "cantidad_clientes": len(lista_clientes),
        "clientes": lista_clientes,
    }


@app.get("/pedidosporrepartidor")
def pedidos_por_repartidor():
    
    #Devuelve, para cada repartidor, los pedidos pendientes:
    #- pedidos en el lote actual
    #- pedidos en la cola de espera
 
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
  
   # Devuelve, para cada repartidor:
   # - pedidos entregados
   # - promedio de estrellas recibidas
   # - distancia total recorrida (suma de distancias de los pedidos)
   # - gasto estimado de nafta (1 litro cada 10 km)
  
    data: Dict[str, Any] = {}

    for zona, repartidor in gestor_reparto.repartidores.items():
        entregados = repartidor.pedidos_entregados

        # --- Promedio de calificación ---
        calificaciones = [
            p.calificacion for p in entregados
            if getattr(p, "calificacion", None) is not None
        ]
        if calificaciones:
            promedio = sum(calificaciones) / len(calificaciones)
        else:
            promedio = None  # o 0.0 si preferís

        # --- Distancia total recorrida (aprox) ---
        distancia_total_km = 0.0
        for p in entregados:
            dist = getattr(p, "distancia_km", 0.0) or 0.0
            distancia_total_km += dist

        # --- Gasto de nafta: 1 litro cada 10 km ---
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
    y le pide al cliente que califique al repartidor (1-5).
    """
    pedido = codigos_pedidos.get(codigo)
    if not pedido:
        raise HTTPException(status_code=404, detail="Código inválido o pedido no encontrado.")

    # Ya entregado antes
    if pedido.entregado:
        return {"status": "already_delivered", "mensaje": "El pedido ya estaba marcado como entregado."}

    pedido.entregado = True

    # Buscar repartidor REAL que tenía este pedido
    repartidor_id = getattr(pedido, "repartidor_id", None)
    repartidor = gestor_reparto.repartidores.get(repartidor_id) if repartidor_id else None

    if repartidor:
        repartidor.registrar_entrega(pedido)
        # Opcional: sacarlo de pendientes (lote o cola)
        if pedido in repartidor.lote_actual.pedidos:
            repartidor.lote_actual.pedidos.remove(pedido)
        elif pedido in repartidor.cola_espera:
            repartidor.cola_espera.remove(pedido)

    # El código ya no se puede volver a usar
    codigos_pedidos.pop(codigo, None)

    # Pedir calificación al cliente
    texto = (
        "✅ Marcamos tu pedido como *entregado*.\n\n"
        "Por favor valorá la atención del repartidor con una nota del *1 al 5* "
        "(siendo 5 la mejor calificación).\n\n"
        "Escribí solo el número, por ejemplo: *5*."
    )
    await send_text(pedido.telefono_cliente, texto)

    # Marcamos estado del usuario para esperar su calificación
    estado_usuarios[pedido.telefono_cliente] = {"fase": "esperando_calificacion"}

    return {
        "status": "ok",
        "telefono_cliente": pedido.telefono_cliente,
        "repartidor_id": repartidor_id,
    }

# --------------------------------------------------------
# MAIN LOCAL
# --------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
