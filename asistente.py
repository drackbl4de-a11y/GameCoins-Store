"""
asistente.py
------------
El "cerebro" del asistente de la burbuja (abajo a la derecha de la página).

NO es una inteligencia artificial: es un asistente POR REGLAS. Funciona así:
  1) Cada tema tiene una lista de PALABRAS CLAVE y una RESPUESTA ya escrita.
  2) Cuando el usuario escribe, buscamos cuáles palabras clave aparecen en su mensaje.
  3) El tema que más palabras clave "gana" y se muestra su respuesta.
  4) Si ninguna coincide, se muestra un mensaje de "no entendí" con opciones.

Para AGREGAR una respuesta nueva solo hay que copiar un bloque de TEMAS y cambiar
sus textos. No hay que tocar nada más (ni app.py ni el JavaScript).

Cada tema (un diccionario) tiene estas partes:
  "id"          -> nombre corto y único del tema
  "titulo"      -> texto del botoncito de sugerencia
  "palabras"    -> palabras clave (escritas en minúscula y SIN tildes)
  "respuesta"   -> lo que contesta el asistente
  "enlaces"     -> (opcional) botones: ("Texto", "nombre_de_la_ruta") o
                   ("Texto", "nombre_de_la_ruta", {"parametro": "valor"})
  "relacionados"-> (opcional) ids de otros temas para sugerir después
  "imagen"      -> (opcional) imagen de la carpeta static que se muestra en el chat
"""

import re
import unicodedata


# ============================================================
# 1. TEMAS (preguntas y respuestas)
# ============================================================

