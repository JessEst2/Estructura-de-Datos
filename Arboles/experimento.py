"""
Experimento del Laboratorio 3.

Mide, para Lista, ABB y Árbol B+:
  - INSERTAR: tiempo de construir la estructura insertando los N estudiantes uno a uno.
  - BUSCAR:   tiempo de buscar estudiantes por ID (en lotes de M búsquedas).
  - LISTAR:   tiempo de obtener todos los estudiantes ordenados por ID.

Hay dos experimentos:
  A) Variar N (número de estudiantes), con M fijo, en datos ordenados y aleatorios.
  B) Variar M (número de búsquedas por lote), con N fijo, en datos aleatorios.

VENTANA MÍNIMA DE MEDICIÓN (guías de benchmarking)
  Una búsqueda dura menos de un microsegundo. Medir intervalos tan cortos es muy ruidoso:
  cualquier interrupción del sistema operativo pesa mucho. Por eso cada medición repite la
  operación las veces necesarias para que el tiempo medido sea de AL MENOS `MINIMO_S`
  segundos (1 s), y luego se divide por el número de repeticiones. Así se reporta el costo
  de UNA operación (que naturalmente está en nanosegundos o microsegundos), pero medido
  sobre una ventana de más de un segundo.

Uso:
    python experimento.py            # experimento completo (~1 hora)
    python experimento.py --rapido   # prueba corta (~1 minuto) para ver que todo funciona
"""
import argparse
import csv
import gc
import math
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
    "M": 1000,                                           # búsquedas por lote (exp. A)
    "MS": [100, 300, 1000, 3000, 10000],                 # valores de M para el experimento B
    "N_FIJO": 10000,                                     # N usado en el experimento B
    "REPETICIONES": 20,
    "MINIMO_S": 1.0,              # duración mínima de cada medición (segundos)
    "MAX_N_ABB_ORDENADO": 30000,  # por encima tarda demasiado en construirse (O(N^2))
    "CARPETA": "resultados",
}
CONFIG_RAPIDA = {
    "NS": [100, 1000, 3000],
    "M": 1000,
    "MS": [100, 1000],
    "N_FIJO": 1000,
    "REPETICIONES": 3,
    "MINIMO_S": 0.05,
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
            # tiempo de UNA construcción, de UN lote de M búsquedas y de UN listado (segundos)
            "t_construccion_s", "t_busqueda_s", "t_listar_s",
            # cuántas veces se repitió cada operación dentro de su ventana
            "veces_construccion", "lotes_busqueda", "veces_listar",
            # duración total medida de cada ventana (segundos): debe ser >= minimo_s
            "ventana_construccion_s", "ventana_busqueda_s", "ventana_listar_s",
            "minimo_s", "altura", "momento_min"]

# Momento en que arrancó el experimento: cada medición guarda cuántos minutos
# habían pasado, para revisar después si el computador cambió de velocidad.
INICIO_GLOBAL = time.perf_counter()


def minutos_transcurridos():
    return (time.perf_counter() - INICIO_GLOBAL) / 60


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


def medir_repetido(funcion, minimo_s):
    """Repite funcion() hasta acumular al menos minimo_s segundos medidos.

    La primera ejecución sirve de calibración: si ya dura minimo_s o más (por ejemplo,
    construir el ABB degenerado con N grande) se usa tal cual. Si no, se descarta (sirve
    de calentamiento), se calcula cuántas veces hay que repetir para llenar la ventana y
    se mide ese bloque de repeticiones.

    Devuelve (resultado de la primera ejecución, segundos por ejecución, veces, ventana total)."""
    resultado, t = cronometrar(funcion)
    if t >= minimo_s:
        return resultado, t, 1, t

    total, veces_total = 0.0, 0
    t_estimado = max(t, 1e-7)
    while total < minimo_s:
        veces = max(1, math.ceil((minimo_s - total) / t_estimado * 1.05))

        def bloque():
            for _ in range(veces):
                funcion()

        _, t_bloque = cronometrar(bloque)
        total += t_bloque
        veces_total += veces
        t_estimado = total / veces_total
    return resultado, total / veces_total, veces_total, total


