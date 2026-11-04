import math 
import random
# Unidades en metros
LADO_CIUDAD = 10000
RADIO_BUSQUEDA = 500

class Punto: 
    def __init__(self, x, y, id = None):
        self.x = x
        self.y = y
        self.id = id

    def __repr__(self):
        return f"Punto({self.id}: {self.x:.1f},{self.y:1f})"


class Rectangulo:
    # Se guardan las esquinas
    def __init__(self, x_min, y_min, x_max, y_max):
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max

    def contiene(self, p):
        # si hay un punto justo en la linea entre dos hijos lo toma el primero que lo acepte
        return self.x_min <= p.x <= self.x_max and self.y_min <= p.y <= self.y_max

    def distancia(self, x, y):
        #distancia real en metros solo si se necesita porque calcular la raiz es caro
        return math.sqrt(self.distancia2(x,y))

    def distancia2(self, x, y):
        # distancia al cuadrado del punto (x,y) al rectangulo
        # (px,py) es el punto del rectangulo más cercano a (x,y)
        px = max(self.x_min, min(x, self.x_max))
        py = max(self.y_min, min(y, self.y_max))
        return (x-px)**2 + (y-py)**2

    def intersecta_circulo(self, x, y, r):
        return self.distancia2(x,y)<= r*r

class Quadtree:
    MAX_PROFUNDIDAD = 20 # Por si hay muchos repetidos, que no divida infinito

    def __init__(self,bbox,capacidad=8,profundidad=0):
        self.bbox = bbox
        self.capacidad = capacidad
        self.profundidad = profundidad
        self.puntos = []#solo las hojas guardan puntos
        self.dividido = False
        self.nw = self.ne = self.sw = self.se = None 
        self.cantidad = 0 # puntos en este nodo y sus hijos

    def hijos(self):
        return(self.nw, self.ne, self.sw, self.se)

    def subdividir(self):
        b = self.bbox
        mx = (b.x_min + b.x_max)/ 2
        my = (b.y_min + b.y_max) / 2
        prof = self.profundidad + 1
        self.nw = Quadtree(Rectangulo(b.x_min, my, mx, b.y_max),self.capacidad, prof)
        self.ne = Quadtree(Rectangulo(mx, my, b.x_max, b.y_max),self.capacidad, prof)
        self.sw = Quadtree(Rectangulo(b.x_min,b.y_min,mx,my),self.capacidad, prof)
        self.ne = Quadtree(Rectangulo(mx,b.y_min,b.x_max,my),self.capacidad, prof)
        self.dividido = True


        # los puntos que tenia esta hoja bajan a los hijos 

        viejos = self.puntos
        self.puntos = []
        for p in viejos:
            for h in self.hijos():
                if h.insertar(p):
                    break

    def insertar(self,p):
        if not self.bbox.contiene(p):
            return False
        if not self.dividido:
            if len(self.puntos)<self.capacidad or self.profundidad >= self.MAX_PROFUNDIDAD:
                self.puntos.append(p)
                self.cantidad +=1
                return True
            self.subdividir()

        for h in self.hijos():
            if h.insertar(p):
                self.cantidad +=1
                return True

        # se supone que no deberia pasar: si el papá lo contiene, algun lo contiene 
        return False

    def query_radius(self, x, y, r=RADIO_BUSQUEDA, encontrados = None):
        if encontrados is None:
                encontrados=[]

        # si el circulo no toca esa zona, se descarta
        if not self.bbox.intersecta_circulo(x,y,r):
            return encontrados

        if self.dividido:
            for h in self.hijos():
                h.query_radius(x,y,r,encontrados)
        else:
            r2 = r*r
            for p in self.puntos:
                dx =  p.x-x
                dy = p.y - y
                if dx * dx + dy * dy <= r2:
                    encontrados.append(p)
        return encontrados

    def nearest_neighbor(self,x,y):
        # mejor = [punto,distacia al cuadrado]; esta es la lista que se modifica en la recursion
        mejor = [None, float("inf")]
        self._nn(x,y,mejor)
        if mejor[0] is None:
            return None,None
        return mejor[0], math.sqrt(mejor[1])

    def _nn(self,x,y,mejor):
        #poda: si hasta el punto mas cercano de esta zona mas lejos que el mejor, no sirve 
        if self.bbox.distancia2(x,y)>=mejor[1]:
            return

        if not self.dividido:
            for p in self.puntos:
                dx = p.x - x
                dy = p.y - y
                d2 = dx * dx + dy * dy 
                if d2 < mejor[1]:
                    mejor[0] = p
                    mejor[1] = d2
            return

        # visito primero los hijos mas cercanos, asi lapoda corta antes
        orden = sorted(self.hijos(), key=lambda h: h.bbox.distancia2(x,y))
        for h in orden:
            h._nn(x,y,mejor)

    # --- cosas para graficar y para el analisis ---

    def hojas(self):
        if not self.dividido:
            yield self
        else:
            for h in self.hijos():
                yield from h.hojas()

    def contar_nodos(self):
        if not self.dividido:
            return 1
        return 1 + sum(h.contar_nodos() for h in self.hijos())

    def altura(self):
        if not self.dividido:
            return 1
        return 1 + max(h.altura() for h in self.hijos())


def construir_quadtree(puntos, capacidad=8):
    qt = Quadtree(Rectangulo(0, 0, LADO_CIUDAD, LADO_CIUDAD), capacidad)
    for p in puntos:
        qt.insertar(p)
    return qt

# fuerza bruta para comparar#
# se utiliza la misma formula de (dx*dx en vex de **2) que usa el quadtree en las hojas,para que la comparación sea justa:
# en python dx*dx es bastante mas rapido que d**2

def radio_fuerza_bruta(puntos,x,y,r=RADIO_BUSQUEDA):
    r2 = r*r
    return[p for p in puntos if (p.x-x)*(p.x-x)+(p.y-y)*(p.y-y)<= r2]

def nn_fuerza_bruta(puntos,x,y):
    mejor = None
    mejor_d2 = float("inf")
    for p in puntos:
        dx = p.x - x
        dy = p.y - y
        d2 = dx*dx + dy*dy
        if d2 < mejor_d2:
            mejor = p
            mejor_d2 = d2
    if mejor is None:
        return None,None
    return mejor, math.sqrt(mejor_d2)

# --- generador de la "ciudad" ---

def generar_ciudad(n, semilla=None, n_barrios=8, fraccion_dispersa=0.3):
    # una ciudad no es uniforme: hay barrios densos y el resto disperso.
    # fraccion_dispersa de los puntos va uniforme por toda la ciudad, el resto en barrios (gaussianas)
    rnd = random.Random(semilla)
    barrios = []
    for _ in range(n_barrios):
        cx = rnd.uniform(1500, LADO_CIUDAD - 1500)
        cy = rnd.uniform(1500, LADO_CIUDAD - 1500)
        sigma = rnd.uniform(300, 1200)
        barrios.append((cx, cy, sigma))

    puntos = []
    for i in range(n):
        if rnd.random() < fraccion_dispersa:
            x = rnd.uniform(0, LADO_CIUDAD)
            y = rnd.uniform(0, LADO_CIUDAD)
        else:
            cx, cy, sigma = rnd.choice(barrios)
            x = rnd.gauss(cx, sigma)
            y = rnd.gauss(cy, sigma)
            # si se sale de la ciudad lo pegamos al borde
            x = min(max(x, 0), LADO_CIUDAD)
            y = min(max(y, 0), LADO_CIUDAD)
        puntos.append(Punto(x, y, i))
    return puntos


