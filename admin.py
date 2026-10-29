"""
admin.py
--------
Rutas del panel de administrador. Todas empiezan por /admin.

Está separado de app.py usando un "Blueprint" de Flask: un grupo de
rutas que luego app.py registra. Por eso en los HTML se escribe
url_for("admin.dashboard") (el nombre del blueprint va antes del punto).

El administrador NO tiene un login aparte: inicia sesión por /login como
todos, pero su cuenta tiene rol = 'ADMIN' en la base de datos.
"""

from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

import db
import imagenes
import correo as servicio_correo
from servicio_pedido import avisar_estado_por_correo

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_requerido(vista):
    """
    Decorador: se escribe @admin_requerido encima de una ruta y la protege.
    Si no hay sesión, manda al login. Si la cuenta no es ADMIN, la devuelve al inicio.
    """
    @wraps(vista)
    def vista_protegida(*args, **kwargs):
        if not session.get("usuario_id"):
            flash("Debes iniciar sesión para entrar al panel de administrador.", "error")
            return redirect(url_for("login"))
        if session.get("rol") != "ADMIN":
            flash("Tu cuenta no tiene permisos de administrador.", "error")
            return redirect(url_for("inicio"))
        return vista(*args, **kwargs)
    return vista_protegida


# ============================================================
# FUNCIONES DE VALIDACIÓN (revisan los formularios)
# ============================================================

def errores_de_paquete(datos):
    """Devuelve una lista con los errores del formulario de paquete (vacía si todo está bien)."""
    errores = []
    if not datos.get("nombre", "").strip():
        errores.append("El nombre del paquete es obligatorio.")
    if not datos.get("moneda_id"):
        errores.append("Selecciona una moneda.")
    try:
        if int(datos.get("cantidad_monedas", 0)) <= 0:
            errores.append("La cantidad de monedas debe ser mayor a 0.")
    except ValueError:
        errores.append("La cantidad de monedas debe ser un número.")
    try:
        if float(datos.get("precio_cop", 0)) <= 0:
            errores.append("El precio debe ser mayor a 0.")
    except ValueError:
        errores.append("El precio debe ser un número.")
    try:
        if int(datos.get("stock", "")) < 0:
            errores.append("El stock no puede ser negativo.")
    except ValueError:
        errores.append("El stock debe ser un número entero.")
    return errores


def errores_de_promocion(datos):
    """Devuelve una lista con los errores del formulario de promoción."""
    errores = []
    if not datos.get("titulo", "").strip():
        errores.append("El título de la promoción es obligatorio.")
    if not datos.get("paquete_id"):
        errores.append("Selecciona un paquete.")
    try:
        porcentaje = float(datos.get("porcentaje_descuento", 0))
        if porcentaje <= 0 or porcentaje > 90:
            errores.append("El porcentaje de descuento debe estar entre 1 y 90.")
    except ValueError:
        errores.append("El porcentaje de descuento debe ser un número.")
    if not datos.get("fecha_inicio") or not datos.get("fecha_fin"):
        errores.append("Las fechas de inicio y fin son obligatorias.")
    elif datos.get("fecha_fin") < datos.get("fecha_inicio"):
        errores.append("La fecha de fin no puede ser anterior a la fecha de inicio.")
    return errores


def fechas_del_filtro():
    """
    Lee ?desde=2026-10-01&hasta=2026-10-10 de la dirección (el buscador por fecha).
    Devuelve (desde, hasta); si una fecha está vacía o mal escrita devuelve None en su lugar.
    """
    fechas = []
    for campo in ["desde", "hasta"]:
        texto = request.args.get(campo, "").strip()
        try:
            datetime.strptime(texto, "%Y-%m-%d")     # comprueba que sea una fecha válida
            fechas.append(texto)
        except ValueError:
            fechas.append(None)
    return fechas[0], fechas[1]


