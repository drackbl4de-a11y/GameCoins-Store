"""
servicio_pedido.py
------------------
Lo que se hace con un pedido FUERA de las rutas: armar el certificado en PDF y
avisarle por correo al cliente. Lo usan app.py (descargar el certificado) y
admin.py (cuando el administrador cambia el estado del pedido).
"""

import secrets

import db
import correo as servicio_correo
from pdf_certificado import generar_certificado_pdf


def crear_pdf_certificado(compra_id, usuario_id):
    """Junta los datos del pedido y arma el PDF. Devuelve (compra, items, usuario, pdf)."""
    compra = db.obtener_compra_por_id(compra_id, usuario_id)
    if not compra:
        return None, None, None, None

    items = db.obtener_detalle_compra(compra_id)
    usuario = db.obtener_usuario_por_id(usuario_id)
    pago = db.obtener_datos_pago(compra_id)

    # El certificado se crea una sola vez; si ya existe, se reutiliza su código
    certificado = db.obtener_certificado_por_compra(compra_id)
    if certificado:
        codigo = certificado["codigo_certificado"]
    else:
        codigo = "CERT-" + secrets.token_hex(4).upper()
        db.crear_certificado(compra_id, codigo)

    pdf = generar_certificado_pdf(compra, items, usuario, codigo, pago)
    return compra, items, usuario, pdf


def avisar_estado_por_correo(compra_id, usuario_id, estado):
    """
    Se llama cuando el admin cambia el estado de un pedido.
      - ENTREGADO -> correo con el certificado en PDF
      - CANCELADO -> correo avisando la cancelación
    Devuelve True si el correo salió, False si falló.
    """
    compra, items, usuario, pdf = crear_pdf_certificado(compra_id, usuario_id)
    if not compra:
        return False

    if estado == "ENTREGADO":
        return servicio_correo.enviar_pedido_entregado(usuario, compra, items, pdf.getvalue())
    return servicio_correo.enviar_pedido_cancelado(usuario, compra, items)
