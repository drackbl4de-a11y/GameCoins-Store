"""
db.py
-----
Aquí está TODO lo que habla con la base de datos PostgreSQL.
app.py y admin.py no escriben SQL: llaman a las funciones de este archivo.

Para no repetir código, hay 4 funciones "ayudantes" (sección 1).
Todas las demás funciones solo escriben su consulta SQL y usan un ayudante.
"""

import psycopg2
import psycopg2.extras
from config import DB_CONFIG, DATABASE_URL


# ============================================================
# 1. AYUDANTES (las 4 funciones que usan todas las demás)
# ============================================================

def conectar():
    """Abre una conexión nueva con la base de datos."""
    return psycopg2.connect(DATABASE_URL)


def consultar(sql, datos=(), uno=False):
    """
    Para los SELECT (leer datos).
      - uno=False -> devuelve una lista de diccionarios (varias filas)
      - uno=True  -> devuelve un solo diccionario, o None si no hay nada
    Los %s del SQL se reemplazan por lo que va en 'datos' (así evitamos
    la inyección SQL: nunca se pega el texto del usuario directo en la consulta).
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql, datos)
        if uno:
            return cursor.fetchone()
        return cursor.fetchall()
    finally:
        conexion.close()


def ejecutar(sql, datos=()):
    """Para INSERT, UPDATE y DELETE (cambiar datos). Guarda los cambios con commit."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(sql, datos)
        conexion.commit()
    finally:
        conexion.close()


def insertar(sql, datos=()):
    """
    Para INSERT que termina en "RETURNING <id>": guarda el registro y
    devuelve el id que PostgreSQL le asignó.
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(sql, datos)
        nuevo_id = cursor.fetchone()[0]
        conexion.commit()
        return nuevo_id
    finally:
        conexion.close()


# Este pedazo de SQL se repite en varias consultas: busca la promoción
# que esté activa HOY para un paquete (si la hay).
PROMOCION_ACTIVA = """
    LEFT JOIN promocion promo
           ON promo.paquete_id = p.paquete_id
          AND promo.estado = TRUE
          AND CURRENT_DATE BETWEEN promo.fecha_inicio AND promo.fecha_fin