TEMAS = [

    # ------------------------------------------------------------
    # CUENTA: registro, correo y código de verificación
    # ------------------------------------------------------------
    {
        "id": "codigo_no_llega",
        "titulo": "No me llega el código",
        "palabras": ["no llega el codigo", "llega el codigo", "llego el codigo", "recibo el codigo",
                     "recibi el codigo", "codigo de verificacion", "codigo", "verificacion",
                     "verificar mi correo", "verificar correo", "reenviar codigo"],
        "respuesta": "Si no te llega el código de verificación:\n"
                     "1. Revisa la carpeta de spam o correo no deseado.\n"
                     "2. Mira que tu correo esté bien escrito (por ejemplo nombre@gmail.com).\n"
                     "3. En la pantalla del código toca «reenvía el código».\n"
                     "4. Espera 1 o 2 minutos: a veces el correo se demora.\n"
                     "Si nada funciona, usa «Cambiar el correo» y regístrate de nuevo.",
        "enlaces": [("Ir al registro", "registro")],
        "relacionados": ["codigo_vencido", "registro_problemas", "contacto_whatsapp"],
    },
    {
        "id": "codigo_vencido",
        "titulo": "El código venció o es incorrecto",
        "palabras": ["codigo vencio", "codigo vencido", "codigo expiro", "expiro", "codigo incorrecto",
                     "codigo no es correcto", "codigo invalido", "codigo equivocado",
                     "demasiados intentos", "vencio el codigo", "se vencio"],
        "respuesta": "El código de verificación dura 10 minutos y se permiten 5 intentos.\n"
                     "• Si venció o fallaste 5 veces, vuelve a registrarte para recibir uno nuevo.\n"
                     "• Si todavía estás a tiempo, toca «reenvía el código» y usa el más reciente "
                     "(el anterior deja de servir).\n"
                     "• Escribe los 6 números sin espacios.",
        "enlaces": [("Registrarme de nuevo", "registro")],
        "relacionados": ["codigo_no_llega"],
    },
    {
        "id": "como_registrarse",
        "titulo": "¿Cómo me registro?",
        "palabras": ["como me registro", "registrarme", "registrarse", "crear cuenta", "crear una cuenta",
                     "nueva cuenta", "registro", "abrir una cuenta"],
        "respuesta": "Para crear tu cuenta:\n"
                     "1. Toca «Registrarse» arriba a la derecha.\n"
                     "2. Escribe tu nombre, apellido, un correo REAL y una contraseña de mínimo 6 caracteres.\n"
                     "3. Te llegará un código de 6 números al correo: escríbelo para confirmar.\n"
                     "4. ¡Listo! Ya puedes iniciar sesión y comprar.",
        "enlaces": [("Ir al registro", "registro")],
        "relacionados": ["registro_problemas", "codigo_no_llega"],
    },
    {
        "id": "registro_problemas",
        "titulo": "No me deja registrarme",
        "palabras": ["no me deja registrar", "no puedo registrar", "no deja registrar", "error al registrar",
                     "fallo el registro", "error en el registro", "correo invalido", "correo no valido",
                     "correo valido", "correo mal escrito", "no coinciden", "contrasenas no coinciden",
                     "todos los campos", "contrasena muy corta", "contrasena corta", "6 caracteres"],
        "respuesta": "El registro puede fallar por alguno de estos motivos:\n"
                     "• Dejaste un campo vacío (todos son obligatorios).\n"
                     "• Las dos contraseñas no coinciden.\n"
                     "• La contraseña tiene menos de 6 caracteres.\n"
                     "• El correo no tiene forma de correo (falta @ o el .com).\n"
                     "• Ya existe una cuenta con ese correo.\n"
                     "• No se pudo enviar el código: revisa que el correo esté bien escrito.\n"
                     "Mira el mensaje rojo que aparece arriba: dice cuál es el error.",
        "enlaces": [("Ir al registro", "registro")],
        "relacionados": ["correo_ya_existe", "codigo_no_llega"],
    },
    {
        "id": "correo_ya_existe",
        "titulo": "Ya existe una cuenta con mi correo",
        "palabras": ["ya existe una cuenta", "correo ya registrado", "ya esta registrado", "ya existe ese correo",
                     "correo ya existe", "ya tengo cuenta", "cuenta ya existe", "ya registrado",
                     "ya existe una cuenta registrada"],
        "respuesta": "Ese correo ya tiene una cuenta, así que no se puede registrar otra vez.\n"
                     "• Si es tuya, inicia sesión con ese correo.\n"
                     "• Si no recuerdas la contraseña, mira la ayuda de «Olvidé mi contraseña».\n"
                     "• Si no es tuya, usa otro correo para registrarte.",
        "enlaces": [("Iniciar sesión", "login")],
        "relacionados": ["olvide_contrasena", "login_problemas"],
    },

    # ------------------------------------------------------------
    # CUENTA: inicio de sesión, contraseña y perfil
    # ------------------------------------------------------------
    {
        "id": "login_problemas",
        "titulo": "No puedo iniciar sesión",
        "palabras": ["no puedo iniciar sesion", "no puedo entrar", "no me deja entrar", "no inicia sesion",
                     "no me deja iniciar", "iniciar sesion", "inicio de sesion", "contrasena incorrecta",
                     "correo o contrasena incorrectos", "contrasena equivocada", "login", "ingresar",
                     "no puedo ingresar", "no me deja ingresar", "entro a mi cuenta", "entrar a mi cuenta",
                     "acceder a mi cuenta", "entrar a la cuenta", "acceder", "como entro"],
        "respuesta": "Si no puedes iniciar sesión:\n"
                     "• Revisa que el correo esté bien escrito (sin espacios).\n"
                     "• Escribe la contraseña con cuidado: importan las mayúsculas y minúsculas.\n"
                     "• Verifica que sí hayas terminado el registro con el código del correo.\n"
                     "• Si no recuerdas la contraseña, toca «¿Olvidaste la contraseña?» y te llega un código al correo.\n"
                     "Por seguridad el mensaje no dice si falló el correo o la contraseña.",
        "enlaces": [("Iniciar sesión", "login")],
        "relacionados": ["olvide_contrasena", "registro_problemas"],
    },
    {
        "id": "olvide_contrasena",
        "titulo": "Olvidé mi contraseña",
        "palabras": ["olvide mi contrasena", "olvide la contrasena", "olvide", "olvidaste", "olvido",
                     "recuperar contrasena", "restablecer contrasena", "no recuerdo mi contrasena",
                     "perdi mi contrasena", "contrasena olvidada", "recuperar cuenta", "recuperar mi cuenta",
                     "no me acuerdo de mi contrasena"],
        "respuesta": "Sí se puede recuperar:\n"
                     "1. En el inicio de sesión toca «¿Olvidaste la contraseña?».\n"
                     "2. Escribe tu correo y te enviamos un código de 6 números.\n"
                     "3. Escribe el código y tu contraseña nueva (mínimo 6 caracteres).\n"
                     "El código dura 10 minutos y tienes 5 intentos. Si no llega, revisa spam o "
                     "escríbenos por WhatsApp.",
        "enlaces": [("Recuperar contraseña", "recuperar_contrasena"), ("Escribir por WhatsApp", "whatsapp")],
        "relacionados": ["cambiar_contrasena", "contacto_whatsapp"],
    },
    {
        "id": "cambiar_contrasena",
        "titulo": "Cambiar mi contraseña",
        "palabras": ["cambiar contrasena", "cambiar mi contrasena", "cambiar la contrasena",
                     "nueva contrasena", "actualizar contrasena", "modificar contrasena",
                     "cambiar de contrasena", "otra contrasena", "poner otra contrasena"],
        "respuesta": "Para cambiar tu contraseña:\n"
                     "1. Inicia sesión y entra a tu Perfil.\n"
                     "2. Abre la pestaña «Mis Datos».\n"
                     "3. Escribe tu contraseña actual, la nueva (mínimo 6 caracteres) y repítela.\n"
                     "4. Guarda los cambios.\n"
                     "Si la actual no es correcta, el cambio no se hace.",
        "enlaces": [("Ir a Mis Datos", "perfil", {"tab": "datos"})],
        "relacionados": ["olvide_contrasena", "foto_perfil"],
    },
    {
        "id": "foto_perfil",
        "titulo": "Problemas con la foto de perfil",
        "palabras": ["foto de perfil", "foto perfil", "cambiar foto", "subir foto", "imagen de perfil",
                     "mi foto", "foto no sale", "foto no aparece", "avatar", "formato de imagen",
                     "imagen muy pesada", "foto"],
        "respuesta": "Para la foto de perfil:\n"
                     "• Ve a Perfil → Mis Datos y elige una imagen.\n"
                     "• Formatos permitidos: PNG, JPG, GIF o WEBP.\n"
                     "• El tamaño máximo es 5 MB.\n"
                     "• Si ya la subiste y no se ve, recarga la página con Ctrl + F5.\n"
                     "• Tu foto sale en el botón de arriba y en tus opiniones.",
        "enlaces": [("Ir a Mis Datos", "perfil", {"tab": "datos"})],
        "relacionados": ["datos_perfil", "estilos_rotos"],
    },
    {
        "id": "datos_perfil",
        "titulo": "Cambiar mis datos o mi correo",
        "palabras": ["cambiar nombre", "cambiar mi nombre", "cambiar mis datos", "editar perfil",
                     "editar mis datos", "actualizar datos", "telefono", "cambiar correo",
                     "cambiar mi correo", "mis datos", "apellido", "cambiar telefono"],
        "respuesta": "En Perfil → Mis Datos puedes cambiar tu nombre, apellido y teléfono, "
                     "además de la foto y la contraseña.\n"
                     "El correo NO se puede cambiar, porque es con el que inicias sesión y recibes "
                     "tus certificados. Si necesitas otro correo, escríbenos.",
        "enlaces": [("Ir a Mis Datos", "perfil", {"tab": "datos"})],
        "relacionados": ["cambiar_contrasena", "foto_perfil"],
    },
    {
        "id": "sesion_se_cierra",
        "titulo": "Me pide iniciar sesión otra vez",
        "palabras": ["sesion se cierra", "se cierra la sesion", "me saca", "me pide iniciar sesion",
                     "debes iniciar sesion", "sesion expirada", "me pide login", "me desconecta",
                     "me pide que inicie sesion", "pierdo la sesion"],
        "respuesta": "Para comprar, ver el carrito, tus pedidos o dejar una opinión necesitas tener la "
                     "sesión iniciada; por eso la página te lleva al inicio de sesión.\n"
                     "Si te la pide aunque ya habías entrado: cerraste el navegador, borraste las "
                     "cookies o el servidor se reinició. Solo vuelve a iniciar sesión.",
        "enlaces": [("Iniciar sesión", "login")],
        "relacionados": ["login_problemas"],
    },
    {
        "id": "cerrar_sesion",
        "titulo": "¿Cómo cierro sesión?",
        "palabras": ["cerrar sesion", "cerrar mi sesion", "cierro sesion", "cierra la sesion", "cerrar la sesion", "salir de la cuenta", "logout", "desconectarme",
                     "salir de mi cuenta", "salir"],
        "respuesta": "Entra a tu Perfil y, al final de la pestaña «Mi Perfil», toca «Cerrar mi sesión».",
        "enlaces": [("Ir a mi Perfil", "perfil")],
        "relacionados": ["datos_perfil"],
    },
    {
        "id": "eliminar_cuenta",
        "titulo": "Eliminar mi cuenta",
        "palabras": ["eliminar cuenta", "eliminar mi cuenta", "borrar cuenta", "borrar mi cuenta",
                     "dar de baja", "cancelar cuenta", "cancelar mi cuenta", "desactivar mi cuenta"],
        "respuesta": "Por ahora no hay un botón para eliminar la cuenta. Escríbenos por WhatsApp "
                     "con el correo de tu cuenta y la solicitud la revisa un administrador.",
        "enlaces": [("Escribir por WhatsApp", "whatsapp")],
        "relacionados": ["contacto_whatsapp"],
    },

    # ------------------------------------------------------------
    # COMPRAS: carrito, precios y pago
    # ------------------------------------------------------------
    {
        "id": "como_comprar",
        "titulo": "¿Cómo compro?",
        "palabras": ["como compro", "como comprar", "como hago una compra", "pasos para comprar",
                     "quiero comprar", "como se compra", "como recargar", "como recargo", "recargar",
                     "comprar robux", "comprar valorant", "comprar vp", "hacer una compra"],
        "respuesta": "Comprar es fácil:\n"
                     "1. Inicia sesión.\n"
                     "2. Entra a «Juegos» y elige Roblox o VALORANT.\n"
                     "3. Elige un pack y toca «Continuar»: se agrega a tu carrito.\n"
                     "4. Abre el carrito 🛒 y toca «Confirmar compra».\n"
                     "5. Escribe tu usuario de Roblox o tu ID de VALORANT y los datos de Nequi "
                     "(el pago es simulado).\n"
                     "6. Toca «Confirmar compra» y verás «compra realizada exitosamente».\n"
                     "Tu pedido queda PROCESADO; cuando sea entregado o cancelado te llega un correo.",
        "enlaces": [("Ver los juegos", "juegos"), ("Ir al carrito", "ver_carrito")],
        "relacionados": ["agregar_carrito_falla", "nequi_problemas", "pago_simulado"],
    },
    {
        "id": "paquete_agotado",
        "titulo": "Un paquete sale AGOTADO",
        "palabras": ["agotado", "agotados", "se agoto", "se acabo", "se acabaron", "sin stock", "stock",
                     "no hay unidades", "ya no quedan", "no quedan", "no hay mas", "sin existencias",
                     "existencias", "unidades disponibles", "cuantas unidades", "cuantos quedan",
                     "cuando vuelve", "cuando hay mas", "cuando reponen", "reponer", "no hay disponibles",
                     "cantidad limitada", "limite de compra", "maximo de compra", "no me deja subir la cantidad",
                     "no puedo sumar", "boton mas no funciona", "solo quedan", "quedan pocas"],
        "respuesta": "Cada paquete tiene un número limitado de unidades (stock).\n"
                     "• Cuando se venden todas, el paquete aparece como AGOTADO y no se puede elegir.\n"
                     "• Si ves «Quedan 3», son las unidades que faltan por vender.\n"
                     "• En el carrito el botón «+» se desactiva cuando ya tienes todas las unidades que quedan.\n"
                     "• Si alguien compra antes que tú, la página te avisa y te pide ajustar el carrito.\n"
                     "• Si el pedido de otra persona se cancela, esas unidades vuelven a estar disponibles.\n"
                     "El administrador puede rellenar el stock desde su panel. Si necesitas un paquete "
                     "agotado, escríbenos por WhatsApp y te avisamos cuando haya.",
        "enlaces": [("Ver los juegos", "juegos"), ("Escribir por WhatsApp", "whatsapp")],
        "relacionados": ["agregar_carrito_falla", "carrito_cantidad", "como_comprar"],
    },
    {
        "id": "agregar_carrito_falla",
        "titulo": "No puedo agregar al carrito",
        "palabras": ["no puedo agregar", "no agrega", "no me deja agregar", "agregar al carrito",
                     "no pasa nada al agregar", "no se agrega", "ese paquete ya no esta disponible",
                     "paquete no disponible", "no disponible", "boton continuar", "no funciona el boton",
                     "no puedo comprar", "no me deja comprar", "boton de continuar", "no aparece el boton",
                     "no me aparece el boton", "no sale el boton"],
        "respuesta": "Si no se agrega el paquete al carrito:\n"
                     "• Tienes que haber iniciado sesión; si no, la página te manda al login.\n"
                     "• Si dice «Ese paquete ya no está disponible», el administrador lo desactivó. "
                     "Elige otro pack.\n"
                     "• Si dice «agotado» o «solo quedan N», se acabó el stock de ese paquete.\n"
                     "• Después de tocar «Continuar» la página se queda donde estabas y arriba aparece "
                     "el aviso verde «se agregó al carrito»; mira el numerito rojo del carrito 🛒.\n"
                     "• Si tampoco aparece el aviso, recarga con Ctrl + F5 e inténtalo otra vez.",
        "enlaces": [("Iniciar sesión", "login"), ("Ir al carrito", "ver_carrito")],
        "relacionados": ["carrito_vacio", "sesion_se_cierra"],
    },
    {
        "id": "carrito_cantidad",
        "titulo": "Cambiar cantidad o quitar del carrito",
        "palabras": ["cambiar cantidad", "aumentar cantidad", "quitar del carrito", "eliminar del carrito",
                     "sacar del carrito", "borrar del carrito", "comprar mas de uno", "dos paquetes",
                     "varios paquetes", "mas de un paquete", "sumar", "restar", "quitar", "eliminar un paquete"],
        "respuesta": "En el carrito cada paquete tiene los botones − y + para cambiar la cantidad. "
                     "Si bajas la cantidad a 0, el paquete se quita.\n"
                     "También puedes tocar «Eliminar» para quitarlo de una vez.\n"
                     "Puedes comprar varios paquetes distintos en un mismo pedido.",
        "enlaces": [("Ir al carrito", "ver_carrito")],
        "relacionados": ["precio_distinto"],
    },
    {
        "id": "carrito_vacio",
        "titulo": "Mi carrito está vacío",
        "palabras": ["carrito vacio", "mi carrito esta vacio", "no aparece en el carrito",
                     "desaparecio del carrito", "carrito no muestra", "se vacio el carrito",
                     "numero rojo", "numerito", "carrito"],
        "respuesta": "El carrito es personal de cada usuario: solo lo ves con tu sesión iniciada.\n"
                     "• Si acabas de pagar, el carrito queda vacío a propósito (la compra ya está en "
                     "Perfil → Pedidos).\n"
                     "• Si no ves lo que agregaste, revisa que hayas entrado con la misma cuenta.\n"
                     "• El numerito rojo del icono 🛒 indica cuántos paquetes tienes.",
        "enlaces": [("Ir al carrito", "ver_carrito"), ("Ver mis pedidos", "perfil", {"tab": "pedidos"})],
        "relacionados": ["ver_pedidos", "carrito_cantidad"],
    },
    {
        "id": "promo_no_aplica",
        "titulo": "La promoción no se aplicó",
        "palabras": ["promocion no", "descuento no", "no se aplico el descuento", "no aplica la promocion",
                     "sin descuento", "promociones", "promocion", "descuento", "oferta", "precio tachado",
                     "vencio la promocion", "promocion termino", "promo", "rebaja"],
        "respuesta": "Las promociones tienen fecha de inicio y de fin, y solo se aplican a los paquetes "
                     "que las tienen (se ven con el precio original tachado).\n"
                     "• Si la promoción ya terminó, vuelve el precio normal.\n"
                     "• El carrito guarda el precio del momento en que agregaste el paquete. Si "
                     "cambió después, elimina el paquete y agrégalo de nuevo.\n"
                     "En la página «Promociones» ves las que están vigentes hoy.",
        "enlaces": [("Ver promociones", "promociones"), ("Ir al carrito", "ver_carrito")],
        "relacionados": ["precio_distinto"],
    },
    {
        "id": "precio_distinto",
        "titulo": "El total no coincide",
        "palabras": ["total no coincide", "precio diferente", "precio distinto", "cobraron de mas",
                     "precio cambiar", "el precio cambiar", "total incorrecto", "precio incorrecto",
                     "el total", "no es el mismo precio", "subtotal", "precio mal"],
        "respuesta": "El total es la suma de (precio × cantidad) de cada paquete del carrito.\n"
                     "• Si un paquete tenía promoción, se usa el precio con descuento.\n"
                     "• El precio queda fijo cuando agregas el paquete; si la promoción cambió, "
                     "elimínalo del carrito y agrégalo de nuevo.\n"
                     "• Los precios están en pesos colombianos (COP).\n"
                     "Si ya pagaste y el total del pedido te parece mal, escríbenos con tu código de pedido.",
        "enlaces": [("Ir al carrito", "ver_carrito"), ("Escribir por WhatsApp", "whatsapp")],
        "relacionados": ["promo_no_aplica", "contacto_whatsapp"],
    },
    {
        "id": "nequi_problemas",
        "titulo": "Error al pagar con Nequi",
        "palabras": ["celular nequi", "numero de celular", "numero nequi", "celular invalido",
                     "celular no valido", "celular colombiano", "10 digitos", "nequi",
                     "pagar con nequi", "error al pagar", "no puedo pagar", "pago no pasa",
                     "falla el pago", "no deja pagar", "checkout", "confirmar compra",
                     "no deja confirmar", "no me deja confirmar", "confirmar la compra", "no me deja pagar", "pagar",
                     "celular no es valido", "no es valido", "celular", "problema con el pago",
                     "problema de pago", "problemas con el pago"],
        "respuesta": "Si no deja confirmar la compra, revisa:\n"
                     "• El nombre de quien paga no puede estar vacío.\n"
                     "• El celular Nequi debe tener 10 dígitos y empezar por 3 (ejemplo 3001234567), "
                     "sin espacios ni el +57.\n"
                     "• Cada paquete necesita su usuario de Roblox o su ID de VALORANT.\n"
                     "Los errores salen en rojo arriba, y lo que escribiste se conserva.\n"
                     "Recuerda: el pago es simulado, no se cobra dinero real.",
        "enlaces": [("Ir al carrito", "ver_carrito")],
        "relacionados": ["dato_entrega", "pago_simulado"],
    },
    {
        "id": "dato_entrega",
        "titulo": "¿Qué pongo en usuario o ID?",
        "palabras": ["usuario de roblox", "id de valorant", "usuario#tag", "dato de entrega",
                     "falta tu usuario", "formato usuario", "tag", "id de jugador", "riot id",
                     "donde pongo mi usuario", "mi usuario de roblox", "falta el dato", "formato del id",
                     "usuario roblox", "id valorant"],
        "respuesta": "En el pago, cada paquete pide a qué cuenta se entregan las monedas:\n"
                     "• Roblox: escribe tu nombre de usuario de Roblox (el que usas para entrar al juego).\n"
                     "• VALORANT: escribe tu ID de jugador con el formato Usuario#TAG, por ejemplo "
                     "Juan#1234 (el TAG tiene de 3 a 5 números).\n"
                     "Revísalo bien antes de confirmar: las monedas se entregan a esa cuenta.",
        "enlaces": [("Ir al carrito", "ver_carrito")],
        "relacionados": ["dato_equivocado", "nequi_problemas"],
    },
    {
        "id": "dato_equivocado",
        "titulo": "Me equivoqué de usuario o ID",
        "palabras": ["me equivoque", "puse mal", "usuario equivocado", "usuario incorrecto", "id equivocado",
                     "cuenta equivocada", "mal escrito mi usuario", "cambiar usuario de roblox",
                     "cambiar el id", "corregir el usuario", "error en el usuario", "entrega a otra cuenta",
                     "me equivoque de usuario", "escribi mal"],
        "respuesta": "Si ya pagaste y te equivocaste en el usuario o el ID, escríbenos cuanto antes por "
                     "WhatsApp con:\n"
                     "• Tu código de pedido (empieza por GCS-).\n"
                     "• El dato correcto de tu cuenta.\n"
                     "Si el pedido aún no está entregado, se puede corregir. Por eso conviene revisar bien "
                     "antes de confirmar la compra.",
        "enlaces": [("Escribir por WhatsApp", "whatsapp"), ("Ver mis pedidos", "perfil", {"tab": "pedidos"})],
        "relacionados": ["codigo_pedido", "pedido_no_llega"],
    },
    {
        "id": "pago_simulado",
        "titulo": "¿El pago es real?",
        "palabras": ["se cobra", "cobran de verdad", "dinero real", "pago real", "pago simulado", "es real",
                     "me van a cobrar", "descontaron", "debitaron", "cobro", "tarjeta", "metodos de pago",
                     "medios de pago", "formas de pago", "como pago", "pse", "daviplata", "paypal",
                     "efectivo", "me cobraron"],
        "respuesta": "No. GameCoins Store es un proyecto académico y el pago con Nequi es una SIMULACIÓN: "
                     "no se cobra dinero real ni se conecta con Nequi.\n"
                     "Solo guardamos el nombre y los últimos 4 dígitos del celular. El único método "
                     "disponible es Nequi (simulado).",
        "enlaces": [("Ver políticas", "politicas")],
        "relacionados": ["seguridad", "proyecto"],
    },

    # ------------------------------------------------------------
    # PEDIDOS Y CERTIFICADO
    # ------------------------------------------------------------
    {
        "id": "ver_pedidos",
        "titulo": "¿Dónde veo mis pedidos?",
        "palabras": ["mis pedidos", "ver mis pedidos", "donde veo mi pedido", "donde veo mis compras",
                     "historial de compras", "historial", "mis compras", "donde estan mis pedidos",
                     "pedido", "compra", "ver mis compras", "ver mi pedido", "compra no aparece",
                     "no aparece mi compra", "no aparece mi pedido", "no veo mi compra", "no veo mi pedido",
                     "no encuentro mi pedido", "no encuentro el pedido", "no encuentro mi compra"],
        "respuesta": "Entra a tu Perfil y abre la pestaña «Pedidos»: ahí aparecen todas tus compras, "
                     "con su estado y su código. Toca un pedido para ver el detalle; el certificado se puede descargar cuando el pedido esté ENTREGADO.",
        "enlaces": [("Ir a mis pedidos", "perfil", {"tab": "pedidos"})],
        "relacionados": ["estado_pedido", "certificado_descargar"],
    },
    {
        "id": "codigo_pedido",
        "titulo": "¿Cuál es mi código de pedido?",
        "palabras": ["codigo de pedido", "codigo del pedido", "gcs-", "numero de pedido",
                     "numero del pedido", "donde esta mi codigo", "id de pedido", "codigo gcs"],
        "respuesta": "El código de pedido empieza por GCS- (por ejemplo GCS-A1B2C3D4). Lo ves en Perfil → "
                     "Pedidos, en el detalle del pedido, en el certificado en PDF y en el correo que te "
                     "enviamos cuando el pedido se entrega o se cancela. Tenlo a la mano si necesitas ayuda por WhatsApp.",
        "enlaces": [("Ir a mis pedidos", "perfil", {"tab": "pedidos"})],
        "relacionados": ["contacto_whatsapp", "pedido_no_llega"],
    },
    {
        "id": "estado_pedido",
        "titulo": "¿Qué significa el estado del pedido?",
        "palabras": ["estado del pedido", "estado de mi pedido", "procesado", "entregado", "cancelado",
                     "que significa procesado", "pedido procesado", "pedido en proceso", "en que estado",
                     "estado de la compra", "sigue en procesado", "en procesado", "sigue procesado"],
        "respuesta": "Tu pedido puede estar en uno de estos estados:\n"
                     "• PROCESADO: la compra se registró y está pendiente de entrega.\n"
                     "• ENTREGADO: el administrador confirmó la entrega. Te llega un correo con el "
                     "certificado en PDF.\n"
                     "• CANCELADO: el pedido se canceló (te llega un correo avisándote) y no cuenta "
                     "en tus totales.\n"
                     "El estado lo cambia un administrador desde su panel de ventas.",
        "enlaces": [("Ver mis pedidos", "perfil", {"tab": "pedidos"})],
        "relacionados": ["pedido_no_llega", "pedido_cancelado"],
    },
    {
        "id": "pedido_no_llega",
        "titulo": "Mis monedas no han llegado",
        "palabras": ["no llegaron", "no me llegaron", "no llego mi pedido", "no han llegado",
                     "monedas no llegan", "robux no llegaron", "no recibi las monedas",
                     "no recibi mis robux", "no recibi", "no he recibido", "no me llegan las monedas",
                     "pedido no llega", "no me han entregado", "sin recibir", "aun no llega",
                     "todavia no llega", "entrega", "demora", "cuanto tarda", "tarda",
                     "tiempo de entrega", "no me llegan mis robux", "mis monedas", "mis robux", "mis vp",
                     "cuanto demora", "cuanto se demora", "no me llego nada", "no llego nada", "no llega nada",
                     "pague y no", "ya pague", "y no llega", "y no llego", "ya paso",
                     "problema con mi pedido", "problema con el pedido", "problema con mi compra"],
        "respuesta": "Si todavía no ves tus monedas:\n"
                     "1. Entra a Perfil → Pedidos y mira el estado. Si dice PROCESADO, aún está pendiente; "
                     "cuando un administrador lo marque ENTREGADO, ya fue enviado.\n"
                     "2. Revisa que el usuario de Roblox o el ID de VALORANT del pedido estén bien "
                     "(están en el detalle del pedido).\n"
                     "3. Si pasó bastante tiempo o hay un error en el dato, escríbenos por WhatsApp con "
                     "tu código de pedido y tu certificado en PDF.",
        "enlaces": [("Ver mis pedidos", "perfil", {"tab": "pedidos"}), ("Escribir por WhatsApp", "whatsapp")],
        "relacionados": ["estado_pedido", "dato_equivocado", "codigo_pedido"],
    },
    {
        "id": "pedido_cancelado",
        "titulo": "Cancelar un pedido o pedir devolución",
        "palabras": ["pedido cancelado", "cancelaron mi pedido", "me cancelaron", "cancelaron el pedido", "cancelaron la compra", "cancelar pedido", "cancelar mi pedido",
                     "cancelar compra", "quiero cancelar", "devolucion", "reembolso", "devolver",
                     "me devuelvan", "cancelar la compra", "devolver mi compra", "devolver la compra",
                     "devolver mi pedido"],
        "respuesta": "Los pedidos los cancela un administrador y, cuando lo hace, te llega un correo "
                     "avisándote. Si necesitas cancelar el tuyo o te cancelaron uno sin entender por qué, escríbenos por WhatsApp con tu código de pedido.\n"
                     "Como el pago es simulado, no hay dinero real que devolver.",
        "enlaces": [("Escribir por WhatsApp", "whatsapp")],
        "relacionados": ["estado_pedido", "pago_simulado"],
    },
    {
        "id": "compra_duplicada",
        "titulo": "Compré dos veces por error",
        "palabras": ["pague dos veces", "compra duplicada", "dos veces", "cobro doble", "compre dos veces",
                     "se repitio la compra", "doble compra", "duplicado", "por error", "compre dos"],
        "respuesta": "Si por error se registraron dos compras, mira en Perfil → Pedidos cuántos pedidos "
                     "tienes. Escríbenos por WhatsApp con los dos códigos de pedido y un administrador "
                     "revisa y cancela el que sobra.",
        "enlaces": [("Ver mis pedidos", "perfil", {"tab": "pedidos"}), ("Escribir por WhatsApp", "whatsapp")],
        "relacionados": ["pedido_cancelado", "codigo_pedido"],
    },
    {
        "id": "certificado_descargar",
        "titulo": "Descargar mi certificado",
        "palabras": ["descargar certificado", "descargar el certificado", "no aparece el certificado",
                     "no veo el certificado", "no sale el boton de certificado", "donde esta el certificado",
                     "donde descargo", "certificado", "comprobante", "factura", "recibo", "pdf",
                     "codigo del certificado", "codigo de certificado", "cert-"],
        "respuesta": "Tu certificado de compra se descarga así:\n"
                     "1. Entra a Perfil → Pedidos.\n"
                     "2. Abre el pedido que quieres.\n"
                     "3. Toca «Descargar certificado de compra».\n"
                     "Ojo: el certificado solo está disponible cuando el pedido está ENTREGADO. Si dice "
                     "PROCESADO, espera a que un administrador lo entregue.\n"
                     "El PDF trae los datos del pedido, del cliente, los paquetes, el total y un código "
                     "CERT-… único. También te llega al correo cuando se entrega.",
        "enlaces": [("Ir a mis pedidos", "perfil", {"tab": "pedidos"})],
        "relacionados": ["certificado_correo", "certificado_no_abre"],
    },
    {
        "id": "correo_no_llega",
        "titulo": "No me llega ningún correo",
        "palabras": ["no llego el correo", "no llega el correo", "no me llegan correos", "no recibo correos",
                     "no ha llegado el correo", "correo no llega", "correo no llego", "el correo no llego",
                     "no me llego el correo", "no recibi el correo", "no recibo el correo", "los correos",
                     "correos", "spam", "correo no deseado", "no llega nada al correo"],
        "respuesta": "¿Qué correo esperas? Revisa primero estos puntos que sirven para cualquiera:\n"
                     "• Mira la carpeta de spam o correo no deseado.\n"
                     "• Comprueba que el correo con el que te registraste esté bien escrito.\n"
                     "• Los correos pueden tardar 1 o 2 minutos.\n"
                     "• Para enviar correos hace falta internet y que el servidor tenga la cuenta de Gmail "
                     "configurada.\n"
                     "Elige abajo cuál es tu caso.",
        "enlaces": [],
        "relacionados": ["codigo_no_llega", "certificado_correo", "contacto_whatsapp"],
    },
    {
        "id": "certificado_correo",
        "titulo": "El certificado no llegó al correo",
        "palabras": ["correo del pedido", "cuando me llega el correo", "correo de entrega", "correo cuando se entrega", "certificado no llego", "no me llego el certificado", "certificado al correo",
                     "certificado no llega", "enviar certificado", "reenviar certificado",
                     "certificado por correo", "no recibi el certificado", "correo del certificado",
                     "enviar a mi correo", "reenviar el certificado", "enviar el certificado"],
        "respuesta": "El certificado se envía al correo cuando un administrador marca tu pedido como "
                     "ENTREGADO (no se envía al comprar). Si ya está entregado y no llegó:\n"
                     "• Mira en spam o correo no deseado.\n"
                     "• Entra a Perfil → Pedidos, abre el pedido y toca «Enviar certificado a mi correo».\n"
                     "• Recuerda que llega al correo con el que te registraste.\n"
                     "• Si aparece «El envío de correos todavía no está configurado», el servidor aún no "
                     "tiene la cuenta de Gmail lista; mientras tanto puedes descargar el PDF directamente.\n"
                     "• Para enviar correos hace falta conexión a internet.",
        "enlaces": [("Ir a mis pedidos", "perfil", {"tab": "pedidos"})],
        "relacionados": ["certificado_descargar", "codigo_no_llega"],
    },
    {
        "id": "certificado_no_abre",
        "titulo": "El PDF no abre o no descarga",
        "palabras": ["pdf no abre", "no abre el pdf", "pdf danado", "no se descarga", "no descarga",
                     "certificado no abre", "archivo no abre", "error al descargar", "no puedo descargar",
                     "descarga no funciona", "no baja el pdf", "abrir el certificado", "abrir el pdf",
                     "no puedo abrir"],
        "respuesta": "Si el certificado no se descarga o no abre:\n"
                     "• Revisa la carpeta de Descargas: a veces se guarda sin avisar.\n"
                     "• Permite las descargas de la página si el navegador las bloqueó.\n"
                     "• Ábrelo con el lector de PDF del navegador o con Adobe Reader.\n"
                     "• Prueba de nuevo desde Perfil → Pedidos → el pedido → «Descargar certificado».\n"
                     "• Si sigue fallando, pide que te lo enviemos al correo.",
        "enlaces": [("Ir a mis pedidos", "perfil", {"tab": "pedidos"})],
        "relacionados": ["certificado_correo"],
    },

    # ------------------------------------------------------------
    # NAVEGACIÓN Y FUNCIONAMIENTO DE LA PÁGINA
    # ------------------------------------------------------------
    {
        "id": "sin_juegos",
        "titulo": "No aparecen juegos o paquetes",
        "palabras": ["no aparecen", "no hay juegos", "no salen los juegos", "no aparece el juego",
                     "no aparecen paquetes", "paquete desaparecio", "juego desaparecio", "sin paquetes",
                     "todavia no hay paquetes", "no veo paquetes", "no veo juegos", "no hay paquetes",
                     "no salen los paquetes", "no sale el juego"],
        "respuesta": "Un juego o paquete puede no verse porque:\n"
                     "• El administrador lo desactivó (queda oculto, pero no se borra).\n"
                     "• El juego todavía no tiene paquetes creados.\n"
                     "• La base de datos no está encendida o falta cargar los datos iniciales "
                     "(esto lo revisa quien administra el sitio).\n"
                     "Prueba recargando con Ctrl + F5. Si sigue igual, avísanos por WhatsApp.",
        "enlaces": [("Ver los juegos", "juegos")],
        "relacionados": ["error_pagina", "buscador"],
    },
    {
        "id": "buscador",
        "titulo": "El buscador no encuentra nada",
        "palabras": ["buscador", "buscar", "no encuentra", "no encuentro", "busqueda", "sin resultados",
                     "no sale al buscar", "barra de busqueda", "buscando"],
        "respuesta": "El buscador (arriba, en el centro) busca por nombre de paquete, de moneda o de juego. "
                     "Prueba con palabras simples como «robux», «valorant» o «500».\n"
                     "No hace falta escribir tildes ni mayúsculas. Presiona Enter para buscar.\n"
                     "Si no aparece nada, quizá ese paquete está desactivado.",
        "enlaces": [("Ver los juegos", "juegos")],
        "relacionados": ["sin_juegos"],
    },
    {
        "id": "error_pagina",
        "titulo": "Me sale un error o página en blanco",
        "palabras": ["error 404", "no encontrada", "pagina no existe", "no existe la pagina",
                     "no carga la pagina", "pagina en blanco", "error", "no abre la pagina", "no abre",
                     "error 500", "internal server", "error del servidor", "se cayo", "no funciona la pagina",
                     "pagina no funciona", "pantalla blanca", "no carga"],
        "respuesta": "Si la página muestra un error:\n"
                     "• «Página no encontrada» (404): la dirección está mal escrita o ya no existe. "
                     "Vuelve al Inicio con el logo.\n"
                     "• «Internal Server Error» o pantalla en blanco: es un problema del servidor, casi "
                     "siempre la base de datos apagada o mal configurada. Quien administra el sitio debe "
                     "revisar la terminal.\n"
                     "• Prueba recargar con Ctrl + F5.\n"
                     "Si el error se repite, cuéntanos en qué página pasó y envía una captura por WhatsApp.",
        "enlaces": [("Ir al inicio", "inicio"), ("Escribir por WhatsApp", "whatsapp")],
        "relacionados": ["pagina_lenta", "estilos_rotos"],
    },
    {
        "id": "pagina_lenta",
        "titulo": "La página está lenta",
        "palabras": ["lenta", "lento", "tarda en cargar", "se demora", "demora en cargar", "carga lenta",
                     "se pega", "se traba", "no responde", "muy pesada", "tarda mucho"],
        "respuesta": "Si la página va lenta:\n"
                     "• Revisa tu conexión a internet (las fuentes e imágenes se descargan).\n"
                     "• Recarga con Ctrl + F5 y cierra pestañas que no uses.\n"
                     "• Si estás en una exposición, el servidor corre en un computador local y puede "
                     "ir más lento si hay muchas personas conectadas.",
        "enlaces": [],
        "relacionados": ["error_pagina", "estilos_rotos"],
    },
    {
        "id": "estilos_rotos",
        "titulo": "La página se ve rara o sin imágenes",
        "palabras": ["se ve mal", "se ve rar", "sin estilos", "no cargan las imagenes", "imagenes no cargan",
                     "no se ven las imagenes", "sin imagenes", "diseno roto", "colores", "letra",
                     "fuente", "desordenad", "descuadrad", "desconfigurad", "no carga el diseno",
                     "logo no sale", "imagen no sale", "no salen las imagenes", "se ve feo", "sin diseno"],
        "respuesta": "Si el diseño se ve desordenado o faltan imágenes:\n"
                     "• Recarga forzando el caché: Ctrl + F5 (o Ctrl + Shift + R).\n"
                     "• Las letras vienen de Google Fonts y necesitan internet; sin conexión se ve otra "
                     "letra, pero todo funciona.\n"
                     "• Si una portada o un pack no tiene imagen, la página dibuja un icono por defecto.\n"
                     "• Prueba en otro navegador (Chrome o Edge).",
        "enlaces": [],
        "relacionados": ["pagina_lenta", "celular_pc"],
    },
    {
        "id": "celular_pc",
        "titulo": "¿Funciona en el celular?",
        "palabras": ["en el celular", "desde el celular", "movil", "responsive", "se ve en el celular",
                     "app", "aplicacion", "tablet", "desde mi telefono", "en mi telefono"],
        "respuesta": "Sí. La página se adapta al ancho de la pantalla, así que funciona en celular, "
                     "tablet y computador desde el navegador. No hay una aplicación para descargar.\n"
                     "Si algo se ve mal en tu celular, cuéntanos qué pantalla era y con qué navegador.",
        "enlaces": [],
        "relacionados": ["estilos_rotos", "contacto_whatsapp"],
    },
    {
        "id": "opiniones",
        "titulo": "No puedo dejar una opinión",
        "palabras": ["no puedo comentar", "no puedo publicar", "dejar opinion", "dejar una opinion",
                     "comentario no aparece", "mi comentario", "opinion", "opiniones", "comentarios",
                     "calificar", "estrellas", "calificacion", "escribe algo antes",
                     "selecciona una calificacion", "publicar", "comentar", "mi opinion no aparece"],
        "respuesta": "Para dejar una opinión:\n"
                     "1. Inicia sesión (sin sesión solo puedes leer).\n"
                     "2. Elige de 1 a 5 estrellas: es obligatorio.\n"
                     "3. Escribe tu comentario y toca «Publicar».\n"
                     "Tu opinión aparece de inmediato con tu nombre y tu foto. Un administrador puede "
                     "responderla y también moderarla.",
        "enlaces": [("Ir a Opiniones", "comentarios")],
        "relacionados": ["foto_perfil", "sesion_se_cierra"],
    },
    {
        "id": "admin_acceso",
        "titulo": "No puedo entrar al panel de administrador",
        "palabras": ["panel de administrador", "panel admin", "soy administrador", "entrar como admin",
                     "acceso admin", "administrador", "permisos de administrador", "no tiene permisos",
                     "admin", "panel de control", "no veo el panel"],
        "respuesta": "El panel de administración es solo para cuentas con rol de administrador. "
                     "Inicia sesión con tu cuenta de administrador y verás el icono 🛠️ arriba, junto al "
                     "carrito. Si dice «Tu cuenta no tiene permisos de administrador», esa cuenta es de "
                     "cliente normal.",
        "enlaces": [("Iniciar sesión", "login")],
        "relacionados": ["login_problemas"],
    },
    {
        "id": "contacto_whatsapp",
        "titulo": "Contactar por WhatsApp",
        "palabras": ["whatsapp", "contactar", "contacto", "contactarlos", "hablar con alguien",
                     "hablar con una persona", "persona real", "soporte", "atencion al cliente",
                     "telefono de contacto", "numero de whatsapp", "qr", "escribirles", "comunicarme",
                     "asesor", "agente humano", "reclamo", "queja", "ayuda humana", "hablar con un asesor"],
        "respuesta": "Puedes escribirnos por WhatsApp, que es la vía más rápida para reportar un problema:\n"
                     "• En el celular: toca el botón «Escribir por WhatsApp».\n"
                     "• En el computador: escanea el código QR con la cámara de tu celular.\n"
                     "Ten a la mano tu código de pedido y cuéntanos qué pasó.",
        "enlaces": [("Escribir por WhatsApp", "whatsapp"), ("Página de Contacto", "contacto")],
        "imagen": "img/whatsapp-qr.png",
        "relacionados": ["codigo_pedido", "pedido_no_llega"],
    },
    {
        "id": "horario",
        "titulo": "¿Cuál es el horario de atención?",
        "palabras": ["horario", "a que hora", "atienden", "24 horas", "cuando responden",
                     "horas de atencion", "hasta que hora", "estan disponibles"],
        "respuesta": "En la página no hay un horario de atención publicado. Escríbenos por WhatsApp cuando "
                     "lo necesites y te responderemos en cuanto sea posible. Mientras tanto, esta "
                     "ayuda del asistente está disponible siempre.",
        "enlaces": [("Escribir por WhatsApp", "whatsapp")],
        "relacionados": ["contacto_whatsapp"],
    },
    {
        "id": "seguridad",
        "titulo": "¿Es seguro? ¿Qué pasa con mis datos?",
        "palabras": ["es seguro", "es confiable", "seguridad", "datos personales", "mis datos estan seguros",
                     "contrasena segura", "estafa", "confiable", "privacidad", "seguro", "me roban"],
        "respuesta": "Es un proyecto académico y se cuidan los datos así:\n"
                     "• Tu contraseña se guarda cifrada (hash): nadie, ni los administradores, puede verla.\n"
                     "• Del pago solo se guardan el nombre y los últimos 4 dígitos del celular.\n"
                     "• Cada persona solo puede ver sus propios pedidos y certificados.\n"
                     "• El correo se verifica con un código para confirmar que es real.",
        "enlaces": [("Políticas y seguridad", "politicas"), ("Términos y condiciones", "terminos")],
        "relacionados": ["pago_simulado", "proyecto"],
    },
    {
        "id": "redes",
        "titulo": "¿Tienen redes sociales?",
        "palabras": ["instagram", "facebook", "tiktok", "youtube", "redes sociales", "redes", "twitter",
                     "grupo de whatsapp", "canal de whatsapp", "canal"],
        "respuesta": "Sí. Nos encuentras en Instagram (@gamecoinsstoree) y en nuestro canal de "
                     "WhatsApp, donde publicamos novedades. Los dos enlaces están también en el pie "
                     "de la página. Para ayuda personal, escríbenos por WhatsApp.",
        "enlaces": [("Instagram", "instagram"), ("Canal de WhatsApp", "canal"),
                    ("Escribir por WhatsApp", "whatsapp")],
        "relacionados": ["contacto_whatsapp"],
    },
    {
        "id": "juegos_disponibles",
        "titulo": "¿Qué juegos y monedas hay?",
        "palabras": ["que juegos", "juegos disponibles", "que monedas", "que paquetes", "que venden",
                     "que ofrecen", "que puedo comprar", "robux", "valorant points", "vp", "roblox",
                     "valorant", "precios", "cuanto cuesta", "cuanto vale", "paquetes disponibles",
                     "que vendes"],
        "respuesta": "Vendemos monedas para dos juegos:\n"
                     "• Roblox → Robux\n"
                     "• VALORANT → VALORANT Points (VP)\n"
                     "Cada juego tiene varios paquetes con su precio en pesos colombianos (COP); "
                     "algunos tienen descuento por tiempo limitado.",
        "enlaces": [("Ver los juegos", "juegos"), ("Ver promociones", "promociones")],
        "relacionados": ["como_comprar", "promo_no_aplica"],
    },
    {
        "id": "politicas",
        "titulo": "Términos, políticas y preguntas frecuentes",
        "palabras": ["terminos", "condiciones", "politicas", "preguntas frecuentes", "faq",
                     "reglas", "normas"],
        "respuesta": "Aquí tienes las páginas informativas de la tienda.",
        "enlaces": [("Preguntas frecuentes", "faq"), ("Términos y condiciones", "terminos"),
                    ("Políticas y seguridad", "politicas")],
        "relacionados": ["seguridad", "contacto_whatsapp"],
    },
    {
        "id": "proyecto",
        "titulo": "¿Qué es esta página?",
        "palabras": ["que es esta pagina", "quienes son", "quienes somos", "proyecto", "sena",
                     "de que trata", "para que sirve esta pagina", "que es gamecoins", "que es gcs",
                     "quien creo", "quien hizo"],
        "respuesta": "GameCoins Store es un proyecto académico del SENA: una tienda web para recargar "
                     "Robux y VALORANT Points, con pago simulado por Nequi, carrito, certificado de compra "
                     "en PDF, opiniones y un panel de administración. Fue hecha con Flask y PostgreSQL.",
        "enlaces": [("Ir al inicio", "inicio")],
        "relacionados": ["pago_simulado", "como_comprar"],
    },

    # ------------------------------------------------------------
    # CONVERSACIÓN GENERAL (van al final: ganan solo si no hay otro tema)
    # ------------------------------------------------------------
    {
        "id": "ayuda",
        "titulo": "¿Qué puedes hacer?",
        "palabras": ["que puedes hacer", "en que me ayudas", "ayuda", "ayudame", "opciones", "menu",
                     "que haces", "como funcionas", "quien eres", "necesito ayuda", "tengo un problema",
                     "problema"],
        "respuesta": "Puedo ayudarte con problemas de la página: cuenta y código del correo, contraseña, "
                     "carrito, pago con Nequi, pedidos, certificado en PDF y más. "
                     "Escribe tu duda con tus palabras o toca una de las opciones.",
        "enlaces": [],
        "relacionados": ["codigo_no_llega", "como_comprar", "pedido_no_llega", "certificado_correo",
                         "login_problemas", "contacto_whatsapp"],
    },
    {
        "id": "saludo",
        "titulo": "Hola",
        "palabras": ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey", "saludos",
                     "ola"],
        "respuesta": "¡Hola! 👋 Soy el asistente de GameCoins Store. Cuéntame qué problema tienes con la "
                     "página y te ayudo.",
        "enlaces": [],
        "relacionados": ["codigo_no_llega", "como_comprar", "pedido_no_llega", "certificado_correo",
                         "olvide_contrasena", "contacto_whatsapp"],
    },
    {
        "id": "gracias",
        "titulo": "Gracias",
        "palabras": ["gracias", "muchas gracias", "te agradezco", "genial", "excelente", "chao", "adios",
                     "hasta luego", "nos vemos"],
        "respuesta": "¡Con gusto! 😊 Si te surge otra duda, aquí estaré.",
        "enlaces": [],
        "relacionados": ["contacto_whatsapp"],
    },
]


