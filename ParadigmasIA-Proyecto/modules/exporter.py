import os
import tempfile
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch


# Paleta de colores del reporte
COLOR_PRIMARIO = colors.HexColor('#2c3e50')
COLOR_SECUNDARIO = colors.HexColor('#34495e')
COLOR_ACENTO = colors.HexColor('#3498db')
COLOR_EXITO = colors.HexColor('#27ae60')
COLOR_ADVERTENCIA = colors.HexColor('#e67e22')
COLOR_PELIGRO = colors.HexColor('#e74c3c')
COLOR_MORADO = colors.HexColor('#9b59b6')
COLOR_FONDO_FILA = colors.HexColor('#ecf0f1')


def generar_pdf(datos: dict, nombre_archivo: str, metodos: dict) -> str:
    # Crear archivo temporal
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    ruta_pdf = tmp.name
    tmp.close()

    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=A4,
        rightMargin=72, leftMargin=72,
        topMargin=72,   bottomMargin=72,
    )

    estilos  = _definir_estilos()
    contenido = _construir_contenido(datos, nombre_archivo, metodos, estilos)

    doc.build(contenido)
    return ruta_pdf

def _construir_contenido(datos, nombre_archivo, metodos, estilos):
    story = []

    _agregar_portada(story, estilos, nombre_archivo, metodos)
    story.append(PageBreak())

    _agregar_resumen_general(story, estilos, datos.get('estadisticas', {}), metodos)
    story.append(PageBreak())

    _agregar_insights(story, estilos, datos.get('insights', []))

    _agregar_correlaciones(story, estilos, datos.get('top_correlaciones', []))

    _agregar_outliers(story, estilos, datos.get('resumen_outliers', []),
                      datos.get('estadisticas', {}).get('total_outliers', 0))
    story.append(PageBreak())

    _agregar_clustering(story, estilos, datos.get('info_clusters', []),
                        datos.get('detalle_clusters', []))
    story.append(PageBreak())

    _agregar_stats_descriptivas(story, estilos, datos.get('stats_descriptivas', []))
    story.append(PageBreak())

    _agregar_info_columnas(story, estilos, datos.get('columnas', []))

    return story


def _agregar_portada(story, estilos, nombre_archivo, metodos):
    story.append(Spacer(1, 1 * inch))
    story.append(Paragraph("DataInsight AI", estilos['titulo']))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Reporte de Analisis Exploratorio de Datos", estilos['subtitulo']))
    story.append(Spacer(1, 0.5 * inch))

    story.append(Paragraph(f"Archivo analizado: <b>{nombre_archivo}</b>", estilos['normal']))
    story.append(Paragraph(
        f"Fecha de generacion: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        estilos['normal']
    ))
    story.append(Spacer(1, 0.3 * inch))

    # Tabla de metodos utilizados
    metodos_data = [
        ['Tecnica', 'Metodo Utilizado'],
        ['Clustering', _nombre_metodo(metodos.get('clustering', 'kmeans'))],
        ['Deteccion de Outliers', _nombre_metodo(metodos.get('outliers', 'zscore'))],
        ['Correlacion', _nombre_metodo(metodos.get('correlacion', 'pearson'))],
    ]
    story.append(_crear_tabla(metodos_data, [2.5 * inch, 2.5 * inch], COLOR_EXITO))


def _agregar_resumen_general(story, estilos, estadisticas, metodos):
    story.append(Paragraph("1. Resumen General", estilos['seccion']))
    story.append(Spacer(1, 0.1 * inch))

    datos_tabla = [
        ['Metrica', 'Valor'],
        ['Total de filas', str(estadisticas.get('total_filas', 0))],
        ['Total de columnas', str(estadisticas.get('total_columnas', 0))],
        ['Variables numericas', str(estadisticas.get('total_numericas', 0))],
        ['Variables categoricas', str(estadisticas.get('total_categoricas', 0))],
        ['Datos faltantes', f"{estadisticas.get('pct_faltantes', 0)}%"],
        ['Outliers detectados', str(estadisticas.get('total_outliers', 0))],
        ['Clusters encontrados', str(estadisticas.get('total_clusters', 0))],
    ]
    story.append(_crear_tabla(datos_tabla, [3 * inch, 2 * inch], COLOR_ACENTO))


def _agregar_insights(story, estilos, insights):
    if not insights:
        return

    story.append(Paragraph("2. Insights Automaticos", estilos['seccion']))
    story.append(Spacer(1, 0.1 * inch))

    for insight in insights:
        categoria = insight.get('categoria', '')
        mensaje = insight.get('mensaje', '')
        tipo = insight.get('tipo', 'info')

        # Color segun tipo
        color_mapa = {
            'info': COLOR_ACENTO,
            'exito': COLOR_EXITO,
            'advertencia': COLOR_ADVERTENCIA,
            'peligro': COLOR_PELIGRO,
        }
        color = color_mapa.get(tipo, COLOR_ACENTO)

        texto = f"<font color='#{_hex(color)}'><b>[{categoria}]</b></font> {mensaje}"
        story.append(Paragraph(texto, estilos['normal']))
        story.append(Spacer(1, 0.05 * inch))

    story.append(Spacer(1, 0.2 * inch))