"""

# Y este calcula el precio ya con el descuento
PRECIO_CON_DESCUENTO = "ROUND(p.precio_cop * (1 - promo.porcentaje_descuento / 100.0))"


# ============================================================
# 2. USUARIOS Y PERFIL
# ============================================================

def obtener_usuario_por_correo(correo):
    return consultar("SELECT * FROM usuario WHERE correo = %s;", (correo,), uno=True)


def obtener_usuario_por_id(usuario_id):
    return consultar("SELECT * FROM usuario WHERE usuario_id = %s;", (usuario_id,), uno=True)


def crear_usuario(nombre, apellido, correo, contrasena_hash, verificado=False):
    """verificado=True cuando la persona ya confirmó su correo con el código."""
    return insertar(
        "INSERT INTO usuario (nombre, apellido, correo, contrasena_hash, correo_verificado) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING usuario_id;",
        (nombre, apellido, correo, contrasena_hash, verificado))


def actualizar_ultimo_login(usuario_id):
    ejecutar("UPDATE usuario SET ultimo_login = NOW() WHERE usuario_id = %s;", (usuario_id,))


def actualizar_datos_personales(usuario_id, nombre, apellido, telefono):
    ejecutar("UPDATE usuario SET nombre = %s, apellido = %s, telefono = %s WHERE usuario_id = %s;",
             (nombre, apellido, telefono, usuario_id))


def actualizar_foto_perfil(usuario_id, foto_perfil_url):
    ejecutar("UPDATE usuario SET foto_perfil_url = %s WHERE usuario_id = %s;",
             (foto_perfil_url, usuario_id))


def actualizar_contrasena(usuario_id, nueva_contrasena_hash):
    ejecutar("UPDATE usuario SET contrasena_hash = %s WHERE usuario_id = %s;",
             (nueva_contrasena_hash, usuario_id))


# ============================================================
# 3. CATÁLOGO (juegos, paquetes, promociones, búsqueda)
# ============================================================

def obtener_juegos_activos():
    """Juegos visibles, con cuántos paquetes tienen y el precio más bajo."""
    return consultar("""
        SELECT j.*, COUNT(p.paquete_id) AS total_paquetes, MIN(p.precio_cop) AS precio_desde,
               MIN(m.nombre) AS moneda_nombre
        FROM juego j
        LEFT JOIN moneda m ON m.juego_id = j.juego_id AND m.estado = TRUE
        LEFT JOIN paquete p ON p.moneda_id = m.moneda_id AND p.estado = TRUE
        WHERE j.estado = TRUE
        GROUP BY j.juego_id
        ORDER BY j.juego_id;
    """)


def obtener_juego_por_id(juego_id):
    return consultar("SELECT * FROM juego WHERE juego_id = %s AND estado = TRUE;", (juego_id,), uno=True)


def obtener_paquetes_por_juego(juego_id):
    """Paquetes de un juego (de menos a más monedas), con su descuento si tienen."""
    return consultar(f"""
        SELECT p.*, m.nombre AS moneda_nombre, m.imagen_url AS moneda_imagen_url,
               promo.porcentaje_descuento, promo.titulo AS promo_titulo,
               {PRECIO_CON_DESCUENTO} AS precio_con_descuento
        FROM paquete p
        JOIN moneda m ON m.moneda_id = p.moneda_id
        {PROMOCION_ACTIVA}
        WHERE m.juego_id = %s AND p.estado = TRUE
        ORDER BY p.cantidad_monedas ASC;
    """, (juego_id,))


def obtener_promociones_activas():
    """Promociones vigentes hoy, con los datos del paquete y del juego."""
    return consultar("""
        SELECT promo.*, p.nombre AS paquete_nombre, p.precio_cop, p.stock,
               p.imagen_url AS paquete_imagen_url, m.imagen_url AS moneda_imagen_url,
               ROUND(p.precio_cop * (1 - promo.porcentaje_descuento / 100.0)) AS precio_con_descuento,
               j.nombre AS juego_nombre, j.juego_id
        FROM promocion promo
        JOIN paquete p ON p.paquete_id = promo.paquete_id
        JOIN moneda m ON m.moneda_id = p.moneda_id
        JOIN juego j ON j.juego_id = m.juego_id
        WHERE promo.estado = TRUE
          AND p.estado = TRUE
          AND CURRENT_DATE BETWEEN promo.fecha_inicio AND promo.fecha_fin
        ORDER BY promo.fecha_fin ASC;
    """)


def obtener_paquete_con_precio(paquete_id):
    """
    Un paquete con su precio final (con descuento si hay promoción, si no
    el precio normal). Se usa al agregar al carrito: el precio se lee de
    la base de datos, nunca del formulario.
    """
    return consultar(f"""
        SELECT p.*, m.nombre AS moneda_nombre, j.nombre AS juego_nombre,
               promo.porcentaje_descuento,
               COALESCE({PRECIO_CON_DESCUENTO}, p.precio_cop) AS precio_final
        FROM paquete p
        JOIN moneda m ON m.moneda_id = p.moneda_id
        JOIN juego j ON j.juego_id = m.juego_id
        {PROMOCION_ACTIVA}
        WHERE p.paquete_id = %s AND p.estado = TRUE;
    """, (paquete_id,), uno=True)


def buscar_paquetes(texto_busqueda):
    """Busca por nombre de paquete, moneda o juego (ILIKE = sin importar mayúsculas)."""
    patron = f"%{texto_busqueda}%"
    return consultar(f"""
        SELECT p.*, m.nombre AS moneda_nombre, m.imagen_url AS moneda_imagen_url,
               j.nombre AS juego_nombre, j.juego_id,
               promo.porcentaje_descuento,
               {PRECIO_CON_DESCUENTO} AS precio_con_descuento
        FROM paquete p
        JOIN moneda m ON m.moneda_id = p.moneda_id
        JOIN juego j ON j.juego_id = m.juego_id
        {PROMOCION_ACTIVA}
        WHERE p.estado = TRUE
          AND (p.nombre ILIKE %s OR m.nombre ILIKE %s OR j.nombre ILIKE %s)
        ORDER BY j.nombre, p.cantidad_monedas ASC;
    """, (patron, patron, patron))


# ============================================================
# 4. CARRITO DE COMPRAS
# ============================================================

def obtener_o_crear_carrito_activo(usuario_id):
    """Devuelve el id del carrito ACTIVO del usuario; si no tiene, lo crea."""
    carrito = consultar(
        "SELECT carrito_id FROM carrito WHERE usuario_id = %s AND estado = 'ACTIVO' LIMIT 1;",
        (usuario_id,), uno=True)
    if carrito:
        return carrito["carrito_id"]
    return insertar(
        "INSERT INTO carrito (usuario_id, estado) VALUES (%s, 'ACTIVO') RETURNING carrito_id;",
        (usuario_id,))


def agregar_item_carrito(carrito_id, paquete_id, precio_unitario):
    """
    Agrega un paquete al carrito. Si ya estaba, le suma 1 a la cantidad.
    Devuelve False si no quedan unidades suficientes (stock), True si se agregó.
    """
    paquete = consultar("SELECT stock FROM paquete WHERE paquete_id = %s;", (paquete_id,), uno=True)
    item = consultar(
        "SELECT detalle_carrito_id, cantidad FROM detalle_carrito WHERE carrito_id = %s AND paquete_id = %s;",
        (carrito_id, paquete_id), uno=True)

    en_carrito = item["cantidad"] if item else 0
    if en_carrito + 1 > paquete["stock"]:
        return False                      # ya tiene en el carrito todo lo que queda

    if item:
        nueva_cantidad = item["cantidad"] + 1
        ejecutar("UPDATE detalle_carrito SET cantidad = %s, subtotal = %s WHERE detalle_carrito_id = %s;",
                 (nueva_cantidad, nueva_cantidad * precio_unitario, item["detalle_carrito_id"]))
    else:
        ejecutar("INSERT INTO detalle_carrito (carrito_id, paquete_id, cantidad, precio_unitario, subtotal) "
                 "VALUES (%s, %s, 1, %s, %s);",
                 (carrito_id, paquete_id, precio_unitario, precio_unitario))
    return True


def obtener_items_carrito(carrito_id):
    return consultar("""
        SELECT dc.*, p.nombre AS paquete_nombre, p.stock AS stock_disponible,
               m.nombre AS moneda_nombre, j.nombre AS juego_nombre
        FROM detalle_carrito dc
        JOIN paquete p ON p.paquete_id = dc.paquete_id
        JOIN moneda m ON m.moneda_id = p.moneda_id
        JOIN juego j ON j.juego_id = m.juego_id
        WHERE dc.carrito_id = %s
        ORDER BY dc.detalle_carrito_id;
    """, (carrito_id,))


def contar_items_carrito(usuario_id):
    """Total de unidades en el carrito (el numerito rojo del ícono del carrito)."""
    fila = consultar("""
        SELECT COALESCE(SUM(dc.cantidad), 0) AS total
        FROM detalle_carrito dc
        JOIN carrito c ON c.carrito_id = dc.carrito_id
        WHERE c.usuario_id = %s AND c.estado = 'ACTIVO';
    """, (usuario_id,), uno=True)
    return fila["total"]


def actualizar_cantidad_item(detalle_carrito_id, usuario_id, delta):
    """
    Suma (+1) o resta (-1) la cantidad de un item. Si llega a 0 se elimina.
    También comprueba que el item sea del carrito de ESE usuario.
    Devuelve False si se quiso sumar más de las unidades que hay (stock).
    """
    item = consultar("""
        SELECT dc.cantidad, dc.precio_unitario, p.stock
        FROM detalle_carrito dc
        JOIN carrito c ON c.carrito_id = dc.carrito_id
        JOIN paquete p ON p.paquete_id = dc.paquete_id
        WHERE dc.detalle_carrito_id = %s AND c.usuario_id = %s;
    """, (detalle_carrito_id, usuario_id), uno=True)
    if not item:
        return True  # no existe o es de otro usuario: no hacemos nada

    nueva_cantidad = item["cantidad"] + delta
    if delta > 0 and nueva_cantidad > item["stock"]:
        return False
    if nueva_cantidad <= 0:
        ejecutar("DELETE FROM detalle_carrito WHERE detalle_carrito_id = %s;", (detalle_carrito_id,))
    else:
        ejecutar("UPDATE detalle_carrito SET cantidad = %s, subtotal = %s WHERE detalle_carrito_id = %s;",
                 (nueva_cantidad, nueva_cantidad * item["precio_unitario"], detalle_carrito_id))
    return True


def descontar_stock(paquete_id, cantidad):
    """
    Resta unidades del stock al confirmar la compra. El "AND stock >= %s" evita que
    quede negativo si dos personas compran la última unidad al mismo tiempo.
    Devuelve True si se pudo descontar, False si ya no alcanzaba.
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("UPDATE paquete SET stock = stock - %s WHERE paquete_id = %s AND stock >= %s "
                       "RETURNING paquete_id;", (cantidad, paquete_id, cantidad))
        fila = cursor.fetchone()          # si no alcanzaba, no se cambió ninguna fila y viene None
        conexion.commit()
        return fila is not None
    finally:
        conexion.close()


