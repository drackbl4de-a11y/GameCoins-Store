"""
correo.py
---------
Envía correos con la librería estándar de Python (smtplib), sin instalar nada.
Hace cuatro cosas:
  1) enviar_codigo_verificacion(): el código de 6 números al registrarse.
  1b) enviar_codigo_recuperacion(): el código para cambiar la contraseña olvidada.
  2) enviar_pedido_entregado(): correo con el certificado en PDF (cuando el admin marca ENTREGADO).
  3) enviar_pedido_cancelado(): correo de aviso (cuando el admin marca CANCELADO).
Las dos devuelven True si el correo salió y False si algo falló.
"""

import smtplib
from email.message import EmailMessage
from html import escape

import config


def correo_configurado():
    """True si en config.py ya se escribieron el usuario y la clave de Gmail."""
    return bool(config.MAIL_USUARIO and config.MAIL_CLAVE)


def pesos(valor):
    return "{:,.0f}".format(valor).replace(",", ".")


def enviar(mensaje):
    """Abre la conexión con Gmail y envía el mensaje. Devuelve True/False."""
    try:
        with smtplib.SMTP(config.MAIL_SERVIDOR, config.MAIL_PUERTO, timeout=15) as servidor:
            servidor.starttls()                                   # conexión cifrada
            servidor.login(config.MAIL_USUARIO, config.MAIL_CLAVE)
            servidor.send_message(mensaje)
        return True
    except Exception as error:
        print("No se pudo enviar el correo:", error)             # se ve en la terminal de VS Code
        return False


def nuevo_mensaje(destinatario, asunto):
    mensaje = EmailMessage()
    mensaje["From"] = f"GameCoins Store <{config.MAIL_USUARIO}>"
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    return mensaje


def pagina_html(contenido):
    """Marco común de los correos: fondo oscuro y franja magenta con el nombre de la tienda."""
    return f"""
    <div style="background:#0b0e17;padding:24px 12px;font-family:Arial,Helvetica,sans-serif;color:#eef0f7;">
      <table align="center" width="100%" style="max-width:520px;" cellpadding="0" cellspacing="0">
        <tr><td style="background:#ff3d78;padding:16px;text-align:center;border-radius:10px;
                       font-size:22px;font-weight:bold;letter-spacing:2px;color:#ffffff;">GAMECOINS STORE</td></tr>
        <tr><td style="padding-top:18px;">{contenido}</td></tr>
        <tr><td style="padding-top:18px;font-size:11px;color:#8b90a3;text-align:center;">
          Proyecto académico SENA · Los pagos son simulados y no se cobra dinero real.</td></tr>
      </table>
    </div>"""


# ------------------------------------------------------------
# 1) Código de verificación del registro
# ------------------------------------------------------------
def enviar_codigo_verificacion(destinatario, nombre, codigo):
    mensaje = nuevo_mensaje(destinatario, "Tu código de verificación - GameCoins Store")
    mensaje.set_content(f"Hola {nombre}, tu código de verificación es: {codigo}. Vence en 10 minutos.")
    mensaje.add_alternative(pagina_html(f"""
        <p style="font-size:15px;">Hola <b>{escape(nombre)}</b>, confirma tu correo con este código:</p>
        <p style="background:#141826;border:1px solid #232838;border-radius:10px;padding:18px;text-align:center;
                  font-size:34px;font-weight:bold;letter-spacing:8px;color:#2dd9c4;">{codigo}</p>
        <p style="font-size:12px;color:#8b90a3;">El código vence en 10 minutos. Si no fuiste tú, ignora este correo.</p>
    """), subtype="html")
    return enviar(mensaje)


# ------------------------------------------------------------
# 1b) Código para recuperar la contraseña
# ------------------------------------------------------------
def enviar_codigo_recuperacion(destinatario, nombre, codigo):
    mensaje = nuevo_mensaje(destinatario, "Recupera tu contraseña - GameCoins Store")
    mensaje.set_content(f"Hola {nombre}, tu código para cambiar la contraseña es: {codigo}. Vence en 10 minutos.")
    mensaje.add_alternative(pagina_html(f"""
        <p style="font-size:15px;">Hola <b>{escape(nombre)}</b>, pediste cambiar tu contraseña. Tu código es:</p>
        <p style="background:#141826;border:1px solid #232838;border-radius:10px;padding:18px;text-align:center;
                  font-size:34px;font-weight:bold;letter-spacing:8px;color:#2dd9c4;">{codigo}</p>
        <p style="font-size:12px;color:#8b90a3;">El código vence en 10 minutos. Si no fuiste tú, ignora este correo:
        tu contraseña actual sigue funcionando.</p>
    """), subtype="html")
    return enviar(mensaje)


