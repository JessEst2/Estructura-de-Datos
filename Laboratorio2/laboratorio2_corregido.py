import hashlib
import json


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class MerkleTree:
    def __init__(self, transacciones: list):
        """Construye el árbol como una tupla de tuplas (niveles de abajo hacia arriba)."""
        self.transacciones = tuple(transacciones)

        if not transacciones:
            self.matriz = ()
            return

        hojas = []
        for tx in transacciones:
            if isinstance(tx, dict):
                hojas.append(sha256(json.dumps(tx, sort_keys=True)))
            else:
                hojas.append(sha256(str(tx)))

        matriz = [tuple(hojas)]

        while len(matriz[-1]) > 1:
            capa_anterior = list(matriz[-1])
            if len(capa_anterior) % 2 != 0:
                capa_anterior.append(capa_anterior[-1])  # se duplica la última

            siguiente_capa = []
            for i in range(0, len(capa_anterior), 2):
                siguiente_capa.append(sha256(capa_anterior[i] + capa_anterior[i + 1]))

            matriz.append(tuple(siguiente_capa))

        self.matriz = tuple(matriz)

    def get_root(self) -> str:
        """Hash raíz del árbol. Cadena vacía si no hay transacciones."""
        if not self.matriz:
            return ""
        return self.matriz[-1][0]

    def get_hoja(self, indice: int) -> str:
        return self.matriz[0][indice]

    def get_proof(self, indice: int) -> list:
        """Prueba de inclusión (lista de hermanos) para la hoja `indice`."""
        if not self.matriz or indice < 0 or indice >= len(self.matriz[0]):
            raise IndexError(f"Índice {indice} fuera de rango (hay {len(self.matriz[0])} hojas)")

        prueba = []
        indice_actual = indice
        for capa in self.matriz[:-1]:
            es_impar = indice_actual % 2 == 1
            if es_impar:
                indice_pareja = indice_actual - 1
            else:
                # si no hay hermano derecho, el nodo se emparejó consigo mismo
                indice_pareja = min(indice_actual + 1, len(capa) - 1)

            prueba.append({
                "posicion": "left" if es_impar else "right",
                "hash": capa[indice_pareja],
            })
            indice_actual //= 2

        return prueba

    def generar_reporte_texto(self) -> str:
        root = self.get_root()
        lineas = [f"MERKLE ROOT FINAL:\n{root}\n", "[RAÍZ]", f" |____ {root[:8]}... (HASH: {root})"]

        if len(self.matriz) > 2:
            lineas.append("\n[NODOS INTERMEDIOS]")
            for i in range(len(self.matriz) - 2, 0, -1):
                for idx, h in enumerate(self.matriz[i]):
                    lineas.append(f" |--- Nivel {i} - nodo {idx + 1}: {h[:8]}...")

        lineas.append("\n[HOJAS Y TRANSACCIONES]")
        for i, (tx, h) in enumerate(zip(self.transacciones, self.matriz[0]), 1):
            lineas.append(f" |--- T{i} ({tx})")
            lineas.append(f" │    |___ Hash H{i}: {h[:8]}... (HASH: {h})")

        return "\n".join(lineas)



class MerkleProof:
    @staticmethod
    def verificar(prueba: list, hash_objetivo: str, raiz: str) -> bool:
        """Reconstruye la raíz a partir de la hoja y sus hermanos."""
        hash_actual = hash_objetivo
        for paso in prueba:
            if paso["posicion"] == "left":
                hash_actual = sha256(paso["hash"] + hash_actual)
            else:
                hash_actual = sha256(hash_actual + paso["hash"])
        return hash_actual == raiz


if __name__ == "__main__":
    # ---------- 1. Cinco bloques de datos ----------
    banco_datos = [
        "Ana paga 150",     # T1
        "Luis paga 230",    # T2
        "Carlos paga 80",   # T3
        "Maria paga 95",    # T4
        "Pedro paga 310",   # T5  -> número impar de hojas
    ]

    print("=" * 70)
    print("1 y 2. CONSTRUCCIÓN DEL ÁRBOL Y RAÍZ")
    print("=" * 70)
    arbol = MerkleTree(banco_datos)
    reporte = arbol.generar_reporte_texto()
    print(reporte)
    raiz_original = arbol.get_root()
    print(f"\nNiveles del árbol: {[len(c) for c in arbol.matriz]}")

    # ---------- 3. Modificar una transacción ----------
    print("\n" + "=" * 70)
    print("3. EFECTO AVALANCHA: SE MODIFICA LA TRANSACCIÓN 2")
    print("=" * 70)
    datos_alterados = list(banco_datos)
    datos_alterados[1] = "Luis paga 999"
    arbol_alterado = MerkleTree(datos_alterados)

    print(f"Raíz original : {raiz_original}")
    print(f"Raíz alterada : {arbol_alterado.get_root()}")
    print(f"¿Son iguales? : {raiz_original == arbol_alterado.get_root()}  -> la raíz detecta el cambio")

    # ---------- 4. Prueba de inclusión de la transacción 3 ----------
    print("\n" + "=" * 70)
    print("4. PRUEBA DE INCLUSIÓN DE LA TRANSACCIÓN 3 ('Carlos paga 80')")
    print("=" * 70)
    indice = 2  # bloque 3 = índice 2
    prueba = arbol.get_proof(indice)
    hoja = arbol.get_hoja(indice)

    print(f"Hash de la hoja: {hoja}")
    for n, paso in enumerate(prueba, 1):
        print(f"  Paso {n}: hermano a la {paso['posicion']:>5} -> {paso['hash'][:16]}...")

    valido = MerkleProof.verificar(prueba, hoja, raiz_original)
    print(f"\n¿Prueba válida? {valido}")

    # ---------- 5. Verificación con un dato incorrecto ----------
    print("\n" + "=" * 70)
    print("5. VERIFICACIÓN CON UN DATO FALSO")
    print("=" * 70)
    hoja_falsa = sha256("Carlos paga 8000")
    valido_falso = MerkleProof.verificar(prueba, hoja_falsa, raiz_original)
    print(f"Hash falso: {hoja_falsa}")
    print(f"¿Prueba válida? {valido_falso}  -> rechazada correctamente")

    # Prueba extra: verifica que la duplicación de la transacción impar si se haga
    print("\n[EXTRA] Verificación de la transacción 5 (hoja impar duplicada):")
    p5 = arbol.get_proof(4)
    print(f"  ¿Prueba válida? {MerkleProof.verificar(p5, arbol.get_hoja(4), raiz_original)}")
