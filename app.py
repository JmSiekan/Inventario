import json
import psycopg2
from database import connection, obtener_nombre_producto, obtener_medida_producto  # Importa la conexión aquí
from flask import Flask, render_template, request, jsonify, redirect, Response, send_file, make_response, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas
import io
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import styles
from reportlab.lib.styles import getSampleStyleSheet
import time
from psycopg2 import sql
import pandas as pd
from io import BytesIO
import xlsxwriter
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
import openpyxl
from flask import send_file
import textwrap


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:arkanito@localhost/DEV'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# Configura la clave secreta
app.secret_key = 'arkanito'
# Inicializa Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Verifica las credenciales (necesitas implementar esto)
        if valid_login(request.form['username'], request.form['password']):
            user = User(request.form['username'])
            login_user(user)
            return redirect('/pagina_segura')
    return render_template('login.html')


def valid_login(username, password):
    try:
        connection = get_database_connection()  # Implementa tu función get_database_connection()
        cursor = connection.cursor()

        query = """
            SELECT id
            FROM users
            WHERE id = %s AND contraseña = %s;
        """

        cursor.execute(query, (username, password))
        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user:
            return True
        else:
            return False
    except Exception as ex:
        print(f"Error en la autenticación: {ex}")
        return False

app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

@app.route('/pagina_segura')
@login_required
def pagina_segura():
    return "Esta es una página segura que requiere autenticación."

def get_database_connection():
    try:
        connection = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="arkanito",
            database="DEV"
        )
        return connection
    except Exception as ex:
        print(f"Error al conectar a la base de datos: {ex}")
        return None

# Ruta para la página principal (index)
@app.route('/')
def index():
    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        # Consulta para la primera tabla de información
        query_info = """
                                SELECT
                        p."NOMBRE_PRODUCTO",
                        COALESCE(SUM(e."CANTIDAD"), 0) - COALESCE(SUM(s."CANTIDAD"), 0) AS "CANTIDAD_DISPONIBLE"
                    FROM
                        public."PRODUCTOS" p
                    LEFT JOIN
                        (SELECT "ID_PRODUCTO", SUM("CANTIDAD") AS "CANTIDAD" FROM public."ENTRADAS" GROUP BY "ID_PRODUCTO") e
                        ON p."ID_PRODUCTO" = e."ID_PRODUCTO"
                    LEFT JOIN
                        (SELECT "ID_PRODUCTO", SUM("CANTIDAD") AS "CANTIDAD" FROM public."SALIDAS" GROUP BY "ID_PRODUCTO") s
                        ON p."ID_PRODUCTO" = s."ID_PRODUCTO"
                    WHERE
                        p."ID_PRODUCTO" IN ('BCS0001', 'RHM0130', 'HDR4052', 'HDR4053', 'HDR4054','HDR4056','HDR4057','HDR4066')
                    GROUP BY
                        p."NOMBRE_PRODUCTO"
                    ORDER BY
                        "CANTIDAD_DISPONIBLE" DESC;

        """

        cursor.execute(query_info)
        producto_info = cursor.fetchall()

        # Consulta para la segunda tabla de herramientas a motor
        query_herramientas_motor = """
                        SELECT
                            p."CATEGORIA", -- Mover la columna de categoría al principio
                            p."NOMBRE_PRODUCTO",
                            COALESCE(SUM(e."CANTIDAD"), 0) - COALESCE(SUM(s."CANTIDAD"), 0) AS "CANTIDAD_DISPONIBLE"
                        FROM
                            public."PRODUCTOS" p
                        LEFT JOIN
                            (SELECT "ID_PRODUCTO", SUM("CANTIDAD") AS "CANTIDAD" FROM public."ENTRADAS" GROUP BY "ID_PRODUCTO") e
                            ON p."ID_PRODUCTO" = e."ID_PRODUCTO"
                        LEFT JOIN
                            (SELECT "ID_PRODUCTO", SUM("CANTIDAD") AS "CANTIDAD" FROM public."SALIDAS" GROUP BY "ID_PRODUCTO") s
                            ON p."ID_PRODUCTO" = s."ID_PRODUCTO"
                        WHERE
                            p."CATEGORIA" = 'HERRAMIENTAS A MOTOR'
                        GROUP BY
                            p."CATEGORIA",
                            p."NOMBRE_PRODUCTO"
                        ORDER BY
                "CANTIDAD_DISPONIBLE" DESC;

                    """

        cursor.execute(query_herramientas_motor)
        herramientas_motor = cursor.fetchall()

        # Consulta para la tercera tabla con la nueva consulta solicitada
        query_tercera_tabla = """
            WITH Totales AS (
    SELECT
        i."DESTINO",
        SUM(s."CANTIDAD") AS "CANTIDADES"
    FROM
        public."SALIDAS" s
    JOIN
        public."INFORMACION" i ON s."LEGAJO" = i."LEGAJO"
    WHERE
        s."FECHA" LIKE '2023-%'
        AND s."ID_PRODUCTO" = 'BCS0001'
    GROUP BY
        i."DESTINO"
)
SELECT
    CASE WHEN "CANTIDADES" >= 5000 THEN "DESTINO" ELSE 'OTROS' END AS "DESTINO_AGRUPADO",
    SUM("CANTIDADES") AS "CANTIDADES"
FROM
    Totales
GROUP BY
    CASE WHEN "CANTIDADES" >= 5000 THEN "DESTINO" ELSE 'OTROS' END
UNION ALL
SELECT
    'TOTAL' AS "DESTINO_AGRUPADO",
    SUM("CANTIDADES") AS "CANTIDADES"
FROM
    Totales
ORDER BY
    "CANTIDADES" DESC;

        """

        cursor.execute(query_tercera_tabla)
        tercera_tabla_info = cursor.fetchall()

        # Consulta para la cuarta tabla con la nueva consulta solicitada
        query_cuarta_tabla = """
            SELECT
                s."FECHA",
                p."NOMBRE_PRODUCTO",
                i."AGENTE",
                s."CANTIDAD"
            FROM
                public."SALIDAS" s
            JOIN
                public."INFORMACION" i ON s."LEGAJO" = i."LEGAJO"
            JOIN
                public."PRODUCTOS" p ON s."ID_PRODUCTO" = p."ID_PRODUCTO"
            ORDER BY
                s."ID_SALIDA" DESC
            LIMIT
                10;
        """

        cursor.execute(query_cuarta_tabla)
        cuarta_tabla_info = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('index.html', producto_info=producto_info, herramientas_motor=herramientas_motor, tercera_tabla_info=tercera_tabla_info, cuarta_tabla_info=cuarta_tabla_info)
    except Exception as ex:
        return f"Error: {ex}"


@app.route('/ver_personal')
def ver_personal():
    connection = get_database_connection()
    cursor = connection.cursor()

    query = """
    SELECT
        i."LEGAJO" AS "LEGAJO_INFORMACION",
        i."AGENTE",
        i."DESTINO",
        p."DNI",
        p."FUNCION",
        p."AREA",
        p."ID_CAPATAZ",
        p."ZONA",
        p."FECHA_BAJA",
        p."MOTIVO_BAJA"
    FROM
        public."INFORMACION" i
    JOIN
        public."PERSONAL" p ON i."LEGAJO" = p."LEGAJO";
    """
    cursor.execute(query)
    producto_info = cursor.fetchall()

    cursor.close()
    connection.close()

    # Renderiza la plantilla HTML y pasa los resultados
    return render_template('ver_personal.html', resultados=producto_info)

def consultar_productos(categoria):
    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        query = """
            SELECT
                p."ID_PRODUCTO",
                p."NOMBRE_PRODUCTO",
                p."CATEGORIA",
                COALESCE(SUM(e."CANTIDAD"), 0) - COALESCE(SUM(s."CANTIDAD"), 0) AS "CANTIDAD_DISPONIBLE"
            FROM
                public."PRODUCTOS" p
            LEFT JOIN
                public."ENTRADAS" e ON p."ID_PRODUCTO" = e."ID_PRODUCTO"
            LEFT JOIN
                public."SALIDAS" s ON p."ID_PRODUCTO" = s."ID_PRODUCTO"
            WHERE
                p."CATEGORIA" = %s
            GROUP BY
                p."ID_PRODUCTO",
                p."NOMBRE_PRODUCTO",
                p."CATEGORIA"
            HAVING
                COALESCE(SUM(e."CANTIDAD"), 0) - COALESCE(SUM(s."CANTIDAD"), 0) > 0
            ORDER BY
                "CANTIDAD_DISPONIBLE" DESC, p."ID_PRODUCTO";
        """

        cursor.execute(query, (categoria,))
        producto_info = cursor.fetchall()

        cursor.close()
        connection.close()

        return producto_info
    except Exception as ex:
        return []

def consultar_productos(categoria):
    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        query = """
            SELECT
        p."ID_PRODUCTO",
        p."NOMBRE_PRODUCTO",
        p."CATEGORIA",
        COALESCE(SUM(e."CANTIDAD"), 0) - COALESCE(SUM(s."CANTIDAD"), 0) AS "CANTIDAD_DISPONIBLE"
    FROM
        public."PRODUCTOS" p
    LEFT JOIN
        public."ENTRADAS" e ON p."ID_PRODUCTO" = e."ID_PRODUCTO"
    LEFT JOIN
        public."SALIDAS" s ON p."ID_PRODUCTO" = s."ID_PRODUCTO"
    WHERE
        p."CATEGORIA" = %s
    GROUP BY
        p."ID_PRODUCTO",
        p."NOMBRE_PRODUCTO",
        p."CATEGORIA"
    HAVING
        COALESCE(SUM(e."CANTIDAD"), 0) - COALESCE(SUM(s."CANTIDAD"), 0) > 0
    ORDER BY
        "CANTIDAD_DISPONIBLE" DESC, p."ID_PRODUCTO";
        """

        cursor.execute(query, (categoria,))
        producto_info = cursor.fetchall()

        cursor.close()
        connection.close()

        return producto_info
    except Exception as ex:
        return []



