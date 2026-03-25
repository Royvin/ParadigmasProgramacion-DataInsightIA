import pandas as pd
import numpy as np

UMBRAL_CATEGORICA_NUMERICA = 10


def analizar(df: pd.DataFrame) -> dict:
    tipos = _detectar_tipos(df)

    return {
        'estadisticas': _calcular_estadisticas_generales(df, tipos),
        'columnas': _info_columnas(df, tipos),
        'stats_descriptivas': _stats_descriptivas(df, tipos),
        'stats_numericas': _stats_numericas(df, tipos),
        'stats_categoricas': _stats_categoricas(df, tipos),
    }


def _detectar_tipos(df: pd.DataFrame) -> dict:

    tipos = {}

    for columna in df.columns:
        serie = df[columna]
        # Intentar detectar fechas primero
        if _es_fecha(serie):
            tipos[columna] = 'fecha'

        elif pd.api.types.is_numeric_dtype(serie):
            n_unicos = serie.nunique()
            if n_unicos <= UMBRAL_CATEGORICA_NUMERICA:
                tipos[columna] = 'categorica'
            else:
                tipos[columna] = 'numerica'

        # Booleano
        elif pd.api.types.is_bool_dtype(serie):
            tipos[columna] = 'categorica'

        # Todo lo demás es categórico
        else:
            tipos[columna] = 'categorica'

    return tipos


def _es_fecha(serie: pd.Series) -> bool:
    # Ya es datetime
    if pd.api.types.is_datetime64_any_dtype(serie):
        return True

    # Solo intentar parsear si es de tipo objeto (texto)
    if serie.dtype != object:
        return False

    # Tomar muestra para no parsear toda la columna
    muestra = serie.dropna().head(20)
    if muestra.empty:
        return False

    try:
        pd.to_datetime(muestra, infer_datetime_format=True)
        return True
    except (ValueError, TypeError):
        return False

def _calcular_estadisticas_generales(df: pd.DataFrame, tipos: dict) -> dict:
    total_filas, total_columnas = df.shape

    # Total de valores faltantes
    total_celdas    = total_filas * total_columnas
    total_faltantes = df.isnull().sum().sum()
    pct_faltantes   = round((total_faltantes / total_celdas) * 100, 1) if total_celdas > 0 else 0

    total_numericas   = sum(1 for t in tipos.values() if t == 'numerica')
    total_categoricas = sum(1 for t in tipos.values() if t == 'categorica')

    return {
        'total_filas': total_filas,
        'total_columnas': total_columnas,
        'pct_faltantes': pct_faltantes,
        'total_numericas': total_numericas,
        'total_categoricas': total_categoricas,
        'total_outliers': 0,   # se rellena en outliers.py
        'total_clusters': 0,   # se rellena en clustering.py
    }

def _info_columnas(df: pd.DataFrame, tipos: dict) -> list:
    columnas = []

    for nombre, tipo in tipos.items():
        serie = df[nombre]
        total = len(serie)
        no_nulos = int(serie.notna().sum())
        unicos = int(serie.nunique())
        completitud = round((no_nulos / total) * 100, 1) if total > 0 else 0

        columnas.append({
            'nombre': nombre,
            'tipo': tipo,
            'no_nulos': no_nulos,
            'unicos': unicos,
            'completitud': completitud,
        })

    return columnas


def _stats_descriptivas(df: pd.DataFrame, tipos: dict) -> list:
    stats = []
    cols_numericas = [col for col, tipo in tipos.items() if tipo == 'numerica']

    for columna in cols_numericas:
        serie = df[columna].dropna()

        if serie.empty:
            continue

        stats.append({
            'columna': columna,
            'media': _formatear(serie.mean()),
            'mediana': _formatear(serie.median()),
            'desviacion': _formatear(serie.std()),
            'minimo': _formatear(serie.min()),
            'maximo': _formatear(serie.max()),
            'asimetria': round(float(serie.skew()), 2),
        })

    return stats

def _stats_numericas(df: pd.DataFrame, tipos: dict) -> list:
    stats = []
    cols_numericas = [col for col, tipo in tipos.items() if tipo == 'numerica']

    for columna in cols_numericas:
        serie = df[columna].dropna()

        if serie.empty:
            continue

        stats.append({
            'columna': columna,
            'conteo': int(serie.count()),
            'media': _formatear(serie.mean()),
            'mediana': _formatear(serie.median()),
            'desviacion': _formatear(serie.std()),
            'q1': _formatear(serie.quantile(0.25)),
            'q3': _formatear(serie.quantile(0.75)),
            'minimo': _formatear(serie.min()),
            'maximo': _formatear(serie.max()),
            'asimetria': round(float(serie.skew()), 2),
            'curtosis': round(float(serie.kurt()), 2),
        })

    return stats

def _stats_categoricas(df: pd.DataFrame, tipos: dict) -> list:
    stats = []
    cols_categoricas = [col for col, tipo in tipos.items() if tipo == 'categorica']

    for columna in cols_categoricas:
        serie = df[columna]
        no_nulos  = serie.dropna()
        faltantes = int(serie.isnull().sum())

        if no_nulos.empty:
            continue

        moda = no_nulos.mode()
        val_moda  = str(moda.iloc[0]) if not moda.empty else '---'
        frec_moda = int(no_nulos.value_counts().iloc[0]) if not no_nulos.empty else 0

        stats.append({
            'columna': columna,
            'conteo': int(no_nulos.count()),
            'unicos': int(no_nulos.nunique()),
            'moda': val_moda,
            'frec_moda': frec_moda,
            'faltantes': faltantes,
        })

    return stats

def _formatear(valor) -> str:
    if pd.isna(valor):
        return '---'

    valor = float(valor)

    if valor == int(valor) and abs(valor) < 1_000_000:
        return f'{int(valor):,}'

    if abs(valor) >= 1_000:
        return f'{valor:,.2f}'

    return f'{valor:.2f}'


def obtener_columnas_numericas(df: pd.DataFrame) -> list:
    tipos = _detectar_tipos(df)
    return [col for col, tipo in tipos.items() if tipo == 'numerica']