def anotar(accion, entidad, entidad_id, detalle):
    """Atajo para guardar en la auditoría lo que hizo el administrador que tiene la sesión abierta."""
    db.registrar_auditoria(session["usuario_id"], accion, entidad, entidad_id, detalle)


# ============================================================
# DASHBOARD (estadísticas)
# ============================================================

@admin_bp.route("/")
@admin_requerido
def dashboard():
    return render_template("admin/dashboard.html", stats=db.obtener_estadisticas())


# ============================================================
# JUEGOS
# ============================================================

@admin_bp.route("/juegos")
@admin_requerido
def juegos():
    return render_template("admin/juegos.html", juegos=db.obtener_juegos_admin())


@admin_bp.route("/juegos/nuevo", methods=["GET", "POST"])
@admin_requerido
def juego_nuevo():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        nombre_moneda = request.form.get("nombre_moneda", "").strip()
        archivo_logo = request.files.get("logo")
        archivo_icono = request.files.get("icono_moneda")

        if not nombre or not nombre_moneda:
            flash("El nombre del juego y el nombre de la moneda son obligatorios.", "error")
            return render_template("admin/juego_form.html", juego=None, moneda=None, valores=request.form)

        error = imagenes.error_de_imagen(archivo_logo) or imagenes.error_de_imagen(archivo_icono)
        if error:
            flash(error, "error")
            return render_template("admin/juego_form.html", juego=None, moneda=None, valores=request.form)

        logo = imagenes.guardar_imagen(archivo_logo, "juegos")
        icono = imagenes.guardar_imagen(archivo_icono, "monedas")
        juego_id = db.crear_juego_con_moneda(nombre, descripcion, nombre_moneda, session["usuario_id"], logo, icono)
        anotar("CREAR", "juego", juego_id, f"Creó el juego '{nombre}'")
        flash(f"El juego '{nombre}' se creó correctamente.", "exito")
        return redirect(url_for("admin.juegos"))

    return render_template("admin/juego_form.html", juego=None, moneda=None, valores={})


@admin_bp.route("/juegos/<int:juego_id>/editar", methods=["GET", "POST"])
@admin_requerido
def juego_editar(juego_id):
    juego = db.obtener_juego_por_id_admin(juego_id)
    if not juego:
        return render_template("404.html"), 404

    moneda = db.obtener_moneda_de_juego(juego_id)

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        archivo_logo = request.files.get("logo")
        archivo_icono = request.files.get("icono_moneda")

        if not nombre:
            flash("El nombre del juego es obligatorio.", "error")
            return render_template("admin/juego_form.html", juego=juego, moneda=moneda, valores=request.form)

        error = imagenes.error_de_imagen(archivo_logo) or imagenes.error_de_imagen(archivo_icono)
        if error:
            flash(error, "error")
            return render_template("admin/juego_form.html", juego=juego, moneda=moneda, valores=request.form)

        logo = imagenes.guardar_imagen(archivo_logo, "juegos")
        icono = imagenes.guardar_imagen(archivo_icono, "monedas")
        db.actualizar_juego(juego_id, nombre, descripcion, logo, icono)

        # Si se subió una imagen nueva, borramos la vieja
        if logo:
            imagenes.borrar_imagen(juego["imagen_url"])
        if icono and moneda:
            imagenes.borrar_imagen(moneda["imagen_url"])

        anotar("EDITAR", "juego", juego_id, f"Editó el juego '{nombre}'")
        flash("Juego actualizado correctamente.", "exito")
        return redirect(url_for("admin.juegos"))

    return render_template("admin/juego_form.html", juego=juego, moneda=moneda, valores=juego)


@admin_bp.route("/juegos/<int:juego_id>/estado", methods=["POST"])
@admin_requerido
def juego_estado(juego_id):
    activar = request.form.get("estado") == "activar"
    db.cambiar_estado_juego(juego_id, activar)
    anotar("EDITAR", "juego", juego_id, "Se activó el juego" if activar else "Se desactivó el juego")
    flash("Estado del juego actualizado.", "exito")
    return redirect(url_for("admin.juegos"))


