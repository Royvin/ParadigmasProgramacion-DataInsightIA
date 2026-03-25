import pandas as pd
import chardet
import os

LIMITE_FILAS = 100_000


def cargar_archivo(ruta: str) -> pd.DataFrame:

    if not os.path.exists(ruta):
        raise ValueError(f'El archivo no existe: {ruta}')

    extension = _obtener_extension(ruta)

    if extension == 'csv':
        df = _leer_csv(ruta)
    elif extension in ('xlsx', 'xls'):
        df = _leer_excel(ruta)
    else:
        raise ValueError(f'Extensión no soportada: {extension}. Use CSV, XLSX o XLS.')

    # Validaciones básicas
    if df.empty:
        raise ValueError('El archivo está vacío o no contiene datos válidos.')

    if len(df) > LIMITE_FILAS:
        raise ValueError(
            f'El archivo tiene {len(df):,} filas. '
            f'El límite permitido es {LIMITE_FILAS:,} filas.'
        )

    df = _limpiar_dataframe(df)

    return df


def obtener_info_archivo(ruta: str) -> dict:
    nombre = os.path.basename(ruta)
    tamanio_kb = round(os.path.getsize(ruta) / 1024, 1)

    try:
        df = cargar_archivo(ruta)
        filas, columnas = df.shape
    except ValueError:
        filas, columnas = 0, 0

    return {
        'nombre':     nombre,
        'filas':      filas,
        'columnas':   columnas,
        'tamanio_kb': tamanio_kb,
    }

def _obtener_extension(ruta: str) -> str:
    """Extrae y normaliza la extensión del archivo."""
    return ruta.rsplit('.', 1)[-1].lower()


def _leer_csv(ruta: str) -> pd.DataFrame:
    for encoding in ('utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1'):
        try:
            df = pd.read_csv(ruta, encoding=encoding, sep=None, engine='python')
            return df
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue

    with open(ruta, 'rb') as archivo:
        resultado = chardet.detect(archivo.read(50_000))
        encoding_detectado = resultado.get('encoding', 'utf-8')

    try:
        df = pd.read_csv(ruta, encoding=encoding_detectado, sep=None, engine='python')
        return df
    except Exception as e:
        raise ValueError(f'No se pudo leer el CSV: {str(e)}')


def _leer_excel(ruta: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(ruta, sheet_name=0)
        return df
    except Exception as e:
        raise ValueError(f'No se pudo leer el archivo Excel: {str(e)}')


def _limpiar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Eliminar filas y columnas completamente vacías
    df = df.dropna(how='all')
    df = df.dropna(axis=1, how='all')

    # Normalizar nombres de columnas
    df.columns = [str(col).strip() for col in df.columns]

    # Eliminar duplicados exactos
    df = df.drop_duplicates()

    # Resetear el índice
    df = df.reset_index(drop=True)

    return df