@app.route('/ver_stock')
def ver_stock():
    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        query = """
            SELECT
    p."ID_PRODUCTO",
    p."NOMBRE_PRODUCTO",
    COALESCE(SUM(e."CANTIDAD"), 0) - COALESCE(SUM(s."CANTIDAD"), 0) AS "CANTIDAD_DISPONIBLE"
FROM
    public."PRODUCTOS" p
LEFT JOIN
    (SELECT "ID_PRODUCTO", SUM("CANTIDAD") AS "CANTIDAD" FROM public."ENTRADAS" GROUP BY "ID_PRODUCTO") e
    ON p."ID_PRODUCTO" = e."ID_PRODUCTO"
LEFT JOIN
    (SELECT "ID_PRODUCTO", SUM("CANTIDAD") AS "CANTIDAD" FROM public."SALIDAS" GROUP BY "ID_PRODUCTO") s
    ON p."ID_PRODUCTO" = s."ID_PRODUCTO"
GROUP BY
    p."ID_PRODUCTO",
    p."NOMBRE_PRODUCTO"
ORDER BY
    p."ID_PRODUCTO";       """

        cursor.execute(query)
        datos_stock = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('ver_stock.html', datos_stock=datos_stock)
    except Exception as ex:
        return f"Error: {ex}"

@app.route('/forestacion')
def forestacion():
        return render_template('forestacion.html')

@app.route('/ver_entradas')
def ver_entradas():
    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        query = """
            SELECT 
    e."ID_ENTRADA",
    e."FECHA",
    e."ID_EXPEDIENTE",
    e."ID_PRODUCTO",
    p."NOMBRE_PRODUCTO",
    e."ID_PROVEEDOR",
    e."CANTIDAD"
FROM 
    public."ENTRADAS" AS e
JOIN 
    public."PRODUCTOS" AS p ON e."ID_PRODUCTO" = p."ID_PRODUCTO"
ORDER BY 
    e."ID_ENTRADA" ASC;
        """

        cursor.execute(query)
        datos_entradas = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('ver_entradas.html', datos_entradas=datos_entradas)
    except Exception as ex:
        return f"Error: {ex}"

@app.route('/ingreso_compras')
def ingreso_compras():
    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        query = """
            SELECT *,
       LEFT("ID_PRODUCTO", 40) AS "ID_PRODUCTO",
       TO_CHAR("CANTIDAD_CONTRATADA", 'FM999,999,999.00') AS "CANTIDAD_CONTRATADA",
       '$' || TO_CHAR("IMPORTE_UNITARIOC", 'FM999,999,999.00') AS "IMPORTE_UNITARIOC",
       '$' || TO_CHAR("CANTIDAD_CONTRATADA" * "IMPORTE_UNITARIOC", 'FM999,999,999.00') AS "MULTIPLICACION"
        FROM public."INGRESO_COMPRAS"
        ORDER BY "ID_SC" ASC;
                    """

        cursor.execute(query)
        datos_ingcompras = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('ingreso_compras.html', datos_ingcompras=datos_ingcompras)
    except Exception as ex:
        return f"Error: {ex}"

@app.route('/ingreso_reclamos')
def ingreso_reclamos():
    return render_template('ingreso_reclamos.html')

@app.route('/guardar_reclamo', methods=['POST'])
def guardar_reclamo():
        reclamo = request.form.get('reclamo')
        domicilio = request.form.get('domicilio')
        distrito = request.form.get('distrito')
        fecha = request.form.get('fecha')
        motivo = request.form.get('motivo')
        agente = request.form.get('agente')

        connection = get_database_connection()
        if connection:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    'INSERT INTO public."RECLAMOS" ("NUM_RECLAMO", "DOMICILIO", "DISTRITO", "FECHA", "MOTIVO", "AGENTE") VALUES (%s, %s, %s, %s, %s, %s)',
                    (reclamo,domicilio, distrito, fecha, motivo, agente))
                connection.commit()
                connection.close()
                # Puedes agregar un punto de control aquí para verificar que la inserción se haya realizado con éxito
                print("Informe guardado exitosamente")

                # Si todo sale bien, redirige al usuario a la página de ingreso de reclamos
                return redirect(url_for('ingreso_reclamos'))
            except Exception as e:
                # En caso de error, retorna una respuesta JSON con el error
                return jsonify({'error': str(e)})




@app.route('/presupuesto')
def presupuesto():
    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        query = """
                            SELECT
                    t1."SUBCATEGORIA",
                    TO_CHAR(SUM(t1."TOTAL OFICIAL"), 'FM999,999,999,999,999,999.00') AS "TOTAL OFICIAL",
                    TO_CHAR(SUM(t2."TOTAL GASTADO"), 'FM999,999,999,999,999,999.00') AS "TOTAL GASTADO",
                    TO_CHAR(p."IMPORTE", 'FM999,999,999,999,999,999.00') AS "PRESUPUESTO",
                    TO_CHAR(p."IMPORTE" - SUM(t2."TOTAL GASTADO"), 'FM999,999,999,999,999,999.00') AS "DIFERENCIA",
                    CASE
                        WHEN p."IMPORTE" = 0 THEN '0.00'  -- Evitar división por cero si PRESUPUESTO es cero
                        ELSE TO_CHAR((SUM(t2."TOTAL GASTADO") / p."IMPORTE") * 100, 'FM999,999,999,999,999,999.00')
                    END AS "PORCENTAJE DE GASTO"
                FROM
                    (
                        SELECT
                            "SUBCATEGORIA",
                            SUM("IMPORTE_UNITARIO" * "CANTIDAD") AS "TOTAL OFICIAL"
                        FROM
                            "SOLICITUD_COMPRAS"
                        GROUP BY
                            "SUBCATEGORIA"
                    ) t1
                LEFT JOIN
                    (
                        SELECT
                            sc."SUBCATEGORIA",
                            SUM(ic."IMPORTE_UNITARIOC" * ic."CANTIDAD_CONTRATADA") AS "TOTAL GASTADO"
                        FROM
                            public."INGRESO_COMPRAS" ic
                        LEFT JOIN
                            public."SOLICITUD_COMPRAS" sc ON ic."ID_SC" = sc."ID_SC"
                        GROUP BY
                            sc."SUBCATEGORIA"
                    ) t2
                ON
                    t1."SUBCATEGORIA" = t2."SUBCATEGORIA"
                LEFT JOIN
                    public."PRESUPUESTOS" p
                ON
                    t1."SUBCATEGORIA" = p."SUBCATEGORIA"
                GROUP BY
                    t1."SUBCATEGORIA", p."IMPORTE"
                ORDER BY
                    t1."SUBCATEGORIA" ASC;

                    """

        cursor.execute(query)
        datos_presupuesto = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('presupuesto.html', datos_presupuesto=datos_presupuesto)
    except Exception as ex:
        return f"Error: {ex}"

@app.route('/ver_salidas')
def ver_salidas():
    # Conexión a la base de datos PostgreSQL
    conn = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="arkanito",
        database="DEV"
    )

    # Crear un cursor para ejecutar consultas
    cursor = conn.cursor()

    # Consulta SQL
    query = """
   SELECT
    "SALIDAS".*,
    "PRODUCTOS"."NOMBRE_PRODUCTO",
    "INFORMACION"."AGENTE",
    TO_CHAR("SALIDAS"."FECHA"::date, 'DD-MM-YYYY') AS "FECHA_FORMATEADA"
    FROM
        public."SALIDAS"
    JOIN
        public."PRODUCTOS" ON "SALIDAS"."ID_PRODUCTO" = "PRODUCTOS"."ID_PRODUCTO"
    JOIN
        public."INFORMACION" ON "SALIDAS"."LEGAJO" = "INFORMACION"."LEGAJO"
    ORDER BY
        "SALIDAS"."ID_SALIDA" desc;
    """

    # Ejecutar la consulta
    cursor.execute(query)

    # Obtener los resultados de la consulta
    resultados = cursor.fetchall()

    # Cerrar el cursor y la conexión
    cursor.close()
    conn.close()

    # Renderizar la plantilla HTML y pasar los resultados a la página
    return render_template('ver_salidas.html', resultados=resultados)