def _agregar_correlaciones(story, estilos, top_correlaciones):
    story.append(Paragraph("3. Top Correlaciones (Pearson)", estilos['seccion']))
    story.append(Spacer(1, 0.1 * inch))

    if not top_correlaciones:
        story.append(Paragraph(
            "No hay suficientes columnas numericas para calcular correlaciones.",
            estilos['normal']
        ))
        story.append(Spacer(1, 0.2 * inch))
        return

    datos_tabla = [['Variable 1', 'Variable 2', 'Coeficiente r', 'Intensidad']]

    for par in top_correlaciones:
        r     = par.get('r', 0)
        r_abs = abs(r)

        if r_abs > 0.7:
            intensidad = 'Fuerte'
        elif r_abs > 0.4:
            intensidad = 'Moderada'
        else:
            intensidad = 'Debil'

        datos_tabla.append([
            par.get('var1', ''),
            par.get('var2', ''),
            f"{r:.4f}",
            intensidad,
        ])

    story.append(_crear_tabla(datos_tabla,
        [1.8 * inch, 1.8 * inch, 1.0 * inch, 0.9 * inch],
        COLOR_ACENTO
    ))
    story.append(Spacer(1, 0.2 * inch))


def _agregar_outliers(story, estilos, resumen_outliers, total_outliers):
    story.append(Paragraph(
        f"4. Deteccion de Outliers (Z-Score) — {total_outliers} detectados",
        estilos['seccion']
    ))
    story.append(Spacer(1, 0.1 * inch))

    if not resumen_outliers:
        story.append(Paragraph(
            "No se detectaron valores atipicos significativos en el dataset.",
            estilos['normal']
        ))
        story.append(Spacer(1, 0.2 * inch))
        return

    datos_tabla = [['Columna', 'Cantidad', 'Porcentaje', 'Impacto']]

    for outlier in resumen_outliers:
        pct     = outlier.get('porcentaje', 0)
        cantidad = outlier.get('cantidad', 0)
        impacto = 'Alto' if pct > 10 else 'Medio' if pct > 5 else 'Bajo'

        datos_tabla.append([
            outlier.get('columna', ''),
            str(cantidad),
            f"{pct:.1f}%",
            impacto,
        ])

    story.append(_crear_tabla(datos_tabla,
        [2.0 * inch, 0.9 * inch, 0.9 * inch, 0.9 * inch],
        COLOR_PELIGRO
    ))
    story.append(Spacer(1, 0.2 * inch))


def _agregar_clustering(story, estilos, info_clusters, detalle_clusters):
    n = len(info_clusters)
    story.append(Paragraph(
        f"5. Analisis de Clustering (K-Means) — {n} grupos",
        estilos['seccion']
    ))
    story.append(Spacer(1, 0.1 * inch))

    if not info_clusters:
        story.append(Paragraph(
            "No fue posible realizar clustering (se necesitan al menos 2 columnas numericas y 10 registros).",
            estilos['normal']
        ))
        story.append(Spacer(1, 0.2 * inch))
        return

    # Resumen de clusters
    estilo_desc = ParagraphStyle(
        'DescCluster',
        fontSize=8,
        textColor=COLOR_SECUNDARIO,
        leading=11,
        wordWrap='LTR',
    )

    datos_tabla = [['Cluster', 'Registros', '% del Total', 'Descripcion']]

    for cluster in info_clusters:
        cluster_id  = cluster.get('id', '')
        tamanio = cluster.get('tamanio', 0)
        descripcion = cluster.get('descripcion', '')

        porcentaje = 0
        for det in detalle_clusters:
            if det.get('id') == cluster_id:
                porcentaje = det.get('porcentaje', 0)
                break

        datos_tabla.append([
            f"Cluster {cluster_id}",
            str(tamanio),
            f"{porcentaje:.1f}%",
            Paragraph(descripcion, estilo_desc),
        ])

    story.append(_crear_tabla(datos_tabla,
        [0.8 * inch, 0.7 * inch, 0.8 * inch, 3.7 * inch],
        COLOR_MORADO
    ))
    story.append(Spacer(1, 0.2 * inch))

    # Detalle por cluster
    for det in detalle_clusters:
        cluster_id = det.get('id', '')
        story.append(Paragraph(
            f"Cluster {cluster_id} — medias vs global",
            estilos['subseccion']
        ))

        estadisticas_det = det.get('estadisticas', [])
        if estadisticas_det:
            datos_det = [['Variable', 'Media del Cluster', 'Media Global']]
            for stat in estadisticas_det:
                datos_det.append([
                    stat.get('columna', ''),
                    str(stat.get('media_cluster', '')),
                    str(stat.get('media_global', '')),
                ])
            story.append(_crear_tabla(datos_det,
                [2.0 * inch, 1.5 * inch, 1.5 * inch],
                COLOR_SECUNDARIO,
                fuente_size=8
            ))
            story.append(Spacer(1, 0.1 * inch))