def devolver_stock(paquete_id, cantidad):
    """Devuelve unidades al stock (por ejemplo cuando un pedido se cancela)."""
    ejecutar("UPDATE paquete SET stock = stock + %s WHERE paquete_id = %s;", (cantidad, paquete_id))


def eliminar_item_carrito(detalle_carrito_id, usuario_id):
    """Quita un paquete del carrito (solo si es del usuario dueño)."""
    ejecutar("""
        DELETE FROM detalle_carrito
        WHERE detalle_carrito_id = %s
          AND carrito_id IN (SELECT carrito_id FROM carrito WHERE usuario_id = %s);
    """, (detalle_carrito_id, usuario_id))


def vaciar_carrito(carrito_id):
    """Después de comprar: borra los items y marca el carrito como CONVERTIDO."""
    ejecutar("DELETE FROM detalle_carrito WHERE carrito_id = %s;", (carrito_id,))
    ejecutar("UPDATE carrito SET estado = 'CONVERTIDO' WHERE carrito_id = %s;", (carrito_id,))


# ============================================================
# 5. COMPRAS (pedidos, pago simulado y certificado)
# ============================================================

def crear_compra(usuario_id, total_cop, codigo_pedido):
    return insertar(
        "INSERT INTO compra (usuario_id, total_cop, codigo_pedido, estado_pedido) "
        "VALUES (%s, %s, %s, 'PROCESADO') RETURNING compra_id;",
        (usuario_id, total_cop, codigo_pedido))


