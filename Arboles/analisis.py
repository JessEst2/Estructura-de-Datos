"""
Análisis estadístico de las mediciones del experimento.

Lee resultados/mediciones.csv y produce:
  - resultados/estadisticas_A.csv : estadísticas por (operación, estructura, orden, N)
  - resultados/estadisticas_B.csv : estadísticas por (estructura, M)
  - resultados/pendientes.csv     : pendientes log-log (comparación con la teoría)
  - resultados/resumen.md         : todo lo anterior en tablas legibles

Uso:
    python analisis.py            # analiza resultados/
    python analisis.py --rapido   # analiza resultados_prueba/
"""
import argparse
import os

import numpy as np
import pandas as pd
from scipy import stats

# Cada operación: (columna de tiempo en el CSV, cómo convertirla, unidad)
OPERACIONES = {
    "busqueda": ("t_busqueda_s", lambda d: d["t_busqueda_s"] / d["M"] * 1e6, "µs por búsqueda"),
    "insercion": ("t_construccion_s", lambda d: d["t_construccion_s"] / d["N"] * 1e6, "µs por inserción"),
    "listar": ("t_listar_s", lambda d: d["t_listar_s"] * 1e3, "ms por listado completo"),
}
NIVEL_CONFIANZA = 0.95


# ----------------------------------------------------------------------
# Estadísticas de un grupo de repeticiones
# ----------------------------------------------------------------------
def atipicos_iqr(valores):
    """Regla del rango intercuartílico (IQR):
    Q1 = percentil 25, Q3 = percentil 75, IQR = Q3 - Q1.
    Es atípico lo que esté por debajo de Q1 - 1.5*IQR o por encima de Q3 + 1.5*IQR."""
    q1, q3 = np.percentile(valores, [25, 75])
    iqr = q3 - q1
    return (valores < q1 - 1.5 * iqr) | (valores > q3 + 1.5 * iqr)


def resumir(valores):
    valores = np.asarray(valores, dtype=float)
    n = len(valores)
    media = valores.mean()
    desv = valores.std(ddof=1) if n > 1 else 0.0           # desviación estándar muestral
    error_estandar = desv / np.sqrt(n) if n > 1 else 0.0
    t_critico = stats.t.ppf((1 + NIVEL_CONFIANZA) / 2, n - 1) if n > 1 else 0.0
    margen = t_critico * error_estandar
    es_atipico = atipicos_iqr(valores) if n >= 4 else np.zeros(n, bool)
    limpios = valores[~es_atipico]
    return {
        "repeticiones": n,
        "media": media,
        "desv_estandar": desv,
        "cv_%": 100 * desv / media if media else np.nan,
        "ic95_inf": media - margen,
        "ic95_sup": media + margen,
        "mediana": np.median(valores),
        "minimo": valores.min(),
        "maximo": valores.max(),
        "atipicos": int(es_atipico.sum()),
        "media_sin_atipicos": limpios.mean(),
    }


def nombre_curva(estructura, orden):
    return f"{estructura} ({orden})"


# ----------------------------------------------------------------------
# Experimento A: variar N
# ----------------------------------------------------------------------
def estadisticas_a(datos):
    filas = []
    for operacion, (columna, convertir, unidad) in OPERACIONES.items():
        d = datos.dropna(subset=[columna]).copy()
        d["valor"] = convertir(d)
        for (estructura, orden, n), grupo in d.groupby(["estructura", "orden", "N"]):
            fila = {"operacion": operacion, "unidad": unidad,
                    "estructura": estructura, "orden": orden, "N": n,
                    "curva": nombre_curva(estructura, orden)}
            fila.update(resumir(grupo["valor"]))
            fila["altura_media"] = pd.to_numeric(grupo["altura"], errors="coerce").mean()
            filas.append(fila)
    return pd.DataFrame(filas)


