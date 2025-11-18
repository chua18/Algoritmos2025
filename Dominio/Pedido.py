class Pedido:
    def __init__(self,id,cliente,ubicacion,comidas):
        self.id=id
        self.cliente=cliente
        self.ubicacion=ubicacion
        self.comidas=comidas
        self.estado="pendiente"
        self.costofinal=0
        self.delivery_asignado=None
        self.tiempo_estimado=0
        
       
      