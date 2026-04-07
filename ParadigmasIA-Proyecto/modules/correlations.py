import pandas as pd
import numpy as np
import plotly.express as px

def obtener_columnas_numericas(df):
    return df.select_dtypes(include=[np.number]).columns.tolist()

def calcular_correlaciones(df, metodo='pearson'):
    
    
    #Obtener solo las columnas numericas
    cols_num = obtener_columnas_numericas(df)
    
    #Verificar que haya al menos 2 columnas numericas para poder correlacionar
    if len(cols_num) < 2:
        return {
            'matriz': pd.DataFrame(),
            'top_pares': [],
            'error': 'Se necesitan al menos 2 columnas numericas para calcular correlaciones.'
        }
    
    #Extraer las columnas numericas y eliminar filas con valores nulos
    df_num = df[cols_num].dropna()
    
    #Calcular la matriz de correlacion segun el metodo elegido
    if metodo == 'spearman':
        # Correlacion de Spearman (basada en rangos)
        corr_matrix = df_num.corr(method='spearman')
    else:
        # Correlacion de Pearson (por defecto)
        corr_matrix = df_num.corr(method='pearson')
    
    #Extraer pares unicos (evitando la diagonal y duplicados)
    pares = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i + 1, len(corr_matrix.columns)):
            var1 = corr_matrix.columns[i]
            var2 = corr_matrix.columns[j]
            r = corr_matrix.iloc[i, j]
            pares.append({
                'var1': var1,
                'var2': var2,
                'r': round(r, 4)
            })
    
    #Ordenar los pares por |r| descendente (de mayor a menor correlacion en valor absoluto)
    pares.sort(key=lambda x: abs(x['r']), reverse=True)
    
    return {
        'matriz': corr_matrix,
        'top_pares': pares,
        'error': None
    }

def generar_grafico_correlacion(matriz_corr, metodo='pearson'):
    
    
    # Validar que la matriz tenga al menos 2 columnas y no este vacia
    if matriz_corr.empty or len(matriz_corr.columns) < 2:
        return '<div class="estado-vacio">No hay suficientes columnas numericas para mostrar correlacion.</div>'
    
    # Crear el mapa de calor con Plotly Express
    fig = px.imshow(
        matriz_corr,
        text_auto='.2f',
        color_continuous_scale='RdBu_r',
        zmin=-1, zmax=1,
        aspect='auto',
        title=f'Matriz de correlacion - {metodo.capitalize()}'
    )
    
    # Ajustes adicionales de diseno
    fig.update_layout(
        width=700,
        height=600,
        font=dict(size=11)
    )
    
    # Convertir la figura a HTML
    return fig.to_html(full_html=False)