# ------------------------------------------------------------
# 2) Correos del pedido: se envían cuando el administrador lo marca
#    como ENTREGADO (con el certificado en PDF) o como CANCELADO.
# ------------------------------------------------------------
def tabla_del_pedido(compra, items):
    """Arma el cuadro con el código, la fecha y las filas del pedido (se usa en los dos correos)."""
    filas = ""
    for item in items:
        filas += f"""
        <tr>
          <td style="padding:10px 0;border-top:1px solid #232838;font-size:13px;color:#eef0f7;">
            <b>{escape(item['paquete_nombre'])}</b><br>
            <span style="color:#8b90a3;font-size:12px;">{escape(item['juego_nombre'])} · Entregado a: {escape(item['dato_entrega'])}</span>
          </td>
          <td style="padding:10px 0;border-top:1px solid #232838;font-size:13px;text-align:right;color:#ff3d78;font-weight:bold;">
            COP {pesos(item['subtotal'])}
          </td>
        </tr>"""

    fecha = compra["fecha_compra"].strftime("%d/%m/%Y %H:%M")
    return f"""
        <table width="100%" cellpadding="14" style="background:#141826;border:1px solid #232838;border-radius:10px;">
          <tr>
            <td style="font-size:11px;color:#8b90a3;">PEDIDO<br>
              <span style="font-size:17px;font-weight:bold;color:#ff3d78;">{compra['codigo_pedido']}</span></td>
            <td style="font-size:11px;color:#8b90a3;text-align:right;">FECHA<br>
              <span style="font-size:13px;color:#eef0f7;">{fecha}</span></td>
          </tr>
        </table>

        <p style="font-size:11px;color:#2dd9c4;font-weight:bold;letter-spacing:1px;margin:18px 0 4px;">RESUMEN DE TU PEDIDO</p>
        <table width="100%" cellpadding="0" cellspacing="0">{filas}
          <tr>
            <td style="padding:12px 0;border-top:2px solid #ff3d78;font-size:14px;font-weight:bold;color:#eef0f7;">Total</td>
            <td style="padding:12px 0;border-top:2px solid #ff3d78;text-align:right;font-size:17px;font-weight:bold;color:#ff3d78;">
              COP {pesos(compra['total_cop'])}</td>
          </tr>
        </table>"""


def enviar_pedido_entregado(usuario, compra, items, pdf_bytes):
    """Correo de 'tu pedido fue entregado', con el certificado en PDF adjunto."""
    mensaje = nuevo_mensaje(usuario["correo"], f"Tu pedido {compra['codigo_pedido']} fue entregado - GameCoins Store")
    mensaje.set_content(f"Hola {usuario['nombre']}, tu pedido {compra['codigo_pedido']} fue entregado. Adjuntamos tu certificado en PDF.")
    mensaje.add_alternative(pagina_html(f"""
        <h2 style="margin:0 0 6px;font-size:24px;text-align:center;color:#2dd9c4;">¡TU PEDIDO FUE ENTREGADO!</h2>
        <p style="font-size:14px;text-align:center;color:#c8cbd8;margin:0 0 18px;">
          Hola <b>{escape(usuario['nombre'])}</b>, ya entregamos tu pedido. Aquí está el resumen;
          tu certificado de compra va adjunto en PDF.</p>
        {tabla_del_pedido(compra, items)}
        <p style="font-size:11px;color:#2dd9c4;font-weight:bold;letter-spacing:1px;margin:18px 0 4px;">¿QUÉ SIGUE?</p>
        <p style="font-size:13px;color:#c8cbd8;margin:0;">1. Revisa tu cuenta del juego: las monedas están en el usuario o ID que escribiste.<br>
           2. Guarda el PDF adjunto: es tu certificado de compra.<br>
           3. Si algo no llegó, escríbenos desde la página de Contacto con tu código de pedido.</p>
    """), subtype="html")

    mensaje.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                           filename=f"certificado_{compra['codigo_pedido']}.pdf")
    return enviar(mensaje)


def enviar_pedido_cancelado(usuario, compra, items):
    """Correo de 'tu pedido fue cancelado' (sin certificado: no hubo entrega)."""
    mensaje = nuevo_mensaje(usuario["correo"], f"Tu pedido {compra['codigo_pedido']} fue cancelado - GameCoins Store")
    mensaje.set_content(f"Hola {usuario['nombre']}, tu pedido {compra['codigo_pedido']} fue cancelado.")
    mensaje.add_alternative(pagina_html(f"""
        <h2 style="margin:0 0 6px;font-size:24px;text-align:center;color:#ff3d78;">TU PEDIDO FUE CANCELADO</h2>
        <p style="font-size:14px;text-align:center;color:#c8cbd8;margin:0 0 18px;">
          Hola <b>{escape(usuario['nombre'])}</b>, el equipo de GameCoins Store canceló este pedido.</p>
        {tabla_del_pedido(compra, items)}
        <p style="font-size:13px;color:#c8cbd8;margin:18px 0 0;">Si tienes dudas sobre la cancelación, escríbenos desde la
           página de Contacto e indica tu código de pedido.</p>
    """), subtype="html")
    return enviar(mensaje)