def _agregar_stats_descriptivas(story, estilos, stats_descriptivas):
    story.append(Paragraph("6. Estadisticas Descriptivas", estilos['seccion']))
    story.append(Spacer(1, 0.1 * inch))

    if not stats_descriptivas:
        story.append(Paragraph("No hay variables numericas para analizar.", estilos['normal']))
        return

    datos_tabla = [['Variable', 'Media', 'Mediana', 'Desv. Est.', 'Min', 'Max', 'Asimetria']]

    for stat in stats_descriptivas:
        datos_tabla.append([
            stat.get('columna', ''),
            str(stat.get('media', '')),
            str(stat.get('mediana', '')),
            str(stat.get('desviacion', '')),
            str(stat.get('minimo', '')),
            str(stat.get('maximo', '')),
            str(stat.get('asimetria', '')),
        ])

    story.append(_crear_tabla(datos_tabla,
        [1.2*inch, 0.7*inch, 0.7*inch, 0.8*inch, 0.6*inch, 0.6*inch, 0.7*inch],
        COLOR_PRIMARIO,
        fuente_size=8
    ))


def _agregar_info_columnas(story, estilos, columnas):
    story.append(Paragraph("7. Informacion de Columnas", estilos['seccion']))
    story.append(Spacer(1, 0.1 * inch))

    if not columnas:
        story.append(Paragraph("No hay informacion de columnas disponible.", estilos['normal']))
        return

    datos_tabla = [['Columna', 'Tipo', 'No Nulos', 'Unicos', 'Completitud']]

    for col in columnas:
        datos_tabla.append([
            col.get('nombre', ''),
            col.get('tipo', ''),
            str(col.get('no_nulos', '')),
            str(col.get('unicos', '')),
            f"{col.get('completitud', 0)}%",
        ])

    story.append(_crear_tabla(datos_tabla,
        [1.5*inch, 0.9*inch, 0.9*inch, 0.8*inch, 0.9*inch],
        COLOR_SECUNDARIO,
        fuente_size=8
    ))

def _definir_estilos() -> dict:
    base = getSampleStyleSheet()

    return {
        'titulo': ParagraphStyle(
            'Titulo',
            parent=base['Heading1'],
            fontSize=22,
            textColor=COLOR_PRIMARIO,
            alignment=1,
            spaceAfter=12,
            fontName='Helvetica-Bold',
        ),
        'subtitulo': ParagraphStyle(
            'Subtitulo',
            parent=base['Heading2'],
            fontSize=14,
            textColor=COLOR_SECUNDARIO,
            alignment=1,
            spaceAfter=8,
        ),
        'seccion': ParagraphStyle(
            'Seccion',
            parent=base['Heading2'],
            fontSize=13,
            textColor=COLOR_PRIMARIO,
            spaceBefore=16,
            spaceAfter=8,
            fontName='Helvetica-Bold',
        ),
        'subseccion': ParagraphStyle(
            'Subseccion',
            parent=base['Heading3'],
            fontSize=10,
            textColor=COLOR_SECUNDARIO,
            spaceBefore=8,
            spaceAfter=4,
            fontName='Helvetica-Bold',
        ),
        'normal': ParagraphStyle(
            'Normal',
            parent=base['Normal'],
            fontSize=9,
            textColor=COLOR_SECUNDARIO,
            spaceAfter=4,
        ),
    }


def _crear_tabla(datos, anchos_col, color_cabecera,
                 fuente_size=9) -> Table:
    tabla = Table(datos, colWidths=anchos_col)

    n_filas = len(datos)
    estilos = [
        # Cabecera
        ('BACKGROUND', (0, 0), (-1, 0),  color_cabecera),
        ('TEXTCOLOR', (0, 0), (-1, 0),  colors.white),
        ('FONTNAME', (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0),  fuente_size),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        # Cuerpo
        ('FONTSIZE', (0, 1), (-1, -1), fuente_size),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]

    # Filas alternadas
    for i in range(1, n_filas):
        if i % 2 == 0:
            estilos.append(('BACKGROUND', (0, i), (-1, i), COLOR_FONDO_FILA))

    tabla.setStyle(TableStyle(estilos))
    return tabla

def _nombre_metodo(clave: str) -> str:
    nombres = {
        'kmeans': 'K-Means',
        'zscore': 'Z-Score',
        'pearson': 'Pearson',
    }
    return nombres.get(clave, clave)

def _hex(color) -> str:
    return color.hexval()[2:]