# ============================================================
# PAQUETES
# ============================================================

@admin_bp.route("/paquetes")
@admin_requerido
def paquetes():
    return render_template("admin/paquetes.html", paquetes=db.obtener_paquetes_admin())


@admin_bp.route("/paquetes/nuevo", methods=["GET", "POST"])
@admin_requerido
def paquete_nuevo():
    monedas = db.obtener_monedas_todas()

    if request.method == "POST":
        archivo = request.files.get("imagen")
        errores = errores_de_paquete(request.form)
        if imagenes.error_de_imagen(archivo):
            errores.append(imagenes.error_de_imagen(archivo))

        if errores:
            for error in errores:
                flash(error, "error")
            return render_template("admin/paquete_form.html", paquete=None, monedas=monedas, valores=request.form)

        imagen = imagenes.guardar_imagen(archivo, "paquetes")
        nombre = request.form["nombre"].strip()
        paquete_id = db.crear_paquete(
            int(request.form["moneda_id"]), session["usuario_id"], nombre,
            request.form.get("descripcion", "").strip(),
            int(request.form["cantidad_monedas"]), float(request.form["precio_cop"]),
            int(request.form["stock"]), imagen)
        anotar("CREAR", "paquete", paquete_id, f"Creó el paquete '{request.form['nombre']}'")
        flash("Paquete creado correctamente.", "exito")
        return redirect(url_for("admin.paquetes"))

    return render_template("admin/paquete_form.html", paquete=None, monedas=monedas, valores={})


@admin_bp.route("/paquetes/<int:paquete_id>/editar", methods=["GET", "POST"])
@admin_requerido
def paquete_editar(paquete_id):
    paquete = db.obtener_paquete_por_id_admin(paquete_id)
    if not paquete:
        return render_template("404.html"), 404

    monedas = db.obtener_monedas_todas()

    if request.method == "POST":
        archivo = request.files.get("imagen")
        errores = errores_de_paquete(request.form)
        if imagenes.error_de_imagen(archivo):
            errores.append(imagenes.error_de_imagen(archivo))

        if errores:
            for error in errores:
                flash(error, "error")
            return render_template("admin/paquete_form.html", paquete=paquete, monedas=monedas, valores=request.form)

        imagen = imagenes.guardar_imagen(archivo, "paquetes")
        db.actualizar_paquete(
            paquete_id, int(request.form["moneda_id"]), request.form["nombre"].strip(),
            request.form.get("descripcion", "").strip(),
            int(request.form["cantidad_monedas"]), float(request.form["precio_cop"]),
            int(request.form["stock"]), imagen)
        if imagen:
            imagenes.borrar_imagen(paquete["imagen_url"])

        anotar("EDITAR", "paquete", paquete_id, f"Editó el paquete '{request.form['nombre']}'")
        flash("Paquete actualizado correctamente.", "exito")
        return redirect(url_for("admin.paquetes"))

    return render_template("admin/paquete_form.html", paquete=paquete, monedas=monedas, valores=paquete)


@admin_bp.route("/paquetes/<int:paquete_id>/rellenar", methods=["POST"])
@admin_requerido
def paquete_rellenar(paquete_id):
    """Botón «Rellenar» de la tabla: suma unidades al stock del paquete."""
    paquete = db.obtener_paquete_por_id_admin(paquete_id)
    if not paquete:
        return render_template("404.html"), 404

    try:
        cantidad = int(request.form.get("cantidad", ""))
    except ValueError:
        cantidad = 0
    if cantidad <= 0 or cantidad > 100000:
        flash("Escribe cuántas unidades quieres agregar (un número mayor a 0).", "error")
        return redirect(url_for("admin.paquetes"))

    db.rellenar_stock(paquete_id, cantidad)
    anotar("EDITAR", "paquete", paquete_id,
           f"Rellenó +{cantidad} unidades de '{paquete['nombre']}' (stock: {paquete['stock'] + cantidad})")
    flash(f"Se agregaron {cantidad} unidades a {paquete['nombre']}. Stock actual: {paquete['stock'] + cantidad}.", "exito")
    return redirect(url_for("admin.paquetes"))


