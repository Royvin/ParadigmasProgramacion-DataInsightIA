from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from modules.loader import cargar_archivo, obtener_info_archivo
from modules.analyzer import analizar
from modules.correlations import calcular_correlaciones, generar_grafico_correlacion
from modules.outliers import detectar_outliers, generar_grafico_outliers
from modules.analyzer import obtener_columnas_numericas
from modules.clustering import aplicar_clustering, generar_grafico_clusters, obtener_info_clusters
from modules.exporter import generar_pdf
import os
from datetime import datetime
import pickle
import uuid
import time

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY', 'datainsight-dev-key-2024')

app.jinja_env.filters['enumerate'] = enumerate

CARPETA_SUBIDAS = os.path.join(os.path.dirname(__file__), 'subidas')
os.makedirs(CARPETA_SUBIDAS, exist_ok=True)

EXTENSIONES_PERMITIDAS = {'csv', 'xlsx', 'xls'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


def guardar_resultados(resultados):
    nombre_archivo = f"resultados_{uuid.uuid4().hex}.pkl"
    ruta = os.path.join(CARPETA_SUBIDAS, nombre_archivo)
    with open(ruta, 'wb') as f:
        pickle.dump(resultados, f)
    return nombre_archivo


def cargar_resultados(nombre_archivo):
    ruta = os.path.join(CARPETA_SUBIDAS, nombre_archivo)
    with open(ruta, 'rb') as f:
        return pickle.load(f)


def limpiar_resultados_antiguos():
    ahora = time.time()
    for archivo in os.listdir(CARPETA_SUBIDAS):
        if archivo.startswith('resultados_') and archivo.endswith('.pkl'):
            ruta = os.path.join(CARPETA_SUBIDAS, archivo)
            if os.path.getmtime(ruta) < ahora - 3600:
                try:
                    os.remove(ruta)
                except:
                    pass


def extension_permitida(nombre_archivo):
    return '.' in nombre_archivo and \
           nombre_archivo.rsplit('.', 1)[1].lower() in EXTENSIONES_PERMITIDAS


# Rutas

@app.route('/')
def inicio():
    return render_template('index.html')


@app.route('/cargar', methods=['POST'])
def cargar():
    archivos = request.files.getlist('archivos')

    if not archivos or archivos[0].filename == '':
        flash('Debes seleccionar al menos un archivo.', 'error')
        return redirect(url_for('inicio'))

    for archivo in archivos:
        if not extension_permitida(archivo.filename):
            flash(f'El archivo "{archivo.filename}" no es valido. Solo se aceptan CSV, XLSX y XLS.', 'error')
            return redirect(url_for('inicio'))

    metodo_clustering = request.form.get('metodo_clustering',  'kmeans')
    metodo_outliers = request.form.get('metodo_outliers',    'zscore')
    metodo_correlacion = request.form.get('metodo_correlacion', 'pearson')

    # Guardar archivos y verificar que se puedan leer
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

    try:
        # Analizar cada archivo por separado y guardar lista de resultados
        lista_resultados = []
        for ruta in rutas_archivos:
            nombre = os.path.basename(ruta)
            resultado = ejecutar_analisis(
                ruta,
                metodo_clustering,
                metodo_outliers,
                metodo_correlacion
            )
            resultado['nombre_archivo'] = nombre
            lista_resultados.append(resultado)

        nombre_res = guardar_resultados(lista_resultados)

        session['resultados_file'] = nombre_res
        session['metodo_clustering'] = metodo_clustering
        session['metodo_outliers'] = metodo_outliers
        session['metodo_correlacion'] = metodo_correlacion
        session['generado_en'] = datetime.now().strftime('%d/%m/%Y %H:%M')
        session['total_archivos'] = len(lista_resultados)

        limpiar_resultados_antiguos()
        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f'Error al procesar el archivo: {str(e)}', 'error')
        return redirect(url_for('inicio'))


