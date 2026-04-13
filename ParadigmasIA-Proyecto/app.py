from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from modules.loader import cargar_archivo, obtener_info_archivo
from modules.analyzer import analizar
from modules.correlations import calcular_correlaciones, generar_grafico_correlacion
from modules.outliers import detectar_outliers, generar_grafico_outliers
from modules.analyzer import obtener_columnas_numericas
from modules.clustering import aplicar_clustering, generar_grafico_clusters, obtener_info_clusters
import os
from datetime import datetime
import pickle
import uuid
import time
import openpyxl  
from openpyxl.styles import Font, PatternFill, Alignment  
import tempfile 

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY', 'datainsight-dev-key-2024')

# Carpeta donde se guardarán los archivos subidos y los resultados serializados
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
            if os.path.getmtime(ruta) < ahora - 3600:  # 1 hora
                try:
                    os.remove(ruta)
                except:
                    pass

def extension_permitida(nombre_archivo):
    return '.' in nombre_archivo and \
           nombre_archivo.rsplit('.', 1)[1].lower() in EXTENSIONES_PERMITIDAS

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
            cargar_archivo(ruta)
        except ValueError as e:
            flash(f'Error en "{archivo.filename}": {str(e)}', 'error')
            return redirect(url_for('inicio'))
        rutas_archivos.append(ruta)

    try:
        resultados = ejecutar_analisis(
            rutas_archivos,
            metodo_clustering,
            metodo_outliers,
            metodo_correlacion
        )

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
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch, cm
    import tempfile
    
    nombre_res = session.get('resultados_file')
    if not nombre_res:
        flash('No hay datos para exportar.', 'error')
        return redirect(url_for('inicio'))
    
    ruta_res = os.path.join(CARPETA_SUBIDAS, nombre_res)
    if not os.path.exists(ruta_res):
        flash('Los resultados expiraron. Carga el archivo nuevamente.', 'error')
        return redirect(url_for('inicio'))
    
    pdf_path = None
    try:
        #Cargar resultados completos
        datos = cargar_resultados(nombre_res)
        
        #Crear archivo PDF temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_path = tmp_file.name
        
        #Crear documento PDF
        doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        story = []
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2c3e50'),
            alignment=1,
            spaceAfter=30,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceBefore=20,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        )
        
        story.append(Paragraph("DataInsight IA", title_style))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph("Reporte de Análisis de Datos", styles['Heading2']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Archivo: {session.get('nombre_archivo', 'archivo.csv')}", styles['Normal']))
        story.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        story.append(PageBreak())

        story.append(Paragraph("1. Resumen General", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        stats = datos.get('estadisticas', {})
        
        stats_data = [
            ['Metrica', 'Valor'],
            ['Total Filas', str(stats.get('total_filas', 0))],
            ['Total Columnas', str(stats.get('total_columnas', 0))],
            ['Variables Numericas', str(stats.get('total_numericas', 0))],
            ['Variables Categoricas', str(stats.get('total_categoricas', 0))],
            ['% Datos Faltantes', f"{stats.get('pct_faltantes', 0)}%"],
            ['Outliers Detectados', str(stats.get('total_outliers', 0))],
            ['Clusters Encontrados', str(stats.get('total_clusters', 0))]
        ]
        
        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(stats_table)

        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("2. Metodos de Analisis", heading_style))
        
        methods_data = [
            ['Tecnica', 'Metodo'],
            ['Clustering', session.get('metodo_clustering', 'kmeans')],
            ['Deteccion de Outliers', session.get('metodo_outliers', 'zscore')],
            ['Correlacion', session.get('metodo_correlacion', 'pearson')]
        ]
        
        methods_table = Table(methods_data, colWidths=[2.5*inch, 2.5*inch])
        methods_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(methods_table)
        
        story.append(PageBreak())
        story.append(Paragraph("3. Insights Detectados", heading_style))
        
        insights = datos.get('insights', [])
        for insight in insights:
            icono = insight.get('icono', '📊')
            categoria = insight.get('categoria', '')
            mensaje = insight.get('mensaje', '')
            
            # Texto plano sin HTML
            texto = f"{icono} {categoria}: {mensaje}"
            story.append(Paragraph(texto, styles['Normal']))
            story.append(Spacer(1, 0.05*inch))
        
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("4. Top Correlaciones", heading_style))
        
        correlaciones = datos.get('top_correlaciones', [])
        if correlaciones:
            corr_data = [['Variable 1', 'Variable 2', 'Coeficiente', 'Fuerza']]
            for corr in correlaciones:
                r = abs(corr.get('r', 0))
                if r > 0.7:
                    fuerza = "Muy fuerte"
                elif r > 0.4:
                    fuerza = "Moderada"
                else:
                    fuerza = "Debil"
                
                corr_data.append([
                    corr.get('var1', ''),
                    corr.get('var2', ''),
                    f"{corr.get('r', 0):.3f}",
                    fuerza
                ])
            
            corr_table = Table(corr_data, colWidths=[1.8*inch, 1.8*inch, 0.8*inch, 0.8*inch])
            corr_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            story.append(corr_table)
        
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("5. Deteccion de Outliers", heading_style))
        
        outliers = datos.get('resumen_outliers', [])
        if outliers:
            outlier_data = [['Columna', '# Outliers', '% Outliers', 'Impacto']]
            for outlier in outliers:
                pct = outlier.get('porcentaje', 0)
                impacto = "Alto" if pct > 10 else "Medio" if pct > 5 else "Bajo"
                outlier_data.append([
                    outlier.get('columna', ''),
                    str(outlier.get('total_outliers', 0)),
                    f"{pct:.1f}%",
                    impacto
                ])
            
            outlier_table = Table(outlier_data, colWidths=[2*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            outlier_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(outlier_table)
        
        story.append(PageBreak())
        story.append(Paragraph("6. Analisis de Clustering", heading_style))
        
        clusters = datos.get('info_clusters', [])
        
        #Imprimir en consola para verificar
        print("debug clusters")
        print(f"Clusters encontrados: {clusters}")
        
        if clusters:
            cluster_data = [['Cluster', 'Tamanio', '% del Total', 'Registros']]
            
            for cluster in clusters:
                cluster_id = cluster.get('cluster', '')
                tamanio = cluster.get('tamanio', 0)
                # Porcentaje - DEBUG
                porcentaje = cluster.get('porcentaje', 0)
                print(f"Cluster {cluster_id}: tamanio={tamanio}, porcentaje={porcentaje}")
                
                cluster_data.append([
                    f"Cluster {cluster_id}",
                    str(tamanio),
                    f"{porcentaje:.1f}%",
                    "Si" if tamanio > 0 else "No"
                ])
            
            cluster_table = Table(cluster_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch])
            cluster_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(cluster_table)
        else:
            story.append(Paragraph("No se detectaron clusters en los datos.", styles['Normal']))
        
        story.append(PageBreak())
        story.append(Paragraph("7. Estadisticas Descriptivas", heading_style))
        
        stats_desc = datos.get('stats_descriptivas', [])
        if stats_desc:
            stats_data = [['Variable', 'Media', 'Mediana', 'Desv. Estandar', 'Minimo', 'Maximo', 'Asimetria']]
            
            for stat in stats_desc:
                stats_data.append([
                    stat.get('columna', ''),
                    str(stat.get('media', '')),
                    str(stat.get('mediana', '')),
                    str(stat.get('desviacion', '')),
                    str(stat.get('minimo', '')),
                    str(stat.get('maximo', '')),
                    str(stat.get('asimetria', ''))
                ])
            
            stats_table_desc = Table(stats_data, colWidths=[1.2*inch, 0.7*inch, 0.7*inch, 0.8*inch, 0.6*inch, 0.6*inch, 0.6*inch])
            stats_table_desc.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(stats_table_desc)
        
        story.append(PageBreak())
        story.append(Paragraph("8. Informacion de Columnas", heading_style))
        
        columnas = datos.get('columnas', [])
        if columnas:
            col_data = [['Columna', 'Tipo', 'Valores No Nulos', 'Valores Unicos', 'Completitud']]
            
            for col in columnas:
                col_data.append([
                    col.get('nombre', ''),
                    col.get('tipo', ''),
                    str(col.get('no_nulos', '')),
                    str(col.get('unicos', '')),
                    f"{col.get('completitud', 0)}%"
                ])
            
            col_table = Table(col_data, colWidths=[1.2*inch, 0.8*inch, 1*inch, 0.8*inch, 0.8*inch])
            col_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
            ]))
            story.append(col_table)
        
        #Construir PDF
        doc.build(story)
        
        #Enviar archivo
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error al generar el PDF: {str(e)}', 'error')
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except:
                pass
        return redirect(url_for('resultados'))


