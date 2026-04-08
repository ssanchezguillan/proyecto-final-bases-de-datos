import math
from neo4j import GraphDatabase
import pymysql
from configuracion import *


#conexion Neo4J
driver = GraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASSWORD))

#conexión MySQL
mysql_conexion = pymysql.connect(
    host=SQL_HOST,
    user=SQL_USER,
    password=SQL_PASSWORD,
    database=SQL_DB
)
cursor = mysql_conexion.cursor()


TOP_N = 30 #definimos el número de usuarios


def limpiar_base_datos_neo4j() -> None:
    """
    Eliminamos todos los nodos y relaciones de Neo4J para
    trabajar siempre sobre una base limpia.
    """
    #eliminamos todo el grafo existente
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


#4.1 SIMILITUD USUARIOS
def obtener_top_usuarios(n: int) -> list:
    """
    Obtenemos los n usuarios con mayor número de reviews.
    """
    #realizamos la consulta para obtener los usuarios más activos
    cursor.execute("""
    SELECT reviewerID, COUNT(*) as total
    FROM reviews
    GROUP BY reviewerID
    ORDER BY total DESC
    LIMIT %s
    """, (n,))

    return [x[0] for x in cursor.fetchall()]


def obtener_valoraciones_usuario(u: str) -> dict:
    """
    Obtenemos los artículos y notas de un usuario.
    """
    #recuperamos asin y nota de cada review
    cursor.execute("""
    SELECT asin, overall
    FROM reviews
    WHERE reviewerID = %s
    """, (u,))

    return {asin: nota for asin, nota in cursor.fetchall()}


def calcular_pearson(u1: dict, u2: dict) -> float:
    """
    Calculamos la correlación de Pearson entre dos usuarios.
    """
    #obtenemos artículos en común
    comunes = set(u1.keys()) & set(u2.keys())

    if len(comunes) == 0:
        return 0

    #extraemos listas de puntuaciones
    r1 = [u1[i] for i in comunes]
    r2 = [u2[i] for i in comunes]

    #calculamos medias
    media1 = sum(r1) / len(r1)
    media2 = sum(r2) / len(r2)

    #calculamos numerador
    numerador = sum((a - media1)*(b - media2) for a, b in zip(r1, r2))

    #calculamos denominador
    denominador1 = sum((a - media1)**2 for a in r1)
    denominador2 = sum((b - media2)**2 for b in r2)

    if denominador1 == 0 or denominador2 == 0:
        return 0

    return numerador / math.sqrt(denominador1 * denominador2)



def ejecutar_similitud_usuarios() -> None:
    """
    Calculamos similitudes y las representamos en Neo4J.
    """
    #limpiamos base de datos
    limpiar_base_datos_neo4j()

    #obtenemos usuarios
    usuarios = obtener_top_usuarios(TOP_N)

    #obtenemos valoraciones de todos los usuarios
    valoraciones = {u: obtener_valoraciones_usuario(u) for u in usuarios}

    with driver.session() as session:

        #creamos nodos de usuarios
        for u in usuarios:
            session.run("MERGE (:Usuario {id:$id})", id=u)

        #calculamos similitudes entre pares
        for i in range(len(usuarios)):
            for j in range(i+1, len(usuarios)):

                u1 = usuarios[i]
                u2 = usuarios[j]

                #artículos en común
                comunes = set(valoraciones[u1].keys()) & set(valoraciones[u2].keys())


                if len(comunes) > 0:
                    sim = calcular_pearson(valoraciones[u1], valoraciones[u2])
                    session.run("""
                    MATCH (a:Usuario {id:$u1}), (b:Usuario {id:$u2})
                    MERGE (a)-[:SIMILAR {peso:$sim}]-(b)
                    """, u1=u1, u2=u2, sim=sim)

        #mostramos usuario con más vecinos
        result = session.run("""
        MATCH (u:Usuario)--(v:Usuario)
        RETURN u.id AS user, COUNT(DISTINCT v) AS vecinos
        ORDER BY vecinos DESC
        LIMIT 1
        """)

        for row in result:
            print(f"Usuario con más vecinos: {row['user']} ({row['vecinos']})")

    print("4.1 Carga de similitudes completada en Neo4J. Puedes consultar el grafo.")