@app.route('/ingresar_salida')
def ingresar_salida():
    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        # Consulta para la primera tabla de información
        query_info = """
                SELECT
                    p."NOMBRE_PRODUCTO",
                    COALESCE(SUM(e."CANTIDAD"), 0) - COALESCE(SUM(s."CANTIDAD"), 0) AS "CANTIDAD_DISPONIBLE"
                FROM
                    public."PRODUCTOS" p
                LEFT JOIN
                    public."ENTRADAS" e ON p."ID_PRODUCTO" = e."ID_PRODUCTO"
                LEFT JOIN
                    public."SALIDAS" s ON p."ID_PRODUCTO" = s."ID_PRODUCTO"
                WHERE
                    p."ID_PRODUCTO" = 'BCS0001'
                GROUP BY
                    p."NOMBRE_PRODUCTO"
                ORDER BY
                    p."NOMBRE_PRODUCTO";
            """

        cursor.execute(query_info)
        producto_info = cursor.fetchall()

        # Consulta para la segunda tabla de herramientas a motor
        herramientas_motor = consultar_productos('HERRAMIENTAS A MOTOR')

        # Consulta para la tercera tabla con la nueva consulta solicitada
        query_tercera_tabla = """
                SELECT
                    p."CATEGORIA",
                    i."DESTINO",
                    p."NOMBRE_PRODUCTO",
                    SUM(s."CANTIDAD") AS "CANTIDAD_TOTAL"
                FROM
                    public."SALIDAS" s
                JOIN
                    public."INFORMACION" i ON s."LEGAJO" = i."LEGAJO"
                JOIN
                    public."PRODUCTOS" p ON s."ID_PRODUCTO" = p."ID_PRODUCTO"
                WHERE
                    p."CATEGORIA" = 'HERRAMIENTAS A MOTOR'
                GROUP BY
                    p."CATEGORIA",
                    i."DESTINO",
                    p."NOMBRE_PRODUCTO"
                HAVING
                    SUM(s."CANTIDAD") > 0
                ORDER BY
                    p."CATEGORIA",
                    i."DESTINO",
                    p."NOMBRE_PRODUCTO";
            """

        cursor.execute(query_tercera_tabla)
        tercera_tabla_info = cursor.fetchall()

        # Consulta para la cuarta tabla con la nueva consulta solicitada
        query_cuarta_tabla = """
                SELECT
                    s."FECHA",
                    p."NOMBRE_PRODUCTO",
                    i."AGENTE",
                    s."CANTIDAD"
                FROM
                    public."SALIDAS" s
                JOIN
                    public."INFORMACION" i ON s."LEGAJO" = i."LEGAJO"
                JOIN
                    public."PRODUCTOS" p ON s."ID_PRODUCTO" = p."ID_PRODUCTO"
                ORDER BY
                    s."ID_SALIDA" DESC
                LIMIT
                    5;
            """

        cursor.execute(query_cuarta_tabla)
        cuarta_tabla_info = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('ingresar_salida.html', producto_info=producto_info, herramientas_motor=herramientas_motor,
                               tercera_tabla_info=tercera_tabla_info, cuarta_tabla_info=cuarta_tabla_info)
    except Exception as ex:
        return f"Error: {ex}"
    return render_template('ingresar_salida.html')

@app.route('/obt_nombprod')
def obt_nombprod():
    id_producto = request.args.get('id_producto')

    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        query = """
            SELECT "NOMBRE_PRODUCTO"
            FROM public."PRODUCTOS"
            WHERE "ID_PRODUCTO" = %s;
        """

        cursor.execute(query, (id_producto,))
        data = cursor.fetchone()
        cursor.close()
        connection.close()

        if data:
            return jsonify({"nombre_producto": data[0]})
        else:
            return jsonify({"error": "Producto no encontrado"})
    except Exception as ex:
        return jsonify({"error": str(ex)})


@app.route('/prueba')
def prueba():
    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        # Consulta para la primera tabla de información
        query_info = """
                SELECT
                    p."NOMBRE_PRODUCTO",
                    COALESCE(SUM(e."CANTIDAD"), 0) - COALESCE(SUM(s."CANTIDAD"), 0) AS "CANTIDAD_DISPONIBLE"
                FROM
                    public."PRODUCTOS" p
                LEFT JOIN
                    public."ENTRADAS" e ON p."ID_PRODUCTO" = e."ID_PRODUCTO"
                LEFT JOIN
                    public."SALIDAS" s ON p."ID_PRODUCTO" = s."ID_PRODUCTO"
                WHERE
                    p."ID_PRODUCTO" = 'BCS0001'
                GROUP BY
                    p."NOMBRE_PRODUCTO"
                ORDER BY
                    p."NOMBRE_PRODUCTO";
            """

        cursor.execute(query_info)
        producto_info = cursor.fetchall()

        # Consulta para la segunda tabla de herramientas a motor
        herramientas_motor = consultar_productos('HERRAMIENTAS A MOTOR')

        # Consulta para la tercera tabla con la nueva consulta solicitada
        query_tercera_tabla = """
                SELECT
                    p."CATEGORIA",
                    i."DESTINO",
                    p."NOMBRE_PRODUCTO",
                    SUM(s."CANTIDAD") AS "CANTIDAD_TOTAL"
                FROM
                    public."SALIDAS" s
                JOIN
                    public."INFORMACION" i ON s."LEGAJO" = i."LEGAJO"
                JOIN
                    public."PRODUCTOS" p ON s."ID_PRODUCTO" = p."ID_PRODUCTO"
                WHERE
                    p."CATEGORIA" = 'HERRAMIENTAS A MOTOR'
                GROUP BY
                    p."CATEGORIA",
                    i."DESTINO",
                    p."NOMBRE_PRODUCTO"
                HAVING
                    SUM(s."CANTIDAD") > 0
                ORDER BY
                    p."CATEGORIA",
                    i."DESTINO",
                    p."NOMBRE_PRODUCTO";
            """

        cursor.execute(query_tercera_tabla)
        tercera_tabla_info = cursor.fetchall()

        # Consulta para la cuarta tabla con la nueva consulta solicitada
        query_cuarta_tabla = """
                SELECT
                    s."FECHA",
                    p."NOMBRE_PRODUCTO",
                    i."AGENTE",
                    s."CANTIDAD"
                FROM
                    public."SALIDAS" s
                JOIN
                    public."INFORMACION" i ON s."LEGAJO" = i."LEGAJO"
                JOIN
                    public."PRODUCTOS" p ON s."ID_PRODUCTO" = p."ID_PRODUCTO"
                ORDER BY
                    s."ID_SALIDA" DESC
                LIMIT
                    5;
            """

        cursor.execute(query_cuarta_tabla)
        cuarta_tabla_info = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('prueba.html', producto_info=producto_info, herramientas_motor=herramientas_motor,
                               tercera_tabla_info=tercera_tabla_info, cuarta_tabla_info=cuarta_tabla_info)
    except Exception as ex:
        return f"Error: {ex}"
    return render_template('prueba.html')

@app.route('/ingresar_salida_ns')
def ingresar_salida_ns():
    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        # Consulta para la primera tabla de información
        query_info = """
                SELECT
                    p."NOMBRE_PRODUCTO",
                    COALESCE(SUM(e."CANTIDAD"), 0) - COALESCE(SUM(s."CANTIDAD"), 0) AS "CANTIDAD_DISPONIBLE"
                FROM
                    public."PRODUCTOS" p
                LEFT JOIN
                    public."ENTRADAS" e ON p."ID_PRODUCTO" = e."ID_PRODUCTO"
                LEFT JOIN
                    public."SALIDAS" s ON p."ID_PRODUCTO" = s."ID_PRODUCTO"
                WHERE
                    p."ID_PRODUCTO" = 'BCS0001'
                GROUP BY
                    p."NOMBRE_PRODUCTO"
                ORDER BY
                    p."NOMBRE_PRODUCTO";
            """

        cursor.execute(query_info)
        producto_info = cursor.fetchall()

        # Consulta para la segunda tabla de herramientas a motor
        herramientas_motor = consultar_productos('HERRAMIENTAS A MOTOR')

        # Consulta para la tercera tabla con la nueva consulta solicitada
        query_tercera_tabla = """
                SELECT
                    p."CATEGORIA",
                    i."DESTINO",
                    p."NOMBRE_PRODUCTO",
                    SUM(s."CANTIDAD") AS "CANTIDAD_TOTAL"
                FROM
                    public."SALIDAS" s
                JOIN
                    public."INFORMACION" i ON s."LEGAJO" = i."LEGAJO"
                JOIN
                    public."PRODUCTOS" p ON s."ID_PRODUCTO" = p."ID_PRODUCTO"
                WHERE
                    p."CATEGORIA" = 'HERRAMIENTAS A MOTOR'
                GROUP BY
                    p."CATEGORIA",
                    i."DESTINO",
                    p."NOMBRE_PRODUCTO"
                HAVING
                    SUM(s."CANTIDAD") > 0
                ORDER BY
                    p."CATEGORIA",
                    i."DESTINO",
                    p."NOMBRE_PRODUCTO";
            """

        cursor.execute(query_tercera_tabla)
        tercera_tabla_info = cursor.fetchall()

        # Consulta para la cuarta tabla con la nueva consulta solicitada
        query_cuarta_tabla = """
                SELECT
                    s."FECHA",
                    p."NOMBRE_PRODUCTO",
                    i."AGENTE",
                    s."CANTIDAD"
                FROM
                    public."SALIDAS" s
                JOIN
                    public."INFORMACION" i ON s."LEGAJO" = i."LEGAJO"
                JOIN
                    public."PRODUCTOS" p ON s."ID_PRODUCTO" = p."ID_PRODUCTO"
                ORDER BY
                    s."ID_SALIDA" DESC
                LIMIT
                    5;
            """

        cursor.execute(query_cuarta_tabla)
        cuarta_tabla_info = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('ingresar_salida_ns.html', producto_info=producto_info, herramientas_motor=herramientas_motor,
                               tercera_tabla_info=tercera_tabla_info, cuarta_tabla_info=cuarta_tabla_info)
    except Exception as ex:
        return f"Error: {ex}"
    return render_template('ingresar_salida_ns.html')

@app.route('/ingresar_entrada', methods=['GET', 'POST'])
def ingresar_entrada():
    if request.method == 'POST':
        # Obtener los datos del formulario
        fecha = request.form.get('fecha')
        id_expediente = request.form.get('id_expediente')
        id_producto = request.form.get('id_producto')
        id_proveedor = request.form.get('id_proveedor')
        cantidad = request.form.get('cantidad')

        # Realizar la inserción en la base de datos
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="arkanito",
            database="DEV"
        )
        cursor = conn.cursor()

        # Obtener el valor más alto de ID_ENTRADA existente en la tabla
        query_max_id = 'SELECT MAX("ID_ENTRADA") FROM "ENTRADAS";'
        cursor.execute(query_max_id)
        max_id = cursor.fetchone()[0]

        # Incrementar el valor más alto en uno para obtener el nuevo ID_ENTRADA
        new_id = max_id + 1

        query = 'INSERT INTO "ENTRADAS" ("ID_ENTRADA", "FECHA", "ID_EXPEDIENTE", "ID_PRODUCTO", "ID_PROVEEDOR", "CANTIDAD") VALUES (%s, %s, %s, %s, %s, %s)'
        values = (new_id, fecha,  id_expediente, id_producto, id_proveedor, cantidad)
        cursor.execute(query, values)

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Datos insertados correctamente'})

    return render_template('ingresar_entrada.html')

