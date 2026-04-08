import pymysql
import matplotlib.pyplot as plt
from pymongo import MongoClient
from collections import Counter
from wordcloud import WordCloud
from configuracion import *
#nuevo tkinter
import tkinter as tk
from tkinter import ttk

#nos conectamos a MySQL igual que antes
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


def evolucion_reviews_por_anio(categoria: str) -> None:
    """
    Mostramos el número de reviews por año en forma de 
    histograma
    """

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


def nube_palabras(categoria: str) -> None:
    """
    Generamos nube de palabras usando MongoDB.
    """
    palabras = []

    if categoria == 'todo':
        cursor_mongo = collection.find({}, {'summary': 1})
    else:
        cursor_mongo = collection.find({'categoria': categoria}, {'summary': 1})

    for doc in cursor_mongo:
        texto = doc.get('summary', '')
        if texto:
            palabras.extend(texto.split())

    #filtramos palabras cortas
    palabras = [p for p in palabras if len(p) > 3]

    if len(palabras) == 0:
        print("No hay palabras para esa categoría")
        return

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



#nueva interfaz usando tkinter
def obtener_categoria():
    return combo_categoria.get()

def lanzar_evolucion():
    evolucion_reviews_por_anio(obtener_categoria())

def lanzar_nube():
    nube_palabras(obtener_categoria())

ventana = tk.Tk()
ventana.title("Visualización interactiva Amazon")
ventana.geometry("500x500")

titulo = tk.Label(ventana, text='Panel de visualziación', font=('Arial', 16))
titulo.pack(pady=15)


#selector de categoria
frame = tk.Frame(ventana)
frame.pack(pady=10)

tk.Label(frame, text='Categoria:').pack(side=tk.LEFT)

combo_categoria = ttk.Combobox(frame, values=['todo', 'video_games', 'toys', 'music', 'instruments', 'clothing_shoes_jewelry'], state='readonly')
combo_categoria.current(0)
combo_categoria.pack(side=tk.LEFT, padx=5)

#botones
tk.Button(ventana, text='Evolución reviews por año', width=30, command=lanzar_evolucion).pack(pady=5)
tk.Button(ventana, text='Popularidad artículos', width=30, command=popularidad_articulos).pack(pady=5)
tk.Button(ventana, text='Histograma notas', width=30, command=histograma_notas).pack(pady=5)
tk.Button(ventana, text='Evolución en el tiempo', width=30, command=evolucion_reviews_tiempo).pack(pady=5)
tk.Button(ventana, text='Reviews por usuario', width=30, command=histograma_reviews_usuario).pack(pady=5)
tk.Button(ventana, text='Nube de palabras', width=30, command=lanzar_nube).pack(pady=5)
tk.Button(ventana, text='Gráfica extra', width=30, command=grafica_extra).pack(pady=5)

tk.Button(ventana, text='Salir', width=30, command=ventana.destroy).pack(pady=20)

ventana.mainloop()