#4.2 USUARIOS - ARTÍCULOS
def ejecutar_usuarios_articulos() -> None:
    """
    Mostramos relaciones entre usuarios y artículos.
    """

    #limpiamos base de datos
    limpiar_base_datos_neo4j()

    #pedimos datos al usuario
    categoria = input("Categoría: ")
    n = input("Número de artículos: ")

    #seleccionamos artículos aleatorios
    cursor.execute(f"""
    SELECT asin FROM productos
    WHERE categoria = %s
    ORDER BY RAND()
    LIMIT {n}
    """, (categoria,))

    articulos = [x[0] for x in cursor.fetchall()]

    with driver.session() as session:

        for asin in articulos:

            cursor.execute("""
            SELECT reviewerID, overall, unixReviewTime
            FROM reviews
            WHERE asin = %s
            """, (asin,))

            for u, nota, tiempo in cursor.fetchall():
                session.run("""
                MERGE (u:Usuario {id:$u})
                MERGE (a:Articulo {id:$a})
                MERGE (u)-[r:REVIEW]->(a)
                SET r.nota = $nota, r.tiempo = $tiempo
                """, u=u, a=asin, nota=nota, tiempo=tiempo)

    print("4.2 Carga de usuarios y artículos completada en Neo4J. Puedes consultar el grafo.")



#4.3 USUARIOS MULTITIPO
def ejecutar_usuarios_multitipo() -> None:
    """
    Mostramos usuarios que han consumido varios tipos de artículos.
    """

    limpiar_base_datos_neo4j()

    cursor.execute("""
    SELECT reviewerID
    FROM reviews
    GROUP BY reviewerID
    ORDER BY reviewerID
    LIMIT 400
    """)

    usuarios = [x[0] for x in cursor.fetchall()]

    with driver.session() as session:

        for u in usuarios:

            cursor.execute("""
            SELECT p.categoria, COUNT(*)
            FROM reviews r
            JOIN productos p ON r.asin = p.asin
            WHERE r.reviewerID = %s
            GROUP BY p.categoria
            """, (u,))

            categorias = cursor.fetchall()

            if len(categorias) > 1:

                for cat, num in categorias:
                    session.run("""
                    MERGE (u:Usuario {id:$u})
                    MERGE (c:Categoria {nombre:$cat})
                    MERGE (u)-[r:CONSUME]->(c)
                    SET r.cantidad = $num
                    """, u=u, cat=cat, num=num)

    print("4.3 Carga de usuarios multitipo completada en Neo4J. Puedes consultar el grafo.")


#4.4 ARTÍCULOS POPULARES
def ejecutar_articulos_populares() -> None:
    """
    Mostramos artículos populares y relaciones entre usuarios.
    """

    limpiar_base_datos_neo4j()

    cursor.execute("""
    SELECT asin, COUNT(*) as total
    FROM reviews
    GROUP BY asin
    HAVING total < 40
    ORDER BY total DESC
    LIMIT 5
    """)

    articulos = [x[0] for x in cursor.fetchall()]

    with driver.session() as session:
        usuarios_por_articulo = {}

        for asin in articulos:

            cursor.execute("""
            SELECT reviewerID
            FROM reviews
            WHERE asin = %s
            """, (asin,))

            usuarios = [x[0] for x in cursor.fetchall()]
            usuarios_por_articulo[asin] = usuarios

            for u in usuarios:
                session.run("""
                MERGE (u:Usuario {id:$u})
                MERGE (a:Articulo {id:$a})
                MERGE (u)-[:REVIEW]->(a)
                """, u=u, a=asin)

        #relaciones entre usuarios
        cursor.execute("""
        SELECT r1.reviewerID, r2.reviewerID, COUNT(DISTINCT r1.asin) as comunes
        FROM reviews r1
        JOIN reviews r2 
            ON r1.asin = r2.asin 
            AND r1.reviewerID < r2.reviewerID
        GROUP BY r1.reviewerID, r2.reviewerID
        HAVING comunes > 0
        """)

        for u1, u2, comunes in cursor.fetchall():
            session.run("""
            MERGE (a:Usuario {id:$u1})
            MERGE (b:Usuario {id:$u2})
            MERGE (a)-[r:COMUN]-(b)
            SET r.n = $n
            """, u1=u1, u2=u2, n=comunes)

    print("4.4 Carga de artículos populares completada en Neo4J. Puedes consultar el grafo.")




#MAIN
def ejecutar_menu_neo4j() -> None:
    """
    Ejecutamos el menú principal de Neo4J.
    """

    while True:

        print("\n--- MENÚ NEO4J ---")
        print("1. Similitud usuarios")
        print("2. Usuarios-artículos")
        print("3. Usuarios multitipo")
        print("4. Artículos populares")
        print("0. Salir")

        opcion: str = input("Opción: ")

        if opcion == "1":
            ejecutar_similitud_usuarios()
        elif opcion == "2":
            ejecutar_usuarios_articulos()
        elif opcion == "3":
            ejecutar_usuarios_multitipo()
        elif opcion == "4":
            ejecutar_articulos_populares()
        elif opcion == "0":
            break
        else:
            print("Opción inválida")


if __name__ == "__main__":
    ejecutar_menu_neo4j()