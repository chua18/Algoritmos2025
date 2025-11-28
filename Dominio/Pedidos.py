from typing import Any, Dict, List, Optional

from Menu import menuCompleto  # usamos tu menuCompleto con 'nombre', 'precio', 'categoria', 'descripcion'

PAGE_SIZE = 5

# ------------------ LÓGICA DE MENÚ (REUTILIZABLE) ------------------ #

def get_paginated_menu(page: int = 1, categoria: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Devuelve una página de productos desde menuCompleto.
    Si pasás categoría, filtra por ese campo.
    """
    productos = menuCompleto

    if categoria is not None:
        productos = [
            item for item in menuCompleto
            if item.get("categoria", "").lower() == categoria.lower()
        ]

    inicio = (page - 1) * PAGE_SIZE
    fin = inicio + PAGE_SIZE
    return productos[inicio:fin]
