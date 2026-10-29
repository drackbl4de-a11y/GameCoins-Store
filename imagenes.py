"""
imagenes.py
-----------
Funciones para subir y borrar imágenes (foto de perfil, logos de juegos,
íconos de monedas e imágenes de paquetes). Las usan app.py y admin.py.
Las imágenes se guardan en la carpeta static/img/<subcarpeta>/ y en la
base de datos solo se guarda su ruta (ej. "img/juegos/a1b2c3.png").
"""

import os
import secrets

from flask import current_app

EXTENSIONES_PERMITIDAS = ["png", "jpg", "jpeg", "webp", "gif"]


def extension_de(archivo):
    """Devuelve la extensión del archivo en minúscula ('foto.PNG' -> 'png')."""
    nombre = archivo.filename or ""
    if "." not in nombre:
        return ""
    return nombre.rsplit(".", 1)[-1].lower()


def error_de_imagen(archivo):
    """
    Devuelve un texto de error si el archivo no es una imagen válida.
    Devuelve None si está bien (o si no se subió ningún archivo).
    """
    if not archivo or archivo.filename == "":
        return None
    if extension_de(archivo) not in EXTENSIONES_PERMITIDAS:
        return "Formato de imagen no válido. Usa PNG, JPG, WEBP o GIF."
    return None


def guardar_imagen(archivo, subcarpeta, nombre=None):
    """
    Guarda la imagen en static/img/<subcarpeta>/ y devuelve su ruta
    (la que va a la base de datos). Si no se da un nombre, se inventa
    uno al azar para que dos imágenes nunca se pisen.
    Devuelve None si no se subió ningún archivo.
    """
    if not archivo or archivo.filename == "":
        return None

    carpeta = os.path.join(current_app.static_folder, "img", subcarpeta)
    os.makedirs(carpeta, exist_ok=True)

    if nombre is None:
        nombre = secrets.token_hex(6)
    nombre_archivo = f"{nombre}.{extension_de(archivo)}"
    archivo.save(os.path.join(carpeta, nombre_archivo))
    return f"img/{subcarpeta}/{nombre_archivo}"


def borrar_imagen(ruta):
    """Borra una imagen vieja del disco (solo si está en las carpetas de imágenes del sitio)."""
    carpetas_permitidas = ("img/juegos/", "img/monedas/", "img/paquetes/")
    if not ruta or ".." in ruta or not ruta.startswith(carpetas_permitidas):
        return
    try:
        os.remove(os.path.join(current_app.static_folder, ruta))
    except OSError:
        pass
