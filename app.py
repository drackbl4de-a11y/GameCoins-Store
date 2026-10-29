"""
app.py
------
Archivo principal del sitio para los usuarios. Aquí están las RUTAS:
cada @app.route("/algo") es una dirección de la página, y la función
que tiene debajo decide qué se muestra.

Las rutas del administrador están en admin.py.
Todo lo que habla con la base de datos está en db.py.

Para ejecutarlo:   python app.py
Y abrir en el navegador:  http://127.0.0.1:5000
"""

import re
import secrets
import time
from datetime import datetime
from urllib.parse import quote

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

import db
import imagenes
import asistente as asistente_bot
from config import (SECRET_KEY, WHATSAPP_NUMERO, WHATSAPP_NUMERO_VISIBLE, WHATSAPP_MENSAJE,
                    WHATSAPP_CANAL_URL, INSTAGRAM_URL)
from admin import admin_bp
from servicio_pedido import crear_pdf_certificado, avisar_estado_por_correo
import correo as servicio_correo
from fechas import hace_cuanto, mes_y_anio

app = Flask(__name__)
app.secret_key = SECRET_KEY                      # necesaria para usar session (el login)
app.register_blueprint(admin_bp)                 # agrega las rutas /admin/...
app.add_template_filter(hace_cuanto, "hace")     # permite escribir {{ fecha|hace }} en los HTML
app.add_template_filter(mes_y_anio, "mes_anio")  # {{ fecha|mes_anio }} -> octubre 2026
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024   # las imágenes subidas pesan máximo 5 MB

# ============================================================
# 1. DATOS QUE VEN TODAS LAS PÁGINAS Y PÁGINA 404
# ============================================================

@app.context_processor
def datos_para_todas_las_paginas():
    """Lo que devuelve esta función se puede usar en cualquier HTML (base.html)."""
    cantidad = 0
    if session.get("usuario_id"):
        cantidad = db.contar_items_carrito(session["usuario_id"])   # numerito del carrito

    return {
        "carrito_cantidad": cantidad,
        "whatsapp_url": f"https://wa.me/{WHATSAPP_NUMERO}?text={quote(WHATSAPP_MENSAJE)}",
        "whatsapp_numero": WHATSAPP_NUMERO_VISIBLE,
        "canal_url": WHATSAPP_CANAL_URL,
        "instagram_url": INSTAGRAM_URL,
    }


@app.errorhandler(404)
def pagina_no_encontrada(error):
    """Se muestra cuando alguien entra a una dirección que no existe."""
    return render_template("404.html"), 404


# ============================================================
# 2. CATÁLOGO: inicio, juegos, promociones, búsqueda
# ============================================================

@app.route("/")
def inicio():
    juegos = db.obtener_juegos_activos()
    promociones = db.obtener_promociones_activas()
    return render_template("index.html", juegos=juegos, promociones=promociones)


@app.route("/juegos")
def juegos():
    return render_template("juegos.html", juegos=db.obtener_juegos_activos())


@app.route("/promociones")
def promociones():
    return render_template("promociones.html", promociones=db.obtener_promociones_activas())


@app.route("/juegos/<int:juego_id>")
def catalogo(juego_id):
    """Paquetes de un juego. <int:juego_id> es el número que viene en la dirección."""
    juego = db.obtener_juego_por_id(juego_id)
    if not juego:
        return render_template("404.html"), 404

    paquetes = db.obtener_paquetes_por_juego(juego_id)
    return render_template("catalogo.html", juego=juego, paquetes=paquetes)


@app.route("/buscar")
def buscar():
    texto = request.args.get("q", "").strip()
    paquetes = db.buscar_paquetes(texto) if texto else []
    return render_template("resultados_busqueda.html", texto=texto, paquetes=paquetes)


# ============================================================
# 3. REGISTRO, LOGIN Y LOGOUT
# ============================================================

