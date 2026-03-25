from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from modules.loader import cargar_archivo, obtener_info_archivo
import os
from datetime import datetime


app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY', 'datainsight-dev-key-2024')

CARPETA_SUBIDAS = os.path.join(os.path.dirname(__file__), 'subidas')
os.makedirs(CARPETA_SUBIDAS, exist_ok=True)

EXTENSIONES_PERMITIDAS = {'csv', 'xlsx', 'xls'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


def extension_permitida(nombre_archivo):
    """Verifica que el archivo tenga una extension valida."""
    return '.' in nombre_archivo and \
           nombre_archivo.rsplit('.', 1)[1].lower() in EXTENSIONES_PERMITIDAS

# Rutas

@app.route('/')
def inicio():
    return render_template('index.html')


@app.route('/cargar', methods=['POST'])
def cargar():
    archivos = request.files.getlist('archivos')

    # Validar que se hayan enviado archivos
    if not archivos or archivos[0].filename == '':
        flash('Debes seleccionar al menos un archivo.', 'error')
        return redirect(url_for('inicio'))

    # Validar extensiones
    for archivo in archivos:
        if not extension_permitida(archivo.filename):
            flash(f'El archivo "{archivo.filename}" no es valido. Solo se aceptan CSV, XLSX y XLS.', 'error')
            return redirect(url_for('inicio'))

    # Leer opciones del formulario
    metodo_clustering  = request.form.get('metodo_clustering', 'kmeans')
    metodo_outliers    = request.form.get('metodo_outliers', 'iqr')
    metodo_correlacion = request.form.get('metodo_correlacion', 'pearson')

    # Guardar archivos y validar que se pueden leer
    rutas_archivos = []
    for archivo in archivos:
        ruta = os.path.join(CARPETA_SUBIDAS, archivo.filename)
        archivo.save(ruta)
        try:
            cargar_archivo(ruta)
        except ValueError as e:
            flash(f'Error en "{archivo.filename}": {str(e)}', 'error')
            return redirect(url_for('inicio'))
        rutas_archivos.append(ruta)

    # Ejecutar analisis
    try:
        resultados = ejecutar_analisis(
            rutas_archivos,
            metodo_clustering,
            metodo_outliers,
            metodo_correlacion
        )

        session['resultados']         = resultados
        session['metodo_clustering']  = metodo_clustering
        session['metodo_outliers']    = metodo_outliers
        session['metodo_correlacion'] = metodo_correlacion
        session['nombre_archivo']     = archivos[0].filename
        session['generado_en']        = datetime.now().strftime('%d/%m/%Y %H:%M')

        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f'Error al procesar el archivo: {str(e)}', 'error')
        return redirect(url_for('inicio'))


@app.route('/dashboard')
def dashboard():
    resultados = session.get('resultados')

    if not resultados:
        flash('No hay datos analizados. Carga un archivo primero.', 'error')
        return redirect(url_for('inicio'))

    return render_template(
        'dashboard.html',
        nombre_archivo     = session.get('nombre_archivo', '---'),
        metodo_clustering  = session.get('metodo_clustering', 'kmeans'),
        metodo_outliers    = session.get('metodo_outliers', 'iqr'),
        metodo_correlacion = session.get('metodo_correlacion', 'pearson'),
        estadisticas       = resultados['estadisticas'],
        columnas           = resultados['columnas'],
        stats_descriptivas = resultados['stats_descriptivas'],
        insights           = resultados['insights'],
        graficos           = resultados['graficos'],
        top_correlaciones  = resultados['top_correlaciones'],
        resumen_outliers   = resultados['resumen_outliers'],
        info_clusters      = resultados['info_clusters'],
    )


@app.route('/resultados')
def resultados():
    datos = session.get('resultados')

    if not datos:
        flash('No hay datos analizados. Carga un archivo primero.', 'error')
        return redirect(url_for('inicio'))

    return render_template(
        'results.html',
        nombre_archivo     = session.get('nombre_archivo', '---'),
        generado_en        = session.get('generado_en', '---'),
        metodo_clustering  = session.get('metodo_clustering', 'kmeans'),
        metodo_outliers    = session.get('metodo_outliers', 'iqr'),
        metodo_correlacion = session.get('metodo_correlacion', 'pearson'),
        estadisticas       = datos['estadisticas'],
        stats_numericas    = datos['stats_numericas'],
        stats_categoricas  = datos['stats_categoricas'],
        insights           = datos['insights'],
        graficos           = datos['graficos'],
        top_correlaciones  = datos['top_correlaciones'],
        filas_outliers     = datos['filas_outliers'],
        columnas_outliers  = datos['columnas_outliers'],
        detalle_clusters   = datos['detalle_clusters'],
    )


@app.route('/exportar')
def exportar():
    datos = session.get('resultados')

    if not datos:
        flash('No hay datos para exportar.', 'error')
        return redirect(url_for('inicio'))

    flash('Exportacion no disponible aun. Proximamente.', 'info')
    return redirect(url_for('resultados'))