def pendientes(est_a):
    """Regresión lineal de log10(tiempo medio) contra log10(N).
    Si tiempo ≈ c·N^k, entonces log(tiempo) = log(c) + k·log(N): la pendiente es k.
      k ≈ 1   -> crece como N       (O(N))
      k ≈ 0   -> casi no crece      (O(1) u O(log N))
      k ≈ 1.x -> crece algo más rápido que N (por ejemplo O(N log N))"""
    filas = []
    for (operacion, curva), g in est_a.groupby(["operacion", "curva"]):
        if len(g) < 3:
            continue
        reg = stats.linregress(np.log10(g["N"]), np.log10(g["media"]))
        filas.append({"operacion": operacion, "curva": curva,
                      "pendiente": reg.slope, "error_pendiente": reg.stderr,
                      "r2": reg.rvalue ** 2, "N_min": g["N"].min(), "N_max": g["N"].max()})
    return pd.DataFrame(filas)


def costo_por_nivel(est_a):
    """Tiempo de búsqueda dividido por la altura: cuánto cuesta bajar UN nivel."""
    b = est_a[(est_a.operacion == "busqueda") & est_a.altura_media.notna()].copy()
    b["ns_por_nivel"] = b["media"] * 1000 / b["altura_media"]
    return b[["curva", "N", "altura_media", "media", "ns_por_nivel"]]


def correlacion_altura_tiempo(datos):
    """Correlación de Pearson entre la altura del árbol y el tiempo por búsqueda,
    usando todas las repeticiones (cada fila es una medición)."""
    d = datos[(datos.experimento == "A_variar_N") & (datos.estructura != "Lista")].copy()
    d["altura"] = pd.to_numeric(d["altura"])
    d["us_por_busqueda"] = d["t_busqueda_s"] / d["M"] * 1e6
    filas = []
    for estructura, g in d.groupby("estructura"):
        r, p = stats.pearsonr(g["altura"], g["us_por_busqueda"])
        filas.append({"estructura": estructura, "r_pearson": r, "p_valor": p, "mediciones": len(g)})
    return pd.DataFrame(filas)


def desde_que_n(est_a):
    """Para cada orden: menor N desde el cual cada árbol es más rápido que la lista
    con diferencia estadísticamente clara (los intervalos de confianza no se tocan)."""
    b = est_a[est_a.operacion == "busqueda"]
    filas = []
    for orden in ("aleatorio", "ordenado"):
        lista = b[(b.estructura == "Lista") & (b.orden == orden)].set_index("N")
        for arbol in ("ABB", "B+"):
            t = b[(b.estructura == arbol) & (b.orden == orden)].set_index("N")
            ns_comunes = sorted(set(lista.index) & set(t.index))
            mas_rapido = [n for n in ns_comunes if t.loc[n, "ic95_sup"] < lista.loc[n, "ic95_inf"]]
            mas_lento = [n for n in ns_comunes if t.loc[n, "ic95_inf"] > lista.loc[n, "ic95_sup"]]
            filas.append({
                "orden": orden, "arbol": arbol,
                "N_donde_arbol_es_mas_rapido": ", ".join(map(str, mas_rapido)) or "ninguno",
                "N_donde_arbol_es_mas_lento": ", ".join(map(str, mas_lento)) or "ninguno",
                "veces_mas_rapido_en_N_max": lista.loc[ns_comunes[-1], "media"] / t.loc[ns_comunes[-1], "media"],
                "N_max_comparado": ns_comunes[-1],
            })
    return pd.DataFrame(filas)


def tiempos_normalizados(datos):
    """Divide cada tiempo de búsqueda por la mediana de su grupo (estructura, orden, N).
    Un valor de 1 significa "igual a lo típico de su grupo"; 2 significa "el doble de lento".
    Así se pueden comparar en una sola escala mediciones de estructuras y N muy distintos."""
    d = datos[datos.experimento == "A_variar_N"].copy()
    d["us"] = d["t_busqueda_s"] / d["M"] * 1e6
    d["relativo"] = d["us"] / d.groupby(["estructura", "orden", "N"])["us"].transform("median")
    return d


def estabilidad(datos):
    """¿Cambió la velocidad del computador durante el experimento?
    Se divide la duración del experimento en 4 cuartos y se mira la mediana del tiempo
    relativo en cada cuarto. Si el computador fue estable, todas deberían ser ≈ 1.
    Además, correlación de Spearman entre el momento de la medición y el tiempo relativo
    (cerca de 0 = no hay tendencia en el tiempo)."""
    if "momento_min" not in datos.columns:
        return None, None
    d = tiempos_normalizados(datos)
    d["cuarto"] = pd.cut(d["momento_min"], 4, labels=["1.º cuarto", "2.º cuarto", "3.º cuarto", "4.º cuarto"])
    tabla = d.groupby("cuarto", observed=True).agg(
        desde_min=("momento_min", "min"), hasta_min=("momento_min", "max"),
        mediciones=("relativo", "size"), mediana_relativa=("relativo", "median")).reset_index()
    rho, p = stats.spearmanr(d["momento_min"], d["relativo"])
    return tabla, {"rho": rho, "p": p}


