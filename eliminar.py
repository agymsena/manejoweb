from conexion import Conexion

def eliminar_usuario(id_usuario):
    conexion = Conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = %s", (id_usuario,))
    conexion.commit()
    conexion.close()
