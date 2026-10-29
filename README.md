# GameCoins Store (GCS)

Tienda web (proyecto académico, sin cobros reales) para comprar Robux y
VALORANT Points en pesos colombianos. Hecha con **Flask + PostgreSQL**.
El pago es una simulación con Nequi.

## Qué hace el sitio
- **Usuario:** registro e inicio de sesión, catálogo por juego, buscador,
  promociones, carrito, compra con pago simulado (Nequi), historial de
  pedidos, certificado de compra en PDF, comentarios con estrellas, perfil
  (datos, foto y contraseña) y páginas de contacto, FAQ, políticas y términos.
- **Administrador** (cuenta con rol `ADMIN`, entra por el mismo login):
  panel con estadísticas, gestión de juegos, paquetes, promociones,
  ventas (cambiar estado; al marcar ENTREGADO o CANCELADO se envía el correo al cliente), usuarios, comentarios y registro de auditoría.

## Archivos del proyecto
```
gamecoins_store/
├── app.py              Rutas del sitio para los usuarios
├── admin.py            Rutas del panel de administrador (/admin)
├── db.py               Todas las consultas a PostgreSQL
├── imagenes.py         Subir y borrar imágenes
├── fechas.py           Convierte fechas en "Hoy", "Ayer", "Hace 1 semana"
├── pdf_certificado.py  Genera el certificado en PDF
├── config.py           Contraseña de la base de datos, clave secreta, correo y número de WhatsApp
├── correo.py           Envío de correos (código de verificación y certificado)
├── asistente.py        Respuestas del asistente de la burbuja (por reglas, sin IA)
├── generar_qr.py       Crea el código QR de WhatsApp (static/img/whatsapp-qr.png)
├── requirements.txt    Librerías que hay que instalar
├── database/
│   ├── schema.sql           Crea las tablas
│   └── datos_iniciales.sql  Juegos, paquetes, promociones y el administrador
├── templates/          Páginas HTML (base.html = encabezado y pie)
│   └── admin/          Páginas del panel de administrador
└── static/             CSS e imágenes
```

## Instalación desde cero
1. **Librerías** (terminal de VS Code, dentro de la carpeta del proyecto):
   `pip install flask psycopg2-binary reportlab`