@app.route("/registro", methods=["GET", "POST"])
def registro():
    # GET = la persona solo abrió la página. POST = envió el formulario.
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")
        confirmar = request.form.get("confirmar_contrasena", "")

        # Validaciones: si algo falla, mostramos un mensaje y volvemos al formulario
        if not nombre or not apellido or not correo or not contrasena:
            flash("Todos los campos son obligatorios.", "error")
            return render_template("register.html")

        if contrasena != confirmar:
            flash("Las contraseñas no coinciden.", "error")
            return render_template("register.html")

        if len(contrasena) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
            return render_template("register.html")

        # El correo debe tener forma de correo: algo@dominio.com
        if not re.fullmatch(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", correo):
            flash("Escribe un correo válido, por ejemplo nombre@gmail.com.", "error")
            return render_template("register.html")

        if db.obtener_usuario_por_correo(correo):
            flash("Ya existe una cuenta registrada con ese correo.", "error")
            return render_template("register.html")

        # La contraseña NUNCA se guarda tal cual: se guarda su "hash" (cifrada)
        contrasena_hash = generate_password_hash(contrasena)

        # Si el envío de correos está configurado, pedimos confirmar que el correo es real:
        # enviamos un código de 6 números y la cuenta se crea cuando la persona lo escribe.
        if servicio_correo.correo_configurado():
            codigo = "{:06d}".format(secrets.randbelow(1000000))
            if not servicio_correo.enviar_codigo_verificacion(correo, nombre, codigo):
                flash("No pudimos enviar el código. Revisa que el correo esté bien escrito e intenta de nuevo.", "error")
                return render_template("register.html")

            # Guardamos los datos en la sesión mientras tanto (el código va cifrado, no en texto)
            session["registro_pendiente"] = {
                "nombre": nombre, "apellido": apellido, "correo": correo,
                "contrasena_hash": contrasena_hash,
                "codigo_hash": generate_password_hash(codigo),
                "vence": time.time() + 600,   # 10 minutos
                "intentos": 0,
            }
            return redirect(url_for("verificar_correo"))

        # Sin envío de correos configurado: la cuenta se crea directamente
        db.crear_usuario(nombre, apellido, correo, contrasena_hash)
        flash("Te has registrado con éxito. Ya puedes iniciar sesión.", "exito")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/verificar-correo", methods=["GET", "POST"])
def verificar_correo():
    """Segundo paso del registro: la persona escribe el código que le llegó al correo."""
    pendiente = session.get("registro_pendiente")
    if not pendiente:
        return redirect(url_for("registro"))

    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip()

        if time.time() > pendiente["vence"]:
            session.pop("registro_pendiente")
            flash("El código venció. Regístrate de nuevo para recibir uno nuevo.", "error")
            return redirect(url_for("registro"))

        if not check_password_hash(pendiente["codigo_hash"], codigo):
            pendiente["intentos"] += 1
            session["registro_pendiente"] = pendiente     # guardamos el nuevo número de intentos
            if pendiente["intentos"] >= 5:
                session.pop("registro_pendiente")
                flash("Demasiados intentos. Regístrate de nuevo.", "error")
                return redirect(url_for("registro"))
            flash("Ese código no es correcto.", "error")
            return render_template("verificar_correo.html", correo=pendiente["correo"])

        # Código correcto: ahora sí se crea la cuenta, con el correo marcado como verificado
        if not db.obtener_usuario_por_correo(pendiente["correo"]):
            db.crear_usuario(pendiente["nombre"], pendiente["apellido"], pendiente["correo"],
                             pendiente["contrasena_hash"], verificado=True)
        session.pop("registro_pendiente")
        flash("¡Correo verificado! Tu cuenta está lista, ya puedes iniciar sesión.", "exito")
        return redirect(url_for("login"))

    return render_template("verificar_correo.html", correo=pendiente["correo"])


@app.route("/verificar-correo/reenviar", methods=["POST"])
def reenviar_codigo():
    pendiente = session.get("registro_pendiente")
    if not pendiente:
        return redirect(url_for("registro"))

    codigo = "{:06d}".format(secrets.randbelow(1000000))
    if servicio_correo.enviar_codigo_verificacion(pendiente["correo"], pendiente["nombre"], codigo):
        pendiente["codigo_hash"] = generate_password_hash(codigo)
        pendiente["vence"] = time.time() + 600
        pendiente["intentos"] = 0
        session["registro_pendiente"] = pendiente
        flash("Te enviamos un código nuevo.", "exito")
    else:
        flash("No pudimos enviar el código. Intenta de nuevo en un momento.", "error")
    return redirect(url_for("verificar_correo"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")

        if not correo or not contrasena:
            flash("Ingresa tu correo y tu contraseña.", "error")
            return render_template("login.html")

        usuario = db.obtener_usuario_por_correo(correo)

        # No decimos cuál de los dos falló (correo o contraseña): es más seguro
        if not usuario or not check_password_hash(usuario["contrasena_hash"], contrasena):
            flash("Correo o contraseña incorrectos.", "error")
            return render_template("login.html")

        # La sesión recuerda quién es el usuario mientras navega.
        # El "rol" decide si puede entrar al panel /admin.
        session["usuario_id"] = usuario["usuario_id"]
        session["usuario_nombre"] = usuario["nombre"]
        session["rol"] = usuario["rol"]
        session["foto"] = usuario["foto_perfil_url"]     # para el botón de perfil del encabezado

        db.actualizar_ultimo_login(usuario["usuario_id"])
        return redirect(url_for("inicio"))

    return render_template("login.html")


# ------------------------------------------------------------
# Olvidé mi contraseña: 1) pide el correo  2) escribe el código y la contraseña nueva
# Igual que en el registro, el código viaja cifrado en la sesión y vence en 10 minutos.
# ------------------------------------------------------------

@app.route("/recuperar", methods=["GET", "POST"])
def recuperar_contrasena():
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()

        if not servicio_correo.correo_configurado():
            flash("El envío de correos no está configurado todavía. Escríbenos por WhatsApp.", "error")
            return render_template("recuperar.html")

        if not re.fullmatch(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", correo):
            flash("Escribe un correo válido, por ejemplo nombre@gmail.com.", "error")
            return render_template("recuperar.html")

        usuario = db.obtener_usuario_por_correo(correo)
        if usuario:
            codigo = "{:06d}".format(secrets.randbelow(1000000))
            if not servicio_correo.enviar_codigo_recuperacion(correo, usuario["nombre"], codigo):
                flash("No pudimos enviar el código. Intenta de nuevo en un momento.", "error")
                return render_template("recuperar.html")
            session["recuperacion"] = {
                "usuario_id": usuario["usuario_id"], "correo": correo,
                "codigo_hash": generate_password_hash(codigo),
                "vence": time.time() + 600, "intentos": 0,
            }
        else:
            # Si el correo no existe no lo decimos (así nadie descubre qué correos tienen cuenta).
            # Guardamos un código imposible para que la pantalla siguiente se vea igual.
            session["recuperacion"] = {
                "usuario_id": None, "correo": correo,
                "codigo_hash": generate_password_hash(secrets.token_hex(8)),
                "vence": time.time() + 600, "intentos": 0,
            }
        return redirect(url_for("recuperar_codigo"))

    return render_template("recuperar.html")


@app.route("/recuperar/codigo", methods=["GET", "POST"])
def recuperar_codigo():
    pendiente = session.get("recuperacion")
    if not pendiente:
        return redirect(url_for("recuperar_contrasena"))

    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip()
        nueva = request.form.get("contrasena", "")
        confirmar = request.form.get("confirmar_contrasena", "")

        if time.time() > pendiente["vence"]:
            session.pop("recuperacion")
            flash("El código venció. Pide uno nuevo.", "error")
            return redirect(url_for("recuperar_contrasena"))

        if len(nueva) < 6:
            flash("La contraseña nueva debe tener al menos 6 caracteres.", "error")
            return render_template("recuperar_codigo.html", correo=pendiente["correo"])

        if nueva != confirmar:
            flash("Las contraseñas no coinciden.", "error")
            return render_template("recuperar_codigo.html", correo=pendiente["correo"])

        if not check_password_hash(pendiente["codigo_hash"], codigo):
            pendiente["intentos"] += 1
            session["recuperacion"] = pendiente
            if pendiente["intentos"] >= 5:
                session.pop("recuperacion")
                flash("Demasiados intentos. Pide un código nuevo.", "error")
                return redirect(url_for("recuperar_contrasena"))
            flash("Ese código no es correcto.", "error")
            return render_template("recuperar_codigo.html", correo=pendiente["correo"])

        # Código correcto: guardamos la contraseña nueva (siempre como hash)
        db.actualizar_contrasena(pendiente["usuario_id"], generate_password_hash(nueva))
        session.pop("recuperacion")
        flash("¡Contraseña cambiada! Ya puedes iniciar sesión con la nueva.", "exito")
        return redirect(url_for("login"))

    return render_template("recuperar_codigo.html", correo=pendiente["correo"])


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("inicio"))


# ============================================================
# 4. CARRITO DE COMPRAS
# ============================================================

@app.route("/carrito/agregar/<int:paquete_id>", methods=["POST"])
def agregar_al_carrito(paquete_id):
    if not session.get("usuario_id"):
        flash("Debes iniciar sesión para agregar productos al carrito.", "error")
        return redirect(url_for("login"))

    paquete = db.obtener_paquete_con_precio(paquete_id)
    if not paquete:
        flash("Ese paquete ya no está disponible.", "error")
        return redirect(request.referrer or url_for("inicio"))

    if paquete["stock"] <= 0:
        flash(f"{paquete['nombre']} está agotado por ahora.", "error")
        return redirect(request.referrer or url_for("inicio"))

    carrito_id = db.obtener_o_crear_carrito_activo(session["usuario_id"])
    if db.agregar_item_carrito(carrito_id, paquete_id, paquete["precio_final"]):
        flash(f"{paquete['nombre']} se agregó al carrito.", "exito")
    else:
        flash(f"Solo quedan {paquete['stock']} unidades de {paquete['nombre']} y ya las tienes en tu carrito.", "error")
    return redirect(request.referrer or url_for("inicio"))


@app.route("/carrito")
def ver_carrito():
    if not session.get("usuario_id"):
        flash("Debes iniciar sesión para ver tu carrito.", "error")
        return redirect(url_for("login"))

    carrito_id = db.obtener_o_crear_carrito_activo(session["usuario_id"])
    items = db.obtener_items_carrito(carrito_id)
    total = sum(item["subtotal"] for item in items)
    return render_template("carrito.html", items=items, total=total)


@app.route("/carrito/actualizar/<int:detalle_id>", methods=["POST"])
def actualizar_carrito(detalle_id):
    if not session.get("usuario_id"):
        return redirect(url_for("login"))

    # Los botones + y - del carrito mandan "sumar" o "restar"
    cambio = 1 if request.form.get("accion") == "sumar" else -1
    if not db.actualizar_cantidad_item(detalle_id, session["usuario_id"], cambio):
        flash("No hay más unidades disponibles de ese paquete.", "error")
    return redirect(url_for("ver_carrito"))


@app.route("/carrito/eliminar/<int:detalle_id>", methods=["POST"])
def eliminar_del_carrito(detalle_id):
    if not session.get("usuario_id"):
        return redirect(url_for("login"))

    db.eliminar_item_carrito(detalle_id, session["usuario_id"])
    flash("Producto eliminado del carrito.", "exito")
    return redirect(url_for("ver_carrito"))


# ============================================================
# 5. CHECKOUT (pago simulado con Nequi) Y PEDIDOS
# ============================================================

def validar_checkout(items, formulario):
    """
    Revisa el formulario de pago. Devuelve dos cosas:
      - errores: lista de mensajes (vacía si todo está bien)
      - datos_entrega: diccionario {id del item: usuario de Roblox o ID de VALORANT}
    """
    errores = []
    datos_entrega = {}

    nombre_titular = formulario.get("nombre_titular", "").strip()
    celular = formulario.get("numero_celular", "").strip().replace(" ", "")

    if not nombre_titular:
        errores.append("Falta el nombre de quien va a pagar.")

    # Celular colombiano: 10 dígitos y empieza por 3
    if not re.fullmatch(r"3\d{9}", celular):
        errores.append("El número de celular Nequi debe ser un celular colombiano válido (10 dígitos, empieza en 3).")

    # Cada paquete necesita su dato de entrega
    for item in items:
        valor = formulario.get(f"dato_entrega_{item['detalle_carrito_id']}", "").strip()
        paquete = item["paquete_nombre"]

        if not valor:
            if item["juego_nombre"] == "Roblox":
                errores.append(f"Falta tu usuario de Roblox para \"{paquete}\".")
            elif item["juego_nombre"] == "VALORANT":
                errores.append(f"Falta tu ID de jugador para \"{paquete}\".")
            else:
                errores.append(f"Falta el dato de entrega para \"{paquete}\".")
        elif item["juego_nombre"] == "VALORANT" and not re.fullmatch(r".+#\d{3,5}", valor):
            # El ID de VALORANT debe verse así: Usuario#1234
            errores.append(f"El ID de VALORANT para \"{paquete}\" debe tener el formato Usuario#TAG.")
        else:
            datos_entrega[item["detalle_carrito_id"]] = valor

    return errores, datos_entrega


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if not session.get("usuario_id"):
        flash("Debes iniciar sesión para continuar con la compra.", "error")
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]
    carrito_id = db.obtener_o_crear_carrito_activo(usuario_id)
    items = db.obtener_items_carrito(carrito_id)

    if not items:
        flash("Tu carrito está vacío.", "error")
        return redirect(url_for("ver_carrito"))

    total = sum(item["subtotal"] for item in items)

    # Antes de pagar, revisamos que todavía queden unidades de lo que hay en el carrito
    for item in items:
        if item["cantidad"] > item["stock_disponible"]:
            if item["stock_disponible"] <= 0:
                flash(f"{item['paquete_nombre']} se agotó. Quítalo del carrito para continuar.", "error")
            else:
                flash(f"De {item['paquete_nombre']} solo quedan {item['stock_disponible']} unidades. "
                      "Baja la cantidad en tu carrito.", "error")
            return redirect(url_for("ver_carrito"))

    if request.method == "POST":
        errores, datos_entrega = validar_checkout(items, request.form)

        if errores:
            for error in errores:
                flash(error, "error")
            return render_template("checkout.html", items=items, total=total, valores=request.form)

        # Descontamos el stock. Si alguien más compró la última unidad justo ahora,
        # devolvemos lo que ya habíamos descontado y avisamos.
        descontados = []
        for item in items:
            if db.descontar_stock(item["paquete_id"], item["cantidad"]):
                descontados.append(item)
            else:
                for hecho in descontados:
                    db.devolver_stock(hecho["paquete_id"], hecho["cantidad"])
                flash(f"{item['paquete_nombre']} se agotó mientras comprabas. Revisa tu carrito.", "error")
                return redirect(url_for("ver_carrito"))

        # Todo está bien: se crea el pedido
        codigo_pedido = "GCS-" + secrets.token_hex(4).upper()
        compra_id = db.crear_compra(usuario_id, total, codigo_pedido)

        for item in items:
            db.crear_detalle_compra(
                compra_id, item["paquete_id"], item["cantidad"], item["precio_unitario"],
                item["subtotal"], datos_entrega[item["detalle_carrito_id"]])

        # Pago simulado: solo guardamos los últimos 4 dígitos del celular
        nombre_titular = request.form.get("nombre_titular", "").strip()
        celular = request.form.get("numero_celular", "").strip().replace(" ", "")
        db.crear_datos_pago(compra_id, nombre_titular, "NEQUI", "*** *** " + celular[-4:], None)

        db.vaciar_carrito(carrito_id)

        # El correo NO se envía ahora: se envía cuando el administrador marque el pedido
        # como ENTREGADO o CANCELADO (ver admin.py).
        flash("¡Compra realizada exitosamente! Tu pedido está en estado PROCESADO. "
              "Te avisaremos por correo cuando sea entregado o cancelado.", "exito")
        return redirect(url_for("detalle_pedido", compra_id=compra_id))

    return render_template("checkout.html", items=items, total=total, valores={})


@app.route("/pedidos")
def pedidos():
    # Los pedidos ahora se ven en la pestaña "Pedidos" del perfil
    return redirect(url_for("perfil", tab="pedidos"))


@app.route("/pedidos/<int:compra_id>")
def detalle_pedido(compra_id):
    if not session.get("usuario_id"):
        flash("Debes iniciar sesión para ver tus pedidos.", "error")
        return redirect(url_for("login"))

    compra = db.obtener_compra_por_id(compra_id, session["usuario_id"])
    if not compra:
        return render_template("404.html"), 404

    items = db.obtener_detalle_compra(compra_id)
    return render_template("detalle_pedido.html", compra=compra, items=items)


@app.route("/pedidos/<int:compra_id>/certificado")
def descargar_certificado(compra_id):
    if not session.get("usuario_id"):
        flash("Debes iniciar sesión para descargar tu certificado.", "error")
        return redirect(url_for("login"))

    compra, items, usuario, pdf = crear_pdf_certificado(compra_id, session["usuario_id"])
    if not compra:
        return render_template("404.html"), 404

    # El certificado solo existe cuando el pedido ya fue entregado
    if compra["estado_pedido"] != "ENTREGADO":
        flash("El certificado estará disponible cuando tu pedido sea ENTREGADO.", "error")
        return redirect(url_for("detalle_pedido", compra_id=compra_id))

    return send_file(pdf, mimetype="application/pdf", as_attachment=True,
                     download_name=f"certificado_{compra['codigo_pedido']}.pdf")


@app.route("/pedidos/<int:compra_id>/enviar-certificado", methods=["POST"])
def enviar_certificado(compra_id):
    """Botón "Enviar a mi correo" del detalle del pedido (solo si ya fue ENTREGADO)."""
    if not session.get("usuario_id"):
        flash("Debes iniciar sesión.", "error")
        return redirect(url_for("login"))

    compra = db.obtener_compra_por_id(compra_id, session["usuario_id"])
    if not compra:
        return render_template("404.html"), 404

    if compra["estado_pedido"] != "ENTREGADO":
        flash("El certificado estará disponible cuando tu pedido sea ENTREGADO.", "error")
    elif not servicio_correo.correo_configurado():
        flash("El envío de correos todavía no está configurado en el servidor.", "error")
    elif avisar_estado_por_correo(compra_id, session["usuario_id"], "ENTREGADO"):
        flash("Te enviamos el certificado a tu correo.", "exito")
    else:
        flash("No pudimos enviar el correo. Intenta de nuevo en un momento.", "error")
    return redirect(url_for("detalle_pedido", compra_id=compra_id))


# ============================================================
# 6. COMENTARIOS
# ============================================================

@app.route("/comentarios", methods=["GET", "POST"])
def comentarios():
    if request.method == "POST":
        if not session.get("usuario_id"):
            flash("Debes iniciar sesión para dejar tu opinión.", "error")
            return redirect(url_for("login"))

        contenido = request.form.get("contenido", "").strip()
        calificacion = request.form.get("calificacion", "")

        if not contenido:
            flash("Escribe algo antes de publicar tu opinión.", "error")
        elif calificacion not in ["1", "2", "3", "4", "5"]:
            flash("Selecciona una calificación de 1 a 5 estrellas.", "error")
        else:
            db.crear_comentario(session["usuario_id"], contenido, int(calificacion))
            flash("¡Gracias por tu opinión!", "exito")
            return redirect(url_for("comentarios"))

    lista = db.obtener_comentarios_visibles()

    # Promedio de estrellas (si hay comentarios)
    promedio = None
    if lista:
        promedio = round(sum(c["calificacion"] for c in lista) / len(lista), 1)

    return render_template("comentarios.html", comentarios=lista, promedio=promedio)


# ============================================================
# 7. PERFIL DEL USUARIO
# ============================================================

@app.route("/perfil")
def perfil():
    if not session.get("usuario_id"):
        flash("Debes iniciar sesión para ver tu perfil.", "error")
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    # La página tiene 3 pestañas: perfil, pedidos y datos (se elige con ?tab=...)
    pestana = request.args.get("tab", "perfil")
    if pestana not in ["perfil", "pedidos", "datos"]:
        pestana = "perfil"

    usuario = db.obtener_usuario_por_id(usuario_id)
    resumen = db.obtener_resumen_perfil(usuario_id)
    favorito = db.obtener_paquete_favorito(usuario_id)

    # Los pedidos del usuario, cada uno con sus paquetes
    lista_pedidos = db.obtener_pedidos_usuario(usuario_id)
    for pedido in lista_pedidos:
        pedido["items"] = db.obtener_detalle_compra(pedido["compra_id"])

    # Días que han pasado desde su primera compra
    dias_desde_primera = 0
    if resumen["primera_compra"]:
        dias_desde_primera = (datetime.now().date() - resumen["primera_compra"].date()).days

    return render_template("perfil.html", pestana=pestana, usuario=usuario, resumen=resumen,
                           favorito=favorito, pedidos=lista_pedidos,
                           dias_desde_primera=dias_desde_primera)


@app.route("/perfil/datos", methods=["POST"])
def actualizar_datos_perfil():
    if not session.get("usuario_id"):
        return redirect(url_for("login"))

    nombre = request.form.get("nombre", "").strip()
    apellido = request.form.get("apellido", "").strip()
    telefono = request.form.get("telefono", "").strip()

    if not nombre or not apellido:
        flash("El nombre y el apellido son obligatorios.", "error")
        return redirect(url_for("perfil", tab="datos"))

    db.actualizar_datos_personales(session["usuario_id"], nombre, apellido, telefono)
    session["usuario_nombre"] = nombre
    flash("Tus datos se actualizaron correctamente.", "exito")
    return redirect(url_for("perfil", tab="datos"))


@app.route("/perfil/foto", methods=["POST"])
def actualizar_foto():
    if not session.get("usuario_id"):
        return redirect(url_for("login"))

    archivo = request.files.get("foto")
    if not archivo or archivo.filename == "":
        flash("Selecciona una imagen antes de subirla.", "error")
        return redirect(url_for("perfil", tab="datos"))

    if imagenes.extension_de(archivo) not in imagenes.EXTENSIONES_PERMITIDAS:
        flash("Formato de imagen no válido. Usa PNG, JPG, GIF o WEBP.", "error")
        return redirect(url_for("perfil", tab="datos"))

    # La foto se guarda como usuario_<id>.png (así cada usuario tiene una sola)
    ruta = imagenes.guardar_imagen(archivo, "perfiles", nombre=f"usuario_{session['usuario_id']}")
    db.actualizar_foto_perfil(session["usuario_id"], ruta)
    session["foto"] = ruta
    flash("Tu foto de perfil se actualizó.", "exito")
    return redirect(url_for("perfil", tab="datos"))


@app.route("/perfil/contrasena", methods=["POST"])
def cambiar_contrasena():
    if not session.get("usuario_id"):
        return redirect(url_for("login"))

    actual = request.form.get("contrasena_actual", "")
    nueva = request.form.get("nueva_contrasena", "")
    confirmar = request.form.get("confirmar_nueva_contrasena", "")

    usuario = db.obtener_usuario_por_id(session["usuario_id"])

    if not check_password_hash(usuario["contrasena_hash"], actual):
        flash("La contraseña actual no es correcta.", "error")
    elif len(nueva) < 6:
        flash("La nueva contraseña debe tener al menos 6 caracteres.", "error")
    elif nueva != confirmar:
        flash("Las contraseñas nuevas no coinciden.", "error")
    else:
        db.actualizar_contrasena(session["usuario_id"], generate_password_hash(nueva))
        flash("Tu contraseña se actualizó correctamente.", "exito")

    return redirect(url_for("perfil", tab="datos"))


# ============================================================
# 8. PÁGINAS DEL PIE DE PÁGINA (solo muestran su HTML)
# ============================================================

@app.route("/contacto")
def contacto():
    return render_template("contacto.html")


@app.route("/preguntas-frecuentes")
def faq():
    return render_template("faq.html")


@app.route("/politicas")
def politicas():
    return render_template("politicas.html")


@app.route("/terminos")
def terminos():
    return render_template("terminos.html")



# ============================================================
# 9. ASISTENTE DE LA BURBUJA (abajo a la derecha)
# ============================================================

@app.route("/asistente", methods=["POST"])
def responder_asistente():
    """
    El JavaScript de la burbuja envía aquí lo que escribió la persona (o el tema de un
    botoncito) y esta función devuelve la respuesta en formato JSON.
    Las respuestas están en asistente.py; aquí solo se arma lo que viaja al navegador.
    """
    datos = request.get_json(silent=True) or {}
    mensaje = str(datos.get("mensaje", ""))[:300]       # máximo 300 letras
    tema_id = datos.get("tema")

    # Si tocó un botoncito llega el "tema"; si escribió, buscamos por palabras clave
    tema = asistente_bot.tema_por_id(tema_id) if tema_id else None
    if tema is None:
        tema = asistente_bot.responder(mensaje)

    # Los enlaces se guardan como nombre de ruta; aquí los convertimos en direcciones reales
    enlaces = []
    for enlace in tema.get("enlaces", []):
        texto, ruta = enlace[0], enlace[1]
        parametros = enlace[2] if len(enlace) > 2 else {}
        if ruta == "whatsapp":
            url = f"https://wa.me/{WHATSAPP_NUMERO}?text={quote(WHATSAPP_MENSAJE)}"
        elif ruta == "instagram":
            url = INSTAGRAM_URL
        elif ruta == "canal":
            url = WHATSAPP_CANAL_URL
        else:
            url = url_for(ruta, **parametros)
        enlaces.append({"texto": texto, "url": url, "externo": ruta in ("whatsapp", "instagram", "canal")})

    # Botoncitos de sugerencia (otros temas relacionados)
    sugerencias = []
    for otro_id in tema.get("relacionados", []):
        otro = asistente_bot.tema_por_id(otro_id)
        if otro:
            sugerencias.append({"texto": otro["titulo"], "tema": otro["id"]})

    imagen = tema.get("imagen")
    return jsonify({
        "respuesta": tema["respuesta"],
        "enlaces": enlaces,
        "sugerencias": sugerencias,
        "imagen": url_for("static", filename=imagen) if imagen else None,
    })


if __name__ == "__main__":
    app.run(debug=True)
