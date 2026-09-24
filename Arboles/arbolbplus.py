"""
Árbol B+ en Python.

Reglas del árbol (con orden m = número máximo de hijos de un nodo interno):
  - Cada nodo guarda como máximo m - 1 claves.
  - Los datos (valores) viven SOLO en las hojas.
  - Los nodos internos solo guardan claves "separadoras" para guiar la búsqueda:
        hijos[i] contiene claves >= claves[i-1]  y  < claves[i]
  - Todas las hojas están enlazadas en orden (atributo `siguiente`),
    lo que permite recorrer todo el árbol ordenado sin volver a subir.
  - Todas las hojas están a la misma profundidad.
"""

from bisect import bisect_left, bisect_right


class _Nodo:
    """Un nodo del árbol. Puede ser hoja o nodo interno."""

    __slots__ = ("es_hoja", "claves", "hijos", "valores", "siguiente")

    def __init__(self, es_hoja):
        self.es_hoja = es_hoja
        self.claves = []      # claves ordenadas
        self.hijos = []       # solo nodos internos: len(hijos) == len(claves) + 1
        self.valores = []     # solo hojas: valores[i] corresponde a claves[i]
        self.siguiente = None  # solo hojas: la hoja de la derecha


class BPlusTree:
    def __init__(self, orden=4):
        if orden < 3:
            raise ValueError("El orden debe ser al menos 3")
        self.orden = orden
        self.max_claves = orden - 1
        self.min_claves = (orden + 1) // 2 - 1   
        self.raiz = _Nodo(es_hoja=True)
        self._tamano = 0

    def __len__(self):
        return self._tamano

    def __contains__(self, clave):
        return self.buscar(clave) is not None

    def _buscar_hoja(self, clave):
        """Baja desde la raíz hasta la hoja donde está (o estaría) la clave.
        Devuelve la hoja y el camino recorrido: lista de (nodo_interno, índice_del_hijo)."""
        nodo = self.raiz
        camino = []
        while not nodo.es_hoja:
            i = bisect_right(nodo.claves, clave)
            camino.append((nodo, i))
            nodo = nodo.hijos[i]
        return nodo, camino

    def buscar(self, clave):
        """Devuelve el valor asociado a la clave, o None si no existe."""
        hoja, _ = self._buscar_hoja(clave)
        i = bisect_left(hoja.claves, clave)
        if i < len(hoja.claves) and hoja.claves[i] == clave:
            return hoja.valores[i]
        return None

    def insertar(self, clave, valor):
        """Inserta (clave, valor). Lanza KeyError si la clave ya existe."""
        hoja, camino = self._buscar_hoja(clave)
        i = bisect_left(hoja.claves, clave)
        if i < len(hoja.claves) and hoja.claves[i] == clave:
            raise KeyError(f"La clave {clave!r} ya existe")

        hoja.claves.insert(i, clave)
        hoja.valores.insert(i, valor)
        self._tamano += 1

        if len(hoja.claves) <= self.max_claves:
            return  # cabe, no hay que hacer nada más

        # La hoja se llenó de más: se divide en dos.
        mitad = len(hoja.claves) // 2
        nueva = _Nodo(es_hoja=True)
        nueva.claves = hoja.claves[mitad:]
        nueva.valores = hoja.valores[mitad:]
        hoja.claves = hoja.claves[:mitad]
        hoja.valores = hoja.valores[:mitad]

        nueva.siguiente = hoja.siguiente
        hoja.siguiente = nueva

        # En una hoja, la primera clave de la nueva hoja se COPIA hacia el padre.
        self._insertar_en_padre(camino, nueva.claves[0], nueva)

    def _insertar_en_padre(self, camino, separador, nuevo_nodo):
        """Sube el separador y el nuevo nodo hacia los padres, dividiendo si hace falta."""
        while camino:
            padre, i = camino.pop()
            padre.claves.insert(i, separador)
            padre.hijos.insert(i + 1, nuevo_nodo)

            if len(padre.claves) <= self.max_claves:
                return

            # El nodo interno se llenó de más: se divide.
            # En un nodo interno, la clave del medio SUBE (no se copia).
            mitad = len(padre.claves) // 2
            separador = padre.claves[mitad]
            nuevo_nodo = _Nodo(es_hoja=False)
            nuevo_nodo.claves = padre.claves[mitad + 1:]
            nuevo_nodo.hijos = padre.hijos[mitad + 1:]
            padre.claves = padre.claves[:mitad]
            padre.hijos = padre.hijos[:mitad + 1]

        # Si llegamos aquí se dividió la raíz: el árbol crece un nivel.
        nueva_raiz = _Nodo(es_hoja=False)
        nueva_raiz.claves = [separador]
        nueva_raiz.hijos = [self.raiz, nuevo_nodo]
        self.raiz = nueva_raiz

    def eliminar(self, clave):
        """Elimina la clave y devuelve su valor. Lanza KeyError si no existe."""
        hoja, camino = self._buscar_hoja(clave)
        i = bisect_left(hoja.claves, clave)
        if i == len(hoja.claves) or hoja.claves[i] != clave:
            raise KeyError(f"La clave {clave!r} no existe")

        hoja.claves.pop(i)
        valor = hoja.valores.pop(i)
        self._tamano -= 1
        self._rebalancear(hoja, camino)
        return valor

    def _rebalancear(self, nodo, camino):
        """Arregla nodos que quedaron con menos claves del mínimo."""
        while True:
            if not camino:  # nodo es la raíz
                if not nodo.es_hoja and len(nodo.hijos) == 1:
                    self.raiz = nodo.hijos[0]  # el árbol baja un nivel
                return

            if len(nodo.claves) >= self.min_claves:
                return  # el nodo sigue siendo válido

            padre, i = camino.pop()
            izq = padre.hijos[i - 1] if i > 0 else None
            der = padre.hijos[i + 1] if i + 1 < len(padre.hijos) else None

            # 1) Pedir prestado al hermano izquierdo
            if izq is not None and len(izq.claves) > self.min_claves:
                if nodo.es_hoja:
                    nodo.claves.insert(0, izq.claves.pop())
                    nodo.valores.insert(0, izq.valores.pop())
                    padre.claves[i - 1] = nodo.claves[0]
                else:
                    nodo.claves.insert(0, padre.claves[i - 1])
                    padre.claves[i - 1] = izq.claves.pop()
                    nodo.hijos.insert(0, izq.hijos.pop())
                return

            # 2) Pedir prestado al hermano derecho
            if der is not None and len(der.claves) > self.min_claves:
                if nodo.es_hoja:
                    nodo.claves.append(der.claves.pop(0))
                    nodo.valores.append(der.valores.pop(0))
                    padre.claves[i] = der.claves[0]
                else:
                    nodo.claves.append(padre.claves[i])
                    padre.claves[i] = der.claves.pop(0)
                    nodo.hijos.append(der.hijos.pop(0))
                return

            # 3) Ningún hermano puede prestar: fusionar con uno de ellos
            if izq is not None:
                self._fusionar(izq, nodo, padre, i - 1)
            else:
                self._fusionar(nodo, der, padre, i)

            # El padre perdió una clave: puede que ahora él necesite arreglo
            nodo = padre

    @staticmethod
    def _fusionar(izq, der, padre, k):
        """Une `der` dentro de `izq`. k es el índice del separador entre ambos en el padre."""
        if izq.es_hoja:
            izq.claves.extend(der.claves)
            izq.valores.extend(der.valores)
            izq.siguiente = der.siguiente
        else:
            # En nodos internos el separador del padre baja al nodo fusionado
            izq.claves.append(padre.claves[k])
            izq.claves.extend(der.claves)
            izq.hijos.extend(der.hijos)
        padre.claves.pop(k)
        padre.hijos.pop(k + 1)

    def _hoja_mas_izquierda(self):
        nodo = self.raiz
        while not nodo.es_hoja:
            nodo = nodo.hijos[0]
        return nodo

    def recorrer(self):
        """Genera todos los pares (clave, valor) en orden ascendente,
        usando la lista enlazada de hojas."""
        hoja = self._hoja_mas_izquierda()
        while hoja is not None:
            yield from zip(hoja.claves, hoja.valores)
            hoja = hoja.siguiente

    def rango(self, desde, hasta):
        """Genera los pares (clave, valor) con desde <= clave <= hasta."""
        hoja, _ = self._buscar_hoja(desde)
        i = bisect_left(hoja.claves, desde)
        while hoja is not None:
            while i < len(hoja.claves):
                if hoja.claves[i] > hasta:
                    return
                yield hoja.claves[i], hoja.valores[i]
                i += 1
            hoja, i = hoja.siguiente, 0

    def clave_maxima(self):
        """Devuelve la clave más grande del árbol, o None si está vacío."""
        nodo = self.raiz
        while not nodo.es_hoja:
            nodo = nodo.hijos[-1]
        return nodo.claves[-1] if nodo.claves else None

    def altura(self):
        h, nodo = 1, self.raiz
        while not nodo.es_hoja:
            nodo = nodo.hijos[0]
            h += 1
        return h

    def imprimir(self):
        """Muestra el árbol nivel por nivel (útil con pocos datos)."""
        nivel = [self.raiz]
        n = 0
        while nivel:
            print(f"Nivel {n}: " + "  ".join(str(nodo.claves) for nodo in nivel))
            if nivel[0].es_hoja:
                break
            nivel = [hijo for nodo in nivel for hijo in nodo.hijos]
            n += 1

  