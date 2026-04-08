import pymysql
from configuracion import * #importamos todo


#creamos conexion mysql
mysql_conexion = pymysql.connect(
    host=SQL_HOST,
    user=SQL_USER,
    password=SQL_PASSWORD,
    database=SQL_DB
)


cursor = mysql_conexion.cursor()

def usuario_existe(reviewerID: str) -> bool:
    """
    Función auxiliar que comprueba si el usuario existe en la base de datos
    """
    query = "SELECT COUNT(*) FROM usuarios WHERE reviewerID = %s"
    cursor.execute(query, (reviewerID,))
    resultado = cursor.fetchone()
    return resultado[0] > 0 #que exista alguno

def categoria_existe(categoria: str) -> bool:
    """
    Función auxiliar que comprueba si la categoría existe en la base de datos
    """
    query = "SELECT COUNT(*) FROM productos WHERE categoria = %s"
    cursor.execute(query, (categoria,))
    resultado = cursor.fetchone()
    return resultado[0] > 0 #que exista alguna

def recomendar_top_10_no_consumidos(reviewerID: str, categoria: str):
    """
    Función principal que devuelve los 10 artículos más populares de una categoría 
    que el usuario todavía no ha consumido
    """

    query = """
    SELECT p.asin, COUNT(*) AS popularidad
    FROM reviews r
    JOIN productos p ON r.asin = p.asin
    WHERE p.categoria = %s
        AND p.asin NOT IN (
            SELECT r2.asin
            FROM reviews r2
            JOIN productos p2 ON r2.asin = p2.asin
            WHERE r2.reviewerID = %s
                AND p2.categoria = %s
        )
    GROUP BY p.asin
    ORDER BY popularidad DESC
    LIMIT 10
    """

    cursor.execute(query, (categoria, reviewerID, categoria))
    return cursor.fetchall() #devolvemos los 10

def menu()-> None:
    """
    Menú interactivo para obtener recomendaciones
    """
    while True:
        print("RECOMENDAR ARTÍCULOS")
        opciones = """
        1. Obtener 10 recomendaciones nuevas
        0. Salir
        """
        print(opciones)

        op = input("\nElige una opción: ")

        if op == "1":
            reviewerID = input("Introduce el reviewerID: ").strip()
            categoria = input("Introduce la categoría: ").strip()

            #comprobamos que existen con las funciones auxliares
            if not usuario_existe(reviewerID):
                print("El usuario no existe en la base de datos")
                continue
        
            if not categoria_existe(categoria):
                print("La categoría no existe en la base de datos")
                continue

            recomendaciones = recomendar_top_10_no_consumidos(reviewerID, categoria)

            if not recomendaciones:
                print("No hay recomendaciones disponibles para este usuario en esta categoría")
            else: 
                print("\nTOp 10 artículos recomendados")
                #vamos 1 a uno agrupando
                for i, (asin, popularidad) in enumerate(recomendaciones, start=1):
                    print(f"{i}. ASIN: {asin} | Número de reviews: {popularidad}")
        
        elif op == "0":
            print("Saliendo del recomendador")
            break

        else:
            print("Opción no válida")


if __name__ == "__main__":
    #ejecutamos menu
    menu()

    