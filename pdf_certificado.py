"""
pdf_certificado.py
------------------
Arma el PDF del certificado de compra usando la librería reportlab.
La función generar_certificado_pdf() la llaman app.py (botón "Descargar")
y también el correo que se envía automáticamente al comprar.
"""

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

ROSADO = colors.HexColor("#ff3d78")   # color principal de la página
OSCURO = colors.HexColor("#0b0e17")   # fondo oscuro de la página
CIAN = colors.HexColor("#1aa896")     # cian un poco más oscuro para leerse sobre blanco
GRIS = colors.HexColor("#555555")
GRIS_CLARO = colors.HexColor("#f3f4f8")
LINEA = colors.HexColor("#dddddd")


def pesos(valor):
    """Convierte 15500 en '15.500' (formato colombiano)."""
    return "{:,.0f}".format(valor).replace(",", ".")


def dibujar_pagina(lienzo, documento):
    """Lo que se repite en cada hoja: franja de arriba y pie de página."""
    ancho, alto = letter
    lienzo.saveState()

    # Franja oscura con una línea rosada abajo
    lienzo.setFillColor(OSCURO)
    lienzo.rect(0, alto - 3 * cm, ancho, 3 * cm, stroke=0, fill=1)
    lienzo.setFillColor(ROSADO)
    lienzo.rect(0, alto - 3 * cm, ancho, 0.2 * cm, stroke=0, fill=1)

    lienzo.setFillColor(colors.white)
    lienzo.setFont("Helvetica-Bold", 22)
    lienzo.drawString(2 * cm, alto - 1.7 * cm, "GAMECOINS STORE")
    lienzo.setFont("Helvetica", 10)
    lienzo.setFillColor(colors.HexColor("#2dd9c4"))
    lienzo.drawString(2 * cm, alto - 2.3 * cm, "Recarga tus monedas favoritas de forma rápida y segura")

    lienzo.setFillColor(colors.white)
    lienzo.setFont("Helvetica-Bold", 11)
    lienzo.drawRightString(ancho - 2 * cm, alto - 1.7 * cm, "CERTIFICADO DE COMPRA")

    # Pie de página
    lienzo.setStrokeColor(LINEA)
    lienzo.line(2 * cm, 1.8 * cm, ancho - 2 * cm, 1.8 * cm)
    lienzo.setFillColor(GRIS)
    lienzo.setFont("Helvetica", 8)
    lienzo.drawString(2 * cm, 1.3 * cm, "GameCoins Store · Proyecto académico SENA · Pago simulado, sin validez comercial")
    lienzo.drawRightString(ancho - 2 * cm, 1.3 * cm, f"Página {documento.page}")
    lienzo.restoreState()