@admin_bp.route("/paquetes/<int:paquete_id>/estado", methods=["POST"])
@admin_requerido
def paquete_estado(paquete_id):
    activar = request.form.get("estado") == "activar"
    db.cambiar_estado_paquete(paquete_id, activar)
    anotar("EDITAR", "paquete", paquete_id, "Se activó el paquete" if activar else "Se desactivó el paquete")
    flash("Paquete activado." if activar else "Paquete desactivado: los usuarios ya no lo ven.", "exito")
    return redirect(url_for("admin.paquetes"))


@admin_bp.route("/paquetes/<int:paquete_id>/eliminar", methods=["POST"])
@admin_requerido
def paquete_eliminar(paquete_id):
    paquete = db.obtener_paquete_por_id_admin(paquete_id)
    if not paquete:
        return render_template("404.html"), 404

    # Si ya hay compras con este paquete, borrarlo dañaría el historial
    if db.paquete_tiene_compras(paquete_id):
        flash("Este paquete ya tiene compras, no se puede eliminar. Usa Desactivar para ocultarlo.", "error")
        return redirect(url_for("admin.paquetes"))

    db.eliminar_paquete(paquete_id)
    imagenes.borrar_imagen(paquete["imagen_url"])
    anotar("ELIMINAR", "paquete", paquete_id, f"Eliminó el paquete '{paquete['nombre']}'")
    flash("Paquete eliminado.", "exito")
    return redirect(url_for("admin.paquetes"))


# ============================================================
# PROMOCIONES
# ============================================================

@admin_bp.route("/promociones")
@admin_requerido
def promociones():
    return render_template("admin/promociones.html", promociones=db.obtener_promociones_admin())


@admin_bp.route("/promociones/nueva", methods=["GET", "POST"])
@admin_requerido
def promocion_nueva():
    paquetes = db.obtener_paquetes_admin()

    if request.method == "POST":
        errores = errores_de_promocion(request.form)
        if errores:
            for error in errores:
                flash(error, "error")
            return render_template("admin/promocion_form.html", promocion=None, paquetes=paquetes, valores=request.form)

        promocion_id = db.crear_promocion(
            int(request.form["paquete_id"]), session["usuario_id"],
            request.form["titulo"].strip(), request.form.get("descripcion", "").strip(),
            float(request.form["porcentaje_descuento"]),
            request.form["fecha_inicio"], request.form["fecha_fin"])
        anotar("CREAR", "promocion", promocion_id, f"Creó la promoción '{request.form['titulo']}'")
        flash("Promoción creada correctamente.", "exito")
        return redirect(url_for("admin.promociones"))

    return render_template("admin/promocion_form.html", promocion=None, paquetes=paquetes, valores={})


@admin_bp.route("/promociones/<int:promocion_id>/editar", methods=["GET", "POST"])
@admin_requerido
def promocion_editar(promocion_id):
    promocion = db.obtener_promocion_por_id(promocion_id)
    if not promocion:
        return render_template("404.html"), 404

    paquetes = db.obtener_paquetes_admin()

    if request.method == "POST":
        errores = errores_de_promocion(request.form)
        if errores:
            for error in errores:
                flash(error, "error")
            return render_template("admin/promocion_form.html", promocion=promocion, paquetes=paquetes, valores=request.form)

        db.actualizar_promocion(
            promocion_id, request.form["titulo"].strip(), request.form.get("descripcion", "").strip(),
            float(request.form["porcentaje_descuento"]),
            request.form["fecha_inicio"], request.form["fecha_fin"])
        anotar("EDITAR", "promocion", promocion_id, f"Editó la promoción '{request.form['titulo']}'")
        flash("Promoción actualizada correctamente.", "exito")
        return redirect(url_for("admin.promociones"))

    return render_template("admin/promocion_form.html", promocion=promocion, paquetes=paquetes, valores=promocion)


