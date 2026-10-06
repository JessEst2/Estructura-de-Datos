"""Tienes un archivo con 10,000 estudiantes (nombre, edad, promedio). Necesitas implementar un sistema que permita:

Buscar un estudiante por su ID (número de matrícula)
Insertar nuevos estudiantes
Listar todos los estudiantes en orden por ID"""
import time
import random

NOMBRES = [
    "Ana", "Luis", "María", "Carlos", "Sofía", "Andrés", "Valentina", "Juan",
    "Camila", "Daniel", "Laura", "Santiago", "Isabella", "Mateo", "Gabriela",
    "Sebastián", "Daniela", "Nicolás", "Mariana", "Felipe", "Paula", "Diego",
    "Natalia", "Alejandro", "Sara", "Tomás", "Juliana", "David", "Lucía", "Samuel",
]


def generar_estudiantes(n=10000, orden="ordenado", semilla=None):
    """
    Crea una lista de n estudiantes.

    n:       cuántos estudiantes crear.
    orden:   "ordenado"  -> IDs en orden creciente: 1, 2, 3, ..., n
             "aleatorio" -> los mismos IDs 1..n, pero revueltos
    semilla: si se da un número, se generan siempre los mismos datos
             (necesario para que el experimento sea reproducible).
    """
    if orden not in ("ordenado", "aleatorio"):
        raise ValueError('orden debe ser "ordenado" o "aleatorio"')

    rnd = random.Random(semilla)  # generador de azar propio, no afecta al resto del programa

    ids = list(range(1, n + 1))
    if orden == "aleatorio":
        rnd.shuffle(ids)

    estudiantes = []
    for id_est in ids:
        estudiantes.append({
            "id": id_est,
            "nombre": rnd.choice(NOMBRES),
            "edad": rnd.randint(16, 30),
            "promedio": round(rnd.uniform(0, 10), 1),
        })
    return estudiantes


def buscar_estudiante(estudiantes):
    id_buscada = int(input("Ingrese el ID del estudiante a buscar: "))

    for estudiante in estudiantes:
        if estudiante["id"] == id_buscada:
            print(f'ID: {estudiante["id"]} | Nombre: {estudiante["nombre"]} | Edad: {estudiante["edad"]} | Promedio: {estudiante["promedio"]}')
            return

    print("Estudiante no encontrado")


def insertar_estudiante(estudiantes):
    id_est = len(estudiantes) + 1
    nombre = input("Ingrese nombre: ")
    edad = int(input("Ingrese edad: "))
    promedio = float(input("Ingrese promedio: "))

    estudiantes.append({
        "id": id_est,
        "nombre": nombre,
        "edad": edad,
        "promedio": promedio
    })


def listar_estudiantes(lista):
    for estudiante in lista:
        print(estudiante)


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


if __name__ == "__main__":
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

    medir_busquedas(estudiantes)