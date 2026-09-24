#construccion arbol ABB
import random
import time

from lista import generar_estudiantes


class Nodo:
    def __init__(self, estudiante):
        self.estudiante = estudiante
        self.izquierda = None
        self.derecha = None

def insertar(raiz, estudiante):
    nuevo = Nodo(estudiante)
    if raiz is None:
        return nuevo

    actual = raiz
    while True:
        if estudiante["id"] < actual.estudiante["id"]:
            if actual.izquierda is None:
                actual.izquierda = nuevo
                return raiz
            actual = actual.izquierda
        else:
            if actual.derecha is None:
                actual.derecha = nuevo
                return raiz
            actual = actual.derecha


def buscar_abb(raiz, id_buscado):
    actual = raiz
    while actual is not None:
        if actual.estudiante["id"] == id_buscado:
            return actual.estudiante
        elif id_buscado < actual.estudiante["id"]:
            actual = actual.izquierda
        else:
            actual = actual.derecha
    return None


def altura(raiz):
    """Altura calculada sin recursión (recorrido por niveles)."""
    if raiz is None:
        return 0
    nivel, h = [raiz], 0
    while nivel:
        h += 1
        nivel = [hijo for n in nivel for hijo in (n.izquierda, n.derecha) if hijo]
    return h


def construir_abb(estudiantes):
    raiz = None
    for estudiante in estudiantes:
        raiz = insertar(raiz, estudiante)
    return raiz


def medir_busquedas_abb(raiz, cantidad_estudiantes):
    ids = random.sample(range(1, cantidad_estudiantes + 1), 100)

    inicio = time.perf_counter()
    for i in ids:
        buscar_abb(raiz, i)
    fin = time.perf_counter()

    return fin - inicio


if __name__ == "__main__":
    estudiantes = generar_estudiantes()

    # 2) Insertando en orden aleatorio: el ABB queda mucho más balanceado
    mezclados = estudiantes[:]
    random.shuffle(mezclados)
    raiz_mezclada = construir_abb(mezclados)

    n = len(estudiantes)
    print("ABB con IDs mezclados:    altura", altura(raiz_mezclada),
          f"| tiempo 100 búsquedas: {medir_busquedas_abb(raiz_mezclada, n):.6f} s")