def generar_certificado_pdf(compra, items, usuario, codigo_certificado, pago=None):
    """
    Recibe los datos del pedido y devuelve el PDF en memoria (BytesIO),
    listo para enviarlo con send_file o adjuntarlo a un correo.
    """
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=letter,
                            topMargin=3.8 * cm, bottomMargin=2.4 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            title=f"Certificado {compra['codigo_pedido']}", author="GameCoins Store")

    # --- Estilos de texto ---
    base = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=base["Title"], textColor=OSCURO, fontSize=24, leading=28, alignment=0, spaceAfter=2)
    subtitulo = ParagraphStyle("subtitulo", parent=base["Normal"], textColor=GRIS, fontSize=10, leading=14, spaceBefore=6, spaceAfter=14)
    seccion = ParagraphStyle("seccion", parent=base["Normal"], textColor=ROSADO, fontSize=10,
                             fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=6)
    etiqueta = ParagraphStyle("etiqueta", parent=base["Normal"], textColor=GRIS, fontSize=8)
    valor = ParagraphStyle("valor", parent=base["Normal"], fontSize=10, leading=12)
    celda = ParagraphStyle("celda", parent=base["Normal"], fontSize=8.5, leading=10)
    celda_titulo = ParagraphStyle("celda_titulo", parent=celda, textColor=colors.white, fontName="Helvetica-Bold")
    total_estilo = ParagraphStyle("total", parent=base["Normal"], fontSize=15, alignment=2, textColor=ROSADO)
    nota = ParagraphStyle("nota", parent=base["Normal"], textColor=GRIS, fontSize=8.5, leading=12)

    contenido = []   # aquí vamos agregando lo que aparece en el PDF, de arriba hacia abajo

    # --- Título y código del certificado ---
    contenido.append(Paragraph("Certificado de compra", titulo))
    contenido.append(Paragraph(
        f"Código de certificado: <b>{codigo_certificado}</b> &nbsp;·&nbsp; "
        f"Emitido el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}", subtitulo))

    # --- Dos cajas: datos del pedido y datos del cliente ---
    fecha = compra["fecha_compra"].strftime("%d/%m/%Y %H:%M")
    if pago:
        metodo = f"{pago['tipo_tarjeta'].title()} (simulado)<br/>Celular {pago['numero_tarjeta_enmascarado']}"
        titular = pago["nombre_titular"]
    else:
        metodo, titular = "Nequi (simulado)", "-"

    telefono = usuario.get("telefono") or "No registrado"
    caja_pedido = [
        Paragraph("DATOS DEL PEDIDO", seccion),
        Paragraph("Código de pedido", etiqueta), Paragraph(compra["codigo_pedido"], valor),
        Paragraph("Fecha de compra", etiqueta), Paragraph(fecha, valor),
        Paragraph("Estado", etiqueta), Paragraph(compra["estado_pedido"], valor),
        Paragraph("Método de pago", etiqueta), Paragraph(metodo, valor),
        Paragraph("Titular del pago", etiqueta), Paragraph(titular, valor),
    ]
    caja_cliente = [
        Paragraph("DATOS DEL CLIENTE", seccion),
        Paragraph("Nombre", etiqueta), Paragraph(f"{usuario['nombre']} {usuario['apellido']}", valor),
        Paragraph("Correo electrónico", etiqueta), Paragraph(usuario["correo"], valor),
        Paragraph("WhatsApp", etiqueta), Paragraph(telefono, valor),
        Paragraph("Cliente desde", etiqueta), Paragraph(usuario["fecha_registro"].strftime("%d/%m/%Y"), valor),
    ]
    cajas = Table([[caja_pedido, caja_cliente]], colWidths=[8.8 * cm, 8.8 * cm])
    cajas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_CLARO),
        ("BOX", (0, 0), (0, 0), 0.5, LINEA),
        ("BOX", (1, 0), (1, 0), 0.5, LINEA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    contenido.append(cajas)

    # --- Tabla con los paquetes comprados ---
    contenido.append(Paragraph("DETALLE DE LA COMPRA", seccion))
    titulos = ["Juego", "Paquete", "Monedas", "Cant.", "Entregado a", "Precio unit.", "Subtotal"]
    filas = [[Paragraph(t, celda_titulo) for t in titulos]]
    for item in items:
        monedas = item["cantidad_monedas"] * item["cantidad"]
        filas.append([
            Paragraph(item["juego_nombre"], celda),
            Paragraph(item["paquete_nombre"], celda),
            Paragraph(f"{monedas} {item['moneda_nombre']}", celda),
            Paragraph(str(item["cantidad"]), celda),
            Paragraph(item["dato_entrega"], celda),
            Paragraph(f"COP {pesos(item['precio_unitario'])}", celda),
            Paragraph(f"COP {pesos(item['subtotal'])}", celda),
        ])

    tabla_items = Table(filas, colWidths=[2.1 * cm, 3 * cm, 2.5 * cm, 1.2 * cm, 3.3 * cm, 2.6 * cm, 2.9 * cm], repeatRows=1)
    tabla_items.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ROSADO),                           # fila de títulos rosada
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),  # filas alternadas
        ("GRID", (0, 0), (-1, -1), 0.5, LINEA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    contenido.append(tabla_items)

    # --- Total ---
    contenido.append(Spacer(1, 12))
    total_caja = Table([[Paragraph(f"<b>TOTAL PAGADO: COP {pesos(compra['total_cop'])}</b>", total_estilo)]],
                       colWidths=[17.6 * cm])
    total_caja.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1.5, ROSADO),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    contenido.append(total_caja)

    # --- Información de entrega y de validez ---
    contenido.append(Paragraph("INFORMACIÓN DE ENTREGA", seccion))
    contenido.append(Paragraph(
        "Las monedas se entregan a la cuenta indicada en la columna <b>Entregado a</b> "
        "(usuario de Roblox o ID de VALORANT). Verifica en tu juego que el saldo se haya actualizado. "
        "Si algo no llega, escríbenos desde la página de <b>Contacto</b> e incluye tu código de pedido "
        f"<b>{compra['codigo_pedido']}</b> y este certificado.", nota))

    contenido.append(Paragraph("VALIDEZ DEL DOCUMENTO", seccion))
    contenido.append(Paragraph(
        "Este certificado es parte de un proyecto académico (GameCoins Store, SENA). "
        "No representa una transacción financiera real ni tiene validez comercial o tributaria: "
        "el pago con Nequi es una simulación y no se cobró dinero. "
        f"Código de certificado: {codigo_certificado}.", nota))

    pdf.build(contenido, onFirstPage=dibujar_pagina, onLaterPages=dibujar_pagina)
    buffer.seek(0)
    return buffer