# ============================================================
# 2. MENSAJES ESPECIALES
# ============================================================

# Lo primero que se muestra al abrir la burbuja
INICIO = {
    "id": "inicio",
    "titulo": "Inicio",
    "respuesta": "¡Hola! 👋 Soy el asistente de GameCoins Store. Te ayudo con los problemas más comunes "
                 "de la página. Toca una opción o escribe tu duda.",
    "enlaces": [],
    "relacionados": ["codigo_no_llega", "como_comprar", "pedido_no_llega", "certificado_correo",
                     "olvide_contrasena", "contacto_whatsapp"],
}

# Cuando ningún tema coincide con lo que escribió la persona
NO_ENTENDI = {
    "id": "no_entendi",
    "titulo": "No entendí",
    "respuesta": "No estoy seguro de haber entendido 🤔. Prueba con otras palabras (por ejemplo "
                 "«no me llega el código» o «mi pedido no llegó») o elige una de estas opciones. "
                 "Si prefieres, puedes escribirnos por WhatsApp.",
    "enlaces": [("Escribir por WhatsApp", "whatsapp")],
    "relacionados": ["codigo_no_llega", "como_comprar", "pedido_no_llega", "certificado_correo",
                     "login_problemas", "error_pagina"],
}


# ============================================================
# 3. FUNCIONES
# ============================================================

