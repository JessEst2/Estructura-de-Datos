# Árbol de Merkle

Implementación de un árbol de Merkle con SHA-256, pruebas de inclusión y dibujo del árbol en ASCII.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `laboratorio2_corregido.py` | El árbol, las pruebas de inclusión y el experimento completo |

## Cómo ejecutarlo

```bash
python3 laboratorio2_corregido.py
```

No necesita instalar nada: solo usa `hashlib` y `json`, que vienen con Python.

## Qué hace

1. Crea 5 transacciones de ejemplo y construye el árbol.
2. Muestra la raíz (Merkle Root) y guarda un reporte en `mi_arbol.txt`.
3. Modifica una transacción y muestra que la raíz cambia por completo.
4. Genera la prueba de inclusión de la transacción 3 y la verifica → `True`.
5. Intenta verificar con un dato falso → `False`.

## Cómo funciona el árbol

- Cada **hoja** es el SHA-256 de un bloque de datos.
- Cada **nodo interno** es el SHA-256 de los hashes de sus dos hijos, pegados uno tras otro.
- Si un nivel tiene un número impar de nodos, el último se **duplica** para poder emparejarlo.
- Arriba del todo queda un solo hash: la **raíz**, que representa todos los datos. Si cambia un solo carácter de una transacción, la raíz cambia.

## Uso básico

```python
from laboratorio2_corregido import MerkleTree, MerkleProof

arbol = MerkleTree(["Ana paga 150", "Luis paga 230", "Carlos paga 80"])

print(arbol.get_root())        # hash raíz
prueba = arbol.get_proof(2)    # prueba de la transacción 3 (índice 2)
hoja = arbol.get_hoja(2)       # hash de esa transacción

MerkleProof.verificar(prueba, hoja, arbol.get_root())   # True
```

La lista puede contener textos o diccionarios. Los diccionarios se serializan con las claves ordenadas, así que el orden en que los escribas no afecta el hash.

## Notas
- `get_proof()` lanza `IndexError` si le pasas un índice que no existe.
- Se utilizo Claude Opus 5 Alto para hacer las verificaciones del código y funcione para todos los posibles escenarios existentes.
