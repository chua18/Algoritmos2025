

class Cliente:
    def __init__(self,id,nombre,numero,ubicacion):
        self.id= id
        self.nombre=nombre
        self.numero=numero
        self.ubicacion=ubicacion

        def __str__(self):
            return f"{self.nombre}"
