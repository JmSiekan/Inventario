import psycopg2
from flask_sqlalchemy import SQLAlchemy

try:
    connection = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="arkanito",
        database="DEV"
    )
    print("Conexión exitosa")


except Exception as ex:
    print(ex)


def obtener_nombre_producto(id_producto):
    try:
        connection = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="arkanito",
            database="DEV"
        )

        with connection.cursor() as cursor:
            query = f'SELECT "NOMBRE_PRODUCTO" FROM public."PRODUCTOS" WHERE "ID_PRODUCTO" = %s'
            cursor.execute(query, (id_producto,))
            nombre_producto = cursor.fetchone()

            if nombre_producto:
                return nombre_producto[0]
            else:
                return None

    except Exception as ex:
        print(ex)
        return None
    finally:
        connection.close()

def obtener_medida_producto(id_producto):
    try:
        connection = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="arkanito",
            database="DEV"
        )

        with connection.cursor() as cursor:
            query = f'SELECT "MEDIDA_PRODUCTO" FROM public."PRODUCTOS" WHERE "ID_PRODUCTO" = %s'
            cursor.execute(query, (id_producto,))
            medida_producto = cursor.fetchone()

            if medida_producto:
                return medida_producto[0]
            else:
                return None

    except Exception as ex:
        print(ex)
        return None
    finally:
        connection.close()

db = SQLAlchemy()

class Productos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)