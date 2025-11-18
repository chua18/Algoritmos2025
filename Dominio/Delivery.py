class Delivery:
    def __init__(self,id,nombre):
        self.id=id
        self.nombre=nombre
        self.disponible=True
        self.reparto=[]
        self.distancia_recorrida=0
        self.combustible_gastado=0

        def asignar_reparto(self,reparto):
            self.reparto.append(reparto)
            self.disponible=False