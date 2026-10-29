"""
generar_qr.py
-------------
Crea la imagen del código QR de WhatsApp: static/img/whatsapp-qr.png

Al escanear el QR con la cámara del celular se abre el chat de WhatsApp de la
tienda con el mensaje inicial ya escrito (el mismo enlace del botón de la página).

Solo hay que ejecutarlo de nuevo si cambias el número o el mensaje en config.py:
    python generar_qr.py

Usa reportlab (que ya está instalado para el PDF) y Pillow (viene con reportlab),
así que no hay que instalar nada nuevo.
"""

import os
from urllib.parse import quote

from PIL import Image
from reportlab.graphics.barcode import qrencoder

from config import WHATSAPP_NUMERO, WHATSAPP_MENSAJE

# El mismo enlace que usa el botón "Escribir por WhatsApp"
ENLACE = f"https://wa.me/{WHATSAPP_NUMERO}?text={quote(WHATSAPP_MENSAJE)}"

TAMANO_CUADRITO = 12      # cada cuadrito del QR mide 12 píxeles
MARGEN = 4                # borde blanco (4 cuadritos), necesario para que la cámara lo lea

# 1) Calculamos la matriz del QR: una cuadrícula de cuadritos oscuros y claros
qr = qrencoder.QRCode(None, qrencoder.QRErrorCorrectLevel.M)
qr.addData(ENLACE)
qr.make()
cuadritos = qr.getModuleCount()

# 2) Dibujamos la imagen: fondo blanco y un cuadro negro por cada cuadrito oscuro
lado = (cuadritos + 2 * MARGEN) * TAMANO_CUADRITO
imagen = Image.new("RGB", (lado, lado), "white")
pixeles = imagen.load()

for fila in range(cuadritos):
    for columna in range(cuadritos):
        if qr.isDark(fila, columna):
            x0 = (columna + MARGEN) * TAMANO_CUADRITO
            y0 = (fila + MARGEN) * TAMANO_CUADRITO
            for x in range(x0, x0 + TAMANO_CUADRITO):
                for y in range(y0, y0 + TAMANO_CUADRITO):
                    pixeles[x, y] = (0, 0, 0)

# 3) Guardamos la imagen en la carpeta static/img
carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "img")
ruta = os.path.join(carpeta, "whatsapp-qr.png")
imagen.save(ruta)
print("Listo: se creó", ruta)
print("Enlace del QR:", ENLACE)
