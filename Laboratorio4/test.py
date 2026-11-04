import random

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle

from QuadTree import (LADO_CIUDAD, RADIO_BUSQUEDA, construir_quadtree, generar_ciudad,
                      nn_fuerza_bruta, radio_fuerza_bruta)

N = 10000
SEMILLA = 42

def verificar(qt, puntos, n_consultas = 1000):
    # en esta funcion verifico que el quadtree si de lo mismo que la fuerza brota, sino, no me sirve 
    rnd = random.Random(SEMILLA +1)
    for _ in range(n_consultas):
        x = rnd.uniform(0, LADO_CIUDAD)
        y = rnd.uniform(0, LADO_CIUDAD)

        ids_qt = sorted(p.id for p in qt.query_radius(x,y))
        ids_fb = sorted(p.id for p in qt.radio_fuerza_bruta(puntos,x,y))
        assert ids_qt == ids_fb, f"radio distinto en ({x:.1f},{y:.1f})"

        _, d_qt = qt.nearest_neighbor(x,y)
        _, d_fb = nn_fuerza_bruta(puntos,x,y)
        #comparo las distancias
        assert abs(d_qt - d_fb)<1e-9, f"vecino distinto en({x:.1f},{y:.1f})"
    print(f"verificación ok {n_consultas} consultas de radio y de vecino mas cercano iguales a fuerza bruta")

    def dibujar_grilla(ax, qt):
        # cada hoja es un rectangulo; juntamos todos los bordes en una sola LineCollection (mucho mas rapido)
        segmentos = []
        for hoja in qt.hojas():
            b = hoja.bbox
            segmentos += [
                [(b.x_min, b.y_min), (b.x_max, b.y_min)],
                [(b.x_max, b.y_min), (b.x_max, b.y_max)],
                [(b.x_max, b.y_max), (b.x_min, b.y_max)],
                [(b.x_min, b.y_max), (b.x_min, b.y_min)],
            ]
        ax.add_collection(LineCollection(segmentos, colors="lightsteelblue", linewidths=0.4))


    def base(ax, qt, puntos, titulo):
        dibujar_grilla(ax, qt)
        ax.scatter([p.x for p in puntos], [p.y for p in puntos], s=1, c="dimgray", label="Puntos de entrega")
        ax.set_xlim(0, LADO_CIUDAD)
        ax.set_ylim(0, LADO_CIUDAD)
        ax.set_aspect("equal")
        ax.set_title(titulo)
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")


    def grafica_radio(qt, puntos, x, y):
        vecinos = qt.query_radius(x, y, RADIO_BUSQUEDA)
        fig, ax = plt.subplots(figsize=(9, 9))
        base(ax, qt, puntos, f"Quadtree con {len(puntos)} puntos: búsqueda en radio de {RADIO_BUSQUEDA} m")
        ax.add_patch(Circle((x, y), RADIO_BUSQUEDA, fill=False, edgecolor="red", linewidth=1.5))
        ax.scatter([p.x for p in vecinos], [p.y for p in vecinos], s=3, c="red",
                label=f"Dentro del radio ({len(vecinos)})")
        ax.scatter([x], [y], marker="x", s=80, c="black", label="Centro de la búsqueda")
        ax.legend(loc="upper right")
        fig.tight_layout()
        fig.savefig("grafica_radio.png", dpi=150)
        print(f"grafica_radio.png: {len(vecinos)} puntos dentro de {RADIO_BUSQUEDA} m de ({x:.0f}, {y:.0f})")


    def grafica_vecino(qt, puntos, x, y):
        vecino, dist = qt.nearest_neighbor(x, y)
        fig, ax = plt.subplots(figsize=(9, 9))
        base(ax, qt, puntos, f"Quadtree con {len(puntos)} puntos: vecino más cercano")
        ax.plot([x, vecino.x], [y, vecino.y], c="red", linewidth=1)
        ax.scatter([vecino.x], [vecino.y], s=40, c="red", label=f"Vecino más cercano ({dist:.1f} m)")
        ax.scatter([x], [y], marker="x", s=80, c="black", label="Punto X")
        ax.legend(loc="upper right")

        # un recuadro con zoom, porque a escala de toda la ciudad no se ve la linea
        zoom = ax.inset_axes([0.02, 0.02, 0.35, 0.35])
        m = max(dist * 3, 150)
        dibujar_grilla(zoom, qt)
        zoom.scatter([p.x for p in puntos], [p.y for p in puntos], s=6, c="dimgray")
        zoom.plot([x, vecino.x], [y, vecino.y], c="red")
        zoom.scatter([vecino.x], [vecino.y], s=40, c="red")
        zoom.scatter([x], [y], marker="x", s=80, c="black")
        zoom.set_xlim(x - m, x + m)
        zoom.set_ylim(y - m, y + m)
        zoom.set_aspect("equal")
        zoom.set_xticks([])
        zoom.set_yticks([])
        zoom.set_title("zoom", fontsize=8)

        fig.tight_layout()
        fig.savefig("grafica_vecino.png", dpi=150)
        print(f"grafica_vecino.png: vecino de ({x:.0f}, {y:.0f}) es el punto {vecino.id}, a {dist:.1f} m")


    if __name__ == "__main__":
        puntos = generar_ciudad(N, semilla=SEMILLA)
        qt = construir_quadtree(puntos)
        print(f"{qt.cantidad} puntos | {qt.contar_nodos()} nodos | altura {qt.altura()}")

        verificar(qt, puntos)

        # centro de la busqueda: un punto cualquiera de la ciudad (fijo para que la grafica sea reproducible)
        rnd = random.Random(SEMILLA)
        x, y = rnd.uniform(2000, 8000), rnd.uniform(2000, 8000)
        grafica_radio(qt, puntos, x, y)
        grafica_vecino(qt, puntos, x + 1234.5, y - 987.6)

        plt.show()