# -------------------------------------------------------
# Funcion temporal de analisis con datos de prueba.
# -------------------------------------------------------

def ejecutar_analisis(rutas, metodo_clustering, metodo_outliers, metodo_correlacion):
    estadisticas = {
        'total_filas':       1250,
        'total_columnas':    8,
        'pct_faltantes':     3,
        'total_numericas':   5,
        'total_categoricas': 3,
        'total_outliers':    47,
        'total_clusters':    3,
    }

    columnas = [
        {'nombre': 'ventas',     'tipo': 'numerica',   'no_nulos': 1240, 'unicos': 980,  'completitud': 99},
        {'nombre': 'region',     'tipo': 'categorica', 'no_nulos': 1250, 'unicos': 5,    'completitud': 100},
        {'nombre': 'fecha',      'tipo': 'fecha',      'no_nulos': 1230, 'unicos': 365,  'completitud': 98},
        {'nombre': 'costo',      'tipo': 'numerica',   'no_nulos': 1100, 'unicos': 750,  'completitud': 88},
        {'nombre': 'categoria',  'tipo': 'categorica', 'no_nulos': 1250, 'unicos': 12,   'completitud': 100},
        {'nombre': 'descuento',  'tipo': 'numerica',   'no_nulos': 900,  'unicos': 20,   'completitud': 72},
        {'nombre': 'cliente_id', 'tipo': 'numerica',   'no_nulos': 1250, 'unicos': 800,  'completitud': 100},
        {'nombre': 'activo',     'tipo': 'categorica', 'no_nulos': 600,  'unicos': 2,    'completitud': 48},
    ]

    stats_descriptivas = [
        {'columna': 'ventas',     'media': '4520.3', 'mediana': '3800.0', 'desviacion': '2100.5', 'minimo': '50.0',  'maximo': '18000.0', 'asimetria': 1.4},
        {'columna': 'costo',      'media': '2100.8', 'mediana': '1900.0', 'desviacion': '980.2',  'minimo': '20.0',  'maximo': '9500.0',  'asimetria': 0.8},
        {'columna': 'descuento',  'media': '12.5',   'mediana': '10.0',   'desviacion': '8.3',    'minimo': '0.0',   'maximo': '50.0',    'asimetria': 0.3},
        {'columna': 'cliente_id', 'media': '5000.1', 'mediana': '5001.0', 'desviacion': '2886.8', 'minimo': '1.0',   'maximo': '9999.0',  'asimetria': 0.0},
    ]

    stats_numericas = [
        {'columna': 'ventas',     'conteo': 1240, 'media': '4520.3', 'mediana': '3800.0', 'desviacion': '2100.5', 'q1': '2200.0', 'q3': '6500.0', 'minimo': '50.0',  'maximo': '18000.0', 'asimetria': 1.4,  'curtosis': 2.1},
        {'columna': 'costo',      'conteo': 1100, 'media': '2100.8', 'mediana': '1900.0', 'desviacion': '980.2',  'q1': '1200.0', 'q3': '2900.0', 'minimo': '20.0',  'maximo': '9500.0',  'asimetria': 0.8,  'curtosis': 0.5},
        {'columna': 'descuento',  'conteo': 900,  'media': '12.5',   'mediana': '10.0',   'desviacion': '8.3',    'q1': '5.0',    'q3': '20.0',   'minimo': '0.0',   'maximo': '50.0',    'asimetria': 0.3,  'curtosis': -0.2},
        {'columna': 'cliente_id', 'conteo': 1250, 'media': '5000.1', 'mediana': '5001.0', 'desviacion': '2886.8', 'q1': '2500.0', 'q3': '7500.0', 'minimo': '1.0',   'maximo': '9999.0',  'asimetria': 0.0,  'curtosis': -1.2},
    ]

    stats_categoricas = [
        {'columna': 'region',    'conteo': 1250, 'unicos': 5,  'moda': 'Norte',       'frec_moda': 420, 'faltantes': 0},
        {'columna': 'categoria', 'conteo': 1250, 'unicos': 12, 'moda': 'Electronica', 'frec_moda': 310, 'faltantes': 0},
        {'columna': 'activo',    'conteo': 600,  'unicos': 2,  'moda': 'Si',          'frec_moda': 480, 'faltantes': 650},
    ]

    insights = [
        {'tipo': 'advertencia', 'icono': '⚠️', 'categoria': 'DISTRIBUCION', 'mensaje': "La variable 'ventas' presenta asimetria positiva fuerte (skew=1.4). Se recomienda aplicar transformacion logaritmica antes del modelado."},
        {'tipo': 'peligro',     'icono': '🔴', 'categoria': 'CALIDAD',      'mensaje': "La columna 'activo' tiene solo 48% de completitud. Considerar imputacion o exclusion del analisis."},
        {'tipo': 'info',        'icono': '🔗', 'categoria': 'CORRELACION',  'mensaje': "Existe correlacion fuerte (r=0.87) entre 'ventas' y 'costo'. A mayor costo, mayores ventas."},
        {'tipo': 'exito',       'icono': '✅', 'categoria': 'CLUSTERING',   'mensaje': "Se detectaron 3 grupos principales. El Cluster 2 agrupa clientes con ventas superiores al promedio."},
        {'tipo': 'advertencia', 'icono': '🔍', 'categoria': 'OUTLIERS',     'mensaje': "El 3.8% de los registros presentan valores atipicos en la columna 'ventas'."},
    ]

    top_correlaciones = [
        {'var1': 'ventas',    'var2': 'costo',      'r': 0.87},
        {'var1': 'ventas',    'var2': 'descuento',  'r': 0.54},
        {'var1': 'costo',     'var2': 'descuento',  'r': 0.41},
        {'var1': 'ventas',    'var2': 'cliente_id', 'r': 0.12},
    ]

    resumen_outliers = [
        {'columna': 'ventas',    'cantidad': 32, 'porcentaje': 2.6},
        {'columna': 'descuento', 'cantidad': 15, 'porcentaje': 1.2},
    ]

    filas_outliers = [
        {'indice': 45,  'cols_afectadas': 2, 'valores': [{'valor': '18000.0', 'es_outlier': True},  {'valor': '50.0', 'es_outlier': True}]},
        {'indice': 312, 'cols_afectadas': 1, 'valores': [{'valor': '17500.0', 'es_outlier': True},  {'valor': '12.0', 'es_outlier': False}]},
        {'indice': 890, 'cols_afectadas': 1, 'valores': [{'valor': '50.0',    'es_outlier': False}, {'valor': '50.0', 'es_outlier': True}]},
    ]

    columnas_outliers = ['ventas', 'descuento']

    info_clusters = [
        {'id': 1, 'tamanio': 480, 'descripcion': 'Clientes con ventas bajas y descuentos minimos. Perfil de comprador ocasional.'},
        {'id': 2, 'tamanio': 420, 'descripcion': 'Clientes con ventas medias y descuentos moderados. Segmento principal del negocio.'},
        {'id': 3, 'tamanio': 350, 'descripcion': 'Clientes con ventas altas y descuentos elevados. Compradores frecuentes de alto valor.'},
    ]

    detalle_clusters = [
        {
            'id': 1, 'tamanio': 480, 'porcentaje': 38,
            'estadisticas': [
                {'columna': 'ventas',    'media_cluster': '1200.5', 'media_global': '4520.3'},
                {'columna': 'costo',     'media_cluster': '800.2',  'media_global': '2100.8'},
                {'columna': 'descuento', 'media_cluster': '5.1',    'media_global': '12.5'},
            ]
        },
        {
            'id': 2, 'tamanio': 420, 'porcentaje': 34,
            'estadisticas': [
                {'columna': 'ventas',    'media_cluster': '4100.0', 'media_global': '4520.3'},
                {'columna': 'costo',     'media_cluster': '2000.5', 'media_global': '2100.8'},
                {'columna': 'descuento', 'media_cluster': '12.8',   'media_global': '12.5'},
            ]
        },
        {
            'id': 3, 'tamanio': 350, 'porcentaje': 28,
            'estadisticas': [
                {'columna': 'ventas',    'media_cluster': '9800.3', 'media_global': '4520.3'},
                {'columna': 'costo',     'media_cluster': '4200.1', 'media_global': '2100.8'},
                {'columna': 'descuento', 'media_cluster': '28.4',   'media_global': '12.5'},
            ]
        },
    ]

    graficos = {
        'distribuciones': [],
        'correlacion':    None,
        'outliers':       None,
        'clustering':     None,
    }

    return {
        'estadisticas':       estadisticas,
        'columnas':           columnas,
        'stats_descriptivas': stats_descriptivas,
        'stats_numericas':    stats_numericas,
        'stats_categoricas':  stats_categoricas,
        'insights':           insights,
        'graficos':           graficos,
        'top_correlaciones':  top_correlaciones,
        'resumen_outliers':   resumen_outliers,
        'filas_outliers':     filas_outliers,
        'columnas_outliers':  columnas_outliers,
        'info_clusters':      info_clusters,
        'detalle_clusters':   detalle_clusters,
    }


# -------------------------------------------------------
# Manejo de errores
# -------------------------------------------------------

@app.errorhandler(404)
def pagina_no_encontrada(e):
    return render_template('index.html'), 404


@app.errorhandler(413)
def archivo_muy_grande(e):
    flash('El archivo supera el limite de 16 MB.', 'error')
    return redirect(url_for('inicio'))


if __name__ == '__main__':
    app.run(debug=True)