@admin_bp.route("/promociones/<int:promocion_id>/estado", methods=["POST"])
@admin_requerido
def promocion_estado(promocion_id):
    activar = request.form.get("estado") == "activar"
    db.cambiar_estado_promocion(promocion_id, activar)
    anotar("EDITAR", "promocion", promocion_id, "Se activó la promoción" if activar else "Se desactivó la promoción")
    flash("Promoción activada." if activar else "Promoción desactivada: los usuarios ya no la ven.", "exito")
    return redirect(url_for("admin.promociones"))


@admin_bp.route("/promociones/<int:promocion_id>/eliminar", methods=["POST"])
@admin_requerido
def promocion_eliminar(promocion_id):
    db.eliminar_promocion(promocion_id)
    anotar("ELIMINAR", "promocion", promocion_id, "Eliminó una promoción")
    flash("Promoción eliminada.", "exito")
    return redirect(url_for("admin.promociones"))


# ============================================================
# VENTAS (las compras que hacen los clientes, vistas por el administrador)
# ============================================================

@admin_bp.route("/ventas")
@admin_requerido
def ventas():
    desde, hasta = fechas_del_filtro()
    lista = db.obtener_todas_las_compras(desde, hasta)

    # Total de dinero de las ventas que se ven en la tabla (respeta el filtro de fechas):
    #   ENTREGADO -> se suma    CANCELADO y PROCESADO -> no cuentan (solo se muestran aparte)
    entregado = sum(v["total_cop"] for v in lista if v["estado_pedido"] == "ENTREGADO")
    cancelado = sum(v["total_cop"] for v in lista if v["estado_pedido"] == "CANCELADO")
    procesado = sum(v["total_cop"] for v in lista if v["estado_pedido"] == "PROCESADO")
    totales = {
        "entregado": entregado, "cancelado": cancelado, "procesado": procesado,
        "total": entregado,
        "n_entregado": sum(1 for v in lista if v["estado_pedido"] == "ENTREGADO"),
        "n_cancelado": sum(1 for v in lista if v["estado_pedido"] == "CANCELADO"),
        "n_procesado": sum(1 for v in lista if v["estado_pedido"] == "PROCESADO"),
    }
    return render_template("admin/ventas.html", ventas=lista, desde=desde, hasta=hasta, totales=totales)


@admin_bp.route("/ventas/<int:compra_id>")
@admin_requerido
def venta_detalle(compra_id):
    compra = db.obtener_compra_por_id_admin(compra_id)
    if not compra:
        return render_template("404.html"), 404

    items = db.obtener_detalle_compra(compra_id)
    return render_template("admin/venta_detalle.html", compra=compra, items=items)