# ----------------------------------------------------------------------
# Experimento B: variar M
# ----------------------------------------------------------------------
def estadisticas_b(datos):
    d = datos[datos.experimento == "B_variar_M"].copy()
    d["valor"] = d["t_busqueda_s"] * 1e3  # ms totales para las M búsquedas
    filas = []
    for (estructura, m), g in d.groupby(["estructura", "M"]):
        fila = {"estructura": estructura, "N": g["N"].iloc[0], "M": m, "unidad": "ms totales"}
        fila.update(resumir(g["valor"]))
        filas.append(fila)
    est_b = pd.DataFrame(filas)
    pend = []
    for estructura, g in est_b.groupby("estructura"):
        reg = stats.linregress(np.log10(g["M"]), np.log10(g["media"]))
        pend.append({"estructura": estructura, "pendiente_vs_M": reg.slope, "r2": reg.rvalue ** 2})
    return est_b, pd.DataFrame(pend)


# ----------------------------------------------------------------------
# Reporte en Markdown
# ----------------------------------------------------------------------
def fmt(x, dec=3):
    if isinstance(x, (int, np.integer)):
        return str(x)
    if pd.isna(x):
        return "-"
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    return f"{x:.{dec}f}"


def tabla_md(df, columnas, nombres=None):
    nombres = nombres or columnas
    lineas = ["| " + " | ".join(nombres) + " |", "|" + "---|" * len(columnas)]
    for _, fila in df.iterrows():
        lineas.append("| " + " | ".join(fmt(fila[c]) if not isinstance(fila[c], str) else fila[c]
                                         for c in columnas) + " |")
    return "\n".join(lineas)


