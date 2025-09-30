from conexion import Conexion

def actualizar_usuario(id_usuario, nuevo_nombre, nuevo_apellido):
    conexion = Conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE usuarios SET nombre = %s, apellido = %s ,membresio=%s WHERE id = %s",
        (nuevo_nombre, nuevo_apellido, id_usuario)
    )
    conexion.commit()
    conexion.close()