def ejecutar_analisis(rutas, metodo_clustering, metodo_outliers, metodo_correlacion):

    df = cargar_archivo(rutas[0])

    resultado_analisis = analizar(df)
    estadisticas       = resultado_analisis['estadisticas']
    columnas           = resultado_analisis['columnas']
    stats_descriptivas = resultado_analisis['stats_descriptivas']
    stats_numericas    = resultado_analisis['stats_numericas']
    stats_categoricas  = resultado_analisis['stats_categoricas']

    #Correlaciones
    corr_data         = calcular_correlaciones(df, metodo_correlacion)
    top_correlaciones = corr_data['top_pares'][:5]
    grafico_corr      = generar_grafico_correlacion(corr_data['matriz'], metodo_correlacion)

    #Outliers
    cols_numericas   = obtener_columnas_numericas(df)
    resultado_outliers = detectar_outliers(df, cols_numericas)

    resumen_outliers   = resultado_outliers['resumen_outliers']
    filas_outliers     = resultado_outliers['filas_outliers']
    columnas_outliers  = resultado_outliers['columnas_outliers']
    total_outliers     = resultado_outliers['total_outliers']
    mascara_outliers   = resultado_outliers['mascara']

    grafico_outliers = generar_grafico_outliers(
        df, mascara_outliers, columnas_outliers
    )

    insights = []

    if top_correlaciones:
        par = top_correlaciones[0]
        r_abs = abs(par['r'])
        if r_abs > 0.7:
            msg = f"Correlacion muy fuerte ({r_abs:.2f}) entre '{par['var1']}' y '{par['var2']}'."
            tipo = 'info'
        elif r_abs > 0.4:
            msg = f"Correlacion moderada ({r_abs:.2f}) entre '{par['var1']}' y '{par['var2']}'."
            tipo = 'info'
        else:
            msg = f"No se detectaron correlaciones fuertes. La mas alta es {r_abs:.2f}."
            tipo = 'advertencia'
        insights.append({'tipo': tipo, 'icono': '📈', 'categoria': 'CORRELACION', 'mensaje': msg})
    else:
        insights.append({
            'tipo': 'advertencia', 'icono': '⚠️', 'categoria': 'CORRELACION',
            'mensaje': 'No hay suficientes columnas numericas para calcular correlaciones.'
        })

    # Insight de outliers
    if total_outliers > 0:
        pct = round((total_outliers / estadisticas['total_filas']) * 100, 1)
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

    # Insight general
    insights.append({
        'tipo': 'info', 'icono': '📊', 'categoria': 'ANALISIS',
        'mensaje': f"Dataset analizado: {estadisticas['total_filas']} filas, {estadisticas['total_columnas']} columnas, {estadisticas['total_numericas']} variables numericas."
    })

    #Clustering 
    # Usar las mismas columnas numéricas que ya tenemos
    labels, n_clusters, centroides, silhouette = aplicar_clustering(df, cols_numericas)
    
    if labels is not None and n_clusters > 0:
        grafico_clusters = generar_grafico_clusters(df, labels, cols_numericas)
        info_clusters, detalle_clusters = obtener_info_clusters(df, labels, centroides, cols_numericas)
        estadisticas['total_clusters'] = n_clusters
        
        # Insight de clustering
        insights.append({
            'tipo': 'info',
            'icono': '🧩',
            'categoria': 'CLUSTERING',
            'mensaje': f"Se detectaron {n_clusters} agrupaciones principales en los datos. "
                       f"El grupo más grande contiene {max([c['tamanio'] for c in info_clusters])} registros."
        })
    else:
        grafico_clusters = None
        info_clusters = []
        detalle_clusters = []
        estadisticas['total_clusters'] = 0
        insights.append({
            'tipo': 'advertencia',
            'icono': '⚠️',
            'categoria': 'CLUSTERING',
            'mensaje': 'No fue posible realizar clustering (faltan columnas numéricas o hay muy pocos datos).'
        })

    estadisticas['total_outliers'] = total_outliers

    graficos = {
        'distribuciones': [],
        'correlacion':    grafico_corr,
        'outliers':       grafico_outliers,
        'clustering':     grafico_clusters,
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

@app.errorhandler(404)
def pagina_no_encontrada(e):
    return render_template('index.html'), 404

@app.errorhandler(413)
def archivo_muy_grande(e):
    flash('El archivo supera el limite de 16 MB.', 'error')
    return redirect(url_for('inicio'))

if __name__ == '__main__':
    app.run(debug=True)