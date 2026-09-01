# Matriz binaria de 100.000 × 100.000 bits en disco

**Estudiante:** JESICA ALEJANDRA ESTOR SOTO
**CC** 1082890547
**Laboratorio:** Laboratorio 1

---

## 1. El problema

Construir y consultar una matriz de 100.000 × 100.000 celdas binarias
(10.000 millones de bits) sin cargarla nunca completa en memoria RAM, y poder
verificar que el contenido quedó correctamente almacenado.

Guardar cada celda en un byte ocuparía 10 GB de RAM y de disco, algo inviable en
un computador normal. La solución que implementa este repositorio combina dos
técnicas: empaquetado de bits (8 celdas por byte, reduce el tamaño a 1,25 GB)
y memoria mapeada a disco (`np.memmap`, mantiene el uso de RAM en unos pocos MB).

---

## 2. Contenido del repositorio

| Archivo | Qué es | Descripción |
|---|---|---|
| lab1.py | Código fuente principal | Todo el programa: creación de la matriz, funciones de lectura y funciones de verificación. Está documentado internamente con docstrings y comentarios que explican cada decisión. |
| matriz.bin | Dato generado (no versionado) | Archivo binario de ~1,25 GB que produce el programa. **No se sube al repositorio** por su tamaño; se regenera ejecutando `lab1.py`. |


## 3. Cómo funciona: el empaquetado de bits

Un byte tiene 8 bits, así que en cada byte caben 8 celdas de la matriz. Cada fila
de 100.000 bits ocupa entonces `100.000 / 8 = 12.500` bytes, y el archivo completo:

```
100.000 filas × 12.500 bytes = 1.250.000.000 bytes ≈ 1,25 GB
```

Ocho veces menos que la versión sin empaquetar. Por eso en el código
`BYTES_FILA = N // 8`.

La consecuencia importante es que **en disco la matriz no tiene 100.000 columnas,
sino 12.500 columnas de bytes**. Para acceder a la columna lógica hay que traducir:

```python
byte_que_lo_contiene = columna // 8       # en qué byte está
posicion_del_bit     = 7 - (columna % 8)  # en qué bit dentro del byte
```

El `7 - ...` corresponde al orden **big-endian**: el bit más significativo del byte
(el de la izquierda, valor 128) es la primera columna del grupo de 8. Ejemplo con
el byte `0b10110010`:

| columna  | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|----------|---|---|---|---|---|---|---|---|
| bit      | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 0 |
| posición | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |

Es el mismo convenio que usa `np.unpackbits` por defecto, lo que permite leer una
fila entera de golpe y obtener exactamente los mismos valores que leyendo bit a bit.
