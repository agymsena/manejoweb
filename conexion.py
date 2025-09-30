import mysql.connector

class Conexion:
    _DATABASE = 'api_python'
    _USERNAME = 'root'
    _PASSWORD = ''   # coloca tu contraseña de MySQL aquí
    _HOST = 'localhost'
    _PORT = 3306

    @classmethod
    def obtener_conexion(cls):
        return mysql.connector.connect(
            user=cls._USERNAME,
            password=cls._PASSWORD,
            host=cls._HOST,
            port=cls._PORT,
            database=cls._DATABASE
        )

    @classmethod
    def liberar_conexion(cls, conexion):
        if conexion:
            conexion.close()

