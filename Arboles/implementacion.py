"""
Sistema de estudiantes usando un árbol B+.

Toma la lista `estudiantes` generada en lista.py y la guarda en un árbol B+
cuya clave es el ID (matrícula) y cuyo valor es el diccionario del estudiante.
"""
import random
import time

import ABB
from arbolbplus import BPlusTree
from lista import generar_estudiantes

ORDEN = 32  # máximo de hijos por nodo (en bases de datos reales suele ser mucho mayor)


def construir_arbol(estudiantes, orden=ORDEN):
    arbol = BPlusTree(orden)
    for estudiante in estudiantes:
        arbol.insertar(estudiante["id"], estudiante)
    return arbol


def mostrar(estudiante):
    print(f'ID: {estudiante["id"]} | Nombre: {estudiante["nombre"]} | Promedio: {estudiante["promedio"]}')


def pedir_entero(mensaje):
    while True:
        try:
            return int(input(mensaje))
        except ValueError:
            print("Debe ser un número entero.")


def pedir_promedio(mensaje):
    while True:
        try:
            promedio = float(input(mensaje))
            if 0 <= promedio <= 10:
                return promedio
            print("El promedio debe estar entre 0 y 10.")
        except ValueError:
            print("Debe ser un número (por ejemplo 7.5).")


def buscar_estudiante(arbol):
    id_buscado = pedir_entero("Ingrese el ID del estudiante a buscar: ")
    estudiante = arbol.buscar(id_buscado)
    if estudiante is None:
        print("Estudiante no encontrado")
    else:
        mostrar(estudiante)


def insertar_estudiante(arbol, estudiantes):
    nuevo_id = (arbol.clave_maxima() or 0) + 1
    nombre = input("Ingrese nombre: ").strip()
    promedio = pedir_promedio("Ingrese promedio: ")
    estudiante = {"id": nuevo_id, "nombre": nombre, "promedio": promedio}
    arbol.insertar(nuevo_id, estudiante)
    estudiantes.append(estudiante)  # la lista también se mantiene al día
    print(f"Estudiante insertado con ID {nuevo_id}")


def listar_estudiantes(arbol):
    for _, estudiante in arbol.recorrer():  # ya salen ordenados por ID
        mostrar(estudiante)


def medir(nombre, buscar, ids):
    inicio = time.perf_counter()
    for i in ids:
        buscar(i)
    print(f"{nombre:<30} {time.perf_counter() - inicio:.6f} s")


def buscar_en_lista(lista, id_buscado):
    for estudiante in lista:
        if estudiante["id"] == id_buscado:
            return estudiante


def comparar_tiempos(estudiantes):
    ordenados = sorted(estudiantes, key=lambda e: e["id"])
    revueltos = random.sample(ordenados, len(ordenados))
    ids = random.sample([e["id"] for e in ordenados], 100)

    for titulo, datos in (("DATOS EN ORDEN", ordenados), ("DATOS REVUELTOS", revueltos)):
        abb = ABB.construir_abb(datos)
        arbol = construir_arbol(datos)
        print(f"\n{titulo} (100 búsquedas)")
        medir("Lista", lambda i: buscar_en_lista(datos, i), ids)
        medir("ABB", lambda i: ABB.buscar_abb(abb, i), ids)
        medir("Árbol B+", arbol.buscar, ids)


def main():
    estudiantes = generar_estudiantes()
    arbol = construir_arbol(estudiantes)

    while True:
        print("\n--- MENU (Árbol B+) ---")
        print("1. Buscar estudiante")
        print("2. Insertar estudiante")
        print("3. Listar estudiantes")
        print("4. Comparar tiempos (lista, ABB y árbol B+)")
        print("5. Salir")

        opcion = input("Seleccione una opción: ").strip()

        if opcion == "1":
            buscar_estudiante(arbol)
        elif opcion == "2":
            insertar_estudiante(arbol, estudiantes)
        elif opcion == "3":
            listar_estudiantes(arbol)
        elif opcion == "4":
            comparar_tiempos(estudiantes)
        elif opcion == "5":
            print("Ha salido.")
            break
        else:
            print("Opción inválida")


if __name__ == "__main__":
    main()