@app.route('/ingresar_entrada_ns', methods=['GET', 'POST'])
def ingresar_entrada_ns():
    if request.method == 'POST':
        # Obtener los datos del formulario
        fecha = request.form.get('fecha')
        id_expediente = request.form.get('id_expediente')
        id_producto = request.form.get('id_producto')
        id_proveedor = request.form.get('id_proveedor')
        numero_serie = request.form.get('numero_serie')

        try:
            # Realizar la inserción en la tabla ENTRADAS y NUM_SERIE dentro de una transacción
            conn = psycopg2.connect(
                host="localhost",
                user="postgres",
                password="arkanito",
                database="DEV"
            )
            cursor = conn.cursor()

            # Obtener el valor más alto de ID_ENTRADA existente en la tabla
            query_max_id = 'SELECT MAX("ID_ENTRADA") FROM "ENTRADAS";'
            cursor.execute(query_max_id)
            max_id = cursor.fetchone()[0]

            # Incrementar el valor más alto en uno para obtener el nuevo ID_ENTRADA
            new_id = max_id + 1

            query_entradas = 'INSERT INTO "ENTRADAS" ("ID_ENTRADA","FECHA", "ID_EXPEDIENTE", "ID_PRODUCTO", "ID_PROVEEDOR", "CANTIDAD") VALUES (%s, %s, %s, %s, %s, %s)'
            values_entradas = (new_id, fecha, id_expediente, id_producto, id_proveedor, 1)  # Cantidad siempre es 1
            cursor.execute(query_entradas, values_entradas)

            # Realizar la inserción en la tabla NUM_SERIE
            query_num_serie = 'INSERT INTO "NUM_SERIE" ("ID_PRODUCTO", "NUM_SERIE", "CANTIDAD") VALUES (%s, %s, %s)'
            values_num_serie = (id_producto, numero_serie, 1)  # Siempre cantidad 1
            cursor.execute(query_num_serie, values_num_serie)

            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({'message': 'Datos insertados correctamente'})

        except psycopg2.errors.UniqueViolation as unique_error:
            # Si ocurre una violación de clave única en NUM_SERIE
            conn.rollback()
            cursor.close()
            conn.close()

            print("Error de violación de clave única:", unique_error)
            return jsonify({'error': 'El número de serie ya existe'})

        except Exception as e:
            # Si ocurre algún otro error
            conn.rollback()
            cursor.close()
            conn.close()

            print("Error general:", e)
            return jsonify({'error': 'Error al insertar los datos'})

    return render_template('ingresar_entrada_ns.html')







@app.route('/buscar_agente', methods=['GET'])
def buscar_agente():
    legajo = request.args.get('legajo')

    # Realizar la consulta en la base de datos para obtener el agente
    conn = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="arkanito",
        database="DEV"
    )
    cursor = conn.cursor()
    query = f"SELECT \"AGENTE\" FROM \"INFORMACION\" WHERE \"LEGAJO\" = {legajo};"
    cursor.execute(query)
    nombre_agente = cursor.fetchone()[0]  # Suponiendo que el resultado es el primer campo

    cursor.close()
    conn.close()

    return jsonify({'agente': nombre_agente})

@app.route('/buscar_nombre_producto', methods=['GET'])
def buscar_nombre_producto():
    id_producto = request.args.get('id_producto')

    # Realizar la consulta en la base de datos para obtener el nombre del producto
    conn = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="arkanito",
        database="DEV"
    )
    cursor = conn.cursor()
    query = f"SELECT \"NOMBRE_PRODUCTO\" FROM \"PRODUCTOS\" WHERE \"ID_PRODUCTO\" = '{id_producto}';"
    cursor.execute(query)
    nombre_producto = cursor.fetchone()[0]  # Suponiendo que el resultado es el primer campo

    cursor.close()
    conn.close()

    return jsonify({'nombre_producto': nombre_producto})

@app.route('/insertar_salida', methods=['POST'])
def insertar_salida():
    fecha = request.form.get('fecha')
    legajo = request.form.get('legajo')
    id_producto = request.form.get('id_producto')
    cantidad = float(request.form.get('cantidad'))  # Convertir a número decimal

    try:
        # Realizar la conexión a la base de datos
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="arkanito",
            database="DEV"
        )
        cursor = conn.cursor()

        # Consultar la cantidad disponible
        query_cantidad_disponible = '''
        SELECT
            COALESCE(SUM(e."CANTIDAD"), 0) - COALESCE(SUM(s."CANTIDAD"), 0) AS "CANTIDAD_DISPONIBLE"
        FROM
            public."PRODUCTOS" p
        LEFT JOIN
            (SELECT "ID_PRODUCTO", SUM("CANTIDAD") AS "CANTIDAD" FROM public."ENTRADAS" GROUP BY "ID_PRODUCTO") e
            ON p."ID_PRODUCTO" = e."ID_PRODUCTO"
        LEFT JOIN
            (SELECT "ID_PRODUCTO", SUM("CANTIDAD") AS "CANTIDAD" FROM public."SALIDAS" GROUP BY "ID_PRODUCTO") s
            ON p."ID_PRODUCTO" = s."ID_PRODUCTO"
        WHERE
            p."ID_PRODUCTO" = %s
        GROUP BY
            p."ID_PRODUCTO";
        '''
        cursor.execute(query_cantidad_disponible, (id_producto,))
        cantidad_disponible = cursor.fetchone()[0]

        # Verificar si hay suficiente stock
        if cantidad_disponible >= cantidad:
            # Realizar la inserción en la tabla de salidas
            query_insert = 'INSERT INTO "SALIDAS" ("FECHA", "LEGAJO", "ID_PRODUCTO", "CANTIDAD") VALUES (%s, %s, %s, %s)'
            values_insert = (fecha, legajo, id_producto, cantidad)
            cursor.execute(query_insert, values_insert)
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'message': 'Datos insertados correctamente'})
        else:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Stock insuficiente para realizar la salida'})

    except Exception as e:
        # Si ocurre algún error
        cursor.close()
        conn.close()
        print("Error:", e)
        return jsonify({'error': 'Error al insertar los datos'})



@app.route('/salsa.html')
def mostrar_pagina_salsa():
    return render_template('salsa.html')

# Ruta para mostrar el formulario
@app.route('/ns_salida', methods=['GET'])
def mostrar_ns_salida():
    return render_template('ns_salida.html')

@app.route('/control_stock')
def control_stock():
    return render_template('control_stock.html')


@app.route('/ingresar_control', methods=['POST'])
def ingresar_control():
    data = request.form.to_dict()

    conn = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="arkanito",
        database="DEV"
    )
    cursor = conn.cursor()

    try:
        for key, value in data.items():
            if key.startswith('fecha'):
                fecha = value
                legajo = data.get(f'legajo{key[5:]}')
                id_producto = data.get(f'id_producto{key[5:]}')
                cantidad = data.get(f'cantidad{key[5:]}')

                query = """
                INSERT INTO "CONTROL" ("FECHA", "LEGAJO", "ID_PRODUCTO", "CANTIDAD")
                VALUES (%s, %s, %s, %s);
                """
                values = (fecha, legajo, id_producto, cantidad)
                cursor.execute(query, values)

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Datos insertados correctamente"})
    except Exception as e:
        print("Error:", e)
        return jsonify({"message": "Error al insertar los datos"}), 500  # Devolver un código de estado de error (por ejemplo, 500)

