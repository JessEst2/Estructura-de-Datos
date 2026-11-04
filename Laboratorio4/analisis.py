# Mide, para cada N:
#   - construir el quadtree (insertar N puntos)
#   - consulta en radio de 500 m: quadtree vs fuerza bruta
#   - vecino mas cercano: quadtree vs fuerza bruta
# Los tiempos son REALES, no se les agrega ni se les quita nada.

import csv
import gc
import math
import os
import random
import statistics
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from QuadTree import (LADO_CIUDAD, RADIO_BUSQUEDA, construir_quadtree, generar_ciudad,
                      nn_fuerza_bruta, radio_fuerza_bruta)

CONFIG = {
    # de 100 en 100 hasta 10000, mas unos N chiquitos porque el cruce de la busqueda en radio queda por debajo de 100
    "NS": [10, 20, 30, 50, 70] + list(range(100, 10001, 100)),
    "REPETICIONES": 5,       # ciudades distintas (semilla distinta) por cada N
    "CONSULTAS_POR_LOTE": 200,
    "VENTANA_S": 0.3,        # cada medicion dura al menos esto
    "CARPETA": "resultados",
}
CONFIG_RAPIDA = {
    "NS": [10, 50, 100, 500, 1000, 3000],
    "REPETICIONES": 2,
    "CONSULTAS_POR_LOTE": 200,
    "VENTANA_S": 0.05,
    "CARPETA": "resultados_prueba",
}

COLUMNAS = ["N", "repeticion", "momento_min", "altura", "nodos", "vecinos_promedio",
            "t_construir_s", "qt_radio_s", "fb_radio_s", "qt_nn_s", "fb_nn_s"]

INICIO = time.perf_counter()


def minutos():
    return (time.perf_counter() - INICIO) / 60


# ---------------- medicion ----------------

def sin_gc(f):
    # apagamos el recolector de basura durante toda la ventana para que no meta pausas en la medicion;
    # se recolecta UNA vez antes (hacerlo en cada lote era carisimo con N chiquito)
    gc.collect()
    gc.disable()
    try:
        return f()
    finally:
        gc.enable()


def medir_construccion(puntos, ventana):
    # construye el arbol una y otra vez hasta llenar la ventana; devuelve segundos por construccion
    def bucle():
        total, veces = 0.0, 0
        while total < ventana:
            t = time.perf_counter()
            construir_quadtree(puntos)
            total += time.perf_counter() - t
            veces += 1
        return total / veces
    return sin_gc(bucle)


def medir_consultas(funcion, rnd_consultas, consultas_por_lote, ventana):
    # lotes de consultas NUEVAS (centros al azar) hasta llenar la ventana; devuelve segundos por consulta.
    # el lote se genera FUERA del cronometro
    def bucle():
        total, n_consultas = 0.0, 0
        while total < ventana:
            lote = [(rnd_consultas.uniform(0, LADO_CIUDAD), rnd_consultas.uniform(0, LADO_CIUDAD))
                    for _ in range(consultas_por_lote)]
            t = time.perf_counter()
            for x, y in lote:
                funcion(x, y)
            total += time.perf_counter() - t
            n_consultas += len(lote)
        return total / n_consultas
    return sin_gc(bucle)


def una_medicion(n, rep, cfg):
    puntos = generar_ciudad(n, semilla=rep)
    qt = construir_quadtree(puntos)

    fila = {"N": n, "repeticion": rep, "altura": qt.altura(), "nodos": qt.contar_nodos()}

    # cuantos vecinos devuelve en promedio una consulta de radio (k), importa para el analisis
    rnd = random.Random(10_000 + rep)
    muestra = [(rnd.uniform(0, LADO_CIUDAD), rnd.uniform(0, LADO_CIUDAD)) for _ in range(300)]
    fila["vecinos_promedio"] = sum(len(qt.query_radius(x, y)) for x, y in muestra) / len(muestra)

    # las 5 mediciones en orden aleatorio, para que ninguna quede siempre de primera
    tareas = {
        "t_construir_s": lambda r: medir_construccion(puntos, cfg["VENTANA_S"]),
        "qt_radio_s": lambda r: medir_consultas(lambda x, y: qt.query_radius(x, y), r, cfg["CONSULTAS_POR_LOTE"], cfg["VENTANA_S"]),
        "fb_radio_s": lambda r: medir_consultas(lambda x, y: radio_fuerza_bruta(puntos, x, y), r, cfg["CONSULTAS_POR_LOTE"], cfg["VENTANA_S"]),
        "qt_nn_s": lambda r: medir_consultas(lambda x, y: qt.nearest_neighbor(x, y), r, cfg["CONSULTAS_POR_LOTE"], cfg["VENTANA_S"]),
        "fb_nn_s": lambda r: medir_consultas(lambda x, y: nn_fuerza_bruta(puntos, x, y), r, cfg["CONSULTAS_POR_LOTE"], cfg["VENTANA_S"]),
    }
    nombres = list(tareas)
    random.Random(rep * 100_003 + n).shuffle(nombres)
    for nombre in nombres:
        # misma semilla para quadtree y fuerza bruta: buscan exactamente los mismos centros
        rnd_consultas = random.Random(20_000 + rep * 7 + n)
        fila[nombre] = tareas[nombre](rnd_consultas)

    fila["momento_min"] = minutos()
    return fila


