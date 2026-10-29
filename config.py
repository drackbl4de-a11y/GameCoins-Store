"""
config.py
---------
Datos de configuración: cómo conectarse a PostgreSQL y la clave secreta de Flask.
"""

# Datos de conexión a PostgreSQL (los mismos que usas en SQL Shell)
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "gamecoins_store",
    "user": "postgres",
    "password": "12022008",   # <-- cámbiala por la tuya (sin tildes ni ñ)
}

# Clave secreta de Flask: sirve para proteger la sesión (el login)
SECRET_KEY = "clave-secreta-de-desarrollo-cambiar"


# ------------------------------------------------------------
# Envío de correos (certificado de compra y código de verificación)
# Usamos una cuenta de Gmail del proyecto. IMPORTANTE: la "clave" NO es la
# contraseña normal de Gmail, es una "contraseña de aplicación" (ver README).
# Si MAIL_USUARIO se deja vacío, la página funciona igual pero NO envía correos.
# ------------------------------------------------------------
MAIL_USUARIO = "gamecoinsstoree@gmail.com"            # ejemplo: "gamecoinsstore.sena@gmail.com"
MAIL_CLAVE = "jhfbegzrhglsmgrm"              # contraseña de aplicación de 16 letras (sin espacios)
MAIL_SERVIDOR = "smtp.gmail.com"
MAIL_PUERTO = 587


# ------------------------------------------------------------
# Contacto por WhatsApp
# Se usan en app.py (botón y página Contacto) y en generar_qr.py (código QR).
# El número va con el código del país y sin "+" ni espacios (57 = Colombia).
# Si lo cambias aquí, vuelve a ejecutar:  python generar_qr.py
# ------------------------------------------------------------
WHATSAPP_NUMERO = "573006218342"
WHATSAPP_NUMERO_VISIBLE = "+57 300 6218342"
WHATSAPP_MENSAJE = "Hola GameCoins Store, necesito ayuda con mi compra."

# Redes sociales (se ven en el pie de página de todas las páginas)
WHATSAPP_CANAL_URL = "https://whatsapp.com/channel/0029VbDtdEYChq6HImIOCr0L"
INSTAGRAM_URL = "https://www.instagram.com/gamecoinsstoree?xtok=eml0NG53ZjIzbzR0"

import os 

import psycopg2

DATABASE_URL = os.environ["DATABASE_URL"]

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)
    