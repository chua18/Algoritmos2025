def get_message_type(message):
    """
    Devuelve una tupla (tipo, contenido) según el tipo de mensaje recibido.
    Soporta texto normal, listas interactivas y botones.
    """
    type_message = message.get("type")

    # --- Caso 1: mensaje de texto ---
    if type_message == "text":
        return "text", message["text"]["body"]

    # --- Caso 2: respuesta a lista interactiva ---
    if type_message == "interactive":
        interactive = message.get("interactive", {})
        subtype = interactive.get("type")

        if subtype == "list_reply":
            return "list_reply", interactive["list_reply"]["id"]
        elif subtype == "button_reply":
            return "button_reply", interactive["button_reply"]["id"]

    # --- Caso desconocido ---
    return type_message, None
