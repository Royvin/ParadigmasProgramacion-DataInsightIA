"""
DataInsight AI - Aplicación principal
Flask web app para análisis exploratorio automatizado de datos.
Permite cargar archivos CSV/Excel, calcular correlaciones, y mostrar resultados.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from modules.loader import cargar_archivo, obtener_info_archivo
from modules.analyzer import analizar
from modules.correlations import calcular_correlaciones, generar_grafico_correlacion
import os
from datetime import datetime
import pickle
import uuid
import time

# ==========================
# Inicialización de la app
# ==========================
app = Flask(__name__)

# Clave secreta para sesiones (usar variable de entorno en producción)
app.secret_key = os.environ.get('SECRET_KEY', 'datainsight-dev-key-2024')

# Carpeta donde se guardarán los archivos subidos y los resultados serializados
CARPETA_SUBIDAS = os.path.join(os.path.dirname(__file__), 'subidas')
os.makedirs(CARPETA_SUBIDAS, exist_ok=True)

# Extensiones de archivo permitidas
EXTENSIONES_PERMITIDAS = {'csv', 'xlsx', 'xls'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Límite de 16 MB

# ===================================================
# Funciones auxiliares para manejo de resultados en disco
# ===================================================
def guardar_resultados(resultados):
    """
    Guarda un diccionario de resultados en un archivo pickle dentro de CARPETA_SUBIDAS.
    Retorna el nombre único del archivo (para almacenar en la sesión).
    """
    nombre_archivo = f"resultados_{uuid.uuid4().hex}.pkl"
    ruta = os.path.join(CARPETA_SUBIDAS, nombre_archivo)
    with open(ruta, 'wb') as f:
        pickle.dump(resultados, f)
    return nombre_archivo

def cargar_resultados(nombre_archivo):
    """
    Carga un diccionario de resultados desde un archivo pickle.
    """
    ruta = os.path.join(CARPETA_SUBIDAS, nombre_archivo)
    with open(ruta, 'rb') as f:
        return pickle.load(f)

def limpiar_resultados_antiguos():
    """
    Elimina archivos de resultados con más de 1 hora de antigüedad.
    Evita acumulación de basura en el servidor.
    """
    ahora = time.time()
    for archivo in os.listdir(CARPETA_SUBIDAS):
        if archivo.startswith('resultados_') and archivo.endswith('.pkl'):
            ruta = os.path.join(CARPETA_SUBIDAS, archivo)
            if os.path.getmtime(ruta) < ahora - 3600:  # 1 hora
                try:
                    os.remove(ruta)
                except:
                    pass  # Si falla, ignorar (p.ej. archivo en uso)

def extension_permitida(nombre_archivo):
    """
    Verifica si la extensión del archivo está dentro de las permitidas.
    """
    return '.' in nombre_archivo and \
           nombre_archivo.rsplit('.', 1)[1].lower() in EXTENSIONES_PERMITIDAS

# ===================================================
# Rutas (endpoints) de la aplicación
# ===================================================

@app.route('/')
def inicio():
    """Página de inicio con el formulario de carga de archivos."""
    return render_template('index.html')

@app.route('/cargar', methods=['POST'])
def cargar():
    """
    Recibe uno o varios archivos, valida extensiones, los guarda en disco,
    ejecuta el análisis (estadísticas + correlaciones) y redirige al dashboard.
    """
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

    # Leer opciones del formulario (métodos de análisis)
    metodo_clustering = request.form.get('metodo_clustering', 'kmeans')
    metodo_outliers = request.form.get('metodo_outliers', 'zscore')
    metodo_correlacion = request.form.get('metodo_correlacion', 'pearson')

    # Guardar archivos físicamente y verificar que se puedan leer
    rutas_archivos = []
    for archivo in archivos:
        ruta = os.path.join(CARPETA_SUBIDAS, archivo.filename)
        archivo.save(ruta)
        try:
            cargar_archivo(ruta)  # Prueba de carga (valida formato)
        except ValueError as e:
            flash(f'Error en "{archivo.filename}": {str(e)}', 'error')
            return redirect(url_for('inicio'))
        rutas_archivos.append(ruta)

    # Ejecutar análisis completo
    try:
        resultados = ejecutar_analisis(
            rutas_archivos,
            metodo_clustering,
            metodo_outliers,
            metodo_correlacion
        )

        # Guardar resultados en disco (no en sesión, para evitar cookie enorme)
        nombre_res = guardar_resultados(resultados)
        session['resultados_file'] = nombre_res
        session['metodo_clustering'] = metodo_clustering
        session['metodo_outliers'] = metodo_outliers
        session['metodo_correlacion'] = metodo_correlacion
        session['nombre_archivo'] = archivos[0].filename
        session['generado_en'] = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        # Limpiar archivos de resultados antiguos (opcional)
        limpiar_resultados_antiguos()

        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f'Error al procesar el archivo: {str(e)}', 'error')
        return redirect(url_for('inicio'))

@app.route('/dashboard')
def dashboard():
    """
    Muestra un resumen visual (dashboard) con estadísticas, gráficos y correlaciones.
    Los resultados se cargan desde el archivo pickle guardado en sesión.
    """
    nombre_res = session.get('resultados_file')
    if not nombre_res:
        flash('No hay datos analizados. Carga un archivo primero.', 'error')
        return redirect(url_for('inicio'))
    
    ruta_res = os.path.join(CARPETA_SUBIDAS, nombre_res)
    if not os.path.exists(ruta_res):
        flash('Los resultados expiraron. Carga el archivo nuevamente.', 'error')
        return redirect(url_for('inicio'))
    
    resultados = cargar_resultados(nombre_res)

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
    """
    Muestra un reporte detallado con todas las estadísticas numéricas, categóricas,
    correlaciones, outliers (placeholder) y clustering (placeholder).
    """
    nombre_res = session.get('resultados_file')
    if not nombre_res:
        flash('No hay datos analizados. Carga un archivo primero.', 'error')
        return redirect(url_for('inicio'))
    
    ruta_res = os.path.join(CARPETA_SUBIDAS, nombre_res)
    if not os.path.exists(ruta_res):
        flash('Los resultados expiraron. Carga el archivo nuevamente.', 'error')
        return redirect(url_for('inicio'))
    
    datos = cargar_resultados(nombre_res)

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
    #   """
    #   Endpoint para exportar el reporte (aún no implementado completamente).
    #   """
    nombre_res = session.get('resultados_file')
    if not nombre_res:
        flash('No hay datos para exportar.', 'error')
        return redirect(url_for('inicio'))
    
    ruta_res = os.path.join(CARPETA_SUBIDAS, nombre_res)
    if not os.path.exists(ruta_res):
        flash('Los resultados expiraron. Carga el archivo nuevamente.', 'error')
        return redirect(url_for('inicio'))
    
    # Cargamos datos para uso futuro (exportación real pendiente)
    datos = cargar_resultados(nombre_res)
    flash('Exportacion no disponible aun. Proximamente.', 'info')
    return redirect(url_for('resultados'))

