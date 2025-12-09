from dataclasses import dataclass, field
from typing import List, Dict, Tuple

from Dominio.Modelos import Pedido

MAX_PEDIDOS_POR_LOTE = 1
ZONAS_VALIDAS = ("NO", "NE", "SO", "SE")


@dataclass
class LoteReparto:
    """
    Representa un lote de pedidos para un repartidor.
    """
    pedidos: List[Pedido] = field(default_factory=list)

    def esta_completo(self) -> bool:
        return len(self.pedidos) >= MAX_PEDIDOS_POR_LOTE

    def agregar_pedido(self, pedido: Pedido) -> None:
        self.pedidos.append(pedido)

    def vaciar(self) -> None:
        self.pedidos.clear()


@dataclass
class RepartidorZona:
    
    """
<<<<<<< HEAD
    Repartidor asignado a una zona (NO, NE, SO, SE).
    Maneja su lote actual y una cola de espera.
=======
    Repartidor identificado por una etiqueta (NO, NE, SO, SE).
    Ahora puede entregar pedidos de cualquier zona geográfica del cliente.
    La 'zona' acá funciona como ID lógico del repartidor, no como filtro exclusivo.
>>>>>>> parent of b5d9ce1 (fix)
    """
   
    zona: str
    telefono_whatsapp: str
    lote_actual: LoteReparto = field(default_factory=LoteReparto)
    cola_espera: List[Pedido] = field(default_factory=list)
    pedidos_entregados: List[Pedido] = field(default_factory=list)  

    def asignar_pedido(self, pedido: Pedido) -> bool:
<<<<<<< HEAD
        """
        Asigna el pedido al lote actual si hay lugar.
        Si el lote está completo, lo manda a la cola de espera.
        Devuelve True si DESPUÉS de asignar el pedido el lote quedó completo.
        """
=======
        
       # Asigna el pedido al lote actual si hay lugar. Si el lote está completo, lo manda a la cola de espera.
       # Devuelve True si DESPUÉS de asignar el pedido el lote quedó completo.
       
>>>>>>> parent of b5d9ce1 (fix)
        if not self.lote_actual.esta_completo():
            self.lote_actual.agregar_pedido(pedido)
            return self.lote_actual.esta_completo()

        # Lote ya lleno → pasa a cola de espera
        self.cola_espera.append(pedido)
        return False

    def obtener_lote_actual(self) -> List[Pedido]:
        """
        Devuelve los pedidos del lote actual ORDENADOS
        por distancia desde el local (distancia_km ascendente).
        """
        pedidos = list(self.lote_actual.pedidos)
        pedidos.sort(key=lambda p: getattr(p, "distancia_km", 0.0))
        return pedidos
        return list(self.lote_actual.pedidos)

    def obtener_pedidos_pendientes(self) -> List[Pedido]:
        """
        Devuelve todos los pedidos que aún no se marcaron como entregados:
        - los del lote actual
        - los de la cola de espera
        """
        return list(self.lote_actual.pedidos) + list(self.cola_espera)

    def registrar_entrega(self, pedido: Pedido) -> None:
<<<<<<< HEAD
        """
        Registra un pedido como entregado (se llama cuando en el futuro
        implementes el flujo de entrega con código).
        """
=======
        
       # Registra un pedido como entregado (se llama cuando en el futuro
       # implementes el flujo de entrega con código).
        
>>>>>>> parent of b5d9ce1 (fix)
        self.pedidos_entregados.append(pedido)

    def marcar_lote_enviado(self) -> List[Pedido]:
        """
        Se llama luego de enviar la imagen al repartidor.
        Vacía el lote actual y lo rellena con la siguiente tanda (si hay).
        Devuelve la lista de pedidos que formaban el lote enviado.
        """
        enviados = list(self.lote_actual.pedidos)
        self.lote_actual.vaciar()

        # Si hay pedidos en cola, cargamos hasta 7 para el próximo lote
        while self.cola_espera and not self.lote_actual.esta_completo():
            p = self.cola_espera.pop(0)
            self.lote_actual.agregar_pedido(p)

        return enviados

@dataclass
class GestorReparto:
    
    """
    Maneja la asignación de pedidos a 4 repartidores (uno por zona).
    """
    
    repartidores: Dict[str, RepartidorZona] = field(default_factory=dict)

    @classmethod
    def desde_config(cls, mapa_telefonos: Dict[str, str]) -> "GestorReparto":
<<<<<<< HEAD
        """
        Crea un GestorReparto a partir de un dict {zona: telefono_wpp}.
        Zonas válidas: NO, NE, SO, SE.
        """
=======
        
       # Crea un GestorReparto a partir de un dict {zona: telefono_wpp}.
       # Zonas válidas: NO, NE, SO, SE.
        
>>>>>>> parent of b5d9ce1 (fix)
        reps: Dict[str, RepartidorZona] = {}
        for zona, tel in mapa_telefonos.items():
            if zona not in ZONAS_VALIDAS:
                continue
            reps[zona] = RepartidorZona(zona=zona, telefono_whatsapp=tel)
        return cls(repartidores=reps)

<<<<<<< HEAD
    def asignar_pedido(self, pedido: Pedido) -> Tuple[bool, str]:
        """
        Asigna el pedido al repartidor de la zona del pedido.
        Devuelve (lote_lleno, zona).

        Si el pedido no tiene zona, se asume "SO" como default.
        """
        zona = pedido.zona or "SO"
        if zona not in self.repartidores:
            # fallback por si falta config de alguna zona
            zona = "SO"
=======
    def asignar_pedido(self, pedido: Pedido) -> tuple[bool, str]:
        
        #Asigna el pedido al repartidor que tenga MÁS ESPACIO en su tanda
        #de hasta 7 pedidos, sin importar la zona del pedido.

        #Devuelve (lote_lleno, id_repartidor) donde id_repartidor puede ser
        #la 'zona' o un nombre interno del repartidor (según cómo lo uses en los logs).
        
        if not self.repartidores:
            raise RuntimeError("No hay repartidores configurados en el GestorReparto.")
>>>>>>> parent of b5d9ce1 (fix)

        repartidor = self.repartidores[zona]
        lleno = repartidor.asignar_pedido(pedido)
        return lleno, zona

<<<<<<< HEAD
    def obtener_lote_actual(self, zona: str) -> List[Pedido]:
        if zona not in self.repartidores:
            return []
        return self.repartidores[zona].obtener_lote_actual()

    def marcar_lote_enviado(self, zona: str) -> List[Pedido]:
        if zona not in self.repartidores:
            return []
=======
        lote_lleno = mejor_repartidor.asignar_pedido(pedido)

        # Usamos mejor_repartidor.zona como identificador, aunque ahora
        # no signifique “zona geográfica” sino “ID lógico del repartidor”
        return lote_lleno, mejor_repartidor.zona


    def obtener_lote_actual(self, zona: str) -> List[Pedido]:
        if zona not in self.repartidores:
            return []
        return self.repartidores[zona].obtener_lote_actual()

    def marcar_lote_enviado(self, zona: str) -> List[Pedido]:
        if zona not in self.repartidores:
            return []
>>>>>>> parent of b5d9ce1 (fix)
        return self.repartidores[zona].marcar_lote_enviado()