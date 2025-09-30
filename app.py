from flask import Flask, render_template, redirect, url_for, flash, request, session, make_response
import traceback
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from flask import jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from functools import wraps  # ¡IMPORTANTE! Agregar esta importación

# Importaciones opcionales con manejo de errores
CLIENTE_DISPONIBLE = False
DAO_DISPONIBLE = False
FORMA_DISPONIBLE = False

try:
    from cliente import Cliente
    CLIENTE_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar Cliente: {e}")

try:
    from cliente_dao import ClienteDAO
    DAO_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar ClienteDAO: {e}")

try:
    from cliente_forma import ClienteForma
    FORMA_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar ClienteForma: {e}")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'llave_secreta_123'
app.config['SESSION_TYPE'] = 'filesystem'

# ------------------ CONFIGURACION SUBIDA DE ARCHIVOS ------------------
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

titulo_app = 'Bienvenido a'

# ------------------ CONEXIÓN MYSQL ------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="api_python"
    )

# ------------------ DECORADOR LOGIN_REQUIRED CORREGIDO ------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------ RUTA PARA ACTUALIZAR PERFIL ------------------
@app.route('/actualizar_perfil', methods=['POST'])
def actualizar_perfil():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para actualizar tu perfil', 'error')
        return redirect(url_for('login'))

    try:
        usuario_id = session.get('user_id')
        telefono = request.form.get('phone')
        direccion = request.form.get('address')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET telefono = %s, direccion = %s WHERE id = %s",
            (telefono, direccion, usuario_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash('Perfil actualizado correctamente', 'success')
    except Exception as e:
        flash(f'Error al actualizar perfil: {str(e)}', 'error')

    return redirect(url_for('perfil'))


# ------------------ LOGIN ------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Limpiar sesión existente al acceder al login
    if request.method == 'GET':
        session.clear()

    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        contrasena = request.form.get('contrasena', '').strip()

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (usuario,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user and check_password_hash(user['password'], contrasena):
                # Establecer marca de tiempo de la sesión
                session['usuario'] = user['usuario']
                session['rol'] = user['rol']
                session['user_id'] = user['id']
                session['login_time'] = datetime.now().isoformat()
                session['session_id'] = os.urandom(16).hex()  # ID único de sesión

                flash(f'Bienvenido {user["usuario"]}', 'success')

                if user['rol'] == 'administrador':
                    return redirect(url_for('pagina2'))
                else:
                    return redirect(url_for('perfil'))
            else:
                flash('Usuario o contraseña incorrectos', 'error')

        except Exception as e:
            app.logger.error(f"Error en login con MySQL: {str(e)}")
            if usuario == 'admin' and contrasena == '1234':
                session.clear()
                session['usuario'] = usuario
                session['rol'] = 'administrador'
                session['user_id'] = 1
                session['login_time'] = datetime.now().isoformat()
                session['session_id'] = os.urandom(16).hex()
                flash(f'Bienvenido {usuario}', 'success')
                return redirect(url_for('pagina2'))
            else:
                flash('Error en el login o usuario inválido', 'error')

    # Configurar headers para no cachear la página de login
    response = make_response(render_template('login.html', titulo='Login - ' + titulo_app))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# ---------- RUTA REGISTRO ----------
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        try:
            usuario = request.form.get('usuario', '').strip()
            correo = request.form.get('correo', '').strip()
            contrasena = request.form.get('contrasena', '').strip()
            confirmar = request.form.get('confirmar', '').strip()
            rol = request.form.get('rol', 'usuario')

            if not usuario or not correo or not contrasena:
                flash("Todos los campos son obligatorios", "error")
                return redirect(url_for('registro'))

            if contrasena != confirmar:
                flash("Las contraseñas no coinciden", "error")
                return redirect(url_for('registro'))

            hashed_pass = generate_password_hash(contrasena)

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM usuarios WHERE usuario = %s OR correo = %s", (usuario, correo))
            if cursor.fetchone():
                flash("El usuario o correo ya existe", "error")
                return redirect(url_for('registro'))

            cursor.execute(
                "INSERT INTO usuarios (usuario, correo, password, rol) VALUES (%s, %s, %s, %s)",
                (usuario, correo, hashed_pass, rol)
            )
            conn.commit()
            cursor.close()
            conn.close()

            flash("Registro exitoso, ahora puedes iniciar sesión", "success")
            return redirect(url_for('login'))

        except Exception as e:
            flash(f"Error en el registro: {str(e)}", "error")

    return render_template('registro.html')

# ---------- RUTA TIENDA ----------
@app.route('/tienda')
@login_required  # Ahora funcionará correctamente
def tienda():
    # La verificación de rol se mantiene como lógica adicional
    if session.get('rol') != 'usuario':
        flash('Debes iniciar sesión como usuario para acceder a la tienda', 'error')
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM productos")
        productos = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f"Error al obtener productos: {str(e)}", "error")
        productos = []

    return render_template('tienda.html', titulo=titulo_app, productos=productos)

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    # Destruir completamente la sesión
    session.clear()
    flash('Sesión cerrada correctamente', 'info')

    # Redirigir a login con headers para evitar cache
    response = redirect(url_for('login'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# ------------------ RUTAS PRINCIPALES ------------------
@app.route('/')
@app.route('/index.html')
def inicio():
    try:
        return render_template('index.html', titulo=titulo_app)
    except Exception as e:
        app.logger.error(f'Error en inicio(): {str(e)}')
        app.logger.error(traceback.format_exc())
        return f"<h1>Error en Gaming Zone</h1><p>{str(e)}</p><a href='/pagina2'>Ir al Gimnasio</a>", 500

@app.route('/pagina2')
@app.route('/gimnasio')
@login_required  # Ahora funcionará correctamente
def pagina2():
    try:
        # El decorador @login_required ya verifica la sesión, pero mantenemos la verificación de rol
        if session.get('rol') != 'administrador':
            flash('Acceso denegado: Solo para administradores.', 'error')
            return redirect(url_for('inicio'))

        # Manejar edición si se pasa un ID por parámetro
        cliente_editar_id = request.args.get('editar')
        cliente_editar = None

        if cliente_editar_id and DAO_DISPONIBLE:
            cliente_editar = ClienteDAO.seleccionar_por_id(int(cliente_editar_id))

        if DAO_DISPONIBLE:
            clientes_db = ClienteDAO.seleccionar() or []
        else:
            clientes_db = []

        cliente = None
        cliente_forma = None

        if CLIENTE_DISPONIBLE:
            cliente = cliente_editar if cliente_editar else Cliente()

        if FORMA_DISPONIBLE:
            cliente_forma = ClienteForma(obj=cliente)

        return render_template('pagina2.html',
                               titulo=titulo_app,
                               clientes=clientes_db,
                               forma=cliente_forma,
                               usuario=session.get('usuario'))
    except Exception as e:
        app.logger.error(f'Error en pagina2(): {str(e)}')
        app.logger.error(traceback.format_exc())
        return f"<h1>Error en Sistema Gimnasio</h1><p>{str(e)}</p><p><a href='/'>Volver al Gaming Zone</a></p>", 500

# ---------- RUTA ESTADISTICAS ----------
@app.route('/estadisticas')
@login_required  # Ahora funcionará correctamente
def estadisticas():
    try:
        if DAO_DISPONIBLE:
            clientes_db = ClienteDAO.seleccionar() or []
        else:
            clientes_db = []

        return render_template('estadisticas.html',
                               titulo=titulo_app,
                               clientes=clientes_db,
                               usuario=session.get('usuario'))
    except Exception as e:
        app.logger.error(f'Error en estadisticas(): {str(e)}')
        return f"<h1>Error en Estadísticas</h1><p>{str(e)}</p><p><a href='/'>Volver al Gaming Zone</a></p>", 500

# ---------- RUTA ACERCA ----------
@app.route('/acerca')
def acerca():
    return render_template('acerca.html', titulo=titulo_app)

# ---------- CRUD CLIENTES ----------
@app.route('/guardar', methods=['POST'])
@login_required  # Agregado para consistencia
def guardar_cliente():
    if session.get('rol') != 'administrador':
        flash('Acceso denegado', 'error')
        return redirect(url_for('login'))

    try:
        if not CLIENTE_DISPONIBLE or not DAO_DISPONIBLE:
            flash('Funcionalidad no disponible', 'error')
            return redirect(url_for('pagina2'))

        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        membresia = float(request.form.get('membresia', 0))

        cliente = Cliente(nombre=nombre, apellido=apellido, membresia=membresia)
        filas_afectadas = ClienteDAO.insertar(cliente)

        if filas_afectadas > 0:
            flash(f'Cliente {nombre} {apellido} agregado correctamente', 'success')
        else:
            flash('Error al guardar el cliente', 'error')

    except Exception as e:
        flash(f'Error al guardar cliente: {str(e)}', 'error')

    return redirect(url_for('pagina2'))

# RUTA ELIMINAR CLIENTE - CORREGIDA
@app.route('/eliminar/<int:id>', methods=['POST'])
@login_required  # Agregado para consistencia
def eliminar_cliente(id):
    if session.get('rol') != 'administrador':
        flash('Acceso denegado', 'error')
        return redirect(url_for('login'))

    try:
        if not DAO_DISPONIBLE:
            flash('Funcionalidad no disponible', 'error')
            return redirect(url_for('pagina2'))

        cliente = ClienteDAO.seleccionar_por_id(id)
        if not cliente:
            flash('Cliente no encontrado', 'error')
        else:
            filas_afectadas = ClienteDAO.eliminar(cliente)
            if filas_afectadas > 0:
                flash(f'Cliente {cliente.nombre} {cliente.apellido} eliminado', 'success')
            else:
                flash('No se pudo eliminar el cliente', 'error')

    except Exception as e:
        flash(f'Error al eliminar cliente: {str(e)}', 'error')

    return redirect(url_for('pagina2'))

@app.route('/actualizar', methods=['POST'])
@login_required  # Agregado para consistencia
def actualizar_cliente():
    if session.get('rol') != 'administrador':
        flash('Acceso denegado: Solo para administradores.', 'error')
        return redirect(url_for('inicio'))

    try:
        # Obtener datos del formulario
        cliente_id = request.form.get('id')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        membresia = request.form.get('membresia')

        print(f"Actualizando cliente - ID: {cliente_id}, Nombre: {nombre}")

        # Validaciones básicas
        if not all([cliente_id, nombre, apellido, membresia]):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('pagina2'))

        # Convertir tipos
        cliente_id = int(cliente_id)
        membresia = float(membresia)

        # Aquí va tu lógica para actualizar en la base de datos
        # Si usas ClienteDAO:
        if DAO_DISPONIBLE and CLIENTE_DISPONIBLE:
            cliente = Cliente(id=cliente_id, nombre=nombre, apellido=apellido, membresia=membresia)
            filas_afectadas = ClienteDAO.actualizar(cliente)

            if filas_afectadas > 0:
                flash(f'Cliente {nombre} {apellido} actualizado correctamente', 'success')
            else:
                flash('No se pudo actualizar el cliente', 'error')
        else:
            flash('Funcionalidad de actualización no disponible', 'error')

    except Exception as e:
        print(f"Error al actualizar cliente: {e}")
        flash(f'Error al actualizar cliente: {str(e)}', 'error')

    return redirect(url_for('pagina2'))

# ---------- RUTAS PRODUCTOS ----------
@app.route('/admin/productos')
@login_required  # Agregado
def admin_productos():
    if session.get('rol') == 'administrador':
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM productos")
            productos = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            flash(f"Error al cargar productos: {str(e)}", "error")
            productos = []
        return render_template('admin_productos.html', titulo="Panel Admin", productos=productos)
    else:
        flash('Acceso denegado: Solo administradores', 'error')
        return redirect(url_for('inicio'))

# ---------- GUARDAR PRODUCTO CON IMAGEN ----------
@app.route('/guardar_producto', methods=['POST'])
@login_required  # Agregado
def guardar_producto():
    if session.get('rol') == 'administrador':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']

        if not nombre or not precio:
            flash('Nombre y precio son obligatorios', 'error')
            return redirect(url_for('admin_productos'))

        file = request.files['imagen']
        filename = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
        elif file:
            flash('Tipo de archivo no permitido', 'error')
            return redirect(url_for('admin_productos'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO productos (nombre, descripcion, precio, imagen) VALUES (%s,%s,%s,%s)",
                (nombre, descripcion, precio, filename)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Producto agregado correctamente', 'success')
        except Exception as e:
            flash(f'Error al agregar producto: {e}', 'error')

        return redirect(url_for('admin_productos'))
    else:
        flash('Acceso denegado: Solo administradores', 'error')
        return redirect(url_for('inicio'))

@app.route('/agregar_carrito', methods=['POST'])
@login_required  # Agregado
def agregar_carrito():
    usuario_id = session.get('user_id')
    if not usuario_id:
        flash('Error de sesión, por favor inicia sesión nuevamente', 'error')
        return redirect(url_for('login'))

    producto_id = request.form.get('producto_id')
    cantidad = int(request.form.get('cantidad', 1))

    if cantidad < 1:
        flash('Cantidad inválida', 'error')
        return redirect(url_for('tienda'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, precio FROM productos WHERE id = %s", (producto_id,))
        producto = cursor.fetchone()

        if not producto:
            flash('Producto no encontrado', 'error')
            return redirect(url_for('tienda'))

        precio_unitario = producto['precio']
        total = precio_unitario * cantidad

        cursor.execute("""
                       INSERT INTO transacciones (usuario_id, producto_id, cantidad, total)
                       VALUES (%s, %s, %s, %s)
                       """, (usuario_id, producto_id, cantidad, total))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Producto agregado a tu historial de compras', 'success')
    except Exception as e:
        flash(f'Error al agregar producto: {str(e)}', 'error')

    return redirect(url_for('perfil'))

@app.route('/perfil')
@login_required  # Ahora funcionará correctamente
def perfil():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM usuarios WHERE id = %s", (session.get('user_id'),))
        usuario = cursor.fetchone()

        cursor.execute("""
                       SELECT t.id, t.cantidad, t.total, t.fecha, p.nombre, p.descripcion, p.imagen
                       FROM transacciones t
                                JOIN productos p ON t.producto_id = p.id
                       WHERE t.usuario_id = %s
                       ORDER BY t.id DESC
                       """, (session.get('user_id'),))
        compras = cursor.fetchall()

        cursor.execute("SELECT * FROM productos")
        productos = cursor.fetchall()

        cursor.close()
        conn.close()
    except Exception as e:
        flash(f"Error al obtener perfil: {str(e)}", "error")
        usuario, compras, productos = {}, [], []

    return render_template("perfil.html", titulo="Mi Perfil", usuario=usuario, compras=compras, productos=productos)

# ---------- RUTA PARA ELIMINAR COMPRA (CORREGIDA) ----------
@app.route('/eliminar_compra/<int:compra_id>', methods=['POST'])
@login_required
def eliminar_compra(compra_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT usuario_id FROM transacciones WHERE id = %s", (compra_id,))
        compra = cursor.fetchone()

        if compra and compra[0] == session.get('user_id'):
            cursor.execute("DELETE FROM transacciones WHERE id = %s", (compra_id,))
            conn.commit()
            flash("Compra eliminada correctamente", "success")
        else:
            flash("No tienes permisos para eliminar esta compra", "error")

        cursor.close()
        conn.close()
    except Exception as e:
        flash(f"Error al eliminar la compra: {str(e)}", "error")

    return redirect(url_for('perfil'))

# ---------- RUTA PARA ELIMINAR PRODUCTO ----------
@app.route('/admin/productos/eliminar/<int:id>', methods=['POST'])
@login_required  # Agregado
def eliminar_producto(id):
    if session.get('rol') == 'administrador':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Primero eliminar las transacciones relacionadas con este producto
            cursor.execute("DELETE FROM transacciones WHERE producto_id = %s", (id,))

            # Luego eliminar el producto
            cursor.execute("DELETE FROM productos WHERE id = %s", (id,))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Producto eliminado correctamente', 'success')

            # Si es una solicitud AJAX, devolver JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Producto eliminado correctamente'})

        except Exception as e:
            flash(f'Error al eliminar producto: {str(e)}', 'error')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': f'Error al eliminar producto: {str(e)}'})

        return redirect(url_for('admin_productos'))
    else:
        flash('Acceso denegado: Solo administradores', 'error')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Acceso denegado'})
        return redirect(url_for('inicio'))

# ---------- RUTA PARA ENVIAR CORREOS MASIVOS ----------
@app.route('/admin/enviar-correos-masivos', methods=['POST'])
@login_required  # Agregado
def enviar_correos_masivos():
    if session.get('rol') != 'administrador':
        return jsonify({'success': False, 'message': 'Acceso denegado: Solo administradores'}), 403

    try:
        # Obtener datos del request
        data = request.get_json()
        asunto = data.get('asunto', 'Nuevas Ofertas y Productos Disponibles')
        mensaje = data.get('mensaje', 'HAY NUEVAS OFERTAS Y NUEVOS PRODUCTOS NO TE LOS PIERDAS')

        # CORRECCIÓN: Limpiar caracteres problemáticos temporalmente
        asunto = asunto.replace('ñ', 'n').replace('Ñ', 'N')
        mensaje = mensaje.replace('ñ', 'n').replace('Ñ', 'N')

        # Obtener usuarios
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT correo, usuario FROM usuarios WHERE correo IS NOT NULL AND correo != ''")
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()

        if not usuarios:
            return jsonify({'success': False, 'message': 'No hay usuarios registrados con correos electrónicos'})

        # Configuración SMTP
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_user = "nicolasbarajastru@gmail.com"
        smtp_password = "xeldisybazgcvuvp"

        correos_enviados = []
        correos_fallidos = []

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)

            for usuario in usuarios:
                try:
                    # Crear mensaje NUEVO en cada iteración
                    msg = MIMEMultipart('alternative')
                    msg['From'] = smtp_user
                    msg['To'] = usuario['correo']
                    msg['Subject'] = asunto

                    html_message = f"""
                    <html>
                    <body>
                        <h2>Nuevas Ofertas en Nuestro Gimnasio!</h2>
                        <p>{mensaje}</p>
                        <p>Visita nuestro sitio para conocer todos los nuevos productos y promociones disponibles.</p>
                        <br>
                        <p>Saludos,<br>El equipo del Gimnasio</p>
                    </body>
                    </html>
                    """

                    part = MIMEText(html_message, 'html')
                    msg.attach(part)

                    server.send_message(msg)
                    correos_enviados.append(usuario['correo'])
                    print(f"Correo enviado a: {usuario['correo']}")

                except Exception as e:
                    correos_fallidos.append({'correo': usuario['correo'], 'error': str(e)})
                    print(f"Error enviando a {usuario['correo']}: {str(e)}")

            server.quit()

        except Exception as e:
            return jsonify({'success': False, 'message': f'Error de conexión SMTP: {str(e)}'}), 500

        return jsonify({
            'success': True,
            'message': f'Correos enviados: {len(correos_enviados)}, Fallidos: {len(correos_fallidos)}',
            'detalles_fallidos': correos_fallidos
        })

    except Exception as e:
        print(f"Error al enviar correos masivos: {str(e)}")
        return jsonify({'success': False, 'message': f'Error al enviar correos: {str(e)}'}), 500

# Ruta de diagnóstico
@app.route('/debug')
def debug():
    info = {
        'session': dict(session),
        'cliente_dao_available': DAO_DISPONIBLE,
        'cliente_available': CLIENTE_DISPONIBLE,
        'cliente_forma_available': FORMA_DISPONIBLE,
        'db_connection': False
    }

    try:
        conn = get_db_connection()
        if conn:
            info['db_connection'] = True
            conn.close()
    except Exception as e:
        info['db_error'] = str(e)

    return info

@app.after_request
def set_response_headers(response):
    """Configura headers para prevenir caching en páginas sensibles"""
    if 'usuario' in session:
        # Para páginas que requieren autenticación, no cachear
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# ------------------ MAIN ------------------
if __name__ == '__main__':
    print(f"Iniciando {titulo_app}...")
    print(f"Gaming Zone: http://localhost:5000/")
    print(f"Sistema Gimnasio: http://localhost:5000/pagina2")
    print(f"Debug: http://localhost:5000/debug")
    print("-" * 50)

    app.run(debug=True, host='0.0.0.0', port=5000)