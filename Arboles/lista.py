"""Tienes un archivo con 10,000 estudiantes (nombre, edad, promedio). Necesitas implementar un sistema que permita:

Buscar un estudiante por su ID (número de matrícula)
Insertar nuevos estudiantes
Listar todos los estudiantes en orden por ID"""
import time
import random
from faker import Faker
def generar_estudiantes():
    fake = Faker()
    estudiantes = []

    for i in range(1, 10001):
        estudiante = {
            "id": i,
            "nombre": fake.first_name(),
            "promedio": round(random.uniform(0, 10), 1)
        }
        estudiantes.append(estudiante)

    return estudiantes


def buscar_estudiante(estudiantes):
    id_buscada = int(input("Ingrese el ID del estudiante a buscar: "))

    for estudiante in estudiantes:
        if estudiante["id"] == id_buscada:
            print(f'ID: {estudiante["id"]} | Nombre: {estudiante["nombre"]} | Promedio: {estudiante["promedio"]}')
            return

    print("Estudiante no encontrado")


def insertar_estudiante(estudiantes):
    id_est = len(estudiantes) + 1
    nombre = input("Ingrese nombre: ")
    promedio = float(input("Ingrese promedio: "))

    estudiantes.append({
        "id": id_est,
        "nombre": nombre,
        "promedio": promedio
    })


def listar_estudiantes(lista):
    for estudiante in lista:
        print(estudiante)


# generar los 10000 estudiantes
estudiantes = generar_estudiantes()


while True:

    print("\n--- MENU ---")
    print("1. Buscar estudiante")
    print("2. Insertar estudiante")
    print("3. Listar estudiantes")
    print("4. Salir")

    opcion = input("Seleccione una opción: ")

    if opcion == "1":
        buscar_estudiante(estudiantes)

    elif opcion == "2":
        insertar_estudiante(estudiantes)

    elif opcion == "3":
        listar_estudiantes(estudiantes)

    elif opcion == "4":
        print("Ha salido.")
        break

    else:
        print("Opción inválida")

#Tiempo de lista

def medir_busquedas(estudiantes):

    ids_aleatorios = random.sample(range(1, len(estudiantes)+1), 100)

    inicio = time.time()

    for id_buscado in ids_aleatorios:

        for estudiante in estudiantes:
            if estudiante["id"] == id_buscado:
                break

    fin = time.time()

    print("Tiempo para 100 búsquedas:", fin - inicio, "segundos")

medir_busquedas(estudiantes)
