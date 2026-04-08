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
    password=SQL_PASSWORD,
    database = SQL_DB
)

cursor = mysql_conexion.cursor()


#conexión con MongoDB usando la base y colección ya creadas
mongo_cliente = MongoClient(MONGO_URL)
mongo_db = mongo_cliente[MONGO_DB]
collection = mongo_db[MONGO_COLLECTION]

def parse_fecha(fecha_str: str) -> datetime:
    """
    Función auxiliar que convierte una fecha en formato 'mes dia, año' a datetime.
    Ejemplo: '02 12, 2011'
    Args:
        fecha_str: fecha de 'reviewTime' del json
    """
    return datetime.strptime(fecha_str, "%m %d, %Y")

def insertar_mysql(buffer) -> None:
    """
    Función que inserta usuarios, productos y reviews en MySQL.
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

def cargar_nuevo_dataset(ruta: str, categoria: str) -> None:
    """
    Función que carga un nuevo dataset línea a línea sin cargarlo entero en memoria.
    
    Los datos estructurados se insertan en MySQL.
    Los campos de texto y helpful se insertan en MongoDB.
    """

    buffer_mysql = []
    buffer_mongo = []
    total_insertadas = 0

    with open(ruta, "r", encoding="utf-8") as f:
        for i, linea in enumerate(f,start=1):
            review = json.loads(linea)

            reviewerID = review.get("reviewerID")
            reviewerName = review.get("reviewerName", "")
            asin = review.get("asin")
            overall = review.get("overall")
            unixTime = review.get("unixReviewTime")
            reviewTime = parse_fecha(review.get("reviewTime"))

            #datos para MySQL
            buffer_mysql.append((reviewerID, reviewerName, asin, categoria, overall, reviewTime, unixTime))

            #datos para MOngoDB
            buffer_mongo.append({
                "reviewerID": reviewerID,
                "asin": asin,
                "summary": review.get("summary"),
                "reviewText": review.get("reviewText"),
                "helpful": review.get("helpful"),
                "categoria": categoria                             
            })

            #insertamos en bloques de 1000
            if len(buffer_mysql) == 1000:
                insertar_mysql(buffer_mysql)
                collection.insert_many(buffer_mongo)
                mysql_conexion.commit()

                total_insertadas += len(buffer_mysql)
                print(f"{total_insertadas} reviews procesadas...")

                buffer_mysql = []
                buffer_mongo = []

        if buffer_mysql:
            insertar_mysql(buffer_mysql)
            collection.insert_many(buffer_mongo)
            mysql_conexion.commit()
            total_insertadas += len(buffer_mysql)

    print("Carga incremental completada")
    print(f"Total de reviews insertadas: {total_insertadas}")

def main()-> None:
    """
    Función principal donde insertamos el nuevo dataset Clothing_Shoes_And_jewelry_5.json
    en la infrastructura ya creada
    """
    ruta = "Clothing_Shoes_and_Jewelry_5.json"
    categoria = "clothing_shoes_jewelry"

    print(f"Insertando nuevo dataset: {categoria}")
    cargar_nuevo_dataset(ruta, categoria)


if __name__ == "__main__":
    main()