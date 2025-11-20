# Menu.py
from typing import List, Dict, TypedDict


class Producto(TypedDict):
    id: str
    nombre: str
    precio: int
    categoria: str
    descripcion: str


# Lista completa de productos (se mantiene el nombre para no romper imports)
menuCompleto: List[Producto] = [
    {"id": "1",  "nombre": "Doble cheese",       "precio": 320, "categoria": "Hamburguesas", "descripcion": "Doble carne, cheddar, cebolla"},
    {"id": "30",  "nombre": "simpe cheese",       "precio": 270, "categoria": "Hamburguesas", "descripcion": "Carne simple, cheddar, cebolla"},
    {"id": "2",  "nombre": "Chillout",           "precio": 390, "categoria": "Hamburguesas", "descripcion": "Carne, cheddar, panceta, BBQ"},
    {"id": "3",  "nombre": "Bunker",             "precio": 450, "categoria": "Hamburguesas", "descripcion": "Triple carne, cheddar, huevo"},
    {"id": "4",  "nombre": "Clásica",            "precio": 300, "categoria": "Hamburguesas", "descripcion": "Carne, cheddar, tomate, mayo"},
    {"id": "5",  "nombre": "Vegan Burger",       "precio": 330, "categoria": "Hamburguesas", "descripcion": "Hamburguesa de lentejas y vegetales"},

    {"id": "6",  "nombre": "Napolitana",         "precio": 430, "categoria": "Pizzas", "descripcion": "Tomate, muzza, albahaca"},
    {"id": "7",  "nombre": "Cuatro Quesos",      "precio": 520, "categoria": "Pizzas", "descripcion": "Muzza, parmesano, roquefort, provolone"},
    {"id": "8",  "nombre": "Pizza Pesto",        "precio": 480, "categoria": "Pizzas", "descripcion": "Muzza, pesto y provolone"},
    {"id": "9",  "nombre": "Americana",          "precio": 500, "categoria": "Pizzas", "descripcion": "Muzza, papas fritas y huevo"},
    {"id": "10", "nombre": "Fugazzeta",          "precio": 470, "categoria": "Pizzas", "descripcion": "Muzza y cebolla caramelizada"},

    {"id": "11", "nombre": "César",              "precio": 360, "categoria": "Ensaladas", "descripcion": "Lechuga, pollo, croutons y parmesano"},
    {"id": "12", "nombre": "Mediterránea",       "precio": 340, "categoria": "Ensaladas", "descripcion": "Verdes, aceitunas, tomate cherry y queso feta"},
    {"id": "16", "nombre": "Quinoa Power",       "precio": 380, "categoria": "Ensaladas", "descripcion": "Quinoa, kale, garbanzos y vegetales"},
    {"id": "17", "nombre": "Caprese",            "precio": 320, "categoria": "Ensaladas", "descripcion": "Tomate, muzza y albahaca fresca"},

    {"id": "13", "nombre": "Coca Cola 350ml",    "precio": 110, "categoria": "Bebidas", "descripcion": "Lata 350 ml"},
    {"id": "14", "nombre": "Fanta 350ml",        "precio": 110, "categoria": "Bebidas", "descripcion": "Lata 350 ml"},
    {"id": "15", "nombre": "Agua 500ml",         "precio": 100, "categoria": "Bebidas", "descripcion": "Botella 500 ml"},
    {"id": "18", "nombre": "Sprite 350ml",       "precio": 110, "categoria": "Bebidas", "descripcion": "Lata 350 ml"},
    {"id": "19", "nombre": "Pomelo 1L",          "precio": 180, "categoria": "Bebidas", "descripcion": "Botella 1 litro"},

    {"id": "20", "nombre": "Milanesa al pan",    "precio": 300, "categoria": "Minutas", "descripcion": "Milanesa, lechuga, tomate y mayo"},
    {"id": "21", "nombre": "Chivito",            "precio": 520, "categoria": "Minutas", "descripcion": "Lomo, jamón, queso, huevo y vegetales"},
    {"id": "22", "nombre": "Lomito",             "precio": 480, "categoria": "Minutas", "descripcion": "Lomo, queso y morrón"},
    {"id": "23", "nombre": "Panchos x2",         "precio": 220, "categoria": "Minutas", "descripcion": "Pan artesanal y salsas a elección"},

    {"id": "24", "nombre": "Flan casero",        "precio": 190, "categoria": "Postres", "descripcion": "Flan con dulce de leche"},
    {"id": "25", "nombre": "Brownie",            "precio": 230, "categoria": "Postres", "descripcion": "Brownie de chocolate con nueces"},
    {"id": "26", "nombre": "Helado 1 bocha",     "precio": 160, "categoria": "Postres", "descripcion": "Vainilla o chocolate"},
    {"id": "27", "nombre": "Chocotorta",         "precio": 220, "categoria": "Postres", "descripcion": "Clásica chocotorta cremosa"},
    {"id": "28", "nombre": "Tiramisú",           "precio": 250, "categoria": "Postres", "descripcion": "Postre estilo italiano"},
    {"id": "29", "nombre": "Cheesecake",         "precio": 270, "categoria": "Postres", "descripcion": "Postre de queso y frutos rojos"},
]


# Diccionario auxiliar: productos agrupados por categoría
productos_por_categoria: Dict[str, List[Producto]] = {}

for producto in menuCompleto:
    categoria = producto["categoria"]
    if categoria not in productos_por_categoria:
        productos_por_categoria[categoria] = []
    productos_por_categoria[categoria].append(producto)


# (Opcional) Lista de categorías para mostrar en un menú de texto o interactivo
categorias_disponibles: List[str] = list(productos_por_categoria.keys())
