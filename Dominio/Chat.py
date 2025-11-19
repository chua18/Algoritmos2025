from functools import wraps
from typing import Any, Optional, Dict, Callable
import inspect
from datetime import datetime


class Chat:
    def __init__(self) -> None:
        # Comandos registrados: "/inicio", "/ayuda", etc.
        # Cada comando guarda metadata de la función asociada.
        self.function_graph: Dict[str, Dict[str, Any]] = {}

        # Teléfono actual del usuario que se está manejando
        self.user_phone: str = ""

        # Función que debe manejar el próximo mensaje (flujo paso a paso)
        self.waiting_for: Optional[Callable[[str], None]] = None

        # Datos de la conversación (carrito, página actual, categoría, etc.)
        self.conversation_data: Dict[str, Any] = {}

        # Función para enviar mensajes al usuario (la setea main.py)
        # Debe ser: Callable[[str], None]
        self.enviador: Optional[Callable[[str], None]] = None

    # ------------------------------------------------------------------
    # Helpers de estado
    # ------------------------------------------------------------------

    def set_waiting_for(self, func: Optional[Callable[[str], None]]) -> None:
        """Define qué función procesará el próximo mensaje del usuario."""
        self.waiting_for = func

    def clear_waiting_for(self) -> None:
        """Limpia la función en espera."""
        self.waiting_for = None

    def set_conversation_data(self, key: str, value: Any) -> None:
        """Guarda un dato en la conversación actual."""
        self.conversation_data[key] = value

    def get_conversation_data(self, key: str, default: Any = None) -> Any:
        """Obtiene un dato de la conversación actual."""
        return self.conversation_data.get(key, default)

    def clear_conversation_data(self) -> None:
        """Limpia todos los datos de la conversación."""
        self.conversation_data.clear()

    # ------------------------------------------------------------------
    # Envío de mensajes
    # ------------------------------------------------------------------

    def enviar(self, texto: str) -> None:
        """
        Envía un mensaje al usuario.
        Si no hay 'enviador' configurado, hace print (útil para debug local).
        """
        if self.enviador is not None:
            self.enviador(texto)
        else:
            print(texto)

    # ------------------------------------------------------------------
    # Registro de comandos
    # ------------------------------------------------------------------

    def register_function(self, command: str) -> Callable:
        """
        Decorador para registrar comandos del bot.

        Uso:
        @bot.register_function("/inicio")
        def cmd_inicio(mensaje: str):
            ...
        """
        def decorator(func: Callable[[str], None]) -> Callable[[str], None]:
            @wraps(func)
            def wrapper(mensaje: str) -> None:
                return func(mensaje)

            # Guardamos metadata del comando
            self.function_graph[command] = {
                "function": wrapper,
                "name": func.__name__,
                "doc": func.__doc__,
                "created_at": datetime.now(),
                "params": inspect.signature(func),
            }
            return wrapper

        return decorator

    # ------------------------------------------------------------------
    # Procesamiento de mensajes
    # ------------------------------------------------------------------

    def process_message(self, mensaje: str) -> None:
        """
        Procesa el mensaje entrante del usuario.
        - Si hay una función en 'waiting_for' y el mensaje NO es un comando,
          se delega a esa función.
        - Si el mensaje empieza con '/', se intenta ejecutar como comando.
        - En otro caso, se avisa que debe usar un comando.
        """
        if mensaje is None:
            return

        mensaje = mensaje.strip()
        if not mensaje:
            return

        # 1) Si el mensaje es un comando, siempre priorizamos el comando
        if mensaje.startswith('/'):
            comando = mensaje.split()[0]  # Tomar solo el comando sin argumentos
            if comando in self.function_graph:
                try:
                    self.function_graph[comando]["function"](mensaje)
                except Exception as exc:
                    # Manejo básico de errores de comandos
                    self.enviar("⚠️ Ocurrió un error al ejecutar el comando.")
                    print(f"Error en comando {comando}: {exc}")
            else:
                self.enviar("❌ Comando no reconocido. Usa /ayuda para ver los comandos disponibles.")
            return

        # 2) Si no es comando y hay una función esperando la respuesta
        if self.waiting_for is not None:
            try:
                self.waiting_for(mensaje)
            except Exception as exc:
                self.enviar("⚠️ Ocurrió un error al procesar tu mensaje.")
                print(f"Error en waiting_for: {exc}")
            return

        # 3) Si no hay función en espera y no es comando
        self.enviar("❌ Por favor usa un comando. Escribe /ayuda para ver las opciones disponibles.")


# Crear instancia global del bot
bot = Chat()