def correr_experimento(cfg):
    os.makedirs(cfg["CARPETA"], exist_ok=True)
    ruta = os.path.join(cfg["CARPETA"], "mediciones.csv")

    # todas las combinaciones (N, repeticion) en orden ALEATORIO: si el pc cambia de velocidad a mitad
    # del experimento, afecta a todos los N por igual y no se confunde con el efecto de N
    combinaciones = [(n, rep) for rep in range(1, cfg["REPETICIONES"] + 1) for n in cfg["NS"]]
    random.Random(12345).shuffle(combinaciones)

    print("calentamiento...")
    una_medicion(500, 999, dict(cfg, VENTANA_S=0.05))

    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        for i, (n, rep) in enumerate(combinaciones, 1):
            w.writerow(una_medicion(n, rep, cfg))
            f.flush()
            print(f"\r{i}/{len(combinaciones)}  N={n:>5} rep={rep}  ({minutos():.1f} min)", end="", flush=True)
    print(f"\nmediciones guardadas en {ruta}")


# ---------------- estadistica ----------------

# valor t de student para IC del 95 % segun grados de libertad (n-1); para no depender de scipy
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262,
       10: 2.228, 14: 2.145, 19: 2.093, 29: 2.045}


def t95(gl):
    if gl in T95:
        return T95[gl]
    menores = [g for g in T95 if g <= gl]
    return T95[max(menores)] if menores else T95[1]


def resumir(valores):
    n = len(valores)
    media = statistics.mean(valores)
    desv = statistics.stdev(valores) if n > 1 else 0.0
    margen = t95(n - 1) * desv / math.sqrt(n) if n > 1 else 0.0
    return {"media": media, "desv": desv, "cv": 100 * desv / media if media else 0.0,
            "ic_inf": media - margen, "ic_sup": media + margen, "mediana": statistics.median(valores)}


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    for fila in filas:
        for k in fila:
            fila[k] = float(fila[k])
        fila["N"] = int(fila["N"])
    return filas


def estadisticas(filas):
    por_n = {}
    for fila in filas:
        por_n.setdefault(fila["N"], []).append(fila)
    est = {}
    for n in sorted(por_n):
        grupo = por_n[n]
        est[n] = {col: resumir([g[col] for g in grupo])
                  for col in ["t_construir_s", "qt_radio_s", "fb_radio_s", "qt_nn_s", "fb_nn_s",
                              "altura", "nodos", "vecinos_promedio"]}
    return est


def pendiente_loglog(xs, ys):
    # regresion lineal de log10(y) contra log10(x): la pendiente k dice que y crece como N^k
    lx = [math.log10(x) for x in xs]
    ly = [math.log10(y) for y in ys]
    mx, my = statistics.mean(lx), statistics.mean(ly)
    k = sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / sum((a - mx) ** 2 for a in lx)
    pred = [my + k * (a - mx) for a in lx]
    ss_res = sum((b - p) ** 2 for b, p in zip(ly, pred))
    ss_tot = sum((b - my) ** 2 for b in ly)
    return k, 1 - ss_res / ss_tot


