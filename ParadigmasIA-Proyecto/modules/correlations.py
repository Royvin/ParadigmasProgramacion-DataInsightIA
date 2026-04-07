# modules/correlations.py
# Modulo de correlaciones para DataInsight AI.
# Proporciona funciones para:
# - Identificar columnas numericas en un DataFrame.
# - Calcular matrices de correlacion (Pearson o Spearman).
# - Generar mapas de calor interactivos con Plotly.

import pandas as pd
import numpy as np
import plotly.express as px


# ===================================================
# Funciones auxiliares
# ===================================================

# Devuelve una lista con los nombres de las columnas numericas (int o float) del DataFrame.
    # Parametros:
    #   df (pd.DataFrame): DataFrame de entrada.
    # Retorna:
    #   list: Nombres de las columnas con tipos numericos.

def obtener_columnas_numericas(df):
    return df.select_dtypes(include=[np.number]).columns.tolist()


# ===================================================
# Calculo de correlaciones
# ===================================================

# Calcula la matriz de correlacion entre todas las columnas numericas del DataFrame.
    # Parametros:
    #   df (pd.DataFrame): Datos de entrada.
    #   metodo (str): 'pearson' (por defecto) o 'spearman'.
    # Retorna:
    #   dict: con claves 'matriz', 'top_pares', 'error'.

def calcular_correlaciones(df, metodo='pearson'):
    
    
    # 1. Obtener solo las columnas numericas
    cols_num = obtener_columnas_numericas(df)
    
    # 2. Verificar que haya al menos 2 columnas numericas para poder correlacionar
    if len(cols_num) < 2:
        return {
            'matriz': pd.DataFrame(),
            'top_pares': [],
            'error': 'Se necesitan al menos 2 columnas numericas para calcular correlaciones.'
        }
    
    # 3. Extraer las columnas numericas y eliminar filas con valores nulos
    df_num = df[cols_num].dropna()
    
    # 4. Calcular la matriz de correlacion segun el metodo elegido
    if metodo == 'spearman':
        # Correlacion de Spearman (basada en rangos)
        corr_matrix = df_num.corr(method='spearman')
    else:
        # Correlacion de Pearson (por defecto)
        corr_matrix = df_num.corr(method='pearson')
    
    # 5. Extraer pares unicos (evitando la diagonal y duplicados)
    pares = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i + 1, len(corr_matrix.columns)):
            var1 = corr_matrix.columns[i]
            var2 = corr_matrix.columns[j]
            r = corr_matrix.iloc[i, j]
            pares.append({
                'var1': var1,
                'var2': var2,
                'r': round(r, 4)   # Redondear a 4 decimales para mejor legibilidad
            })
    
    # 6. Ordenar los pares por |r| descendente (de mayor a menor correlacion en valor absoluto)
    pares.sort(key=lambda x: abs(x['r']), reverse=True)
    
    return {
        'matriz': corr_matrix,
        'top_pares': pares,
        'error': None
    }


# ===================================================
# Generacion de graficos (mapa de calor)
# ===================================================

# Genera un mapa de calor interactivo a partir de una matriz de correlacion.
    # Parametros:
    #   matriz_corr (pd.DataFrame): Matriz de correlacion (resultado de calcular_correlaciones).
    #   metodo (str): 'pearson' o 'spearman' (solo para el titulo del grafico).
    # Retorna:
    #   str: Codigo HTML del grafico de Plotly, listo para incrustar en una plantilla Flask.
    #        Si la matriz es invalida, retorna un mensaje HTML de error.

def generar_grafico_correlacion(matriz_corr, metodo='pearson'):
    
    
    # Validar que la matriz tenga al menos 2 columnas y no este vacia
    if matriz_corr.empty or len(matriz_corr.columns) < 2:
        return '<div class="estado-vacio">No hay suficientes columnas numericas para mostrar correlacion.</div>'
    
    # Crear el mapa de calor con Plotly Express
    fig = px.imshow(
        matriz_corr,
        text_auto='.2f',                    # Muestra el valor dentro de cada celda con 2 decimales
        color_continuous_scale='RdBu_r',    # Escala de colores: rojo (positivo) a azul (negativo)
        zmin=-1, zmax=1,                    # Rango fijo de correlacion [-1, 1]
        aspect='auto',                      # Ajuste automatico del tamano de las celdas
        title=f'Matriz de correlacion - {metodo.capitalize()}'
    )
    
    # Ajustes adicionales de diseno
    fig.update_layout(
        width=700,
        height=600,
        font=dict(size=11)
    )
    
    # Convertir la figura a HTML (sin incluir todo el documento, solo el div del grafico)
    return fig.to_html(full_html=False)