def escribir_resumen(carpeta, datos, est_a, pend, por_nivel, corr, cruce, est_b, pend_b,
                     tabla_estab=None, spearman=None):
    with open(os.path.join(carpeta, "entorno.txt"), encoding="utf-8") as f:
        entorno = f.read()

    partes = ["# Resumen de resultados\n",
              "Generado automáticamente por `analisis.py` a partir de `mediciones.csv`.\n",
              "## Entorno de la medición\n", "```\n" + entorno + "```\n",
              f"Total de mediciones: {len(datos)} filas.\n"]

    partes.append("## Estabilidad del computador durante el experimento\n")
    if tabla_estab is None:
        partes.append("No disponible: el archivo de mediciones no tiene la columna `momento_min`.\n")
    else:
        partes.append("Tiempo de búsqueda de cada medición dividido por la mediana de su grupo "
                      "(estructura, orden, N). Si el computador mantuvo la misma velocidad, la mediana "
                      "de cada cuarto del experimento debe ser cercana a 1.\n")
        partes.append(tabla_md(tabla_estab, ["cuarto", "desde_min", "hasta_min", "mediciones", "mediana_relativa"],
                               ["Parte del experimento", "Desde (min)", "Hasta (min)", "Mediciones",
                                "Mediana del tiempo relativo"]) + "\n")
        partes.append(f"Correlación de Spearman entre el momento de la medición y el tiempo relativo: "
                      f"ρ = {spearman['rho']:.3f} (p-valor = {spearman['p']:.3g}). "
                      "Cerca de 0 = sin tendencia en el tiempo.\n")

    cols = ["curva", "N", "repeticiones", "media", "desv_estandar", "cv_%",
            "ic95_inf", "ic95_sup", "mediana", "atipicos", "media_sin_atipicos"]
    nombres = ["Estructura", "N", "Rep.", "Media", "Desv. est.", "CV %",
               "IC95 inf", "IC95 sup", "Mediana", "Atípicos", "Media sin atípicos"]
    for operacion, (_, _, unidad) in OPERACIONES.items():
        t = est_a[est_a.operacion == operacion].sort_values(["curva", "N"])
        partes.append(f"## Experimento A — {operacion} ({unidad})\n")
        partes.append(tabla_md(t, cols, nombres) + "\n")

    partes.append("## Comparación con la teoría: pendientes log-log\n")
    partes.append("Pendiente k de la recta log10(tiempo) vs log10(N). "
                  "k≈1 indica O(N); k≈0 indica crecimiento muy lento (O(log N) u O(1)).\n")
    partes.append(tabla_md(pend.sort_values(["operacion", "curva"]),
                           ["operacion", "curva", "pendiente", "error_pendiente", "r2", "N_min", "N_max"],
                           ["Operación", "Estructura", "Pendiente k", "Error de k", "R²", "N mín", "N máx"]) + "\n")

    partes.append("## Altura del árbol y tiempo de búsqueda\n")
    partes.append(tabla_md(por_nivel.sort_values(["curva", "N"]),
                           ["curva", "N", "altura_media", "media", "ns_por_nivel"],
                           ["Estructura", "N", "Altura media", "µs por búsqueda", "ns por nivel"]) + "\n")
    partes.append("Correlación de Pearson entre altura y tiempo por búsqueda (todas las mediciones):\n")
    partes.append(tabla_md(corr, ["estructura", "r_pearson", "p_valor", "mediciones"],
                           ["Estructura", "r", "p-valor", "Mediciones"]) + "\n")

    partes.append("## ¿Desde qué N el árbol supera a la lista? (búsqueda)\n")
    partes.append("Se considera diferencia clara cuando los intervalos de confianza del 95% no se superponen.\n")
    partes.append(tabla_md(cruce, ["orden", "arbol", "N_donde_arbol_es_mas_rapido",
                                   "N_donde_arbol_es_mas_lento", "N_max_comparado", "veces_mas_rapido_en_N_max"],
                           ["Orden", "Árbol", "N donde el árbol es más rápido",
                            "N donde el árbol es más lento", "N máx comparado",
                            "Veces más rápido en ese N"]) + "\n")

    partes.append(f"## Experimento B — variar M (N = {int(est_b.N.iloc[0])}, datos aleatorios, ms totales)\n")
    partes.append(tabla_md(est_b.sort_values(["estructura", "M"]),
                           ["estructura", "M", "repeticiones", "media", "desv_estandar", "cv_%",
                            "ic95_inf", "ic95_sup", "atipicos"],
                           ["Estructura", "M", "Rep.", "Media", "Desv. est.", "CV %",
                            "IC95 inf", "IC95 sup", "Atípicos"]) + "\n")
    partes.append("Pendiente log-log del tiempo total contra M (se espera ≈1: el doble de búsquedas, el doble de tiempo):\n")
    partes.append(tabla_md(pend_b, ["estructura", "pendiente_vs_M", "r2"], ["Estructura", "Pendiente", "R²"]) + "\n")

    with open(os.path.join(carpeta, "resumen.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(partes))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rapido", action="store_true")
    args = parser.parse_args()
    carpeta = "resultados_prueba" if args.rapido else "resultados"

    datos = pd.read_csv(os.path.join(carpeta, "mediciones.csv"))
    datos_a = datos[datos.experimento == "A_variar_N"]

    est_a = estadisticas_a(datos_a)
    pend = pendientes(est_a)
    por_nivel = costo_por_nivel(est_a)
    corr = correlacion_altura_tiempo(datos)
    cruce = desde_que_n(est_a)
    est_b, pend_b = estadisticas_b(datos)
    tabla_estab, spearman = estabilidad(datos)

    est_a.to_csv(os.path.join(carpeta, "estadisticas_A.csv"), index=False)
    est_b.to_csv(os.path.join(carpeta, "estadisticas_B.csv"), index=False)
    pend.to_csv(os.path.join(carpeta, "pendientes.csv"), index=False)
    escribir_resumen(carpeta, datos, est_a, pend, por_nivel, corr, cruce, est_b, pend_b,
                     tabla_estab, spearman)

    print(f"Análisis guardado en {carpeta}/ (resumen.md, estadisticas_A.csv, estadisticas_B.csv, pendientes.csv)")
    print(f"Siguiente paso: python graficas.py{' --rapido' if args.rapido else ''}")


if __name__ == "__main__":
    main()