@app.route('/insertar_salida_ns', methods=['POST'])
def insertar_salida_ns():
    if request.method == 'POST':
        # Obtener los datos del formulario
        fecha = request.form.get('fecha')
        legajo = request.form.get('legajo')
        id_producto = request.form.get('id_producto')
        num_serie = request.form.get('num_serie')
        motivo = request.form.get('motivo')  # Asegúrate de que el campo 'motivo' esté en el formulario

        try:
            conn = psycopg2.connect(
                host="localhost",
                user="postgres",
                password="arkanito",
                database="DEV"
            )
            cursor = conn.cursor()

            conn.autocommit = False  # Iniciar transacción

            # Verificar si el NUM_SERIE existe y su cantidad es mayor que 0
            query_buscar_serie = 'SELECT "CANTIDAD" FROM "NUM_SERIE" WHERE "NUM_SERIE" = %s AND "CANTIDAD" = 1'
            cursor.execute(query_buscar_serie, (num_serie,))
            result = cursor.fetchone()

            if result:
                # Actualizar la cantidad a 0 en la tabla NUM_SERIE
                query_actualizar_cantidad = 'UPDATE "NUM_SERIE" SET "CANTIDAD" = 0 WHERE "NUM_SERIE" = %s AND "CANTIDAD" = 1'
                cursor.execute(query_actualizar_cantidad, (num_serie,))

                if cursor.rowcount > 0:
                    # Obtener el máximo valor actual de ID_CARGO
                    query_max_id_cargo = 'SELECT MAX("ID_CARGO") FROM "CARGOS"'
                    cursor.execute(query_max_id_cargo)
                    max_id_cargo_result = cursor.fetchone()[0]

                    # Verificar si max_id_cargo_result es None y asignar un valor predeterminado si es así
                    if max_id_cargo_result is None:
                        max_id_cargo = 0
                    else:
                        max_id_cargo = max_id_cargo_result

                    # Generar el nuevo ID_CARGO sumando 1 al máximo valor actual
                    new_id_cargo = max_id_cargo + 1

                    # Insertar en la tabla CARGOS con el nuevo ID_CARGO y cantidad 1
                    query_cargos = 'INSERT INTO "CARGOS" ("ID_CARGO", "FECHA", "LEGAJO", "ID_PRODUCTO", "NUM_SERIE", "MOTIVO", "CANTIDAD") VALUES (%s, %s, %s, %s, %s, %s, %s)'
                    values_cargos = (new_id_cargo, fecha, legajo, id_producto, num_serie, motivo, 1)
                    cursor.execute(query_cargos, values_cargos)

                    # Insertar en la tabla SALIDAS con cantidad 1
                    query_salidas = 'INSERT INTO "SALIDAS" ("FECHA", "LEGAJO", "ID_PRODUCTO", "CANTIDAD") VALUES (%s, %s, %s, %s)'
                    values_salidas = (fecha, legajo, id_producto, 1)
                    cursor.execute(query_salidas, values_salidas)

                    print("Salida insertada correctamente en SALIDAS y CARGOS")

                    conn.commit()  # Confirmar la transacción

                    return jsonify({'message': 'Salida insertada correctamente en SALIDAS y CARGOS'})
                else:
                    conn.rollback()  # Revertir la transacción
                    return jsonify({'message': 'El producto no está en stock'})
            else:
                conn.rollback()  # Revertir la transacción
                return jsonify({'message': 'El producto no está en stock o el número de serie no es válido'})
        except Exception as e:
            print("Error:", str(e))
            conn.rollback()  # Revertir la transacción en caso de error
            return jsonify({'message': 'Error al insertar los datos'})
        finally:
            conn.autocommit = True  # Restaurar el modo de autocommit
            cursor.close()
            conn.close()





# Definir la ruta para verificar el stock
@app.route('/verificar_stock', methods=['GET'])
def verificar_stock():
    # Obtener el ID_PRODUCTO de la solicitud
    id_producto = request.args.get('id_producto')

    # Realizar la consulta SQL para obtener las cantidades de entradas y salidas
    query = """
    SELECT
        p."ID_PRODUCTO",
        p."NOMBRE_PRODUCTO",
        COALESCE(SUM(e."CANTIDAD"), 0) AS "CANTIDAD_ENTRADAS",
        COALESCE(SUM(s."CANTIDAD"), 0) AS "CANTIDAD_SALIDAS",
        (COALESCE(SUM(e."CANTIDAD"), 0) - COALESCE(SUM(s."CANTIDAD"), 0)) AS "STOCK_ACTUAL"
    FROM
        public."PRODUCTOS" p
    LEFT JOIN
        public."ENTRADAS" e ON p."ID_PRODUCTO" = e."ID_PRODUCTO"
    LEFT JOIN
        public."SALIDAS" s ON p."ID_PRODUCTO" = s."ID_PRODUCTO"
    WHERE
        p."ID_PRODUCTO" = '{id_producto}'
    GROUP BY
        p."ID_PRODUCTO",
        p."NOMBRE_PRODUCTO";
    """

    # Ejecutar la consulta en la base de datos
    # Aquí debes tener el código para ejecutar la consulta en tu base de datos

    # Supongamos que obtienes los resultados de la consulta en variables
    cantidad_entradas = 100  # Ejemplo, reemplaza con el valor real
    cantidad_salidas = 50  # Ejemplo, reemplaza con el valor real
    stock_actual = cantidad_entradas - cantidad_salidas

    # Asegurarse de que el stock no sea menor que 0
    if stock_actual < 0:
        stock_actual = 0

    # Crear un diccionario con los resultados
    data = {
        'cantidad_entradas': cantidad_entradas,
        'cantidad_salidas': cantidad_salidas,
        'stock_actual': stock_actual
    }

    # Devolver los resultados como JSON
    return jsonify(data)

@app.route('/obtener_ultimas_salidas', methods=['GET'])
def obtener_ultimas_salidas():
    try:
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="arkanito",
            database="DEV"
        )
        cursor = conn.cursor()

        query_ultimas_salidas = 'SELECT "FECHA", "NOMBRE_PRODUCTO", "AGENTE", "CANTIDAD" FROM "SALIDAS" ORDER BY "FECHA" DESC LIMIT 5'
        cursor.execute(query_ultimas_salidas)
        ultimas_salidas = cursor.fetchall()

        return jsonify({'ultimas_salidas': ultimas_salidas})

    except Exception as e:
        return jsonify({'message': 'Error al obtener las últimas salidas'})
    finally:
        cursor.close()
        conn.close()

@app.route('/obtener_numeros_serie', methods=['GET'])
def obtener_numeros_serie():
    try:
        id_producto = request.args.get('id_producto')

        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="arkanito",
            database="DEV"
        )
        cursor = conn.cursor()

        query = 'SELECT "NUM_SERIE" FROM "NUM_SERIE" WHERE "ID_PRODUCTO" = %s AND "CANTIDAD" > 0'
        cursor.execute(query, (id_producto,))
        numeros_serie = [row[0] for row in cursor.fetchall()]

        return jsonify({'numeros_serie': numeros_serie})

    except Exception as e:
        return jsonify({'error': 'Error al obtener los números de serie'})

    finally:
        cursor.close()
        conn.close()

# Configuración de la base de datos
db_config = {
    "host": "localhost",
    "user": "postgres",
    "password": "arkanito",
    "database": "DEV"
}
@app.route('/cargos')
def mostrar_cargos():
    try:
        # Conexión a la base de datos
        conn = psycopg2.connect(**db_config)

        # Crear un cursor
        cursor = conn.cursor()

        # Ejecutar la consulta
        query = 'SELECT * FROM public."CARGOS" ORDER BY "ID_CARGO" ASC'
        cursor.execute(query)

        # Obtener los resultados
        resultados = cursor.fetchall()

        # Cerrar cursor y conexión
        cursor.close()
        conn.close()

        return render_template('cargos.html', cargos=resultados)
    except Exception as e:
        return f"Error: {e}"




# Ruta para generar el PDF
@app.route('/generar_pdf_salidas')
def generar_pdf_salidas():
    # Realiza la consulta a la base de datos para obtener los datos
    query = text("""
                SELECT
                c."ID_CARGO" AS ID_CARGO,
                c."FECHA" AS FECHA,
                i."AGENTE" AS AGENTE,
                c."LEGAJO" AS LEGAJO,
                p."NOMBRE_PRODUCTO" AS NOMBRE_PRODUCTO,
                c."ID_PRODUCTO" AS ID_PRODUCTO,
                c."CANTIDAD" AS CANTIDAD,
                c."MOTIVO" AS MOTIVO,
                c."NUM_SERIE" AS NUM_SERIE
            FROM
                "CARGOS" c
            JOIN
                "INFORMACION" i ON c."LEGAJO" = i."LEGAJO"
            JOIN
                "PRODUCTOS" p ON c."ID_PRODUCTO" = p."ID_PRODUCTO"
            WHERE
                c."ID_CARGO" = (SELECT MAX("ID_CARGO") FROM "CARGOS");
    """)
    # Ejecuta la consulta y obtiene los resultados
    results = db.session.execute(query).fetchall()  # Asumiendo que "db" es tu conexión a la base de datos

    # Crear el PDF usando ReportLab
    response = io.BytesIO()
    pdf = canvas.Canvas(response, pagesize=letter)

    # Definir el estilo del título
    title_style = styles.getSampleStyleSheet()["Title"]
    title_style.alignment = TA_CENTER  # Alineación centrada
    title_style.fontSize = 15  # Tamaño de fuente
    title_style.fontName = "Helvetica-Bold"  # Fuente en negrita

    # Agregar título al PDF
    titulo = "CARGO DE MÁQUINAS Y HERRAMIENTAS DE TRABAJO"
    pdf.setFont("Helvetica-Bold", 15)  # Ajusta la fuente y el tamaño
    pdf.drawCentredString(letter[0] / 2, 650, titulo)



    # Ruta a la imagen en el sistema de archivos local
    image_path = "C:/Users/Guaymallen/PycharmProjects/sistema funcionando - ok al 29-08/static/guayma.jpg"

    # Agregar imagen al encabezado
    pdf.drawImage(image_path, 30, 700, width=550, height=100)  # Ajusta las coordenadas y el tamaño

    # Agregar el texto inicial al PDF
    texto_inicial = "Recibí de la Dirección de Espacios Verdes de la Municipalidad de Guaymallén, la/s siguente/s maquinaria/s y/o herramientas que serán usadas durante el transcurso del horario laboral:"
    pdf.setFont("Helvetica", 12)  # Ajusta la fuente y el tamaño

    # Coordenadas iniciales
    x = 50
    y = 600

    # Límite derecho de la página
    limite_derecho = letter[0] - 50  # Ajusta el margen

    # Divide y agrega el texto al PDF con saltos de línea
    lineas = texto_inicial.split()
    texto_actual = ""
    for palabra in lineas:
        if pdf.stringWidth(texto_actual + " " + palabra, "Helvetica", 12) < limite_derecho - x:
            texto_actual += " " + palabra
        else:
            pdf.drawString(x, y, texto_actual)
            y -= 15  # Ajusta el espaciado vertical
            texto_actual = palabra

    # Agrega la última línea del texto
    pdf.drawString(x, y, texto_actual)


    # Datos para la tabla
    data = [["INFORMACIÓN", "DATOS"]]  # Encabezados de la tabla

    # Agregar los pares de etiqueta y dato a la matriz
    for row in results:
        data.append(["FECHA:", row[1]])  # Cambia "NOMBRE:" y row[0] según tus necesidades
        data.append(["CARGO:", row[0]])  # Cambia "FECHA:" y row[1] según tus necesidades
        data.append(["LEGAJO:", row[3]])  # Cambia "CARGO:" y row[2] según tus necesidades
        data.append(["AGENTE:", row[2]])
        data.append(["ID_PRODUCTO:", row[5]])
        cargo = str(row[4])[:50] if len(str(row[4])) > 50 else str(row[4])
        data.append(["PRODUCTO:", cargo])
        data.append(["NÚMERO DE SERIE:", row[8]])
        data.append(["CANTIDAD:", row[6]])
        data.append(["MOTIVO:", row[7]])



    # Crear la tabla
    table = Table(data)

    # Estilo de la tabla
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#FFFFFF'),
        ('TEXTCOLOR', (0, 0), (-1, 0), (0, 0, 0)),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), '#FFFFFF'),
        ('GRID', (0, 0), (-1, -1), 1, (0.5, 0.5, 0.5)),
    ])
    table.setStyle(style)

    # Ajusta las coordenadas donde se dibuja la tabla
    table.wrapOn(pdf, 10, 10)  # Ajusta las coordenadas x, y según tu diseño
    table.drawOn(pdf, 100, 350)  # Ajusta las coordenadas x, y según tu diseño

    pdf.save()

    # Configurar la respuesta del Flask para mostrar el PDF
    response.seek(0)
    return send_file(response, as_attachment=True, mimetype='application/pdf', download_name='salidas.pdf')