# ===================================================
# Función principal de análisis
# ===================================================
def ejecutar_analisis(rutas, metodo_clustering, metodo_outliers, metodo_correlacion):
    """
    Orquesta el análisis completo del primer archivo (por ahora solo uno).
    Calcula estadísticas básicas, correlaciones y genera insights.
    
    Parámetros:
        rutas: lista de rutas de archivos (solo se usa la primera)
        metodo_clustering: string (placeholder)
        metodo_outliers: string (placeholder)
        metodo_correlacion: 'pearson' o 'spearman'
    
    Retorna:
        dict con todas las claves necesarias para las plantillas.
    """
    # Cargar el primer archivo como DataFrame
    df = cargar_archivo(rutas[0])

    # Análisis básico (estadísticas, tipos de columnas, etc.)
    resultado_analisis = analizar(df)

    estadisticas = resultado_analisis['estadisticas']
    columnas = resultado_analisis['columnas']
    stats_descriptivas = resultado_analisis['stats_descriptivas']
    stats_numericas = resultado_analisis['stats_numericas']
    stats_categoricas = resultado_analisis['stats_categoricas']

    # ========== CÁLCULO DE CORRELACIONES ==========
    
    corr_data = calcular_correlaciones(df, metodo_correlacion)
    top_correlaciones = corr_data['top_pares'][:5]   # Top 5 pares con mayor |r|
    grafico_corr = generar_grafico_correlacion(corr_data['matriz'], metodo_correlacion)

    # ========== GENERACIÓN DE INSIGHTS (basados en correlaciones) ==========
    insights = []
    if top_correlaciones:
        par_fuerte = top_correlaciones[0]
        r_abs = abs(par_fuerte['r'])
        if r_abs > 0.7:
            mensaje = f"Correlación muy fuerte ({r_abs:.2f}) entre '{par_fuerte['var1']}' y '{par_fuerte['var2']}'. Esto sugiere una relación lineal importante."
        elif r_abs > 0.4:
            mensaje = f"Correlación moderada ({r_abs:.2f}) entre '{par_fuerte['var1']}' y '{par_fuerte['var2']}'."
        else:
            mensaje = f"La correlación más alta es {r_abs:.2f} entre '{par_fuerte['var1']}' y '{par_fuerte['var2']}', indicando una relación débil."
        insights.append({
            'tipo': 'info',
            'icono': '📈',
            'categoria': 'CORRELACIÓN',
            'mensaje': mensaje
        })
    else:
        insights.append({
            'tipo': 'advertencia',
            'icono': '⚠️',
            'categoria': 'CORRELACIÓN',
            'mensaje': 'No hay suficientes columnas numéricas para calcular correlaciones (se necesitan al menos 2).'
        })

    # Insight general del análisis
    insights.append({
        'tipo': 'info',
        'icono': '📊',
        'categoria': 'ANÁLISIS',
        'mensaje': f"Análisis exploratorio completado. Se encontraron {len(columnas)} columnas y {estadisticas['total_filas']} filas."
    })

    # ========== OUTLIERS Y CLUSTERING (placeholders para desarrollo futuro) ==========
    resumen_outliers = []
    filas_outliers = []
    columnas_outliers = []
    info_clusters = []
    detalle_clusters = []

    # ========== GRÁFICOS (por ahora solo el de correlación) ==========
    graficos = {
        'distribuciones': [],   # Histogramas, boxplots (pendiente)
        'correlacion': grafico_corr,
        'outliers': None,
        'clustering': None,
    }

    # Actualizar estadísticas con valores por defecto (outliers y clusters aún no implementados)
    estadisticas['total_outliers'] = 0
    estadisticas['total_clusters'] = 0

    # Devolver todos los datos necesarios para las vistas
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

# ===================================================
# Manejadores de errores HTTP
# ===================================================
@app.errorhandler(404)
def pagina_no_encontrada(e):
    """Página no encontrada: redirige al inicio con error silencioso (código 404)."""
    return render_template('index.html'), 404

@app.errorhandler(413)
def archivo_muy_grande(e):
    """Error de tamaño de archivo excedido (16 MB)."""
    flash('El archivo supera el limite de 16 MB.', 'error')
    return redirect(url_for('inicio'))

# ===================================================
# Punto de entrada de la aplicación
# ===================================================
if __name__ == '__main__':
    app.run(debug=True)