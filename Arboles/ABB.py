#construccion arbol ABB
from lista import estudiantes

class Nodo:
    def __init__(self, estudiante):
        self.estudiante = estudiante
        self.izquierda = None
        self.derecha = None


def insertar(nodo, estudiante):

    if nodo is None:
        return Nodo(estudiante)

    if estudiante["id"] < nodo.estudiante["id"]:
        nodo.izquierda = insertar(nodo.izquierda, estudiante)

    else:
        nodo.derecha = insertar(nodo.derecha, estudiante)

    return nodo


def buscar_abb(nodo, id_buscado):

    if nodo is None:
        return None

    if nodo.estudiante["id"] == id_buscado:
        return nodo.estudiante

    elif id_buscado < nodo.estudiante["id"]:
        return buscar_abb(nodo.izquierda, id_buscado)

    else:
        return buscar_abb(nodo.derecha, id_buscado)



# construir el ABB
raiz = None

for estudiante in estudiantes:
    raiz = insertar(raiz, estudiante)


import time
import random

def medir_busquedas_abb(raiz):

    ids = random.sample(range(1,10001),100)

    inicio = time.time()

    for i in ids:
        buscar_abb(raiz, i)

    fin = time.time()

    print("Tiempo ABB:", fin - inicio, "segundos")

medir_busquedas_abb(raiz)