@app.route('/agregar_producto' , methods=['GET', 'POST'])
def agregar_producto():
    # Realiza la consulta SQL para obtener las categorías
    connection = get_database_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute('SELECT "NOMBRE_CATEGORIA" FROM public."CATEGORIAS" ORDER BY "NOMBRE_CATEGORIA" ASC')
        categorias = [row[0] for row in cursor.fetchall()]  # Obtiene todas las categorías como una lista
        connection.close()
    else:
        categorias = []

    return render_template('agregar_producto.html', categorias=categorias)


# Ruta para generar el código de producto
@app.route('/generar_codigo_producto', methods=['POST'])
def generar_codigo_producto():
    categoria = request.form['categoria']
    connection = get_database_connection()
    if connection:
        cursor = connection.cursor()

        # Encuentra el último "ID_PRODUCTO" en la categoría seleccionada
        cursor.execute(
            'SELECT "ID_PRODUCTO" FROM public."PRODUCTOS" WHERE "CATEGORIA" = %s ORDER BY "ID_PRODUCTO" DESC LIMIT 1',
            (categoria,))
        ultimo_id_producto = cursor.fetchone()

        if ultimo_id_producto:
            ultimo_id_producto_str = str(ultimo_id_producto[0])
            # Encuentra la última parte numérica del "ID_PRODUCTO"
            numero_parte = ''.join(filter(str.isdigit, ultimo_id_producto_str))
            if numero_parte:
                ultimo_numero = int(numero_parte)
                nuevo_numero = ultimo_numero + 1
            else:
                nuevo_numero = 1
        else:
            nuevo_numero = 1

        # Obtén el "ID_CATEGORIA" correspondiente a la categoría seleccionada
        cursor.execute('SELECT "ID_CATEGORIA" FROM public."CATEGORIAS" WHERE "NOMBRE_CATEGORIA" = %s', (categoria,))
        id_categoria = cursor.fetchone()[0]

        if id_categoria:
            nuevo_id_producto = f'{id_categoria}{nuevo_numero:04d}'  # Formatea el nuevo "ID_PRODUCTO"
        else:
            nuevo_id_producto = ''

        connection.close()
        return jsonify({'codigo_producto': nuevo_id_producto})
    else:
        return jsonify({'codigo_producto': ''})

# Ruta para procesar el formulario y realizar la inserción
@app.route('/guardar_producto', methods=['POST'])
def guardar_producto():
    categoria = request.form['categoria']
    codigo_producto = request.form['codigoProducto']
    nombre_producto = request.form['nombreProducto']
    especificacion_producto = request.form['especificacionProducto']
    medida_producto = request.form['medidaProducto']

    connection = get_database_connection()
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute('INSERT INTO public."PRODUCTOS" ("ID_PRODUCTO", "NOMBRE_PRODUCTO", "ESPECIFICACION_PRODUCTO", "MEDIDA_PRODUCTO", "CATEGORIA") VALUES (%s, %s, %s, %s, %s)',
                (codigo_producto, nombre_producto, especificacion_producto, medida_producto, categoria))
            connection.commit()
            connection.close()

            flash('Producto guardado correctamente', 'success')
            return redirect(url_for('agregar_producto'))
        except Exception as ex:
            connection.rollback()
            connection.close()
            flash(f'Error al guardar el producto: {ex}', 'error')
            return redirect(url_for('agregar_producto'))
    else:
        flash('Error al conectar a la base de datos.', 'error')
        return redirect(url_for('agregar_producto'))

@app.route('/ver_numseries')
def ver_numseries():
    connection = get_database_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                P."ID_PRODUCTO",
                P."NOMBRE_PRODUCTO",
                NUM."NUM_SERIE",
                P."CATEGORIA",
                NUM."CANTIDAD"
            FROM
                public."NUM_SERIE" NUM
            JOIN
                public."PRODUCTOS" P ON NUM."ID_PRODUCTO" = P."ID_PRODUCTO"
            ORDER BY
                P."NOMBRE_PRODUCTO" ASC;
        """)
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('ver_numseries.html', results=results)
    else:
        return "Error de conexión a la base de datos"


@app.route("/ver_controles")
def ver_controles():
    # Obtener la conexión a la base de datos
    connection = get_database_connection()

    # Crea un cursor
    cursor = connection.cursor()

    if connection:
        # Ejecuta la consulta SQL y obtén los resultados
        cursor.execute('''
            SELECT
                c.*,
                p."NOMBRE_PRODUCTO" AS "NOMBRE_PRODUCTO_RELACIONADO"
            FROM
                public."CONTROL" c
            JOIN
                public."PRODUCTOS" p ON c."ID_PRODUCTO" = p."ID_PRODUCTO"
            ORDER BY
                c."ID_CONTROL" ASC
        ''')

        # Obtiene los resultados de la consulta
        data = cursor.fetchall()

        # Cierra el cursor, pero NO cierres la conexión aquí
        cursor.close()

        # Renderiza la página HTML con los resultados
        return render_template("ver_controles.html", data=data)
    else:
        return "Error de conexión a la base de datos"

@app.route("/ver_pendientes")
def ver_pendientes():
    try:
        # Conéctate a la base de datos
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="arkanito",
            database="DEV"
        )
        cursor = conn.cursor()

        # Ejecuta la consulta SQL
        agente = request.args.get('agente')  # Obtén el valor del agente si se ha enviado desde el formulario
        if agente:
            cursor.execute('''
                SELECT "ID_RECLAMO", "NUM_RECLAMO", "DOMICILIO", "AGENTE", "DISTRITO", "MOTIVO"
                FROM public."RECLAMOS"
                WHERE "ID_RECLAMO" NOT IN (SELECT "ID_RECLAMO" FROM public."INFORMES")
                AND "AGENTE" = %s;
            ''', (agente,))
        else:
            cursor.execute('''
                SELECT "ID_RECLAMO", "NUM_RECLAMO", "DOMICILIO", "AGENTE", "DISTRITO", "MOTIVO"
                FROM public."RECLAMOS"
                WHERE "ID_RECLAMO" NOT IN (SELECT "ID_RECLAMO" FROM public."INFORMES");
            ''')

        # Obtén los resultados
        pendientes = cursor.fetchall()


        # Cierra la conexión a la base de datos
        cursor.close()
        conn.close()


        # Renderiza la plantilla HTML y pasa los resultados como contexto
        return render_template('ver_pendientes.html', pendientes=pendientes)
    except Exception as e:
        return jsonify({'error': str(e)})


def obtener_datos_desde_bd():
    # Configura la conexión a tu base de datos PostgreSQL
    connection = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="arkanito",
        database="DEV"
    )

    # Define tu consulta SQL
    query = """
             SELECT 
    "SALIDAS"."FECHA_FORMATO",
    "SALIDAS"."ID_SALIDA",
    "SALIDAS"."FECHA", 
    "SALIDAS"."LEGAJO",
    "SALIDAS"."ID_PRODUCTO", 
    "SALIDAS"."CANTIDAD", 
    "SALIDAS"."NOMBRE_PRODUCTO", 
    "SALIDAS"."AGENTE",
    "SALIDAS"."DESTINO"