def medir_busquedas(buscar, estructura, n, m, semilla, minimo_s):
    """Busca lotes de M IDs, con IDs NUEVOS en cada lote, hasta acumular minimo_s segundos.

    Usar IDs nuevos en cada lote evita repetir siempre los mismos caminos del árbol: si se
    repitieran, esos nodos quedarían en la memoria caché del procesador y la medición
    saldría más rápida de lo real. Los IDs se generan ANTES de cronometrar.
    Con la misma semilla, las tres estructuras buscan exactamente la misma secuencia de IDs.

    Devuelve (segundos por lote de M búsquedas, número de lotes, ventana total)."""
    rnd = random.Random(semilla)
    rango = range(1, n + 1)

    def nuevos_lotes(k):
        return [rnd.choices(rango, k=m) for _ in range(k)]  # con reemplazo: M puede ser > N

    def buscar_lotes(lotes):
        encontrados = 0
        for ids in lotes:
            for id_buscado in ids:
                if buscar(estructura, id_buscado) is not None:
                    encontrados += 1
        return encontrados

    def comprobar(encontrados, esperados):
        if encontrados != esperados:  # todos los IDs buscados existen: deben encontrarse
            raise RuntimeError(f"Búsqueda incorrecta: {encontrados} de {esperados}")

    # Calibración con un lote
    lotes = nuevos_lotes(1)
    encontrados, t = cronometrar(lambda: buscar_lotes(lotes))
    comprobar(encontrados, m)
    if t >= minimo_s:
        return t, 1, t

    total, n_lotes = 0.0, 0
    t_estimado = max(t, 1e-7)
    max_lotes_por_bloque = max(1, 200_000 // m)  # no generar millones de IDs de una vez
    while total < minimo_s:
        k = max(1, math.ceil((minimo_s - total) / t_estimado * 1.05))
        k = min(k, max_lotes_por_bloque)
        lotes = nuevos_lotes(k)
        encontrados, t_bloque = cronometrar(lambda: buscar_lotes(lotes))
        comprobar(encontrados, k * m)
        total += t_bloque
        n_lotes += k
        t_estimado = total / n_lotes
    return total / n_lotes, n_lotes, total


def medir(nombre, estudiantes, m, semilla_busquedas, minimo_s, medir_todo=True):
    """Mide construir, buscar y listar una estructura. Devuelve una fila para el CSV."""
    ops = ESTRUCTURAS[nombre]
    n = len(estudiantes)
    fila = {"minimo_s": minimo_s}

    if medir_todo:
        estructura, t_c, veces_c, vent_c = medir_repetido(lambda: ops["construir"](estudiantes), minimo_s)
        fila.update(t_construccion_s=t_c, veces_construccion=veces_c, ventana_construccion_s=vent_c)
    else:
        estructura = ops["construir"](estudiantes)

    t_b, lotes, vent_b = medir_busquedas(ops["buscar"], estructura, n, m, semilla_busquedas, minimo_s)
    fila.update(t_busqueda_s=t_b, lotes_busqueda=lotes, ventana_busqueda_s=vent_b)

    if medir_todo:
        listado, t_l, veces_l, vent_l = medir_repetido(lambda: ops["listar"](estructura), minimo_s)
        if [e["id"] for e in listado] != list(range(1, n + 1)):
            raise RuntimeError(f"{nombre}: el listado no salió en orden")
        fila.update(t_listar_s=t_l, veces_listar=veces_l, ventana_listar_s=vent_l)

    fila["altura"] = ops["altura"](estructura)
    return fila


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
    reloj = time.get_clock_info("perf_counter")
    with open(os.path.join(carpeta, "entorno.txt"), "w", encoding="utf-8") as f:
        f.write(f"Fecha: {datetime.now():%Y-%m-%d %H:%M}\n")
        f.write(f"Sistema operativo: {platform.platform()}\n")
        f.write(f"Procesador: {platform.processor() or platform.machine()}\n")
        f.write(f"Núcleos lógicos: {os.cpu_count()}\n")
        f.write(f"RAM: {ram}\n")
        f.write(f"Python: {sys.version.split()[0]} ({platform.python_implementation()})\n")
        f.write(f"Reloj: time.perf_counter ({reloj.implementation}), resolución {reloj.resolution:.1e} s\n")
        f.write(f"Orden del árbol B+: {ORDEN_BPLUS}\n")
        for clave, valor in cfg.items():
            f.write(f"{clave}: {valor}\n")


def calentamiento():
    """Una ronda corta que NO se guarda. Las primeras ejecuciones de un programa suelen
    ser más lentas (Python carga cosas en memoria por primera vez)."""
    estudiantes = generar_estudiantes(2000, "aleatorio", semilla=999)
    for nombre in ESTRUCTURAS:
        medir(nombre, estudiantes, 500, 999, minimo_s=0.05)


def experimento_a(cfg, escritor, archivo):
    """A) Varía N. M fijo. Datos ordenados y aleatorios.

    IMPORTANTE: en cada repetición las configuraciones (N, orden) se recorren en un
    ORDEN ALEATORIO. Si se midieran en orden (primero todos los N=100, luego N=300...),
    cualquier cambio de velocidad del computador durante el experimento quedaría
    mezclado con el efecto de N. Mezclándolas, ese cambio afecta a todos los N por igual."""
    configuraciones = [(n, orden) for n in cfg["NS"] for orden in ("ordenado", "aleatorio")]
    total = len(configuraciones) * cfg["REPETICIONES"]
    hecho = 0
    for rep in range(1, cfg["REPETICIONES"] + 1):
        mezcladas = configuraciones[:]
        random.Random(5_000_000 + rep).shuffle(mezcladas)
        for n, orden in mezcladas:
            estudiantes = generar_estudiantes(n, orden, semilla=rep)
            for nombre in orden_de_estructuras(ESTRUCTURAS, semilla=rep * 31 + n):
                if nombre == "ABB" and orden == "ordenado" and n > cfg["MAX_N_ABB_ORDENADO"]:
                    continue
                fila = medir(nombre, estudiantes, cfg["M"], 1_000_000 + rep, cfg["MINIMO_S"])
                fila.update(experimento="A_variar_N", estructura=nombre, orden=orden,
                            N=n, M=cfg["M"], repeticion=rep, momento_min=minutos_transcurridos())
                escritor.writerow(fila)
            archivo.flush()

            hecho += 1
            print(f"\r[A] repetición {rep:>2}/{cfg['REPETICIONES']}  N={n:>6} {orden:<9}"
                  f"  ({hecho}/{total}, {minutos_transcurridos():.1f} min)", end="", flush=True)
    print()


def experimento_b(cfg, escritor, archivo):
    """B) Varía M. N fijo. Datos aleatorios. Solo se mide buscar (construir y listar no
    dependen de M). Los valores de M se recorren en orden aleatorio en cada repetición."""
    n = cfg["N_FIJO"]
    for rep in range(1, cfg["REPETICIONES"] + 1):
        estudiantes = generar_estudiantes(n, "aleatorio", semilla=rep)
        valores_m = list(cfg["MS"])
        random.Random(6_000_000 + rep).shuffle(valores_m)
        for m in valores_m:
            for nombre in orden_de_estructuras(ESTRUCTURAS, semilla=rep * 7 + m):
                fila = medir(nombre, estudiantes, m, 2_000_000 + rep, cfg["MINIMO_S"], medir_todo=False)
                fila.update(experimento="B_variar_M", estructura=nombre, orden="aleatorio",
                            N=n, M=m, repeticion=rep, momento_min=minutos_transcurridos())
                escritor.writerow(fila)
        archivo.flush()
        print(f"\r[B] N={n} repetición {rep:>2}/{cfg['REPETICIONES']}"
              f"  ({minutos_transcurridos():.1f} min)", end="", flush=True)
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
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        escritor.writeheader()
        experimento_a(cfg, escritor, archivo)
        experimento_b(cfg, escritor, archivo)

    print(f"Listo en {minutos_transcurridos():.1f} min. Mediciones en {ruta}")
    print(f"Siguiente paso: python analisis.py{' --rapido' if args.rapido else ''}")


if __name__ == "__main__":
    main()
