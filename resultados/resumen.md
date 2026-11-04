# Resumen del benchmark (generado por analisis.py)

- N medidos: 105 valores, de 10 a 10000
- Repeticiones por N: 5 (ciudad distinta en cada una)
- Ventana mínima por medición: 0.3 s
- Radio de búsqueda: 500 m en una ciudad de 10000 m × 10000 m
- Duración total: 15.1 min

## ¿Desde qué N gana el quadtree?

Criterio: el quadtree es más rápido con los intervalos de confianza del 95 % separados, y lo sigue siendo para todos los N mayores.

| Consulta | Quadtree gana desde N = | N donde gana la fuerza bruta | N empatados (IC se tocan) |
|---|---|---|---|
| Radio 500 m | 70 | 10, 20, 30 | 50 |
| Vecino más cercano | 200 | 10, 20, 30, 50, 70, 100 | ninguno |

## Pendientes log-log (tiempo ∝ N^k), N ≥ 100

| Curva | k | R² |
|---|---|---|
| Quadtree radio | 0.514 | 0.985 |
| Fuerza bruta radio | 1.003 | 1.000 |
| Quadtree vecino | 0.145 | 0.967 |
| Fuerza bruta vecino | 0.997 | 1.000 |
| Construir quadtree | 1.126 | 1.000 |
| Vecinos devueltos (k) | 1.002 | 1.000 |

## Tabla por N (µs por consulta; construir en ms)

| N | Altura | Vecinos en radio | Construir (ms) | QT radio | FB radio | QT vecino | FB vecino | Consultas de radio para compensar construir | Consultas de vecino para compensar |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 2.0 | 0.1 | 0.01 | 2.69 ± 0.06 | 1.17 ± 0.03 | 4.78 ± 0.05 | 1.12 ± 0.02 | nunca | nunca |
| 20 | 2.4 | 0.1 | 0.02 | 3.14 ± 0.22 | 2.20 ± 0.04 | 5.58 ± 0.72 | 1.95 ± 0.02 | nunca | nunca |
| 30 | 3.0 | 0.2 | 0.04 | 3.61 ± 0.05 | 3.16 ± 0.10 | 6.39 ± 0.10 | 2.76 ± 0.12 | nunca | nunca |
| 50 | 3.4 | 0.4 | 0.08 | 4.85 ± 0.42 | 5.17 ± 0.14 | 9.14 ± 1.10 | 4.42 ± 0.06 | 258 | nunca |
| 70 | 4.2 | 0.6 | 0.12 | 5.49 ± 0.23 | 7.20 ± 0.21 | 10.05 ± 0.44 | 6.05 ± 0.03 | 72 | nunca |
| 100 | 4.8 | 0.8 | 0.19 | 6.15 ± 0.08 | 10.11 ± 0.22 | 11.15 ± 0.59 | 8.51 ± 0.12 | 49 | nunca |
| 200 | 5.6 | 1.6 | 0.45 | 7.95 ± 0.27 | 20.11 ± 0.89 | 13.09 ± 0.58 | 16.47 ± 0.15 | 37 | 133 |
| 300 | 6.0 | 2.4 | 0.71 | 8.96 ± 0.25 | 30.15 ± 0.36 | 13.59 ± 0.61 | 25.04 ± 0.80 | 34 | 63 |
| 500 | 6.2 | 4.0 | 1.26 | 10.87 ± 0.25 | 50.25 ± 0.74 | 14.98 ± 0.43 | 41.35 ± 0.78 | 32 | 48 |
| 1000 | 7.4 | 7.9 | 2.78 | 14.56 ± 0.40 | 98.14 ± 1.14 | 16.55 ± 0.53 | 81.59 ± 0.62 | 34 | 43 |
| 2000 | 7.8 | 16.0 | 6.11 | 20.40 ± 0.30 | 199.68 ± 1.60 | 18.51 ± 0.29 | 164.78 ± 1.79 | 35 | 42 |
| 3000 | 8.2 | 24.2 | 9.60 | 25.19 ± 0.22 | 300.65 ± 3.19 | 19.49 ± 0.33 | 245.39 ± 2.04 | 35 | 43 |
| 5000 | 8.4 | 40.3 | 17.00 | 33.82 ± 0.62 | 503.74 ± 11.95 | 21.00 ± 0.49 | 406.42 ± 2.78 | 37 | 45 |
| 7000 | 9.0 | 56.3 | 24.77 | 41.72 ± 0.63 | 707.84 ± 9.81 | 21.71 ± 0.26 | 570.98 ± 8.01 | 38 | 46 |
| 10000 | 9.0 | 80.2 | 37.04 | 52.95 ± 0.57 | 1018.74 ± 17.45 | 22.90 ± 0.27 | 835.64 ± 21.90 | 39 | 46 |

(± = desviación estándar entre repeticiones. La tabla completa está en `estadisticas.csv`.)

## Ruido

CV de las consultas: mediana 1.6 %, máximo 25.1 %.

| Parte del experimento | Minutos | Mediana del tiempo relativo |
|---|---|---|
| 1.º cuarto | 0.0 – 3.8 | 1.000 |
| 2.º cuarto | 3.8 – 7.5 | 1.000 |
| 3.º cuarto | 7.5 – 11.3 | 1.000 |
| 4.º cuarto | 11.3 – 15.1 | 1.000 |
