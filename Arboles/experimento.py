"""
Experimento del Laboratorio 3.

Mide, para Lista, ABB y Árbol B+:
  - INSERTAR: tiempo de construir la estructura insertando los N estudiantes uno a uno.
  - BUSCAR:   tiempo de hacer M búsquedas por ID.
  - LISTAR:   tiempo de obtener todos los estudiantes ordenados por ID.

Hay dos experimentos:
  A) Variar N (número de estudiantes), con M fijo, en datos ordenados y aleatorios.
  B) Variar M (número de búsquedas), con N fijo, en datos aleatorios.

Uso:
    python experimento.py            # experimento completo (tarda ~20-40 minutos)
    python experimento.py --rapido   # prueba corta (~1 minuto) para ver que todo funciona

Los resultados crudos (una fila por medición) quedan en resultados/ (o resultados_prueba/).
"""
import argparse
import csv
import gc
import os
import platform
import random
import sys
import time
from datetime import datetime

import ABB
from arbolbplus import BPlusTree
from lista import generar_estudiantes

# ----------------------------------------------------------------------
# Parámetros del experimento
# ----------------------------------------------------------------------
CONFIG_COMPLETA = {
    "NS": [100, 300, 1000, 3000, 10000, 30000, 100000],  # tamaños para el experimento A
    "M": 1000,                                           # búsquedas por repetición (exp. A)
    "MS": [100, 300, 1000, 3000, 10000],                 # valores de M para el experimento B
    "N_FIJO": 10000,                                     # N usado en el experimento B
    "REPETICIONES": 30,
    "MAX_N_ABB_ORDENADO": 30000,  # por encima tarda demasiado en construirse (O(N^2))
    "CARPETA": "resultados",
}
CONFIG_RAPIDA = {
    "NS": [100, 1000, 3000],
    "M": 1000,
    "MS": [100, 1000],
    "N_FIJO": 1000,
    "REPETICIONES": 3,
    "MAX_N_ABB_ORDENADO": 3000,
    "CARPETA": "resultados_prueba",
}
ORDEN_BPLUS = 32  # máximo de hijos por nodo del árbol B+


# ----------------------------------------------------------------------
# Las tres estructuras, con la misma "interfaz":
#   construir(estudiantes) -> estructura
#   buscar(estructura, id) -> estudiante o None
#   listar(estructura)     -> lista de estudiantes ordenada por ID
#   altura(estructura)     -> número de niveles (vacío para la lista)
# ----------------------------------------------------------------------
def construir_lista(estudiantes):
    lista = []
    for estudiante in estudiantes:
        lista.append(estudiante)
    return lista


def buscar_lista(lista, id_buscado):
    for estudiante in lista:
        if estudiante["id"] == id_buscado:
            return estudiante
    return None


def listar_lista(lista):
    return sorted(lista, key=lambda e: e["id"])


def construir_bplus(estudiantes):
    arbol = BPlusTree(ORDEN_BPLUS)
    for estudiante in estudiantes:
        arbol.insertar(estudiante["id"], estudiante)
    return arbol


ESTRUCTURAS = {
    "Lista": {
        "construir": construir_lista,
        "buscar": buscar_lista,
        "listar": listar_lista,
        "altura": lambda lista: "",
    },
    "ABB": {
        "construir": ABB.construir_abb,
        "buscar": ABB.buscar_abb,
        "listar": ABB.recorrer_inorden,
        "altura": ABB.altura,
    },
    "B+": {
        "construir": construir_bplus,
        "buscar": lambda arbol, id_buscado: arbol.buscar(id_buscado),
        "listar": lambda arbol: [e for _, e in arbol.recorrer()],
        "altura": lambda arbol: arbol.altura(),
    },
}

COLUMNAS = ["experimento", "estructura", "orden", "N", "M", "repeticion",
            "t_construccion_s", "t_busqueda_s", "t_listar_s", "altura", "encontrados"]


# ----------------------------------------------------------------------
# Medición
# ----------------------------------------------------------------------
def cronometrar(funcion):
    """Ejecuta funcion() y devuelve (resultado, segundos).
    El recolector de basura se apaga mientras se mide para que no meta pausas."""
    gc.collect()
    gc.disable()
    try:
        inicio = time.perf_counter()
        resultado = funcion()
        segundos = time.perf_counter() - inicio
    finally:
        gc.enable()
    return resultado, segundos


def buscar_todos(buscar, estructura, ids):
    encontrados = 0
    for id_buscado in ids:
        if buscar(estructura, id_buscado) is not None:
            encontrados += 1
    return encontrados


def medir(nombre, estudiantes, ids, medir_listar=True):
    """Construye la estructura, busca los ids y lista. Devuelve los tiempos y la altura."""
    ops = ESTRUCTURAS[nombre]
    estructura, t_construir = cronometrar(lambda: ops["construir"](estudiantes))
    encontrados, t_buscar = cronometrar(lambda: buscar_todos(ops["buscar"], estructura, ids))

    t_listar = ""
    if medir_listar:
        listado, t_listar = cronometrar(lambda: ops["listar"](estructura))
        # Comprobación de correctitud: el listado debe salir 1, 2, ..., N
        if [e["id"] for e in listado] != list(range(1, len(estudiantes) + 1)):
            raise RuntimeError(f"{nombre}: el listado no salió en orden")

    # Comprobación de correctitud: todos los IDs buscados existen, deben encontrarse
    if encontrados != len(ids):
        raise RuntimeError(f"{nombre}: encontró {encontrados} de {len(ids)}")

    return {
        "t_construccion_s": t_construir,
        "t_busqueda_s": t_buscar,
        "t_listar_s": t_listar,
        "altura": ops["altura"](estructura),
        "encontrados": encontrados,
    }