def crear_detalle_compra(compra_id, paquete_id, cantidad, precio_unitario, subtotal, dato_entrega):
    """Un paquete comprado, con el dato de entrega (usuario de Roblox o ID de VALORANT)."""
    ejecutar("""
        INSERT INTO detalle_compra (compra_id, paquete_id, cantidad, precio_unitario, subtotal, dato_entrega)
        VALUES (%s, %s, %s, %s, %s, %s);
    """, (compra_id, paquete_id, cantidad, precio_unitario, subtotal, dato_entrega))


def crear_datos_pago(compra_id, nombre_titular, tipo_tarjeta, numero_enmascarado, vencimiento):
    """Pago SIMULADO: solo se guardan los últimos 4 dígitos, nunca el número completo."""
    ejecutar("""
        INSERT INTO datos_entrega_pago
            (compra_id, nombre_titular, tipo_tarjeta, numero_tarjeta_enmascarado,
             fecha_vencimiento_simulada, pago_simulado)
        VALUES (%s, %s, %s, %s, %s, TRUE);
    """, (compra_id, nombre_titular, tipo_tarjeta, numero_enmascarado, vencimiento))


def obtener_compra_por_id(compra_id, usuario_id):
    """Un pedido, comprobando que sea del usuario (nadie ve pedidos ajenos)."""
    return consultar("SELECT * FROM compra WHERE compra_id = %s AND usuario_id = %s;",
                     (compra_id, usuario_id), uno=True)