@app.route('/dashboard')
def dashboard():
    nombre_res = session.get('resultados_file')
    if not nombre_res:
        flash('No hay datos analizados. Carga un archivo primero.', 'error')
        return redirect(url_for('inicio'))

    ruta_res = os.path.join(CARPETA_SUBIDAS, nombre_res)
    if not os.path.exists(ruta_res):
        flash('Los resultados expiraron. Carga el archivo nuevamente.', 'error')
        return redirect(url_for('inicio'))

    lista_resultados = cargar_resultados(nombre_res)

    # Indice del archivo activo (por defecto el primero)
    indice = request.args.get('archivo', 0, type=int)
    indice = max(0, min(indice, len(lista_resultados) - 1))

    resultados = lista_resultados[indice]

    # Lista de nombres para el selector
    nombres_archivos = [r['nombre_archivo'] for r in lista_resultados]

    return render_template(
        'dashboard.html',
        nombre_archivo = resultados['nombre_archivo'],
        metodo_clustering = session.get('metodo_clustering',  'kmeans'),
        metodo_outliers = session.get('metodo_outliers',    'zscore'),
        metodo_correlacion = session.get('metodo_correlacion', 'pearson'),
        estadisticas = resultados['estadisticas'],
        columnas = resultados['columnas'],
        stats_descriptivas = resultados['stats_descriptivas'],
        insights = resultados['insights'],
        graficos = resultados['graficos'],
        top_correlaciones = resultados['top_correlaciones'],
        resumen_outliers = resultados['resumen_outliers'],
        info_clusters = resultados['info_clusters'],
        # Para el selector de archivos
        nombres_archivos = nombres_archivos,
        indice_activo = indice,
    )


@app.route('/resultados')
def resultados():
    nombre_res = session.get('resultados_file')
    if not nombre_res:
        flash('No hay datos analizados. Carga un archivo primero.', 'error')
        return redirect(url_for('inicio'))

    ruta_res = os.path.join(CARPETA_SUBIDAS, nombre_res)
    if not os.path.exists(ruta_res):
        flash('Los resultados expiraron. Carga el archivo nuevamente.', 'error')
        return redirect(url_for('inicio'))

    lista_resultados = cargar_resultados(nombre_res)

    indice = request.args.get('archivo', 0, type=int)
    indice = max(0, min(indice, len(lista_resultados) - 1))

    datos = lista_resultados[indice]

    nombres_archivos = [r['nombre_archivo'] for r in lista_resultados]

    return render_template(
        'results.html',
        nombre_archivo = datos['nombre_archivo'],
        generado_en = session.get('generado_en', '---'),
        metodo_clustering = session.get('metodo_clustering',  'kmeans'),
        metodo_outliers = session.get('metodo_outliers',    'zscore'),
        metodo_correlacion = session.get('metodo_correlacion', 'pearson'),
        estadisticas = datos['estadisticas'],
        stats_numericas = datos['stats_numericas'],
        stats_categoricas = datos['stats_categoricas'],
        insights = datos['insights'],
        graficos = datos['graficos'],
        top_correlaciones = datos['top_correlaciones'],
        filas_outliers = datos['filas_outliers'],
        columnas_outliers = datos['columnas_outliers'],
        detalle_clusters = datos['detalle_clusters'],
        # Para el selector de archivos
        nombres_archivos = nombres_archivos,
        indice_activo = indice,
    )

@app.route('/exportar')
def exportar():
    nombre_res = session.get('resultados_file')
    if not nombre_res:
        flash('No hay datos para exportar.', 'error')
        return redirect(url_for('inicio'))

    ruta_res = os.path.join(CARPETA_SUBIDAS, nombre_res)
    if not os.path.exists(ruta_res):
        flash('Los resultados expiraron. Carga el archivo nuevamente.', 'error')
        return redirect(url_for('inicio'))

    try:
        lista_resultados = cargar_resultados(nombre_res)

        # Exportar el archivo activo
        indice = request.args.get('archivo', 0, type=int)
        indice = max(0, min(indice, len(lista_resultados) - 1))
        datos  = lista_resultados[indice]

        metodos = {
            'clustering': session.get('metodo_clustering',  'kmeans'),
            'outliers': session.get('metodo_outliers',    'zscore'),
            'correlacion': session.get('metodo_correlacion', 'pearson'),
        }

        ruta_pdf = generar_pdf(
            datos=datos,
            nombre_archivo=datos['nombre_archivo'],
            metodos=metodos,
        )

        nombre_descarga = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return send_file(
            ruta_pdf,
            as_attachment=True,
            download_name=nombre_descarga,
            mimetype='application/pdf',
        )

    except Exception as e:
        flash(f'Error al generar el PDF: {str(e)}', 'error')
        return redirect(url_for('resultados'))


#Funcion de analisis

