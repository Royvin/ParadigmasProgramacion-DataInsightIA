import pandas as pd
import numpy as np
from scipy import stats
import plotly.graph_objects as go
import plotly.io as pio


UMBRAL_ZSCORE = 3.0
MAX_FILAS_TABLA = 50


def detectar_outliers(df: pd.DataFrame, columnas_numericas: list) -> dict:
    if not columnas_numericas:
        return _resultado_vacio()

    # Filtrar solo columnas numéricas que existen en el df
    cols = [c for c in columnas_numericas if c in df.columns]
    if not cols:
        return _resultado_vacio()

    # Calcular Z-Score para cada columna numérica
    mascara = pd.DataFrame(False, index=df.index, columns=cols)

    for col in cols:
        serie = df[col].dropna()
        if len(serie) < 4:
            continue
        z_scores = np.abs(stats.zscore(serie))
        indices_outliers = serie.index[z_scores > UMBRAL_ZSCORE]
        mascara.loc[indices_outliers, col] = True

    resumen_outliers = []
    columnas_con_outliers = []

    for col in cols:
        cantidad = int(mascara[col].sum())
        if cantidad > 0:
            porcentaje = round((cantidad / len(df)) * 100, 1)
            resumen_outliers.append({
                'columna':    col,
                'cantidad':   cantidad,
                'porcentaje': porcentaje,
            })
            columnas_con_outliers.append(col)

    # Ordenar por cantidad descendente
    resumen_outliers.sort(key=lambda x: x['cantidad'], reverse=True)

    filas_con_outlier = mascara.any(axis=1)
    indices_filas = df.index[filas_con_outlier].tolist()
    total_outliers = len(indices_filas)

    filas_outliers = _construir_filas_tabla(
        df, mascara, indices_filas, columnas_con_outliers
    )

    return {
        'resumen_outliers':  resumen_outliers,
        'filas_outliers':    filas_outliers,
        'columnas_outliers': columnas_con_outliers,
        'total_outliers':    total_outliers,
        'mascara':           mascara,
    }


def generar_grafico_outliers(df: pd.DataFrame, mascara: pd.DataFrame,
                              columnas_con_outliers: list) -> str | None:

    if not columnas_con_outliers or mascara.empty:
        return None

    # Limitar a máximo 6 columnas para que el gráfico sea legible
    cols_grafico = columnas_con_outliers[:6]

    fig = go.Figure()

    for col in cols_grafico:
        serie = df[col].dropna()

        # Puntos normales
        indices_normales = serie.index[mascara.loc[serie.index, col] == False]
        # Puntos outliers
        indices_outliers = serie.index[mascara.loc[serie.index, col]]

        # Boxplot base
        fig.add_trace(go.Box(
            y=serie,
            name=col,
            boxpoints=False,
            marker_color='#00e5ff',
            line_color='#00e5ff',
            fillcolor='rgba(0,229,255,0.1)',
            showlegend=False,
        ))

        if len(indices_outliers) > 0:
            fig.add_trace(go.Scatter(
                x=[col] * len(indices_outliers),
                y=df.loc[indices_outliers, col],
                mode='markers',
                name='Outlier',
                marker=dict(color='#ff4757', size=8, symbol='circle'),
                showlegend=True if col == cols_grafico[0] else False,
            ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans, sans-serif', color='#7986b4', size=12),
        xaxis=dict(gridcolor='#1e2540', zerolinecolor='#252d48'),
        yaxis=dict(gridcolor='#1e2540', zerolinecolor='#252d48'),
        margin=dict(t=30, b=40, l=50, r=20),
        legend=dict(
            font=dict(color='#7986b4'),
            bgcolor='rgba(0,0,0,0)',
        ),
        height=380,
    )

    return pio.to_html(fig, include_plotlyjs=False, full_html=False)


def _construir_filas_tabla(df: pd.DataFrame, mascara: pd.DataFrame,
                            indices_filas: list, cols: list) -> list:

    filas = []
    cols_disponibles = [c for c in cols if c in df.columns]

    for idx in indices_filas[:MAX_FILAS_TABLA]:
        valores = []
        cols_afectadas = 0

        for col in cols_disponibles:
            valor = df.loc[idx, col]
            es_outlier = bool(mascara.loc[idx, col])
            if es_outlier:
                cols_afectadas += 1
            valores.append({
                'valor':      _formatear_valor(valor),
                'es_outlier': es_outlier,
            })

        filas.append({
            'indice':         int(idx),
            'valores':        valores,
            'cols_afectadas': cols_afectadas,
        })

    return filas


def _formatear_valor(valor) -> str:
    if pd.isna(valor):
        return '---'
    if isinstance(valor, float):
        return f'{valor:,.2f}'
    return str(valor)


def _resultado_vacio() -> dict:
    return {
        'resumen_outliers':  [],
        'filas_outliers':    [],
        'columnas_outliers': [],
        'total_outliers':    0,
        'mascara':           pd.DataFrame(),
    }