def obtener_detalle_compra(compra_id):
    return consultar("""
        SELECT dc.*, p.nombre AS paquete_nombre, p.cantidad_monedas, m.nombre AS moneda_nombre, j.nombre AS juego_nombre,
               p.imagen_url AS paquete_imagen_url, m.imagen_url AS moneda_imagen_url
        FROM detalle_compra dc
        JOIN paquete p ON p.paquete_id = dc.paquete_id
        JOIN moneda m ON m.moneda_id = p.moneda_id
        JOIN juego j ON j.juego_id = m.juego_id
        WHERE dc.compra_id = %s
        ORDER BY dc.detalle_compra_id;
    """, (compra_id,))


def obtener_datos_pago(compra_id):
    """Datos del pago simulado (titular y celular tapado) de un pedido."""
    return consultar("SELECT * FROM datos_entrega_pago WHERE compra_id = %s;", (compra_id,), uno=True)


def obtener_pedidos_usuario(usuario_id):
    return consultar("SELECT * FROM compra WHERE usuario_id = %s ORDER BY fecha_compra DESC;", (usuario_id,))


def obtener_resumen_perfil(usuario_id):
    """Números de la pestaña "Mi Perfil": pedidos, paquetes comprados, total gastado y primera compra."""
    return consultar("""
        SELECT COUNT(DISTINCT c.compra_id) AS pedidos,
               COALESCE(SUM(dc.cantidad), 0) AS paquetes,
               MIN(c.fecha_compra) AS primera_compra,
               (SELECT COALESCE(SUM(total_cop), 0) FROM compra
                 WHERE usuario_id = %s AND estado_pedido != 'CANCELADO') AS gastado
        FROM compra c
        JOIN detalle_compra dc ON dc.compra_id = c.compra_id
        WHERE c.usuario_id = %s AND c.estado_pedido != 'CANCELADO';
    """, (usuario_id, usuario_id), uno=True)


def obtener_paquete_favorito(usuario_id):
    """El paquete que más ha comprado el usuario (o None si todavía no ha comprado)."""
    return consultar("""
        SELECT p.nombre, p.imagen_url, m.imagen_url AS moneda_imagen_url,
               j.nombre AS juego_nombre, SUM(dc.cantidad) AS unidades
        FROM detalle_compra dc
        JOIN compra c ON c.compra_id = dc.compra_id
        JOIN paquete p ON p.paquete_id = dc.paquete_id
        JOIN moneda m ON m.moneda_id = p.moneda_id
        JOIN juego j ON j.juego_id = m.juego_id
        WHERE c.usuario_id = %s AND c.estado_pedido != 'CANCELADO'
        GROUP BY p.paquete_id, p.nombre, p.imagen_url, m.imagen_url, j.nombre
        ORDER BY unidades DESC
        LIMIT 1;
    """, (usuario_id,), uno=True)


def obtener_certificado_por_compra(compra_id):
    return consultar("SELECT * FROM certificado WHERE compra_id = %s;", (compra_id,), uno=True)


def crear_certificado(compra_id, codigo_certificado):
    ejecutar("INSERT INTO certificado (compra_id, codigo_certificado) VALUES (%s, %s);",
             (compra_id, codigo_certificado))


# ============================================================
# 6. COMENTARIOS
# ============================================================

def crear_comentario(usuario_id, contenido, calificacion):
    ejecutar("INSERT INTO comentario (usuario_id, contenido, calificacion, visible) VALUES (%s, %s, %s, TRUE);",
             (usuario_id, contenido, calificacion))


def obtener_comentarios_visibles():
    return consultar("""
        SELECT c.*, u.nombre AS usuario_nombre, u.foto_perfil_url AS usuario_foto
        FROM comentario c
        JOIN usuario u ON u.usuario_id = c.usuario_id
        WHERE c.visible = TRUE
        ORDER BY c.fecha_comentario DESC;
    """)


# ============================================================
# 7. PANEL DE ADMINISTRADOR
# ============================================================

# --- Auditoría y estadísticas ---

