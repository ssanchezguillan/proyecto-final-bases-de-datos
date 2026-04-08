import pymysql
import matplotlib.pyplot as plt
from pymongo import MongoClient
from collections import Counter
from wordcloud import WordCloud
from configuracion import *

#nos conectamos a MySQL 
mysql_conexion = pymysql.connect(
    host=SQL_HOST,
    user=SQL_USER,
    password=SQL_PASSWORD,
    database=SQL_DB
)

cursor = mysql_conexion.cursor()

#nos conectamos a MongoDB
mongo_cliente = MongoClient(MONGO_URL)
mongo_db = mongo_cliente[MONGO_DB]
collection = mongo_db[MONGO_COLLECTION]


def evolucion_reviews_por_anio() -> None:
    """
    Mostramos el número de reviews por año en forma de 
    histograma
    """

    categoria = input("Introduce una categoría o (o 'todo'): ")

    if categoria == 'todo':
        query = """
        SELECT YEAR(reviewTime), COUNT(*)
        FROM reviews
        GROUP BY YEAR(reviewTime)
        """
        cursor.execute(query)

    else:
        query = """
        SELECT YEAR(r.reviewTime), COUNT(*)
        FROM reviews r
        JOIN productos p ON r.asin = p.asin
        WHERE p.categoria = %s
        GROUP BY YEAR(r.reviewTime)
        """
        cursor.execute(query, (categoria,))

    datos = cursor.fetchall()

    anios = [x[0] for x in datos]
    counts = [x[1] for x in datos]

    if categoria == 'todo':
        color = 'blue'
        titulo = 'Evolución de reviews por año (todas las categorías)'
    else:
        color = 'orange'
        titulo = f'Evolución de reviews por año ({categoria})'

    plt.bar(anios, counts, color=color)
    plt.title(titulo)

    plt.xlabel('Años')
    plt.ylabel('Número de reviews')
    plt.show()


def popularidad_articulos() -> None:
    """
    Mostramos la popularidad de artículos según número 
    de reviews
    """

    query = """
    SELECT asin, COUNT(*) as total
    FROM reviews
    GROUP BY asin
    ORDER BY total DESC
    LIMIT 100
    """

    cursor.execute(query)
    datos = cursor.fetchall()

    valores = [x[1] for x in datos]

    plt.plot(valores)
    plt.title('Evolución de popularidad de artículos')
    plt.xlabel('Artículos')
    plt.ylabel('Número de reviews')
    plt.show()


def histograma_notas() -> None:
    """
    Mostramos histogramas de notas (overall)
    """

    cursor.execute('SELECT overall FROM reviews')
    datos = cursor.fetchall()

    notas = [x[0] for x in datos]

    #definimos los valores posibles (notas de 1 a 5)
    valores = [1, 2, 3, 4, 5]

    #calculamos frecuencias manualmente
    frecuencias = []
    for v in valores:
        frecuencias.append(notas.count(v))

    #dibujamos gráfico
    plt.bar(valores, frecuencias)
    plt.xticks(valores)
    plt.title('Reviews por nota de todos los productos')
    plt.xlabel('Nota')
    plt.ylabel('Número de reviews')
    plt.show()


def evolucion_reviews_tiempo() -> None:
    """
    Mostramos evolución acumulada de reviews en
    el tiempo
    """
    cursor.execute("""
    SELECT unixReviewTime FROM reviews ORDER BY unixReviewTime
    """)

    datos = cursor.fetchall()

    tiempos = [x[0] for x in datos]
    acumulado = list(range(1,len(tiempos)+1))

    plt.plot(tiempos, acumulado)
    plt.title('Evolución de reviews a lo largo del tiempo de todos los productos')
    plt.xlabel('Tiempo')
    plt.ylabel('Número de reviews hasta ese momento')
    plt.show()


def histograma_reviews_usuario() -> None:
    """
    Mostramos número de reviews por usuario.
    """

    cursor.execute("""
    SELECT reviewerID, COUNT(*)
    FROM reviews
    GROUP BY reviewerID
    """)

    datos = cursor.fetchall()

    valores = [x[1] for x in datos]

    plt.hist(valores, bins=50)
    plt.title('Reviews por usuario')
    plt.xlabel('Número de reviews')
    plt.ylabel('Número de usuarios')
    plt.show()


def nube_palabras() -> None:
    """
    Generamos nube de palabras usando MongoDB.
    """
    palabras = []

    for doc in collection.find({}, {'summary': 1}):
        texto = doc.get('summary', '')
        palabras.extend(texto.split())

    #filtramos palabras cortas
    palabras = [p for p in palabras if len(p) > 3]

    texto_final = " ".join(palabras)

    wc = WordCloud(width=800, height=400).generate(texto_final)

    plt.imshow(wc)
    plt.axis('off')
    plt.title('Nube de palabras')
    plt.show()


def grafica_extra() -> None:
    """
    Mostramos los usuarios más activos.
    """

    cursor.execute("""
    SELECT reviewerID, COUNT(*) as total
    FROM reviews
    GROUP BY reviewerID
    ORDER BY total DESC
    LIMIT 20
    """)

    datos = cursor.fetchall()

    valores = [x[1] for x in datos]

    plt.bar(range(len(valores)), valores)
    plt.title('Top usuarios más activos')
    plt.xlabel('Usuarios')
    plt.ylabel('Número de reviews')
    plt.show()


def menu() -> None:
    """
    Menú interactivo.
    """

    while True:
        print("\n--- MENÚ ---")
        print("1. Evolución reviews por año")
        print("2. Popularidad artículos")
        print("3. Histograma notas")
        print("4. Evolución en el tiempo")
        print("5. Reviews por usuario")
        print("6. Nube de palabras")
        print("7. Gráfica extra")
        print("0. Salir")

        opcion = input("Elige opción: ")

        if opcion == "1":
            evolucion_reviews_por_anio()
        elif opcion == "2":
            popularidad_articulos()
        elif opcion == "3":
            histograma_notas()
        elif opcion == "4":
            evolucion_reviews_tiempo()
        elif opcion == "5":
            histograma_reviews_usuario()
        elif opcion == "6":
            nube_palabras()
        elif opcion == "7":
            grafica_extra()
        elif opcion == "0":
            break
        else:
            print("Opción inválida")


if __name__ == "__main__":
    menu()