def cruce(est, col_qt, col_fb):
    # N desde el cual el quadtree es mas rapido CON intervalos de confianza separados,
    # y lo sigue siendo para todos los N mayores
    ns = sorted(est)
    gana_qt = [est[n][col_qt]["ic_sup"] < est[n][col_fb]["ic_inf"] for n in ns]
    gana_fb = [est[n][col_fb]["ic_sup"] < est[n][col_qt]["ic_inf"] for n in ns]
    desde = None
    for i in range(len(ns)):
        if all(gana_qt[i:]):
            desde = ns[i]
            break
    ns_fb = [n for n, g in zip(ns, gana_fb) if g]
    ns_empate = [n for n, a, b in zip(ns, gana_qt, gana_fb) if not a and not b]
    return desde, ns_fb, ns_empate


def consultas_para_compensar(est, col_qt, col_fb):
    # cuantas consultas hay que hacer para que construir el arbol valga la pena:
    # t_construir + m * t_qt < m * t_fb   ->   m > t_construir / (t_fb - t_qt)
    res = {}
    for n in est:
        ahorro = est[n][col_fb]["media"] - est[n][col_qt]["media"]
        res[n] = est[n]["t_construir_s"]["media"] / ahorro if ahorro > 0 else float("inf")
    return res


def estabilidad(filas):
    # tiempo relativo = tiempo de la medicion / mediana de su N. Si el pc fue estable, deberia dar ~1 todo el rato
    medianas = {}
    for col in ["qt_radio_s", "fb_radio_s", "qt_nn_s", "fb_nn_s"]:
        por_n = {}
        for f in filas:
            por_n.setdefault(f["N"], []).append(f[col])
        medianas[col] = {n: statistics.median(v) for n, v in por_n.items()}
    puntos = []
    for f in filas:
        rel = statistics.mean(f[c] / medianas[c][f["N"]] for c in medianas)
        puntos.append((f["momento_min"], rel))
    puntos.sort()
    cuartos = []
    q = max(1, len(puntos) // 4)
    for i in range(4):
        trozo = puntos[i * q:(i + 1) * q] if i < 3 else puntos[3 * q:]
        if trozo:
            cuartos.append((trozo[0][0], trozo[-1][0], statistics.median(r for _, r in trozo)))
    return puntos, cuartos


# ---------------- reporte ----------------

def us(s):
    return s * 1e6


def escribir_resumen(cfg, filas, est, carpeta):
    ns = sorted(est)
    lineas = ["# Resumen del benchmark (generado por analisis.py)\n",
              f"- N medidos: {len(ns)} valores, de {ns[0]} a {ns[-1]}",
              f"- Repeticiones por N: {cfg['REPETICIONES']} (ciudad distinta en cada una)",
              f"- Ventana mínima por medición: {cfg['VENTANA_S']} s",
              f"- Radio de búsqueda: {RADIO_BUSQUEDA} m en una ciudad de {LADO_CIUDAD} m × {LADO_CIUDAD} m",
              f"- Duración total: {max(f['momento_min'] for f in filas):.1f} min\n"]

    lineas.append("## ¿Desde qué N gana el quadtree?\n")
    lineas.append("Criterio: el quadtree es más rápido con los intervalos de confianza del 95 % separados, "
                  "y lo sigue siendo para todos los N mayores.\n")
    lineas.append("| Consulta | Quadtree gana desde N = | N donde gana la fuerza bruta | N empatados (IC se tocan) |")
    lineas.append("|---|---|---|---|")
    for nombre, cq, cf in [("Radio 500 m", "qt_radio_s", "fb_radio_s"), ("Vecino más cercano", "qt_nn_s", "fb_nn_s")]:
        desde, ns_fb, ns_emp = cruce(est, cq, cf)
        lineas.append(f"| {nombre} | {desde} | {', '.join(map(str, ns_fb)) or 'ninguno'} | "
                      f"{', '.join(map(str, ns_emp)) or 'ninguno'} |")

    lineas.append("\n## Pendientes log-log (tiempo ∝ N^k), N ≥ 100\n")
    lineas.append("| Curva | k | R² |")
    lineas.append("|---|---|---|")
    ns100 = [n for n in ns if n >= 100]
    for nombre, col in [("Quadtree radio", "qt_radio_s"), ("Fuerza bruta radio", "fb_radio_s"),
                        ("Quadtree vecino", "qt_nn_s"), ("Fuerza bruta vecino", "fb_nn_s"),
                        ("Construir quadtree", "t_construir_s"), ("Vecinos devueltos (k)", "vecinos_promedio")]:
        k, r2 = pendiente_loglog(ns100, [est[n][col]["media"] for n in ns100])
        lineas.append(f"| {nombre} | {k:.3f} | {r2:.3f} |")

    lineas.append("\n## Tabla por N (µs por consulta; construir en ms)\n")
    lineas.append("| N | Altura | Vecinos en radio | Construir (ms) | QT radio | FB radio | QT vecino | FB vecino | "
                  "Consultas de radio para compensar construir | Consultas de vecino para compensar |")
    lineas.append("|---|---|---|---|---|---|---|---|---|---|")
    comp_r = consultas_para_compensar(est, "qt_radio_s", "fb_radio_s")
    comp_n = consultas_para_compensar(est, "qt_nn_s", "fb_nn_s")
    muestra = [n for n in ns if n < 100 or n in (100, 200, 300, 500, 1000, 2000, 3000, 5000, 7000, 10000)]
    for n in muestra:
        e = est[n]
        def c(v):
            return "nunca" if v == float("inf") else f"{math.ceil(v)}"
        lineas.append(f"| {n} | {e['altura']['media']:.1f} | {e['vecinos_promedio']['media']:.1f} | "
                      f"{e['t_construir_s']['media'] * 1e3:.2f} | "
                      f"{us(e['qt_radio_s']['media']):.2f} ± {us(e['qt_radio_s']['desv']):.2f} | "
                      f"{us(e['fb_radio_s']['media']):.2f} ± {us(e['fb_radio_s']['desv']):.2f} | "
                      f"{us(e['qt_nn_s']['media']):.2f} ± {us(e['qt_nn_s']['desv']):.2f} | "
                      f"{us(e['fb_nn_s']['media']):.2f} ± {us(e['fb_nn_s']['desv']):.2f} | "
                      f"{c(comp_r[n])} | {c(comp_n[n])} |")
    lineas.append("\n(± = desviación estándar entre repeticiones. La tabla completa está en `estadisticas.csv`.)\n")

    lineas.append("## Ruido\n")
    cvs = [est[n][col]["cv"] for n in ns for col in ["qt_radio_s", "fb_radio_s", "qt_nn_s", "fb_nn_s"]]
    lineas.append(f"CV de las consultas: mediana {statistics.median(cvs):.1f} %, máximo {max(cvs):.1f} %.\n")
    _, cuartos = estabilidad(filas)
    lineas.append("| Parte del experimento | Minutos | Mediana del tiempo relativo |")
    lineas.append("|---|---|---|")
    for i, (a, b, m) in enumerate(cuartos, 1):
        lineas.append(f"| {i}.º cuarto | {a:.1f} – {b:.1f} | {m:.3f} |")

    with open(os.path.join(carpeta, "resumen.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")

    with open(os.path.join(carpeta, "estadisticas.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["N", "medida", "media", "desv", "cv_%", "ic95_inf", "ic95_sup", "mediana"])
        for n in ns:
            for col, r in est[n].items():
                w.writerow([n, col, r["media"], r["desv"], r["cv"], r["ic_inf"], r["ic_sup"], r["mediana"]])


# ---------------- graficas ----------------

COLOR_QT = "tab:blue"
COLOR_FB = "tab:red"
NOTA = "Línea = media de las repeticiones; banda = intervalo de confianza del 95 %. Sin suavizar."


def curva(ax, est, ns, col, color, etiqueta):
    m = [us(est[n][col]["media"]) for n in ns]
    lo = [us(est[n][col]["ic_inf"]) for n in ns]
    hi = [us(est[n][col]["ic_sup"]) for n in ns]
    ax.plot(ns, m, color=color, marker="o", markersize=2.5, linewidth=1, label=etiqueta)
    ax.fill_between(ns, lo, hi, color=color, alpha=0.2)


def guardar(fig, nombre, carpeta):
    fig.text(0.01, 0.005, NOTA, fontsize=7, color="gray")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    ruta = os.path.join(carpeta, nombre)
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    print("  ", ruta)


def graficas(est, filas, carpeta):
    os.makedirs(carpeta, exist_ok=True)
    ns = sorted(est)

    for col_qt, col_fb, titulo, archivo in [
        ("qt_radio_s", "fb_radio_s", f"Consulta en radio de {RADIO_BUSQUEDA} m", "1_radio.png"),
        ("qt_nn_s", "fb_nn_s", "Vecino más cercano", "2_vecino.png"),
    ]:
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))
        for ax, sub in [(a1, ns), (a2, [n for n in ns if n <= 1000])]:
            curva(ax, est, sub, col_fb, COLOR_FB, "Fuerza bruta (lista)")
            curva(ax, est, sub, col_qt, COLOR_QT, "Quadtree")
            ax.set_xlabel("N (puntos de entrega)")
            ax.set_ylabel("Tiempo por consulta (µs)")
            ax.grid(alpha=0.3)
            ax.legend()
        desde, _, _ = cruce(est, col_qt, col_fb)
        if desde is not None and desde <= 1000:
            a2.axvline(desde, color="gray", linestyle=":")
            a2.annotate(f"quadtree gana\ndesde N = {desde}", (desde, a2.get_ylim()[1] * 0.8),
                        fontsize=8, color="gray", xytext=(5, 0), textcoords="offset points")
        a1.set_title(f"{titulo}: N de {ns[0]} a {ns[-1]}")
        a2.set_title(f"{titulo}: zoom N ≤ 1000")
        guardar(fig, archivo, carpeta)

    # log-log con pendientes
    fig, ax = plt.subplots(figsize=(9, 6))
    ns100 = [n for n in ns if n >= 100]
    for col, color, estilo, nombre in [("fb_radio_s", COLOR_FB, "-", "Fuerza bruta, radio"),
                                       ("qt_radio_s", COLOR_QT, "-", "Quadtree, radio"),
                                       ("fb_nn_s", COLOR_FB, "--", "Fuerza bruta, vecino"),
                                       ("qt_nn_s", COLOR_QT, "--", "Quadtree, vecino")]:
        k, _ = pendiente_loglog(ns100, [est[n][col]["media"] for n in ns100])
        ax.plot(ns, [us(est[n][col]["media"]) for n in ns], color=color, linestyle=estilo,
                linewidth=1, label=f"{nombre} (pendiente {k:.2f})")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title("Tiempo por consulta vs N (escala log-log)")
    ax.set_xlabel("N (puntos de entrega, escala log)")
    ax.set_ylabel("Tiempo por consulta (µs, escala log)")
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8)
    guardar(fig, "3_loglog.png", carpeta)

    # costo de construir y cuantas consultas hacen falta para que compense
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))
    a1.plot(ns, [est[n]["t_construir_s"]["media"] * 1e3 for n in ns], color="tab:purple", marker="o",
            markersize=2.5, linewidth=1)
    a1.fill_between(ns, [est[n]["t_construir_s"]["ic_inf"] * 1e3 for n in ns],
                    [est[n]["t_construir_s"]["ic_sup"] * 1e3 for n in ns], color="tab:purple", alpha=0.2)
    a1.set_title("Costo de construir el quadtree")
    a1.set_xlabel("N (puntos de entrega)")
    a1.set_ylabel("Tiempo de construcción (ms)")
    a1.grid(alpha=0.3)
    for col_qt, col_fb, color, nombre in [("qt_radio_s", "fb_radio_s", "tab:green", "consultas de radio"),
                                          ("qt_nn_s", "fb_nn_s", "tab:orange", "consultas de vecino")]:
        comp = consultas_para_compensar(est, col_qt, col_fb)
        xs = [n for n in ns if comp[n] != float("inf")]
        a2.plot(xs, [comp[n] for n in xs], color=color, marker="o", markersize=2.5, linewidth=1, label=nombre)
    a2.set_yscale("log")
    a2.set_title("¿Cuántas consultas hacen falta para que construir el árbol compense?")
    a2.set_xlabel("N (puntos de entrega)")
    a2.set_ylabel("Consultas necesarias (escala log)")
    a2.grid(alpha=0.3, which="both")
    a2.legend()
    guardar(fig, "4_construccion.png", carpeta)


def main():
    correr_experimento(CONFIG)

    filas = leer(os.path.join(CONFIG["CARPETA"], "mediciones.csv"))
    est = estadisticas(filas)
    escribir_resumen(CONFIG, filas, est, CONFIG["CARPETA"])
    print("graficas:")
    graficas(est, filas, "graficas")
    print(f"resumen en {CONFIG['CARPETA']}/resumen.md")


if __name__ == "__main__":
    main()