def registrar_auditoria(admin_id, accion, entidad_afectada, entidad_id, detalle):
    """Deja anotado qué hizo el administrador (y cuándo, gracias al NOW() de la tabla)."""
    ejecutar("""
        INSERT INTO registro_auditoria (admin_id, accion, entidad_afectada, entidad_id, detalle)
        VALUES (%s, %s, %s, %s, %s);
    """, (admin_id, accion, entidad_afectada, entidad_id, detalle))


def obtener_auditoria(desde=None, hasta=None):
    return consultar("""
        SELECT r.*, u.nombre AS admin_nombre
        FROM registro_auditoria r
        JOIN usuario u ON u.usuario_id = r.admin_id
        WHERE (%s::date IS NULL OR r.fecha_accion::date >= %s::date)
          AND (%s::date IS NULL OR r.fecha_accion::date <= %s::date)
        ORDER BY r.fecha_accion DESC
        LIMIT 200;
    """, (desde, desde, hasta, hasta))


def obtener_estadisticas():
    """Los números del dashboard."""
    # Misma regla que la página Ventas: solo los pedidos ENTREGADOS suman dinero
    ventas = consultar("SELECT COALESCE(SUM(total_cop), 0) AS total FROM compra WHERE estado_pedido = 'ENTREGADO';", uno=True)
    pedidos = consultar("SELECT COUNT(*) AS total FROM compra;", uno=True)
    usuarios = consultar("SELECT COUNT(*) AS total FROM usuario;", uno=True)
    activos = consultar("SELECT COUNT(*) AS total FROM usuario WHERE estado = 'A';", uno=True)
    mas_vendido = consultar("""
        SELECT p.nombre, SUM(dc.cantidad) AS unidades
        FROM detalle_compra dc
        JOIN paquete p ON p.paquete_id = dc.paquete_id
        GROUP BY p.paquete_id, p.nombre
        ORDER BY unidades DESC
        LIMIT 1;
    """, uno=True)

    return {
        "ventas_totales": ventas["total"],
        "total_pedidos": pedidos["total"],
        "total_usuarios": usuarios["total"],
        "usuarios_activos": activos["total"],
        "paquete_mas_vendido": mas_vendido,
    }


# --- Juegos ---

def obtener_juegos_admin():
    return consultar("SELECT * FROM juego ORDER BY juego_id;")


def obtener_juego_por_id_admin(juego_id):
    return consultar("SELECT * FROM juego WHERE juego_id = %s;", (juego_id,), uno=True)


def obtener_moneda_de_juego(juego_id):
    return consultar("SELECT * FROM moneda WHERE juego_id = %s ORDER BY moneda_id LIMIT 1;", (juego_id,), uno=True)


def crear_juego_con_moneda(nombre, descripcion, nombre_moneda, admin_id, imagen_url=None, moneda_imagen_url=None):
    """Crea el juego y su moneda (ej. Roblox + Robux) de una vez."""
    juego_id = insertar(
        "INSERT INTO juego (nombre, descripcion, imagen_url, estado, admin_id) "
        "VALUES (%s, %s, %s, TRUE, %s) RETURNING juego_id;",
        (nombre, descripcion, imagen_url, admin_id))
    ejecutar("INSERT INTO moneda (juego_id, nombre, imagen_url, estado) VALUES (%s, %s, %s, TRUE);",
             (juego_id, nombre_moneda, moneda_imagen_url))
    return juego_id


def actualizar_juego(juego_id, nombre, descripcion, imagen_url=None, moneda_imagen_url=None):
    """
    COALESCE(%s, imagen_url) significa: "usa la imagen nueva, pero si no
    llegó ninguna (None), deja la que ya tenía".
    """
    ejecutar("UPDATE juego SET nombre = %s, descripcion = %s, imagen_url = COALESCE(%s, imagen_url) "
             "WHERE juego_id = %s;", (nombre, descripcion, imagen_url, juego_id))
    if moneda_imagen_url:
        ejecutar("UPDATE moneda SET imagen_url = %s WHERE juego_id = %s;", (moneda_imagen_url, juego_id))


def cambiar_estado_juego(juego_id, nuevo_estado):
    """No se borra de verdad: se desactiva, para no perder el historial de compras."""
    ejecutar("UPDATE juego SET estado = %s WHERE juego_id = %s;", (nuevo_estado, juego_id))


