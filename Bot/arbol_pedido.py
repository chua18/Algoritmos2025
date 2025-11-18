
class NodoPedido:
    def __init__(self, pedido):
        self.pedido = pedido
        self.izquierda = None
        self.derecha = None

class ArbolPedidos:
    def __init__(self):
        self.raiz = None

    def insertar(self, pedido):
        if not self.raiz:
            self.raiz = NodoPedido(pedido)
        else:
            self._insertar_recursivo(self.raiz, pedido)

    def _insertar_recursivo(self, nodo, pedido):
        if pedido.distancia < nodo.pedido.distancia:
            if nodo.izquierda is None:
                nodo.izquierda = NodoPedido(pedido)
            else:
                self._insertar_recursivo(nodo.izquierda, pedido)
        else:
            if nodo.derecha is None:
                nodo.derecha = NodoPedido(pedido)
            else:
                self._insertar_recursivo(nodo.derecha, pedido)

    def recorrido_inorden(self):
        pedidos = []
        self._recorrido_inorden_recursivo(self.raiz, pedidos)
        return pedidos

    def _recorrido_inorden_recursivo(self, nodo, pedidos):
        if nodo:
            self._recorrido_inorden_recursivo(nodo.izquierda, pedidos)
            pedidos.append(nodo.pedido)
            self._recorrido_inorden_recursivo(nodo.derecha, pedidos)

    def eliminar(self, codigo):
        """Elimina un pedido del árbol (cuando el delivery lo entrega)"""
        self.raiz = self._eliminar_recursivo(self.raiz, codigo)

    def _eliminar_recursivo(self, nodo, codigo):
        if nodo is None:
            return nodo
        if codigo < nodo.pedido.codigo:
            nodo.izquierda = self._eliminar_recursivo(nodo.izquierda, codigo)
        elif codigo > nodo.pedido.codigo:
            nodo.derecha = self._eliminar_recursivo(nodo.derecha, codigo)
        else:
            if nodo.izquierda is None:
                return nodo.derecha
            elif nodo.derecha is None:
                return nodo.izquierda
            temp = self._min_value_node(nodo.derecha)
            nodo.pedido = temp.pedido
            nodo.derecha = self._eliminar_recursivo(nodo.derecha, temp.pedido.codigo)
        return nodo

    def _min_value_node(self, nodo):
        actual = nodo
        while actual.izquierda is not None:
            actual = actual.izquierda
        return actual
