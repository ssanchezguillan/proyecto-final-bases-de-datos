#APARTADO OPCIONAL: IMPLEMENTACIÓN DEL MODELO DEL MACHINE LEARNING

import pymysql
import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from configuracion import *


#conexión MySQL
mysql_conexion = pymysql.connect(
    host = SQL_HOST,
    user = SQL_USER,
    password=SQL_PASSWORD,
    database=SQL_DB
)

#1.Cargamos los datos
def cargar_reviews_categoria(categoria: str) -> pd.DataFrame:
    """
    Función para cargar reviewerID, asin y overall de una categoría concreta desde MySQL
    """
    query = """
    SELECT r.reviewerID, r.asin, r.overall
    FROM reviews r
    JOIN productos p ON r.asin = p.asin
    WHERE p.categoria = %s
    """
    df = pd.read_sql(query, mysql_conexion, params=[categoria])
    return df

#2.Filtramos los usuarios y los productos
def filtrar_datos(df: pd.DataFrame, min_reviews_usuario: int=5, min_reviews_producto: int=5) -> pd.DataFrame:
    """
    Función que filtra usuarios y productos con pocas interacciones
    """

    contador_users = df['reviewerID'].value_counts()
    users_validos = contador_users[contador_users>=min_reviews_usuario].index

    contador_productos = df['asin'].value_counts()
    products_validos = contador_productos[contador_productos>=min_reviews_producto].index
    
    df_filtrado = df[df['reviewerID'].isin(users_validos) &
    df['asin'].isin(products_validos)].copy()

    return df_filtrado

#3. Conjuntos de train y test
def separar_train_test(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Función que reserva una review por usuario para test si es posible
    """
    filas_train = []
    filas_test = []

    for reviewerID, grupo in df.groupby('reviewerID'):
        grupo =grupo.sample(frac=1, random_state=42) #barajeamos
        if len(grupo) >=2:
            filas_test.append(grupo.iloc[0])
            for _, fila in grupo.iloc[1:].iterrows():
                filas_train.append(fila)
        
        else: #añadimos la primera
            for _, fila in grupo.iterrows():
                filas_train.append(fila)

    train_df = pd.DataFrame(filas_train)
    test_df = pd.DataFrame(filas_test)

    return train_df, test_df

#4. Creamos la matriz usuario-producto
def matriz_user_prod(train_df: pd.DataFrame) -> pd.DataFrame:
    """
    Construímos la matriz usuario-producto rellenando vacíos con 0
    """
    matriz = train_df.pivot_table(
        index = "reviewerID",
        columns="asin",
        values='overall',
        fill_value=0
    )

    return matriz

#5.Entrenamos KNN
def entrenar_knn(matriz: pd.DataFrame, n_neighbors: int=5) -> NearestNeighbors:
    """
    Función que entrena modelo KNN sobre la matriz usuario-producto
    """
    modelo = NearestNeighbors(metric='cosine', algorithm='brute', n_neighbors=n_neighbors)
    modelo.fit(matriz.values) #usamos al funcion fit estudiada en las prácticas de ML
    return modelo

#6. Generamos las recomendaciones
def recomendar_usuario(reviewerID: str, train_df: pd.DataFrame, matriz: pd.DataFrame, modelo: NearestNeighbors, n_neigbors: int=5, top_n: int= 10):
    """
    Función que recomienda productos no consumidos a un usuario usando vecinos KNN
    """
    if reviewerID not in matriz.index:
        return []
    
    #posicion del usuario en la matriz
    user_pos = matriz.index.get_loc(reviewerID)
    user_vector = matriz.iloc[user_pos].values.reshape(1,-1)

    #vecinos
    distancias, indices = modelo.kneighbors(user_vector, n_neighbors=n_neigbors+1)

    vecinos_indices = indices.flatten()[1:]
    vecinos_distancias = distancias.flatten()[1:] #quitamos al propio usuario en ambas

    vecinos_ids = matriz.index[vecinos_indices]

    #creamos un set de productos ya consumidos por el usuario
    consumidos = set(train_df[train_df['reviewerID'] == reviewerID]['asin'].tolist())

    #recogemos puntuaciones de vecinos
    puntuaciones = {}

    for vecino_id, distancia in zip(vecinos_ids, vecinos_distancias):
        similitud = 1-distancia
        reviews_vecino = train_df[train_df['reviewerID'] == vecino_id]

        for _, fila in reviews_vecino.iterrows():
            asin = fila['asin']
            rating = fila['overall']

            if asin not in consumidos:
                #acumulamos puntuación ponderada por similitud
                if asin not in puntuaciones:
                    puntuaciones[asin] = {'score': 0.0, 'peso': 0.0}

                puntuaciones[asin]['score']+= rating*similitud
                puntuaciones[asin]['peso']+= similitud

    recomendaciones = []
    for asin, valores in puntuaciones.items():
        if valores['peso'] > 0:
            score_final = valores['score'] / valores['peso']
            recomendaciones.append((asin, score_final))

    recomendaciones.sort(key=lambda x: x[1], reverse=True)
    return recomendaciones[:top_n]


#7. Evaluamos
def evaluar_dar_10(train_df: pd.DataFrame, test_df: pd.DataFrame, matriz: pd.DataFrame, modelo: NearestNeighbors, n_neighbors: int=5) -> float:
    """
    Función que evalua si el producto que hemos reservado para test aparece en el top 10 recomendados

    """
    aciertos = 0
    total = 0

    for _, fila in test_df.iterrows():
        reviewerID = fila['reviewerID']
        asin_real = fila['asin']

        recomendaciones = recomendar_usuario(
            reviewerID,
            train_df,
            matriz,
            modelo,
            n_neigbors=n_neighbors,
            top_n=10
        )

        recomendados = [asin for asin, _ in recomendaciones]

        if asin_real in recomendados:
            aciertos += 1
        total +=1

    if total > 0:
        return aciertos/total
    else:
        return 0.0
        

#8. funcion principal
def main():
    categoria = 'music' #posibilidad de cambiar
    print(f"Cargamos datos de la categoría: {categoria}")

    df = cargar_reviews_categoria(categoria)
    print(f"Reviews cargadas: {len(df)}")

    df = filtrar_datos(df, min_reviews_usuario=5, min_reviews_producto=5)
    print(f"Reviews tras filtrado: {len(df)}")

    train_df, test_df = separar_train_test(df)

    print(f"Train: {len(train_df)} reviews")
    print(f"Test: {len(test_df)} reviews")

    matriz = matriz_user_prod(train_df)
    print(f"Matriz usuario-producto: {matriz.shape[0]} usuarios x {matriz.shape[1]} productos")

    modelo = entrenar_knn(matriz, n_neighbors=5)

    #probar recomendaciones de ejemplo
    usuario_ejemplo = matriz.index[0]
    recomendaciones = recomendar_usuario(usuario_ejemplo, train_df, matriz, modelo, n_neigbors=5, top_n=10)

    print(f"\nRecomendaciones para el usuario: {usuario_ejemplo}")
    for i, (asin, score) in enumerate(recomendaciones, start=1):
        print(f"{i}. {asin} | score estimado: {score:.3f}")

    
    #evaluamos
    hit_rate = evaluar_dar_10(train_df, test_df, matriz, modelo, n_neighbors=5)
    print(f"\nHit Rate@10: {hit_rate:.4f}")


if __name__ == "__main__":
    main()