# --- Paquetes ---

def obtener_monedas_todas():
    return consultar("""
        SELECT m.moneda_id, m.nombre AS moneda_nombre, j.nombre AS juego_nombre
        FROM moneda m
        JOIN juego j ON j.juego_id = m.juego_id
        ORDER BY j.nombre, m.nombre;
    """)


def obtener_paquetes_admin():
    return consultar("""
        SELECT p.*, m.nombre AS moneda_nombre, j.nombre AS juego_nombre
        FROM paquete p
        JOIN moneda m ON m.moneda_id = p.moneda_id
        JOIN juego j ON j.juego_id = m.juego_id
        ORDER BY j.nombre, p.cantidad_monedas;
    """)


def obtener_paquete_por_id_admin(paquete_id):
    return consultar("SELECT * FROM paquete WHERE paquete_id = %s;", (paquete_id,), uno=True)


def crear_paquete(moneda_id, admin_id, nombre, descripcion, cantidad_monedas, precio_cop, stock, imagen_url=None):
    return insertar("""
        INSERT INTO paquete (moneda_id, admin_id, nombre, descripcion, cantidad_monedas, precio_cop, stock, imagen_url, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        RETURNING paquete_id;
    """, (moneda_id, admin_id, nombre, descripcion, cantidad_monedas, precio_cop, stock, imagen_url))


def actualizar_paquete(paquete_id, moneda_id, nombre, descripcion, cantidad_monedas, precio_cop, stock, imagen_url=None):
    ejecutar("""
        UPDATE paquete
        SET moneda_id = %s, nombre = %s, descripcion = %s,
            cantidad_monedas = %s, precio_cop = %s, stock = %s,
            imagen_url = COALESCE(%s, imagen_url), fecha_actualizacion = NOW()
        WHERE paquete_id = %s;
    """, (moneda_id, nombre, descripcion, cantidad_monedas, precio_cop, stock, imagen_url, paquete_id))


def rellenar_stock(paquete_id, cantidad):
    """El admin suma unidades al stock de un paquete (por ejemplo +10)."""
    ejecutar("UPDATE paquete SET stock = stock + %s, fecha_actualizacion = NOW() WHERE paquete_id = %s;",
             (cantidad, paquete_id))


def cambiar_estado_paquete(paquete_id, nuevo_estado):
    """Desactivar = ocultarlo a los usuarios sin borrarlo (así las compras viejas no se rompen)."""
    ejecutar("UPDATE paquete SET estado = %s WHERE paquete_id = %s;", (nuevo_estado, paquete_id))


def paquete_tiene_compras(paquete_id):
    """True si alguien ya compró este paquete (en ese caso no se puede borrar de verdad)."""
    fila = consultar("SELECT 1 AS hay FROM detalle_compra WHERE paquete_id = %s LIMIT 1;",
                     (paquete_id,), uno=True)
    return fila is not None


def eliminar_paquete(paquete_id):
    """Borra el paquete de verdad, junto con sus promociones y sus apariciones en carritos."""
    ejecutar("DELETE FROM detalle_carrito WHERE paquete_id = %s;", (paquete_id,))
    ejecutar("DELETE FROM promocion WHERE paquete_id = %s;", (paquete_id,))
    ejecutar("DELETE FROM paquete WHERE paquete_id = %s;", (paquete_id,))


# --- Promociones ---

def obtener_promociones_admin():
    return consultar("""
        SELECT promo.*, p.nombre AS paquete_nombre, j.nombre AS juego_nombre
        FROM promocion promo
        JOIN paquete p ON p.paquete_id = promo.paquete_id
        JOIN moneda m ON m.moneda_id = p.moneda_id
        JOIN juego j ON j.juego_id = m.juego_id
        ORDER BY promo.fecha_fin DESC;
    """)


def obtener_promocion_por_id(promocion_id):
    return consultar("SELECT * FROM promocion WHERE promocion_id = %s;", (promocion_id,), uno=True)