2. **Base de datos** (SQL Shell / psql):
   ```sql
   CREATE DATABASE gamecoins_store;
   \c gamecoins_store
   \i 'C:/RUTA/gamecoins_store/database/schema.sql'
   \i 'C:/RUTA/gamecoins_store/database/datos_iniciales.sql'
   ```
   (usa `/` en la ruta, no `\`)
3. **Contraseña:** en `config.py` cambia `TU_CONTRASENA_DE_POSTGRES` por la de tu PostgreSQL.
4. **Ejecutar:** `python app.py` y abrir http://127.0.0.1:5000

Cuenta de administrador: `admin@gamecoins.com` / `Admin123!`

## Guía para exponer el código

**Idea general:** el navegador pide una dirección → una *ruta* de Flask la
atiende → llama a una función de `db.py` que hace la consulta SQL → el
resultado se envía a una *plantilla* HTML que lo muestra.

| Tema | Dónde está | Qué explicar |
|---|---|---|
| Rutas | `app.py` | `@app.route("/ruta")` + una función que devuelve una página |
| Base de datos | `db.py` | 3 ayudantes: `consultar` (SELECT), `ejecutar` (INSERT/UPDATE/DELETE) e `insertar` (devuelve el id nuevo) |
| Seguridad de contraseñas | `registro()` y `login()` | `generate_password_hash` guarda la contraseña cifrada; `check_password_hash` la compara |
| Sesión y roles | `login()` y `admin_requerido` | La sesión guarda `usuario_id` y `rol`; el decorador deja entrar a `/admin` solo si el rol es ADMIN |
| Consultas seguras | `db.py` | Los `%s` evitan la inyección SQL |
| Carrito | `app.py` sección 4 | Cada usuario tiene un carrito `ACTIVO`; si repites un paquete, solo sube la cantidad |
| Compra simulada | `validar_checkout` y `checkout` | Se validan los datos; solo se guardan los últimos 4 dígitos del celular |
| Promociones | `db.py` (`PROMOCION_ACTIVA`) | Un `LEFT JOIN` trae el descuento si hoy está vigente |
| Certificado PDF | `pdf_certificado.py` | La librería reportlab arma el PDF |
| Fechas relativas y buscador por fecha | `fechas.py`, `fechas_del_filtro` en `admin.py` | El filtro `|hace` muestra "Hoy/Ayer/Hace 1 semana"; el buscador usa `?desde=` y `?hasta=` en la dirección |
| Perfil con pestañas | `perfil()` en `app.py` y `perfil.html` | La pestaña se elige con `?tab=perfil`, `?tab=pedidos` o `?tab=datos`; el botón del encabezado lleva a esta página |
| Desactivar vs. eliminar | `cambiar_estado_*` y `eliminar_paquete` en `db.py` | Desactivar oculta el paquete o promoción a los usuarios; eliminar lo borra de verdad (un paquete con compras no se puede eliminar) |
| Respuestas a comentarios | `comentario_responder` en `admin.py` | Se guarda en `comentario.respuesta_admin` y se muestra en la página de opiniones |
| Panel admin | `admin.py` | Un *Blueprint* agrupa las rutas `/admin`; cada acción queda en la auditoría |
| Borrado suave | `cambiar_estado_*` en `db.py` | "Eliminar" = desactivar, para no perder el historial de compras |


## Envío de correos (certificado y verificación del correo)

La página envía dos correos: el **código de verificación** al registrarse (para comprobar que el correo es real)
y el **certificado de compra en PDF** después de cada compra. Se usa una cuenta de Gmail del proyecto:

1. En esa cuenta de Gmail activa la **verificación en dos pasos** (Cuenta de Google → Seguridad).
2. En Seguridad busca **Contraseñas de aplicaciones**, crea una llamada "GameCoins" y copia la clave de 16 letras.
3. Abre `config.py` y completa:
   ```python
   MAIL_USUARIO = "tucorreo@gmail.com"
   MAIL_CLAVE = "abcdefghijklmnop"   # la clave de aplicación, NO tu contraseña normal
   ```
4. Reinicia Flask. Si `MAIL_USUARIO` queda vacío, la página funciona igual pero no envía correos
   (y el registro crea la cuenta sin pedir código).

| Archivo | Qué hace |
|---|---|
| `correo.py` | Arma y envía los correos con `smtplib` (código de verificación y certificado con PDF adjunto) |
| `pdf_certificado.py` | Dibuja el PDF del certificado con reportlab |
| `app.py` → `verificar_correo()` | Pide el código de 6 números y crea la cuenta |
| `app.py` → `enviar_certificado_por_correo()` | Se llama al terminar la compra y desde el botón "Enviar certificado a mi correo" |

## Contacto por WhatsApp: botón y código QR

- En **celular** se usa el botón «Escribir por WhatsApp» (abre el chat con el mensaje ya escrito).
- En **computador** la página Contacto muestra además un **código QR**: se escanea con la cámara del celular
  y abre el mismo chat. En pantallas pequeñas el QR se oculta (CSS `@media`).
- El número y el mensaje están en `config.py` (`WHATSAPP_NUMERO`, `WHATSAPP_MENSAJE`). Si los cambias, crea el QR
  de nuevo con `python generar_qr.py` (no hay que instalar nada: usa reportlab y Pillow).

## Asistente de ayuda (burbuja abajo a la derecha)

Es un asistente **por reglas**, no una inteligencia artificial: cada tema tiene palabras clave y una respuesta
escrita de antemano. Funciona sin internet y sin costo.

| Archivo | Qué hace |
|---|---|
| `asistente.py` | Lista `TEMAS` (palabras clave + respuesta + botones) y la función `responder()` que elige el tema con más coincidencias |
| `app.py` → `responder_asistente()` | Ruta `POST /asistente`: recibe la pregunta y devuelve la respuesta en JSON |
| `templates/_asistente.html` | La burbuja, la ventana del chat y el JavaScript (`fetch`) |
| `static/css/style.css` | Estilos `.gcs-asistente*` (al final del archivo) |

**Para agregar una respuesta nueva:** copia un bloque de `TEMAS` en `asistente.py`, cambia el `id`, el `titulo`,
las `palabras` (en minúscula y sin tildes) y la `respuesta`. No hay que tocar nada más.


## Olvidé mi contraseña (código por correo)
- En el login, «¿Olvidaste la contraseña?» lleva a `/recuperar`: se escribe el correo y se envía un código de 6 números.
- En `/recuperar/codigo` se escribe el código y la contraseña nueva. El código vence en 10 minutos y tiene 5 intentos.
- Si el correo no tiene cuenta, la página responde igual (así nadie descubre qué correos están registrados).
- Necesita `MAIL_USUARIO` y `MAIL_CLAVE` en `config.py`; sin ellos muestra un aviso y manda a WhatsApp.
- Archivos: rutas en `app.py`, `enviar_codigo_recuperacion()` en `correo.py`, plantillas `recuperar.html` y `recuperar_codigo.html`.

## Redes sociales
Los enlaces de Instagram y del canal de WhatsApp están en `config.py` (`INSTAGRAM_URL`, `WHATSAPP_CANAL_URL`) y se ven en el pie de página.

## Ventas y correos del pedido
- En el panel de admin, la sección «Compras» ahora se llama **Ventas** (`/admin/ventas`).
- Al comprar NO se envía correo: el pedido queda PROCESADO.
- Cuando el admin cambia el estado a **ENTREGADO**, el cliente recibe el correo con el certificado en PDF; a **CANCELADO**, un correo de aviso. Si guarda el mismo estado otra vez, no se repite el correo.
- El cliente solo puede descargar o reenviarse el certificado cuando el pedido está ENTREGADO.
- Archivos: `venta_estado()` en `admin.py`, `servicio_pedido.py` (arma el PDF y decide qué correo) y `enviar_pedido_entregado()` / `enviar_pedido_cancelado()` en `correo.py`.

## Stock de los paquetes (agotado y rellenar)
- Cada paquete tiene una columna `stock` (por defecto 10 unidades). Cada compra confirmada descuenta unidades; en 0 el paquete sale **AGOTADO** y no se puede agregar al carrito. Con 5 o menos se ve «Quedan N».
- En el carrito el botón «+» se bloquea al llegar al stock, y el checkout vuelve a revisar el stock antes de cobrar (si alguien compró la última unidad antes, avisa).
- Panel de admin → Paquetes: columna Stock con el desplegable **＋ Rellenar** (escribes cuántas unidades sumar; el stock no se reinicia al recargar) y el campo Stock en Editar/Nuevo paquete.
- Si se cancela una venta, sus unidades vuelven al stock; si se reactiva y no alcanzan, no deja.
- Si ya tenían la base de datos creada, ejecuten una vez `database/actualizar_stock.sql` en SQL Shell (o vuelvan a correr `schema.sql`).
- Archivos: `descontar_stock`, `devolver_stock`, `rellenar_stock` en `db.py`; `paquete_rellenar` en `admin.py`.

## Total de dinero en Ventas
- Al final de la página Ventas hay tarjetas con: **Entregado** (suma al total), **Cancelado** (se muestra en rojo y no cuenta), **Procesado** (aún no cuenta) y el **TOTAL DE DINERO**, que es solo la suma de los pedidos entregados.
- Respeta el filtro de fechas. El «Ventas totales» del dashboard usa la misma regla.
- Código: `ventas()` en `admin.py` y `obtener_estadisticas` en `db.py`.
