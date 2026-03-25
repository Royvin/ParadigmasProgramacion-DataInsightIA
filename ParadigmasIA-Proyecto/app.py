from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from modules.loader import cargar_archivo, obtener_info_archivo
from modules.analyzer import analizar
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
    metodo_clustering = request.form.get('metodo_clustering', 'kmeans')
    metodo_outliers = request.form.get('metodo_outliers', 'zscore')
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

        session['resultados'] = resultados
        session['metodo_clustering'] = metodo_clustering
        session['metodo_outliers'] = metodo_outliers
        session['metodo_correlacion'] = metodo_correlacion
        session['nombre_archivo'] = archivos[0].filename
        session['generado_en'] = datetime.now().strftime('%d/%m/%Y %H:%M')

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
        nombre_archivo = session.get('nombre_archivo', '---'),
        metodo_clustering = session.get('metodo_clustering', 'kmeans'),
        metodo_outliers = session.get('metodo_outliers', 'iqr'),
        metodo_correlacion = session.get('metodo_correlacion', 'pearson'),
        estadisticas = resultados['estadisticas'],
        columnas = resultados['columnas'],
        stats_descriptivas = resultados['stats_descriptivas'],
        insights = resultados['insights'],
        graficos = resultados['graficos'],
        top_correlaciones = resultados['top_correlaciones'],
        resumen_outliers = resultados['resumen_outliers'],
        info_clusters = resultados['info_clusters'],
    )


@app.route('/resultados')
def resultados():
    datos = session.get('resultados')

    if not datos:
        flash('No hay datos analizados. Carga un archivo primero.', 'error')
        return redirect(url_for('inicio'))

    return render_template(
        'results.html',
        nombre_archivo = session.get('nombre_archivo', '---'),
        generado_en  = session.get('generado_en', '---'),
        metodo_clustering  = session.get('metodo_clustering', 'kmeans'),
        metodo_outliers = session.get('metodo_outliers', 'zscore'),
        metodo_correlacion = session.get('metodo_correlacion', 'pearson'),
        estadisticas = datos['estadisticas'],
        stats_numericas  = datos['stats_numericas'],
        stats_categoricas = datos['stats_categoricas'],
        insights = datos['insights'],
        graficos = datos['graficos'],
        top_correlaciones  = datos['top_correlaciones'],
        filas_outliers = datos['filas_outliers'],
        columnas_outliers = datos['columnas_outliers'],
        detalle_clusters  = datos['detalle_clusters'],
    )


@app.route('/exportar')
def exportar():
    datos = session.get('resultados')

    if not datos:
        flash('No hay datos para exportar.', 'error')
        return redirect(url_for('inicio'))

    flash('Exportacion no disponible aun. Proximamente.', 'info')
    return redirect(url_for('resultados'))


def ejecutar_analisis(rutas, metodo_clustering, metodo_outliers, metodo_correlacion): 
    df = cargar_archivo(rutas[0])
 
    resultado_analisis = analizar(df)
 
    estadisticas = resultado_analisis['estadisticas']
    columnas = resultado_analisis['columnas']
    stats_descriptivas = resultado_analisis['stats_descriptivas']
    stats_numericas = resultado_analisis['stats_numericas']
    stats_categoricas = resultado_analisis['stats_categoricas']
 
    insights = [
        {'tipo': 'info', 'icono': '📊', 'categoria': 'ANALISIS',
         'mensaje': 'Analisis exploratorio completado. Proximas versiones incluiran correlaciones, outliers y clustering reales.'},
    ]
 
    top_correlaciones = []
    resumen_outliers = []
    filas_outliers = []
    columnas_outliers = []
    info_clusters = []
    detalle_clusters = []
 
    graficos = {
        'distribuciones': [],
        'correlacion': None,
        'outliers': None,
        'clustering': None,
    }
 
    return {
        'estadisticas': estadisticas,
        'columnas':  columnas,
        'stats_descriptivas': stats_descriptivas,
        'stats_numericas': stats_numericas,
        'stats_categoricas': stats_categoricas,
        'insights': insights,
        'graficos': graficos,
        'top_correlaciones': top_correlaciones,
        'resumen_outliers': resumen_outliers,
        'filas_outliers': filas_outliers,
        'columnas_outliers': columnas_outliers,
        'info_clusters': info_clusters,
        'detalle_clusters': detalle_clusters,
    }

# Manejo de errores

@app.errorhandler(404)
def pagina_no_encontrada(e):
    return render_template('index.html'), 404


@app.errorhandler(413)
def archivo_muy_grande(e):
    flash('El archivo supera el limite de 16 MB.', 'error')
    return redirect(url_for('inicio'))


if __name__ == '__main__':
    app.run(debug=True)