FROM (
    SELECT 
        "SALIDAS"."ID_SALIDA",
        "SALIDAS"."FECHA", 
        "SALIDAS"."LEGAJO",
        "SALIDAS"."ID_PRODUCTO", 
        "SALIDAS"."CANTIDAD", 
        "PRODUCTOS"."NOMBRE_PRODUCTO", 
        "INFORMACION"."AGENTE",
        "INFORMACION"."DESTINO",  
        TO_CHAR("SALIDAS"."FECHA"::DATE, 'DD/MM/YYYY') AS "FECHA_FORMATO"
    FROM 
        public."SALIDAS"
    JOIN 
        public."PRODUCTOS" ON "SALIDAS"."ID_PRODUCTO" = "PRODUCTOS"."ID_PRODUCTO"
    JOIN 
        public."INFORMACION" ON "SALIDAS"."LEGAJO" = "INFORMACION"."LEGAJO"
    ORDER BY 
        "SALIDAS"."ID_SALIDA" DESC
    LIMIT 150000
) AS "SALIDAS";

    """

    # Ejecuta la consulta y obtén los resultados en un DataFrame
    df = pd.read_sql_query(query, connection)

    # Cierra la conexión a la base de datos
    connection.close()

    return df


@app.route('/descargar_excel', methods=['GET'])
def descargar_excel():
    # Obtener los datos desde la base de datos
    df = obtener_datos_desde_bd()

    # Crear un objeto BytesIO para guardar el archivo Excel en memoria
    output = BytesIO()

    # Escribir el DataFrame en el objeto BytesIO
    df.to_excel(output, engine='xlsxwriter', sheet_name='Salidas', index=False)

    # Mover el cursor al principio del objeto BytesIO
    output.seek(0)

    # Crear una respuesta HTTP con el archivo Excel adjunto
    response = Response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=salidas.xlsx'

    return response

@app.route('/necesidades_compras', methods=['GET', 'POST'])
def necesidades_compras():
    if request.method == 'POST':
        # Conexión a la base de datos PostgreSQL
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="arkanito",
            database="DEV"
        )
        # Inicializa el cursor
        cursor = conn.cursor()

        try:
            # Obtener los datos del formulario HTML
            fecha = request.form.get('fecha')  # Ajusta el nombre del campo
            legajo = request.form.get('legajo')  # Ajusta el nombre del campo
            producto = request.form.get('producto')  # Ajusta el nombre del campo
            link = request.form.get('link')  # Ajusta el nombre del campo

            # Validar que los datos no estén vacíos
            if not fecha or not legajo:
                return jsonify({'error': 'Fecha y Legajo son obligatorios'})

            # Realizar la inserción en la base de datos
            cursor.execute('''
                INSERT INTO public."NECESIDAD_COMPRA" ("FECHA", "LEGAJO", "PRODUCTO", "LINK")
                VALUES (%s, %s, %s, %s)
            ''', (fecha, legajo, producto, link))

            conn.commit()  # Guardar los cambios en la base de datos

            # Redirigir al usuario nuevamente a la misma página
            return redirect('/necesidades_compras')
        except Exception as e:
            return render_template('necesidades_compras.html')
    else:
        # Manejar el caso de solicitud 'GET'
        # Aquí debes devolver una respuesta apropiada para las solicitudes 'GET'
        # Puedes renderizar un formulario vacío o una página inicial, según tu diseño
        return render_template('necesidades_compras.html')



@app.route('/ver_reclamos')
def ver_reclamos():
    # Conexión a la base de datos PostgreSQL
    conn = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="arkanito",
        database="DEV"
    )

    # Crear un cursor para ejecutar consultas
    cursor = conn.cursor()

    # Consulta SQL
    query = """
    SELECT
    TO_CHAR(r."FECHA", 'DD-MM-YYYY') AS "FECHA_PEDIDO",
    TO_CHAR(i."FECHA", 'DD-MM-YYYY') AS "FECHA_INSPECCION",
    r."ID_RECLAMO",
	r."NUM_RECLAMO",
    r."DOMICILIO",
    i."ESPECIES",
    i."CANTIDAD",
    i."MOTIVO",
    i."RESOLUCION",
    i."AGENTE",
    i."TAREA",
    CASE
        WHEN r."ID_RECLAMO" IS NOT NULL AND i."ID_RECLAMO" IS NOT NULL THEN 'SI'
        ELSE 'NO'
    END AS "REALIZADO"
FROM
    public."RECLAMOS" r
LEFT JOIN
    public."INFORMES" i
ON
    r."ID_RECLAMO" = i."ID_RECLAMO"
ORDER BY
    r."ID_RECLAMO" ASC;
    """

    # Ejecutar la consulta
    cursor.execute(query)

    # Obtener los resultados de la consulta
    resultados = cursor.fetchall()

    # Cerrar el cursor y la conexión
    cursor.close()
    conn.close()

    # Renderizar la plantilla HTML y pasar los resultados a la página
    return render_template('ver_reclamos.html', resultados=resultados)

@app.route('/informe_reclamo')
def informe_reclamo():
    # Puedes realizar cualquier lógica adicional aquí antes de renderizar la plantilla
    # Por ejemplo, si deseas pasar datos a la plantilla, puedes hacerlo aquí.

    # Luego, renderiza la plantilla ingreso_reclamo.html desde la carpeta templates
    return render_template('informe_reclamo.html')

@app.route('/tarea_realizada', methods=['GET', 'POST'])
def tarea_realizada():
    if request.method == 'POST':
        # Conexión a la base de datos PostgreSQL
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="arkanito",
            database="DEV"
        )
        # Inicializa el cursor
        cursor = conn.cursor()

        try:
            # Obtener los datos del formulario HTML
            id_reclamo = request.form.get('idReclamo')  # Puedes ajustar el nombre del campo
            fecha_forestacion = request.form.get('fechaForestacion')  # Ajusta el nombre del campo

            # Validar que los datos no estén vacíos
            if not id_reclamo or not fecha_forestacion:
                return jsonify({'error': 'ID de reclamo y fecha de forestación son obligatorios'})

            # Realizar la inserción en la base de datos
            cursor.execute('''
                INSERT INTO public."TAREA_FORESTACION" ("ID_RECLAMO", "FECHA_FORESTACION")
                VALUES (%s, %s)
            ''', (id_reclamo, fecha_forestacion))

            conn.commit()  # Guardar los cambios en la base de datos

            # Redirigir al usuario nuevamente a la misma página
            return redirect('/tarea_realizada')
        except Exception as e:
            return render_template('tarea_realizada.html')

    # Si no es una solicitud POST, simplemente renderiza el formulario
    return render_template('tarea_realizada.html', exito=False)



@app.route('/obtener_domicilio', methods=['GET'])
def obtener_domicilio():
    id_reclamo = request.args.get('id_reclamo')

    # Conexión a la base de datos PostgreSQL
    conn = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="arkanito",
        database="DEV"
    )

    try:
        # Crear un cursor para ejecutar consultas
        cursor = conn.cursor()

        # Consulta SQL para obtener el DOMICILIO para el ID_RECLAMO especificado
        query = """
        SELECT "DOMICILIO"
        FROM public."RECLAMOS"
        WHERE "ID_RECLAMO" = %s
        """

        # Ejecutar la consulta con el ID_RECLAMO proporcionado
        cursor.execute(query, (id_reclamo,))
        domicilio = cursor.fetchone()

        if domicilio is not None:
            domicilio = domicilio[0]
        else:
            domicilio = "No encontrado"

        # Cerrar el cursor y la conexión
        cursor.close()
        conn.close()

        return jsonify({'domicilio': domicilio})

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/guardar_informe', methods=['POST'])
def guardar_informe():
    id_reclamo = request.form.get('idReclamo')
    fecha = request.form.get('fecha')
    especies = request.form.get('especies')
    cantidad = request.form.get('cantidad')
    motivo = request.form.get('motivo')
    resolucion = request.form.get('resolucion')
    domicilio = request.form.get('domicilio')  # Obtener el valor del domicilio
    agente = request.form.get('agente')
    tarea = request.form.get('tarea')
    otros = request.form.get('otros')

    print(request.form)  # Esto imprimirá los datos recibidos desde el formulario

    # Realiza la inserción en la tabla "INFORMES"
    insercion_sql = """
    INSERT INTO public."INFORMES" ("FECHA", "ID_RECLAMO", "DOMICILIO", "ESPECIES", "CANTIDAD", "MOTIVO", "RESOLUCION", "AGENTE", "TAREA", "OTROS")
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    try:
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="arkanito",
            database="DEV"
        )
        cursor = conn.cursor()

        # Obtener el DOMICILIO
        consulta_domicilio_sql = """
        SELECT "DOMICILIO"
        FROM public."RECLAMOS"
        WHERE "ID_RECLAMO" = %s;
        """
        cursor.execute(consulta_domicilio_sql, (id_reclamo,))
        domicilio = cursor.fetchone()[0]

        # Ejecutar la inserción
        cursor.execute(insercion_sql, (fecha, id_reclamo, domicilio, especies, cantidad, motivo, resolucion, agente, tarea, otros))
        conn.commit()

        cursor.close()
        conn.close()

        # Puedes agregar un punto de control aquí para verificar que la inserción se haya realizado con éxito
        print("Informe guardado exitosamente")

        return jsonify({'mensaje': 'Informe guardado exitosamente'})

    except Exception as e:
        # Puedes agregar un punto de control aquí para verificar cualquier error que ocurra
        print("Error al guardar el informe:", str(e))
        return jsonify({'error': str(e)})


