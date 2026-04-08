import json
import pymysql
from pymongo import MongoClient
from datetime import datetime
from typing import List, Tuple, Dict, Any
from configuracion import *

#creamos conexión con MySQL sin especificar base de datos porque puede no existir aún
mysql_conexion = pymysql.connect(
    host=SQL_HOST,
    user=SQL_USER,
    password=SQL_PASSWORD
)

cursor = mysql_conexion.cursor()

#creamos la base de datos si no existe y la seleccionamos para trabajar sobre ella
cursor.execute(f"CREATE DATABASE IF NOT EXISTS {SQL_DB}")
cursor.execute(f"USE {SQL_DB}")

#establecemos conexión con MongoDB para almacenar los datos no estructurados
mongo_cliente = MongoClient(MONGO_URL)
mongo_db = mongo_cliente[MONGO_DB]
collection = mongo_db[MONGO_COLLECTION]


def crear_tablas() -> None:
    """
    Creamos las tablas necesarias en MySQL si no existen.

    -usuarios: almacena los identificadores de usuarios
    -productos: almacena los productos y su categoría
    -reviews: almacena las valoraciones con claves foráneas
    """
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(
        reviewerID VARCHAR(50) PRIMARY KEY,
        reviewerName VARCHAR(255)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos(
        asin VARCHAR(50) PRIMARY KEY,
        categoria VARCHAR(50)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews(
        review_id INT AUTO_INCREMENT PRIMARY KEY,
        reviewerID VARCHAR(50),
        asin VARCHAR(50),
        overall FLOAT,
        reviewTime DATE,
        unixReviewTime BIGINT,
        FOREIGN KEY (reviewerID) REFERENCES usuarios(reviewerID),
        FOREIGN KEY (asin) REFERENCES productos(asin)
    )
    """)


def parse_fecha(fecha_str: str) -> datetime:
    """
    Convertimos la fecha del JSON (string) a tipo datetime.

    Args:
        fecha_str: fecha en formato "mes día, año"

    Returns:
        datetime: fecha parseada
    """
    return datetime.strptime(fecha_str, "%m %d, %Y")


def insertar_mysql(buffer: List[Tuple[Any, ...]]) -> None:
    """
    Insertamos datos en MySQL en bloques para mejorar la eficiencia.

    Args:
        buffer: lista de tuplas con los datos procesados
    """

    #insertamos usuarios evitando duplicados
    cursor.executemany("""
        INSERT IGNORE INTO usuarios VALUES (%s, %s)
    """, [(r[0], r[1]) for r in buffer])

    #insertamos productos evitando duplicados
    cursor.executemany("""
        INSERT IGNORE INTO productos VALUES (%s, %s)
    """, [(r[2], r[3]) for r in buffer])

    #insertamos reviews
    cursor.executemany("""
        INSERT INTO reviews (reviewerID, asin, overall, reviewTime, unixReviewTime)
        VALUES (%s, %s, %s, %s, %s)
    """, [(r[0], r[2], r[4], r[5], r[6]) for r in buffer])


def cargar_dataset(ruta: str, categoria: str) -> None:
    """
    Cargamos un dataset JSON línea a línea sin cargarlo completamente en memoria.

    -procesamos cada review
    -almacenamos en buffers
    -insertamos en bloques en MySQL y MongoDB

    Args:
        ruta: ruta del fichero JSON
        categoria: tipo de producto
    """

    buffer_mysql = []
    buffer_mongo = []

    with open(ruta, 'r', encoding='utf-8') as f:
        for i, linea in enumerate(f):

            review = json.loads(linea)

            reviewerID = review.get('reviewerID')
            reviewerName = review.get('reviewerName', '')
            asin = review.get('asin')
            overall = review.get('overall')
            unixTime = review.get('unixReviewTime')
            reviewTime = parse_fecha(review.get('reviewTime'))

            #almacenamos los datos estructurados en el buffer de MySQL
            buffer_mysql.append((reviewerID, reviewerName, asin, categoria, overall, reviewTime, unixTime))

            #almacenamos los datos no estructurados en el buffer de MongoDB
            buffer_mongo.append({
                'reviewerID': reviewerID,
                'asin': asin,
                'summary': review.get('summary'),
                'reviewText': review.get('reviewText'),
                'helpful': review.get("helpful")
            })

            #cuando alcanzamos 1000 registros insertamos en bloque
            if len(buffer_mysql) == 1000:

                insertar_mysql(buffer_mysql)
                collection.insert_many(buffer_mongo)

                #reiniciamos buffers
                buffer_mysql = []
                buffer_mongo = []

                print(f"{i} registros procesados...")

        #insertamos los registros restantes
        if buffer_mysql:
            insertar_mysql(buffer_mysql)
            collection.insert_many(buffer_mongo)

    #confirmamos cambios en MySQL
    mysql_conexion.commit()


def main() -> None:
    """
    Función principal del programa.

    -creamos las tablas
    -cargamos todos los datasets definidos en configuracion.py
    """

    crear_tablas()

    for categoria, ruta in DATASETS.items():
        print(f'Cargando {categoria}...')
        cargar_dataset(ruta, categoria)

    print('Carga completada')


if __name__ == "__main__":
    main()