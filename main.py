from flask import Flask, render_template, request, redirect, url_for
from eliminar import eliminar_usuario
from actualizar import actualizar_usuario

app = Flask(__name__)

# -----------------------
# RUTAS PRINCIPALES
# -----------------------

# Página principal
@app.route('/')
def index():
    # Aquí podrías pasar datos de usuarios, canales, productos, etc.
    return render_template('index.html')

# Página 2
@app.route('/pagina2')
def pagina2():
    return render_template('pagina2.html')

# -----------------------
# RUTAS DE USUARIO
# -----------------------

# Eliminar usuario (mejor usar POST por seguridad)
@app.route('/eliminar/<int:id_usuario>', methods=['POST'])
def eliminar(id_usuario):
    eliminar_usuario(id_usuario)
    return redirect(url_for('index'))

# Actualizar usuario
@app.route('/actualizar/<int:id_usuario>', methods=['POST'])
def actualizar(id_usuario):
    # Se espera que el formulario envíe 'nombre' y 'apellido'
    nuevo_nombre = request.form.get('nombre', '').strip()
    nuevo_apellido = request.form.get('apellido', '').strip()

    if nuevo_nombre and nuevo_apellido:
        actualizar_usuario(id_usuario, nuevo_nombre, nuevo_apellido)
    return redirect(url_for('index'))

# -----------------------
# EJECUCIÓN
# -----------------------
if __name__ == '__main__':
    app.run(debug=True)
