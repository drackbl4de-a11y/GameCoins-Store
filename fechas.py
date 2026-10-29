"""
fechas.py
---------
Convierte una fecha en un texto fácil de leer: "Hoy", "Ayer", "Hace 3 días",
"Hace 1 semana", "Hace 2 meses"... Se usa en los HTML con el filtro "hace":

    {{ compra.fecha_compra|hace }}
"""

from datetime import datetime


def hace_cuanto(fecha):
    """Recibe un datetime y devuelve el texto relativo a hoy."""
    if not fecha:
        return "—"

    dias = (datetime.now().date() - fecha.date()).days   # días completos de diferencia

    if dias < 0:
        return fecha.strftime("%d/%m/%Y")                # fecha futura: la mostramos normal
    if dias == 0:
        return "Hoy"
    if dias == 1:
        return "Ayer"
    if dias < 7:
        return f"Hace {dias} días"
    if dias < 30:
        semanas = dias // 7
        return "Hace 1 semana" if semanas == 1 else f"Hace {semanas} semanas"
    if dias < 365:
        meses = dias // 30
        return "Hace 1 mes" if meses == 1 else f"Hace {meses} meses"

    anios = dias // 365
    return "Hace 1 año" if anios == 1 else f"Hace {anios} años"


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def mes_y_anio(fecha):
    """Convierte una fecha en 'octubre 2026'."""
    return f"{MESES[fecha.month - 1]} {fecha.year}"