def normalizar(texto):
    """
    Deja el texto en minúscula, sin tildes y sin símbolos raros, para poder compararlo.
    'Mi CÓDIGO no llegó!!' -> ' mi codigo no llego '
    (el espacio del principio y del final ayuda a buscar palabras completas)
    """
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(letra for letra in texto if unicodedata.category(letra) != "Mn")   # quita tildes
    texto = re.sub(r"[^a-z0-9#\- ]", " ", texto)         # deja letras, números, # y -
    return " " + " ".join(texto.split()) + " "           # un solo espacio entre palabras


# Palabras que significan lo mismo: antes de buscar, el mensaje se "traduce" a la palabra
# que usamos en las palabras clave (así "clave" y "password" cuentan como "contrasena").
SINONIMOS = {
    "clave": "contrasena", "claves": "contrasena", "password": "contrasena", "pasword": "contrasena",
    "mail": "correo", "email": "correo", "gmail": "correo", "hotmail": "correo",
    "reenvio": "reenviar", "reenvia": "reenviar", "reenvian": "reenviar", "reenviame": "reenviar",
    "cambio": "cambiar", "cambie": "cambiar", "cambiarla": "cambiar", "cambiarlo": "cambiar",
    "cel": "celular", "celu": "celular",
    "mandar": "enviar", "mandan": "enviar", "mandaron": "enviar", "manda": "enviar",
}