def crear_promocion(paquete_id, admin_id, titulo, descripcion, porcentaje_descuento, fecha_inicio, fecha_fin):
    return insertar("""
        INSERT INTO promocion (paquete_id, admin_id, titulo, descripcion, porcentaje_descuento, fecha_inicio, fecha_fin, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
        RETURNING promocion_id;
    """, (paquete_id, admin_id, titulo, descripcion, porcentaje_descuento, fecha_inicio, fecha_fin))


def actualizar_promocion(promocion_id, titulo, descripcion, porcentaje_descuento, fecha_inicio, fecha_fin):
    ejecutar("""
        UPDATE promocion
        SET titulo = %s, descripcion = %s, porcentaje_descuento = %s,
            fecha_inicio = %s, fecha_fin = %s
        WHERE promocion_id = %s;
    """, (titulo, descripcion, porcentaje_descuento, fecha_inicio, fecha_fin, promocion_id))


def cambiar_estado_promocion(promocion_id, nuevo_estado):
    """Desactivar una promoción la oculta a los usuarios sin borrarla."""
    ejecutar("UPDATE promocion SET estado = %s WHERE promocion_id = %s;", (nuevo_estado, promocion_id))


def eliminar_promocion(promocion_id):
    ejecutar("DELETE FROM promocion WHERE promocion_id = %s;", (promocion_id,))


# --- Compras ---

def obtener_todas_las_compras(desde=None, hasta=None):
    return consultar("""
        SELECT c.*, u.nombre AS usuario_nombre, u.correo AS usuario_correo
        FROM compra c
        JOIN usuario u ON u.usuario_id = c.usuario_id
        WHERE (%s::date IS NULL OR c.fecha_compra::date >= %s::date)
          AND (%s::date IS NULL OR c.fecha_compra::date <= %s::date)
        ORDER BY c.fecha_compra DESC;
    """, (desde, desde, hasta, hasta))


def obtener_compra_por_id_admin(compra_id):
    return consultar("""
        SELECT c.*, u.nombre AS usuario_nombre, u.correo AS usuario_correo
        FROM compra c
        JOIN usuario u ON u.usuario_id = c.usuario_id
        WHERE c.compra_id = %s;
    """, (compra_id,), uno=True)


def actualizar_estado_pedido(compra_id, nuevo_estado):
    ejecutar("UPDATE compra SET estado_pedido = %s WHERE compra_id = %s;", (nuevo_estado, compra_id))


# --- Usuarios ---

def obtener_usuarios_admin(desde=None, hasta=None):
    return consultar("""
        SELECT usuario_id, nombre, apellido, correo, estado, fecha_registro, ultimo_login
        FROM usuario
        WHERE (%s::date IS NULL OR fecha_registro::date >= %s::date)
          AND (%s::date IS NULL OR fecha_registro::date <= %s::date)
        ORDER BY fecha_registro DESC;
    """, (desde, desde, hasta, hasta))


def cambiar_estado_usuario(usuario_id, nuevo_estado):
    """'A' = activo, 'I' = inactivo."""
    ejecutar("UPDATE usuario SET estado = %s WHERE usuario_id = %s;", (nuevo_estado, usuario_id))


# --- Comentarios ---

def obtener_comentarios_admin(desde=None, hasta=None):
    return consultar("""
        SELECT c.*, u.nombre AS usuario_nombre, u.foto_perfil_url AS usuario_foto
        FROM comentario c
        JOIN usuario u ON u.usuario_id = c.usuario_id
        WHERE (%s::date IS NULL OR c.fecha_comentario::date >= %s::date)
          AND (%s::date IS NULL OR c.fecha_comentario::date <= %s::date)
        ORDER BY c.fecha_comentario DESC;
    """, (desde, desde, hasta, hasta))


def responder_comentario(comentario_id, admin_id, respuesta):
    """Guarda (o cambia) la respuesta del administrador a un comentario."""
    ejecutar("""
        UPDATE comentario
        SET respuesta_admin = %s, fecha_respuesta = NOW(), admin_id = %s
        WHERE comentario_id = %s;
    """, (respuesta, admin_id, comentario_id))


def eliminar_comentario(comentario_id):
    ejecutar("DELETE FROM comentario WHERE comentario_id = %s;", (comentario_id,))