@admin_bp.route("/ventas/<int:compra_id>/estado", methods=["POST"])
@admin_requerido
def venta_estado(compra_id):
    nuevo_estado = request.form.get("estado_pedido")
    compra = db.obtener_compra_por_id_admin(compra_id)
    if not compra:
        return render_template("404.html"), 404

    if nuevo_estado in ["PROCESADO", "ENTREGADO", "CANCELADO"]:
        estado_anterior = compra["estado_pedido"]
        items_pedido = db.obtener_detalle_compra(compra_id)

        # Si se cancela, las unidades vuelven al stock. Si se "des-cancela", se descuentan otra vez
        # (y si ya no alcanzan, no dejamos hacer el cambio).
        if nuevo_estado == "CANCELADO" and estado_anterior != "CANCELADO":
            for item in items_pedido:
                db.devolver_stock(item["paquete_id"], item["cantidad"])
        elif estado_anterior == "CANCELADO" and nuevo_estado != "CANCELADO":
            descontados = []
            for item in items_pedido:
                if db.descontar_stock(item["paquete_id"], item["cantidad"]):
                    descontados.append(item)
                else:
                    for hecho in descontados:
                        db.devolver_stock(hecho["paquete_id"], hecho["cantidad"])
                    flash(f"No se puede reactivar: ya no hay stock suficiente de {item['paquete_nombre']}.", "error")
                    return redirect(url_for("admin.venta_detalle", compra_id=compra_id))

        db.actualizar_estado_pedido(compra_id, nuevo_estado)
        anotar("EDITAR", "compra", compra_id, f"Cambió el estado de la venta a {nuevo_estado}")

        # El cliente recibe el correo SOLO cuando el estado cambia a ENTREGADO o CANCELADO
        # (si el admin guarda otra vez el mismo estado, no se manda el correo repetido).
        if nuevo_estado in ["ENTREGADO", "CANCELADO"] and nuevo_estado != estado_anterior:
            if not servicio_correo.correo_configurado():
                flash("Estado actualizado, pero no se envió el correo: falta configurar el correo en config.py.", "error")
            elif avisar_estado_por_correo(compra_id, compra["usuario_id"], nuevo_estado):
                flash(f"Estado actualizado. Le enviamos el correo a {compra['usuario_correo']}.", "exito")
            else:
                flash("Estado actualizado, pero no se pudo enviar el correo.", "error")
        else:
            flash("Estado del pedido actualizado.", "exito")
    return redirect(url_for("admin.venta_detalle", compra_id=compra_id))


# ============================================================
# USUARIOS
# ============================================================

@admin_bp.route("/usuarios")
@admin_requerido
def usuarios():
    desde, hasta = fechas_del_filtro()
    lista = db.obtener_usuarios_admin(desde, hasta)
    return render_template("admin/usuarios.html", usuarios=lista, desde=desde, hasta=hasta)


@admin_bp.route("/usuarios/<int:usuario_id>/estado", methods=["POST"])
@admin_requerido
def usuario_estado(usuario_id):
    # 'A' = activo, 'I' = inactivo
    nuevo_estado = "A" if request.form.get("estado") == "activar" else "I"
    db.cambiar_estado_usuario(usuario_id, nuevo_estado)
    anotar("EDITAR", "usuario", usuario_id, f"Cambió el estado del usuario a {nuevo_estado}")
    flash("Estado del usuario actualizado.", "exito")
    return redirect(url_for("admin.usuarios"))


# ============================================================
# COMENTARIOS
# ============================================================

@admin_bp.route("/comentarios")
@admin_requerido
def comentarios():
    desde, hasta = fechas_del_filtro()
    lista = db.obtener_comentarios_admin(desde, hasta)
    return render_template("admin/comentarios.html", comentarios=lista, desde=desde, hasta=hasta)


@admin_bp.route("/comentarios/<int:comentario_id>/responder", methods=["POST"])
@admin_requerido
def comentario_responder(comentario_id):
    respuesta = request.form.get("respuesta", "").strip()

    if not respuesta:
        flash("Escribe una respuesta antes de enviarla.", "error")
    elif len(respuesta) > 500:
        flash("La respuesta puede tener máximo 500 caracteres.", "error")
    else:
        db.responder_comentario(comentario_id, session["usuario_id"], respuesta)
        anotar("EDITAR", "comentario", comentario_id, "Respondió un comentario")
        flash("Respuesta publicada.", "exito")
    return redirect(url_for("admin.comentarios"))


@admin_bp.route("/comentarios/<int:comentario_id>/eliminar", methods=["POST"])
@admin_requerido
def comentario_eliminar(comentario_id):
    db.eliminar_comentario(comentario_id)
    anotar("ELIMINAR", "comentario", comentario_id, "Eliminó un comentario")
    flash("Comentario eliminado.", "exito")
    return redirect(url_for("admin.comentarios"))


# ============================================================
# AUDITORÍA
# ============================================================

@admin_bp.route("/auditoria")
@admin_requerido
def auditoria():
    desde, hasta = fechas_del_filtro()
    lista = db.obtener_auditoria(desde, hasta)
    return render_template("admin/auditoria.html", registros=lista, desde=desde, hasta=hasta)