@app.route('/generar_informe_desde_db', methods=['GET'])
def generar_informe_desde_db():
    try:
        # Obtén el ID_RECLAMO (puedes pasarlo como parámetro GET en la URL)
        id_reclamo = request.args.get('id_reclamo')

        # Realiza la consulta en la base de datos para obtener los datos necesarios
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="arkanito",
            database="DEV"
        )
        cursor = conn.cursor()

        cursor.execute('''
            SELECT i."FECHA", i."DOMICILIO", i."ESPECIES", i."CANTIDAD", i."MOTIVO", i."RESOLUCION", i."AGENTE", i."TAREA", i."OTROS", r."DISTRITO"
            FROM public."INFORMES" i
            INNER JOIN public."RECLAMOS" r ON i."ID_RECLAMO" = r."ID_RECLAMO"
            WHERE i."ID_RECLAMO" = %s
        ''', (id_reclamo,))

        # Recupera los datos de la consulta
        row = cursor.fetchone()
        if not row:
            raise Exception('No se encontraron datos para el ID_RECLAMO proporcionado.')

        fecha, domicilio, especies, cantidad, motivo, resolucion, agente, tarea, otros, distrito = row

        # Crear el objeto Canvas para generar el PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)

        # Ruta a la imagen en el sistema de archivos local
        image_path = "C:/Users/Guaymallen/PycharmProjects/sistema funcionando - ok al 29-08/static/guayma.jpg"

        # Agregar imagen al PDF
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.drawImage(image_path, 30, 700, width=550, height=100)  # Ajusta las coordenadas y el tamaño

        # Agregar el título al PDF
        titulo = f'Informe de Inspección - Nota: {id_reclamo}'
        pdf.setFont("Helvetica-Bold", 16)  # Establece el título en negrita y el tamaño
        pdf.drawString(200, 670, titulo)  # Ajusta las coordenadas para el título

        # Establecer la fuente y el tamaño para el contenido del texto principal
        pdf.setFont("Helvetica", 12)  # Establece la fuente y el tamaño del contenido

        # Establecer el margen derecho
        margen_derecho = 400  # Ajusta esta coordenada X según tus preferencias

        # Definir la variable max_caracteres_por_linea antes de usarla
        max_caracteres_por_linea = 80  # Ajusta según tus preferencias

        # Definir la posición vertical inicial
        y_position = 600  # Ajusta la coordenada "y" según tus preferencias

        # Agregar el texto principal al PDF
        if especies == "EL ÁRBOL YA HA SIDO EXTRAÍDO":
            contenido = f'La inspección realizada en el día {fecha} en el domicilio {domicilio},{distrito} verifica ' \
                        f'\nque el árbol ya ha sido extraído. Por lo tanto se sugiere:'
        elif especies == "DOMICILIO":
            contenido = f'La inspección realizada en el día {fecha} en el domicilio {domicilio},{distrito} no fue efectuada ' \
                        f'por no encontrarse la dirección.'
        else:
            if cantidad == 1:
                contenido = f'La inspección realizada en el día {fecha} en el domicilio {domicilio},{distrito} verifica ' \
                            f'\nla presencia de {cantidad} ejemplar de {especies}.\nEl mismo se encuentra {motivo}, ' \
                            f'por lo tanto se sugiere por resolución:{resolucion} realizar:'
            else:
                contenido = f'La inspección realizada en la fecha {fecha} en el domicilio {domicilio},{distrito} verifica ' \
                            f'\nla presencia de {cantidad} ejemplares de {especies}.\nLos mismos se encuentran {motivo}, ' \
                            f'por lo tanto se sugiere por resolución:{resolucion} realizar:'

        # Divide el contenido en líneas de un máximo de X caracteres
        contenido_dividido = textwrap.wrap(contenido, max_caracteres_por_linea)

        # Luego, puedes agregar las líneas al PDF
        for linea in contenido_dividido:
            pdf.drawString(30, y_position, linea)  # Ajusta las coordenadas para el texto
            y_position -= 20  # Ajusta el espaciado entre líneas


        # Luego, agrega el texto "tarea" con un salto de línea si es largo
        pdf.setFont("Helvetica", 12)  # Ajusta la fuente y el tamaño

        # Agrega un punto al final del texto de "tarea" si no está vacío
        if tarea:
            tarea += '.\n'

        # Divide el texto de "tarea" en líneas en función de los espacios en blanco
        lineas_tarea = []
        linea_actual = ''

        for palabra in tarea.split():
            if len(linea_actual) + len(palabra) + 1 <= max_caracteres_por_linea:
                # Agrega la palabra a la línea actual
                if linea_actual:
                    linea_actual += ' ' + palabra
                else:
                    linea_actual = palabra
            else:
                # La palabra no cabe en la línea actual, agrega la línea actual a la lista y comienza una nueva línea
                lineas_tarea.append(linea_actual)
                linea_actual = palabra

        # Agrega la última línea (si existe)
        if linea_actual:
            lineas_tarea.append(linea_actual)

        # Ajusta las coordenadas iniciales para el texto de "tarea"
        x_position = 30  # Ajusta la coordenada "x" según tus preferencias

        # Dibuja cada línea del texto de "tarea" en el PDF
        for linea in lineas_tarea:
            pdf.drawString(x_position, y_position, linea)
            y_position -= 20  # Ajusta el espaciado entre líneas

        # Agregar el texto al medio
        mensaje_medio = f'{otros}'  # Agrega un punto al final del texto
        pdf.setFont("Helvetica", 12)  # Ajusta la fuente y el tamaño

        # Divide el mensaje en líneas en función de los espacios en blanco
        lineas_otros = []
        linea_actual = ''

        for palabra in mensaje_medio.split():
            if len(linea_actual) + len(palabra) + 1 <= max_caracteres_por_linea:
                # Agrega la palabra a la línea actual
                if linea_actual:
                    linea_actual += ' ' + palabra
                else:
                    linea_actual = palabra
            else:
                # La palabra no cabe en la línea actual, agrega la línea actual a la lista y comienza una nueva línea
                lineas_otros.append(linea_actual)
                linea_actual = palabra

        # Agrega la última línea (si existe)
        if linea_actual:
            lineas_otros.append(linea_actual)

        # Ajusta las coordenadas iniciales para el texto de "otros"
        x_position = 30  # Ajusta la coordenada "x" según tus preferencias
        y_position = 500  # Ajusta la coordenada "y" según tus preferencias

        # Dibuja cada línea del texto de "otros" en el PDF
        for linea in lineas_otros:
            pdf.drawString(x_position, y_position, linea)
            y_position -= 20  # Ajusta el espaciado entre líneas

        # Agregar el texto al final de la página
        mensaje_final = f'La inspección fue realizada por el inspector {agente}.'
        pdf.drawString(150, 400, mensaje_final)  # Ajusta las coordenadas para el mensaje final

        # Agregar el texto adicional debajo de "La inspección fue realizada por el inspector..."
        texto_adicional = f'Guaymallén,_________________ de 2023.'
        pdf.setFont("Helvetica", 12)  # Ajusta la fuente y el tamaño para el texto adicional
        pdf.drawString(300, 360, texto_adicional)  # Ajusta las coordenadas para el texto adicional

        # Agregar el texto adicional debajo de "La inspección fue realizada por el inspector..."
        texto_adicional1 = f'En el día de la fecha se realizó la tarea.'
        pdf.setFont("Helvetica", 12)  # Ajusta la fuente y el tamaño para el texto adicional
        pdf.drawString(320, 340, texto_adicional1)  # Ajusta las coordenadas para el texto adicional

        pdf.save()  # Guarda el PDF

        buffer.seek(0)

        return send_file(buffer, as_attachment=True, download_name='informe.pdf', mimetype='application/pdf')

    except Exception as e:
        return jsonify({'error': str(e)})


@app.route("/pendientes_excel", methods=["GET"])
def pendientes_excel():
    agente = request.args.get('agente')

    if request.method == "GET" and "download" in request.args:
        try:
            # Conéctate a la base de datos
            conn = psycopg2.connect(
                host="localhost",
                user="postgres",
                password="arkanito",
                database="DEV"
            )
            cursor = conn.cursor()

            # Ejecuta la consulta SQL
            if agente:
                cursor.execute('''
                    SELECT "ID_RECLAMO", "NUM_RECLAMO","MOTIVO", "DOMICILIO", "AGENTE", "DISTRITO"
                    FROM public."RECLAMOS"
                    WHERE "ID_RECLAMO" NOT IN (SELECT "ID_RECLAMO" FROM public."INFORMES")
                    AND "AGENTE" = %s;
                ''', (agente,))
            else:
                cursor.execute('''
                    SELECT "ID_RECLAMO", "NUM_RECLAMO", "MOTIVO", "DOMICILIO", "AGENTE", "DISTRITO"
                    FROM public."RECLAMOS"
                    WHERE "ID_RECLAMO" NOT IN (SELECT "ID_RECLAMO" FROM public."INFORMES");
                ''')

            # Obtén los resultados
            pendientes = cursor.fetchall()

            # Cierra la conexión a la base de datos
            cursor.close()
            conn.close()

            # Crear un archivo Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(["ID_RECLAMO", "NUM_RECLAMO","MOTIVO", "DOMICILIO", "AGENTE", "DISTRITO"])

            for pendiente in pendientes:
                ws.append(pendiente)

            # Guardar el archivo Excel en un buffer
            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)

            # Devolver el archivo Excel como una respuesta de descarga
            return send_file(buffer, as_attachment=True, download_name='pendientes.xlsx',
                             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        except Exception as e:
            return jsonify({'error': str(e)})
    else:
        # Si no se solicitó la descarga, simplemente muestra la tabla en HTML
        try:
            # Conéctate a la base de datos
            conn = psycopg2.connect(
                host="localhost",
                user="postgres",
                password="arkanito",
                database="DEV"
            )
            cursor = conn.cursor()

            # Ejecuta la consulta SQL
            if agente:
                cursor.execute('''
                    SELECT "ID_RECLAMO", "NUM_RECLAMO", "DOMICILIO", "AGENTE", "DISTRITO", "MOTIVO"
                    FROM public."RECLAMOS"
                    WHERE "ID_RECLAMO" NOT IN (SELECT "ID_RECLAMO" FROM public."INFORMES")
                    AND "AGENTE" = %s;
                ''', (agente,))
            else:
                cursor.execute('''
                    SELECT "ID_RECLAMO", "NUM_RECLAMO", "DOMICILIO", "AGENTE", "DISTRITO", "MOTIVO"
                    FROM public."RECLAMOS"
                    WHERE "ID_RECLAMO" NOT IN (SELECT "ID_RECLAMO" FROM public."INFORMES");
                ''')

            # Obtén los resultados
            pendientes = cursor.fetchall()

            # Cierra la conexión a la base de datos
            cursor.close()
            conn.close()

            # Renderiza la plantilla HTML y pasa los resultados como contexto
            return render_template('ver_pendientes.html', pendientes=pendientes)

        except Exception as e:
            return jsonify({'error': str(e)})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)