def ejecutar_analisis(ruta, metodo_clustering, metodo_outliers ,metodo_correlacion):
    df = cargar_archivo(ruta)

    resultado_analisis = analizar(df)
    estadisticas = resultado_analisis['estadisticas']
    columnas = resultado_analisis['columnas']
    stats_descriptivas = resultado_analisis['stats_descriptivas']
    stats_numericas = resultado_analisis['stats_numericas']
    stats_categoricas = resultado_analisis['stats_categoricas']

    # Correlaciones
    corr_data = calcular_correlaciones(df, metodo_correlacion)
    top_correlaciones = corr_data['top_pares'][:5]
    grafico_corr = generar_grafico_correlacion(corr_data['matriz'], metodo_correlacion)

    # Outliers
    cols_numericas = obtener_columnas_numericas(df)
    resultado_outliers = detectar_outliers(df, cols_numericas)

    resumen_outliers = resultado_outliers['resumen_outliers']
    filas_outliers = resultado_outliers['filas_outliers']
    columnas_outliers = resultado_outliers['columnas_outliers']
    total_outliers = resultado_outliers['total_outliers']
    mascara_outliers = resultado_outliers['mascara']

    grafico_outliers = generar_grafico_outliers(df, mascara_outliers, columnas_outliers)

    # Insights
    insights = []

    if top_correlaciones:
        par   = top_correlaciones[0]
        r_abs = abs(par['r'])
        if r_abs > 0.7:
            msg  = f"Correlacion muy fuerte ({r_abs:.2f}) entre '{par['var1']}' y '{par['var2']}'."
            tipo = 'info'
        elif r_abs > 0.4:
            msg  = f"Correlacion moderada ({r_abs:.2f}) entre '{par['var1']}' y '{par['var2']}'."
            tipo = 'info'
        else:
            msg  = f"No se detectaron correlaciones fuertes. La mas alta es {r_abs:.2f}."
            tipo = 'advertencia'
        insights.append({'tipo': tipo, 'icono': '📈', 'categoria': 'CORRELACION', 'mensaje': msg})
    else:
        insights.append({
            'tipo': 'advertencia', 'icono': '⚠️', 'categoria': 'CORRELACION',
            'mensaje': 'No hay suficientes columnas numericas para calcular correlaciones.'
        })

    if total_outliers > 0:
        pct     = round((total_outliers / estadisticas['total_filas']) * 100, 1)
        col_mas = resumen_outliers[0]['columna'] if resumen_outliers else '---'
        tipo_out = 'peligro' if pct > 5 else 'advertencia'
        insights.append({
            'tipo': tipo_out, 'icono': '🔍', 'categoria': 'OUTLIERS',
            'mensaje': f"Se detectaron {total_outliers} registros atipicos ({pct}% del total). La columna con mas outliers es '{col_mas}'."
        })
    else:
        insights.append({
            'tipo': 'exito', 'icono': '✅', 'categoria': 'OUTLIERS',
            'mensaje': 'No se detectaron valores atipicos significativos en el dataset.'
        })

    insights.append({
        'tipo': 'info', 'icono': '📊', 'categoria': 'ANALISIS',
        'mensaje': f"Dataset analizado: {estadisticas['total_filas']} filas, {estadisticas['total_columnas']} columnas, {estadisticas['total_numericas']} variables numericas."
    })

    # Clustering
    labels, n_clusters, centroides, silhouette = aplicar_clustering(df, cols_numericas)

    if labels is not None and n_clusters > 0:
        grafico_clusters             = generar_grafico_clusters(df, labels, cols_numericas)
        info_clusters, detalle_clusters = obtener_info_clusters(df, labels, centroides, cols_numericas)
        estadisticas['total_clusters'] = n_clusters
        insights.append({
            'tipo': 'info', 'icono': '🧩', 'categoria': 'CLUSTERING',
            'mensaje': f"Se detectaron {n_clusters} agrupaciones principales. El grupo mas grande contiene {max(c['tamanio'] for c in info_clusters)} registros."
        })
    else:
        grafico_clusters = None
        info_clusters = []
        detalle_clusters = []
        estadisticas['total_clusters'] = 0
        insights.append({
            'tipo': 'advertencia', 'icono': '⚠️', 'categoria': 'CLUSTERING',
            'mensaje': 'No fue posible realizar clustering (se necesitan al menos 2 columnas numericas y 10 registros).'
        })

    estadisticas['total_outliers'] = total_outliers

    graficos = {
        'distribuciones': [],
        'correlacion': grafico_corr,
        'outliers': grafico_outliers,
        'clustering': grafico_clusters,
    }

    return {
        'estadisticas': estadisticas,
        'columnas': columnas,
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