def tema_por_id(tema_id):
    """Busca un tema por su id. Devuelve None si no existe."""
    if tema_id == INICIO["id"]:
        return INICIO
    for tema in TEMAS:
        if tema["id"] == tema_id:
            return tema
    return None


def responder(mensaje):
    """
    Recibe lo que escribió la persona y devuelve el tema que mejor le responde.
    Cada palabra clave que aparece suma tantos puntos como palabras tenga
    ("no llega el codigo" vale 4, "codigo" vale 1). Gana el tema con más puntos.
    """
    texto = normalizar(mensaje)
    palabras_del_mensaje = [SINONIMOS.get(palabra, palabra) for palabra in texto.split()]
    texto = " " + " ".join(palabras_del_mensaje) + " "

    mejor_tema = None
    mejor_puntaje = 0

    for tema in TEMAS:
        puntaje = 0
        for palabra in tema["palabras"]:
            # " " + palabra: la palabra clave debe EMPEZAR una palabra del mensaje
            # (así "llega" también encuentra "llegan", "llegó"...)
            if " " + palabra in texto:
                puntaje += len(palabra.split())
        if puntaje > mejor_puntaje:        # con ">" gana el primero de la lista si hay empate
            mejor_puntaje = puntaje
            mejor_tema = tema

    if mejor_tema is None:
        return NO_ENTENDI
    return mejor_tema