def ids_de_busqueda(n, m, semilla):
    """M IDs al azar entre 1 y N, CON reemplazo (así M puede ser mayor que N)."""
    return random.Random(semilla).choices(range(1, n + 1), k=m)


def orden_de_estructuras(nombres, semilla):
    """Se cambia el orden en que se miden las estructuras en cada repetición, para que
    ninguna quede siempre de primera (o de última) y eso no sesgue los tiempos."""
    nombres = list(nombres)
    random.Random(semilla).shuffle(nombres)
    return nombres


# ----------------------------------------------------------------------
# Experimentos
# ----------------------------------------------------------------------
def guardar_entorno(cfg, carpeta):
    try:
        ram_gb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3
        ram = f"{ram_gb:.1f} GB"
    except (ValueError, AttributeError, OSError):
        ram = "no disponible (anótala a mano)"
    with open(os.path.join(carpeta, "entorno.txt"), "w", encoding="utf-8") as f:
        f.write(f"Fecha: {datetime.now():%Y-%m-%d %H:%M}\n")
        f.write(f"Sistema operativo: {platform.platform()}\n")
        f.write(f"Procesador: {platform.processor() or platform.machine()}\n")
        f.write(f"Núcleos lógicos: {os.cpu_count()}\n")
        f.write(f"RAM: {ram}\n")
        f.write(f"Python: {sys.version.split()[0]} ({platform.python_implementation()})\n")
        f.write(f"Orden del árbol B+: {ORDEN_BPLUS}\n")
        for clave, valor in cfg.items():
            f.write(f"{clave}: {valor}\n")


def calentamiento():
    """Una ronda corta que NO se guarda. Las primeras ejecuciones de un programa suelen
    ser más lentas (Python carga cosas en memoria por primera vez)."""
    estudiantes = generar_estudiantes(2000, "aleatorio", semilla=999)
    ids = ids_de_busqueda(2000, 500, semilla=999)
    for nombre in ESTRUCTURAS:
        medir(nombre, estudiantes, ids)


def experimento_a(cfg, escritor, archivo):
    """A) Varía N. M fijo. Datos ordenados y aleatorios."""
    total = len(cfg["NS"]) * 2 * cfg["REPETICIONES"]
    hecho = 0
    inicio = time.perf_counter()
    for n in cfg["NS"]:
        for orden in ("ordenado", "aleatorio"):
            for rep in range(1, cfg["REPETICIONES"] + 1):
                estudiantes = generar_estudiantes(n, orden, semilla=rep)
                ids = ids_de_busqueda(n, cfg["M"], semilla=1_000_000 + rep)

                for nombre in orden_de_estructuras(ESTRUCTURAS, semilla=rep):
                    if nombre == "ABB" and orden == "ordenado" and n > cfg["MAX_N_ABB_ORDENADO"]:
                        continue
                    fila = medir(nombre, estudiantes, ids)
                    fila.update(experimento="A_variar_N", estructura=nombre, orden=orden,
                                N=n, M=cfg["M"], repeticion=rep)
                    escritor.writerow(fila)
                archivo.flush()

                hecho += 1
                transcurrido = time.perf_counter() - inicio
                print(f"\r[A] N={n:>6} {orden:<9} rep {rep:>2}/{cfg['REPETICIONES']}"
                      f"  ({hecho}/{total}, {transcurrido / 60:.1f} min)", end="", flush=True)
    print()


def experimento_b(cfg, escritor, archivo):
    """B) Varía M. N fijo. Datos aleatorios. (No se mide listar: no depende de M.)"""
    n = cfg["N_FIJO"]
    for rep in range(1, cfg["REPETICIONES"] + 1):
        estudiantes = generar_estudiantes(n, "aleatorio", semilla=rep)
        for m in cfg["MS"]:
            ids = ids_de_busqueda(n, m, semilla=2_000_000 + rep)
            for nombre in orden_de_estructuras(ESTRUCTURAS, semilla=rep * 7 + m):
                fila = medir(nombre, estudiantes, ids, medir_listar=False)
                fila.update(experimento="B_variar_M", estructura=nombre, orden="aleatorio",
                            N=n, M=m, repeticion=rep)
                escritor.writerow(fila)
        archivo.flush()
        print(f"\r[B] N={n} rep {rep:>2}/{cfg['REPETICIONES']}", end="", flush=True)
    print()


def main():
    parser = argparse.ArgumentParser(description="Experimento Lista vs ABB vs B+")
    parser.add_argument("--rapido", action="store_true", help="prueba corta para verificar que todo funciona")
    args = parser.parse_args()
    cfg = CONFIG_RAPIDA if args.rapido else CONFIG_COMPLETA

    carpeta = cfg["CARPETA"]
    os.makedirs(carpeta, exist_ok=True)
    guardar_entorno(cfg, carpeta)

    print("Calentamiento...")
    calentamiento()

    ruta = os.path.join(carpeta, "mediciones.csv")
    inicio = time.perf_counter()
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        escritor.writeheader()
        experimento_a(cfg, escritor, archivo)
        experimento_b(cfg, escritor, archivo)

    print(f"Listo en {(time.perf_counter() - inicio) / 60:.1f} min. Mediciones en {ruta}")
    print(f"Siguiente paso: python analisis.py{' --rapido' if args.rapido else ''}")


if __name__ == "__main__":
    main()
