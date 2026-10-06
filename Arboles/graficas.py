"""
Gráficas del Laboratorio 3.

Lee los archivos que produce analisis.py y guarda las imágenes en graficas/
(o graficas_prueba/ con --rapido). No vuelve a correr ningún experimento.

Uso:
    python graficas.py
    python graficas.py --rapido
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")  # guardar imágenes sin abrir ventanas
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLOR = {"Lista": "tab:red", "ABB": "tab:blue", "B+": "tab:green"}
LINEA = {"aleatorio": "-", "ordenado": "--"}
MARCA = {"aleatorio": "o", "ordenado": "s"}
NOTA_IC = "Puntos = media de las repeticiones; barras = intervalo de confianza del 95 %."


def estilo(ax, titulo, eje_x, eje_y, nota=None):
    ax.set_title(titulo, fontsize=12, fontweight="bold")
    ax.set_xlabel(eje_x)
    ax.set_ylabel(eje_y)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
    if nota:
        ax.figure.text(0.01, 0.01, nota, fontsize=7.5, color="dimgray")


def guardar(fig, carpeta, nombre):
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    ruta = os.path.join(carpeta, nombre)
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    print("  ", ruta)


def curvas(ax, est, operacion, pendientes=None):
    """Una curva por (estructura, orden) con barras de error del IC 95 %."""
    datos = est[est.operacion == operacion]
    for (estructura, orden), g in datos.groupby(["estructura", "orden"]):
        g = g.sort_values("N")
        etiqueta = f"{estructura}, IDs {orden}s"
        if pendientes is not None:
            fila = pendientes[(pendientes.operacion == operacion) &
                              (pendientes.curva == f"{estructura} ({orden})")]
            if len(fila):
                etiqueta += f"  (pendiente = {fila.pendiente.iloc[0]:.2f})"
        abajo = (g["media"] - g["ic95_inf"]).clip(lower=0)
        arriba = g["ic95_sup"] - g["media"]
        ax.errorbar(g["N"], g["media"], yerr=[abajo, arriba], label=etiqueta,
                    color=COLOR[estructura], linestyle=LINEA[orden], marker=MARCA[orden],
                    markersize=4, capsize=3, linewidth=1.5)


def grafica_busqueda_lineal(est, carpeta, m):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    curvas(ax, est, "busqueda")
    estilo(ax, f"Tiempo de búsqueda vs. número de estudiantes (escala lineal, M = {m})",
           "N (número de estudiantes)", "Tiempo por búsqueda (µs)", NOTA_IC)
    guardar(fig, carpeta, "1_busqueda_vs_N_lineal.png")


def grafica_loglog(est, pend, carpeta, operacion, titulo, eje_y, archivo, nota_extra=""):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    curvas(ax, est, operacion, pend)
    ax.set_xscale("log")
    ax.set_yscale("log")
    estilo(ax, titulo, "N (número de estudiantes, escala log)", eje_y,
           NOTA_IC + " La pendiente k de cada recta indica tiempo ∝ N^k." + nota_extra)
    guardar(fig, carpeta, archivo)


def grafica_altura(est, carpeta):
    datos = est[(est.operacion == "busqueda") & est.altura_media.notna()]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for (estructura, orden), g in datos.groupby(["estructura", "orden"]):
        g = g.sort_values("N")
        ax.plot(g["N"], g["altura_media"], label=f"{estructura}, IDs {orden}s",
                color=COLOR[estructura], linestyle=LINEA[orden], marker=MARCA[orden], markersize=4)
    ns = np.array(sorted(est.N.unique()), dtype=float)
    ax.plot(ns, np.ceil(np.log2(ns + 1)), color="black", linestyle=":", label="Mínima posible para un ABB: ⌈log₂(N+1)⌉")
    ax.plot(ns, ns, color="gray", linestyle="-.", label="Altura = N (árbol degenerado)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    estilo(ax, "Altura del árbol vs. número de estudiantes", "N (número de estudiantes, escala log)",
           "Altura (niveles, escala log)", "Altura media de las repeticiones.")
    guardar(fig, carpeta, "3_altura_vs_N.png")


def grafica_tiempo_vs_altura(est, carpeta):
    datos = est[(est.operacion == "busqueda") & est.altura_media.notna()]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for (estructura, orden), g in datos.groupby(["estructura", "orden"]):
        ax.scatter(g["altura_media"], g["media"], label=f"{estructura}, IDs {orden}s",
                   color=COLOR[estructura], marker=MARCA[orden], s=35, alpha=0.8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    estilo(ax, "Tiempo de búsqueda vs. altura del árbol", "Altura del árbol (niveles, escala log)",
           "Tiempo por búsqueda (µs, escala log)", "Cada punto es un valor de N (media de las repeticiones).")
    guardar(fig, carpeta, "4_tiempo_vs_altura.png")


def grafica_m(est_b, carpeta):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for estructura, g in est_b.groupby("estructura"):
        g = g.sort_values("M")
        abajo = (g["media"] - g["ic95_inf"]).clip(lower=0)
        ax.errorbar(g["M"], g["media"], yerr=[abajo, g["ic95_sup"] - g["media"]], label=estructura,
                    color=COLOR[estructura], marker="o", markersize=4, capsize=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    n = int(est_b.N.iloc[0])
    estilo(ax, f"Tiempo total de búsqueda vs. número de búsquedas M (N = {n}, IDs aleatorios)",
           "M (número de búsquedas, escala log)", "Tiempo total de las M búsquedas (ms, escala log)", NOTA_IC)
    guardar(fig, carpeta, "7_busqueda_vs_M.png")


def grafica_dispersion(mediciones, carpeta):
    """Cajas y bigotes: muestra la distribución de las repeticiones y los atípicos."""
    a = mediciones[mediciones.experimento == "A_variar_N"].copy()
    n = 10000 if 10000 in a.N.values else a.N.max()
    a = a[a.N == n]
    a["us"] = a["t_busqueda_s"] / a["M"] * 1e6
    grupos, etiquetas, colores = [], [], []
    for estructura in ("Lista", "ABB", "B+"):
        for orden in ("ordenado", "aleatorio"):
            g = a[(a.estructura == estructura) & (a.orden == orden)]["us"]
            if len(g):
                grupos.append(g.values)
                etiquetas.append(f"{estructura}\n{orden}")
                colores.append(COLOR[estructura])
    fig, ax = plt.subplots(figsize=(9, 5.5))
    cajas = ax.boxplot(grupos, patch_artist=True, whis=1.5)
    ax.set_xticks(range(1, len(etiquetas) + 1), etiquetas)
    for caja, color in zip(cajas["boxes"], colores):
        caja.set_facecolor(color)
        caja.set_alpha(0.4)
    ax.set_yscale("log")
    ax.set_title(f"Dispersión de las repeticiones del tiempo de búsqueda (N = {n})",
                 fontsize=12, fontweight="bold")
    ax.set_xlabel("Estructura y orden de inserción")
    ax.set_ylabel("Tiempo por búsqueda (µs, escala log)")
    ax.grid(True, axis="y", which="both", alpha=0.3)
    fig.text(0.01, 0.01, "Caja = 50 % central (Q1 a Q3); línea = mediana; "
                         "círculos = atípicos según la regla 1.5·IQR.", fontsize=7.5, color="dimgray")
    guardar(fig, carpeta, "8_dispersion_busqueda.png")


def grafica_estabilidad(mediciones, carpeta):
    """Tiempo relativo (medición / mediana de su grupo) a lo largo del experimento."""
    if "momento_min" not in mediciones.columns:
        print("   (sin columna momento_min: se omite la gráfica de estabilidad)")
        return
    from analisis import tiempos_normalizados
    d = tiempos_normalizados(mediciones).sort_values("momento_min")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.scatter(d["momento_min"], d["relativo"], s=6, alpha=0.25, color="tab:gray",
               label="Cada medición de búsqueda")
    tendencia = d["relativo"].rolling(max(len(d) // 40, 5), center=True).median()
    ax.plot(d["momento_min"], tendencia, color="tab:purple", linewidth=2,
            label="Mediana móvil (tendencia)")
    ax.axhline(1, color="black", linestyle=":", label="1 = tiempo típico de su grupo")
    ax.set_ylim(0, 3)
    estilo(ax, "Estabilidad del computador durante el experimento",
           "Momento de la medición (minutos desde el inicio)",
           "Tiempo relativo (medición / mediana de su grupo)",
           "Si el computador mantuvo la misma velocidad, la línea morada debe quedarse cerca de 1. "
           "Valores por encima de 3 no se muestran.")
    guardar(fig, carpeta, "9_estabilidad_en_el_tiempo.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rapido", action="store_true")
    args = parser.parse_args()
    origen = "resultados_prueba" if args.rapido else "resultados"
    destino = "graficas_prueba" if args.rapido else "graficas"
    os.makedirs(destino, exist_ok=True)

    est = pd.read_csv(os.path.join(origen, "estadisticas_A.csv"))
    est_b = pd.read_csv(os.path.join(origen, "estadisticas_B.csv"))
    pend = pd.read_csv(os.path.join(origen, "pendientes.csv"))
    mediciones = pd.read_csv(os.path.join(origen, "mediciones.csv"))
    m = int(mediciones[mediciones.experimento == "A_variar_N"].M.iloc[0])

    print("Gráficas guardadas:")
    grafica_busqueda_lineal(est, destino, m)
    grafica_loglog(est, pend, destino, "busqueda",
                   f"Tiempo de búsqueda vs. N (escala log-log, M = {m})",
                   "Tiempo por búsqueda (µs, escala log)", "2_busqueda_vs_N_loglog.png")
    grafica_altura(est, destino)
    grafica_tiempo_vs_altura(est, destino)
    grafica_loglog(est, pend, destino, "insercion",
                   "Tiempo de inserción vs. N (escala log-log)",
                   "Tiempo medio por inserción (µs, escala log)", "5_insercion_vs_N.png",
                   " Por inserción = tiempo de construir / N.")
    grafica_loglog(est, pend, destino, "listar",
                   "Tiempo de listar todos los estudiantes en orden vs. N (escala log-log)",
                   "Tiempo del listado completo (ms, escala log)", "6_listar_vs_N.png")
    grafica_m(est_b, destino)
    grafica_dispersion(mediciones, destino)
    grafica_estabilidad(mediciones, destino)


if __name__ == "__main__":
    main()
