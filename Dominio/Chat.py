from typing import Any, Dict, List
from Menu import menuCompleto

PAGE_SIZE = 5  # cantidad de productos por página

def get_paginated_menu(page: int = 1, category: str = None) -> List[Dict[str, Any]]:
    resultados = menuCompleto

    # Filtrar por categoría si se pasa
    if category:
        resultados = [item for item in resultados if item["categoria"].lower() == category.lower()]

    # Paginación
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    paginated = resultados[start:end]

    return paginated


class Chat:
    def __init__(self):
        self.pagina_Actual = 1
        self.categoria_Actual = None  # sin filtro por defecto
        self.orden_por_precio = None  # puede ser 'asc' o 'desc'

    def generar_mensaje_menu(self) -> Dict[str, Any]:
        productos = get_paginated_menu(self.pagina_Actual, self.categoria_Actual)

        # Ordenar por precio si corresponde
        if self.orden_por_precio == "asc":
            productos.sort(key=lambda x: x["precio"])
        elif self.orden_por_precio == "desc":
            productos.sort(key=lambda x: x["precio"], reverse=True)

        # Texto principal del cuerpo
        texto = "🍔 *Menú disponible:*\nSeleccioná un producto o una acción.\n"

        # Construcción del mensaje tipo lista
        botones = {
            "type": "list",
            "header": {"type": "text", "text": "Menú de productos"},
            "body": {"text": texto},
            "footer": {"text": f"📄 Página {self.pagina_Actual}"},
            "action": {
                "button": "Ver opciones",
                "sections": [
                    {
                        "title": "Productos disponibles",
                        "rows": [
                            {
                                "id": f"producto_{p['id']}",
                                "title": f"{p['nombre']} - ${p['precio']}",
                                "description": f"{p['descripcion']}"
                            }
                            for p in productos
                        ]
                    },
                    {
                        "title": "Acciones",
                        "rows": [
                            {"id": "prev_page", "title": "⬅️ Página anterior"},
                            {"id": "next_page", "title": "➡️ Página siguiente"},
                            {"id": "ordenar", "title": "↕️ Ordenar precio"},
                            {"id": "filtrar_categoria", "title": "📂 Filtrar por categoría"},

                            
                        ]                        
                    }
                ]
            }
        }

        if self.pagina_Actual>=3:
            botones["action"]["sections"][1]["rows"].append(
                {"id": "go_first_page", "title": "🔁Volver al inicio"},
            )

        return botones

    def manejar_accion(self, accion_id: str, category: str = None):
        # Acciones del usuario
        if accion_id == "next_page":
            self.pagina_Actual += 1

        elif accion_id == "prev_page" and self.pagina_Actual > 1:
            self.pagina_Actual -= 1

        elif accion_id == "ordenar":
           if self.orden_por_precio == "asc":
              self.orden_por_precio = "desc"
           else :
               self.orden_por_precio="asc"

        elif accion_id=="go_first_page":
            self.pagina_Actual=1

        elif accion_id.startswith("filtro_"):  # ejemplo: filtro_postres
            self.categoria_Actual = accion_id.replace("filtro_", "")
            self.pagina_Actual = 1
            
        elif accion_id.startswith("producto_"):
            producto_id = int(accion_id.replace("producto_", ""))
            return {"mensaje": f"🛒 Agregaste el producto con ID {producto_id} al carrito."}

        # Retorna el mensaje actualizado del menú
        return self.generar_mensaje_menu()
