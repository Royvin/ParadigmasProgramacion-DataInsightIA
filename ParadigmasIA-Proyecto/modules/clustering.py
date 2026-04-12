
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
import plotly.express as px
import plotly.graph_objects as go

def aplicar_clustering(df, columnas_numericas, max_clusters=8):
   
    if len(columnas_numericas) < 2:
        return None, 0, None, None
    
    # Tomar solo columnas numéricas y eliminar NaN
    X = df[columnas_numericas].dropna()
    if len(X) < 10:
        return None, 0, None, None
    
    # Escalar datos
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Determinar número óptimo de clusters (2..max_clusters)
    best_k = 2
    best_score = -1
    for k in range(2, min(max_clusters, len(X))):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        if len(set(labels)) > 1:
            score = silhouette_score(X_scaled, labels)
            if score > best_score:
                best_score = score
                best_k = k
    
    # Aplicar K-means con el mejor k
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    
    # Calcular centroides en escala original
    centroides = pd.DataFrame(
        scaler.inverse_transform(kmeans.cluster_centers_),
        columns=columnas_numericas
    )
    
    return labels, best_k, centroides, best_score

def generar_grafico_clusters(df, labels, columnas_numericas):
 

    if labels is None or len(set(labels)) < 2:
        return '<div class="estado-vacio">No se pudieron generar clusters (datos insuficientes).</div>'
    
    # Filtrar filas con cluster asignado (sin NaN)
    df_clust = df[columnas_numericas].dropna().copy()
    df_clust['cluster'] = labels
    
    # Reducción a 2D si es necesario
    if len(columnas_numericas) == 2:
        x_col, y_col = columnas_numericas[0], columnas_numericas[1]
        x_data = df_clust[x_col]
        y_data = df_clust[y_col]
        titulo_ejes = f"{x_col} vs {y_col}"
    else:
        # Aplicar PCA
        pca = PCA(n_components=2)
        coords = pca.fit_transform(df_clust[columnas_numericas])
        df_clust['PC1'] = coords[:, 0]
        df_clust['PC2'] = coords[:, 1]
        x_data = df_clust['PC1']
        y_data = df_clust['PC2']
        titulo_ejes = "Componente Principal 1 / Componente Principal 2"
    
    fig = px.scatter(
        df_clust, x=x_data, y=y_data, color='cluster',
        title=f"Visualización de clusters (K-means, {len(set(labels))} grupos)",
        labels={'x': titulo_ejes.split(' vs ')[0] if 'vs' in titulo_ejes else 'PC1',
                'y': titulo_ejes.split(' vs ')[1] if 'vs' in titulo_ejes else 'PC2'},
        color_continuous_scale='Viridis',
        opacity=0.7
    )
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#7986b4'),
        legend_title_text='Cluster'
    )
    return fig.to_html(full_html=False)

def obtener_info_clusters(df, labels, centroides, columnas_numericas):
 
    if labels is None:
        return [], []
    
    df_temp = df[columnas_numericas].dropna().copy()
    df_temp['cluster'] = labels
    n_total = len(df_temp)
    
    # Estadísticas globales (para comparación)
    medias_globales = df_temp[columnas_numericas].mean()
    
    info_clusters = []
    detalle_clusters = []
    
    for cluster_id in sorted(df_temp['cluster'].unique()):
        mask = df_temp['cluster'] == cluster_id
        size = mask.sum()
        porcentaje = round(100 * size / n_total, 1)
        
        # Medias del cluster
        medias_cluster = df_temp.loc[mask, columnas_numericas].mean()
        
        # Construir descripción: la variable con mayor diferencia respecto a la media global
        diffs = (medias_cluster - medias_globales).abs()
        var_destacada = diffs.idxmax()
        direccion = "superior" if medias_cluster[var_destacada] > medias_globales[var_destacada] else "inferior"
        descripcion = f"Grupo de {size} registros ({porcentaje}%). Destaca por tener {var_destacada} {direccion} al promedio general."
        
        info_clusters.append({
            'id': cluster_id,
            'tamanio': size,
            'descripcion': descripcion
        })
        
        # Detalle para tabla en results.html
        estadisticas_cluster = []
        for col in columnas_numericas:
            estadisticas_cluster.append({
                'columna': col,
                'media_cluster': round(medias_cluster[col], 2),
                'media_global': round(medias_globales[col], 2)
            })
        detalle_clusters.append({
            'id': cluster_id,
            'tamanio': size,
            'porcentaje': porcentaje,
            'estadisticas': estadisticas_cluster
        })
    
    return info_clusters, detalle_clusters