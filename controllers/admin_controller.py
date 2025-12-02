from flask import Blueprint, render_template, request, redirect, url_for,session
from models.database import get_db_connection
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import send_file
import datetime

admin_controller = Blueprint('admin_controller', __name__, url_prefix='/admin')


# ----------------------------
# DASHBOARD ADMIN = VER PRODUCTOS
# ----------------------------
@admin_controller.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    productos = conn.execute("""
        SELECT id, nombre, descripcion, precio, stock, imagen
        FROM producto
    """).fetchall()
    conn.close()

    productos_lista = [dict(p) for p in productos]
    return render_template('admin/productos.html', productos=productos_lista)

# ----------------------------
# FORMULARIO AGREGAR PRODUCTO
# ----------------------------
@admin_controller.route('/agregar_producto', methods=['GET'])
def form_agregar_producto():
    conn = get_db_connection()

    # Traer proveedores (role_id=4)
    proveedores = conn.execute("""
        SELECT id, usuario FROM usuario WHERE role_id=4
    """).fetchall()

    # Traer categorías
    categorias = conn.execute("""
        SELECT id, nombre FROM categoria
    """).fetchall()

    conn.close()
    return render_template("admin/agregar_producto.html", proveedores=proveedores, categorias=categorias)


# ----------------------------
# GUARDAR PRODUCTO EN BD
# ----------------------------
@admin_controller.route('/agregar_producto', methods=['POST'])
def agregar_producto():
    nombre = request.form.get("nombre")
    descripcion = request.form.get("descripcion")
    precio = float(request.form.get("precio"))
    stock = int(request.form.get("stock"))
    imagen_file = request.files.get("imagen")

    # --- guardar imagen ---
    if imagen_file:
        uploads_path = "static/uploads"
        if not os.path.exists(uploads_path):
            os.makedirs(uploads_path)

        filename = imagen_file.filename
        save_path = os.path.join(uploads_path, filename)
        imagen_file.save(save_path)

        # Guardamos solo el nombre del archivo
        ruta_imagen = filename
    else:
        ruta_imagen = ""

    # Guardar en BD 
    conn = get_db_connection()
    proveedor_id = int(request.form.get("proveedor_id"))
    categoria_id = int(request.form.get("categoria_id"))

    conn.execute("""
        INSERT INTO producto (nombre, descripcion, precio, stock, imagen, proveedor_id, categoria_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (nombre, descripcion, precio, stock, ruta_imagen, proveedor_id, categoria_id))


    conn.commit()
    conn.close()

    return redirect(url_for("admin_controller.dashboard"))


# ----------------------------
# LISTAR TODAS LAS VENTAS
# ----------------------------
@admin_controller.route('/ventas')
def listar_ventas():
    conn = get_db_connection()

    ventas = conn.execute("""
        SELECT v.id, v.fecha, v.total, u.usuario AS cliente, tp.nombre AS tipo_pago
        FROM venta v
        JOIN pedido p ON v.pedido_id = p.id
        JOIN usuario u ON p.cliente_id = u.id
        JOIN tipo_pago tp ON v.tipo_pago_id = tp.id
        ORDER BY v.fecha DESC
    """).fetchall()

    # Traer detalles de cada venta
    detalles = {}
    for v in ventas:
        filas = conn.execute("""
            SELECT dv.cantidad, dv.precio, pr.nombre
            FROM detalle_venta dv
            JOIN producto pr ON dv.producto_id = pr.id
            WHERE dv.venta_id = ?
        """, (v["id"],)).fetchall()

        detalles[v["id"]] = filas

    conn.close()

    return render_template("admin/ventas.html", ventas=ventas, detalles=detalles)


# ------------------------------------
# GENERAR REPORTE PDF DE TODAS LAS VENTAS
# ------------------------------------
@admin_controller.route("/ventas/reporte")
def reporte_ventas():
    conn = get_db_connection()

    ventas = conn.execute("""
        SELECT v.id, v.fecha, v.total, u.usuario AS cliente, tp.nombre AS tipo_pago
        FROM venta v
        JOIN pedido p ON v.pedido_id = p.id
        JOIN usuario u ON p.cliente_id = u.id
        JOIN tipo_pago tp ON v.tipo_pago_id = tp.id
        ORDER BY v.fecha DESC
    """).fetchall()

    detalles_dict = {}
    for v in ventas:
        detalles = conn.execute("""
            SELECT dv.cantidad, dv.precio, pr.nombre
            FROM detalle_venta dv
            JOIN producto pr ON dv.producto_id = pr.id
            WHERE dv.venta_id = ?
        """, (v["id"],)).fetchall()

        detalles_dict[v["id"]] = detalles

    conn.close()

    # Crear PDF
    ruta_carpeta = "static/reportes"
    if not os.path.exists(ruta_carpeta):
        os.makedirs(ruta_carpeta)

    filename = os.path.join(
        ruta_carpeta,
        f"reporte_ventas_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    pdf = canvas.Canvas(filename, pagesize=letter)
    pdf.setFont("Helvetica", 10)

    y = 750
    pdf.drawString(220, 780, "REPORTE DE VENTAS - HARDNET")

    for v in ventas:
        if y < 80:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = 750

        pdf.drawString(50, y, f"Venta #{v['id']} | Fecha: {v['fecha']} | Cliente: {v['cliente']} | Pago: {v['tipo_pago']} | Total: ${v['total']}")
        y -= 15

        for d in detalles_dict[v["id"]]:
            pdf.drawString(80, y, f"- {d['nombre']} | Cant: {d['cantidad']} | Precio: ${d['precio']}")
            y -= 13

        y -= 10  # espacio entre ventas

    pdf.save()

    return send_file(filename, as_attachment=True)


# ------------------------------------
# LISTA DE CLIENTES
# ------------------------------------
@admin_controller.route("/clientes")
def clientes():
    conn = get_db_connection()
    clientes = conn.execute("""
        SELECT id, usuario, email, telefono, direccion
        FROM usuario
        WHERE role_id = 3   -- solo clientes
    """).fetchall()
    conn.close()

    return render_template("admin/clientes.html", clientes=clientes)


# ------------------------------------
# FORMULARIO CREAR CLIENTE
# ------------------------------------
@admin_controller.route("/clientes/crear", methods=["GET"])
def crear_cliente_form():
    return render_template("admin/crear_cliente.html")


from werkzeug.security import generate_password_hash

@admin_controller.route("/clientes/crear", methods=["POST"])
def crear_cliente():
    usuario = request.form.get("usuario")
    email = request.form.get("email")
    telefono = request.form.get("telefono")
    direccion = request.form.get("direccion")
    password = generate_password_hash(request.form.get("password"))

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO usuario (usuario, email, telefono, direccion, password, role_id)
        VALUES (?, ?, ?, ?, ?, 3)
    """, (usuario, email, telefono, direccion, password))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_controller.clientes"))


@admin_controller.route("/clientes/eliminar/<int:id>")
def eliminar_cliente(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM usuario WHERE id = ? AND role_id = 3", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_controller.clientes"))


@admin_controller.route("/clientes/editar/<int:id>")
def editar_cliente_form(id):
    conn = get_db_connection()
    cliente = conn.execute("""
        SELECT * FROM usuario WHERE id = ? AND role_id = 3
    """, (id,)).fetchone()
    conn.close()

    return render_template("admin/editar_cliente.html", cliente=cliente)

@admin_controller.route("/clientes/editar/<int:id>", methods=["POST"])
def editar_cliente(id):
    usuario = request.form.get("usuario")
    email = request.form.get("email")
    telefono = request.form.get("telefono")
    direccion = request.form.get("direccion")

    conn = get_db_connection()
    conn.execute("""
        UPDATE usuario
        SET usuario=?, email=?, telefono=?, direccion=?
        WHERE id=? AND role_id=3
    """, (usuario, email, telefono, direccion, id))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_controller.clientes"))

# ------------------------------------
# LISTA DE EMPLEADOS
# ------------------------------------
@admin_controller.route("/empleados")
def empleados():
    conn = get_db_connection()
    empleados = conn.execute("""
        SELECT id, usuario, email, telefono, direccion
        FROM usuario
        WHERE role_id = 2   -- solo empleados
    """).fetchall()
    conn.close()
    return render_template("admin/empleados.html", empleados=empleados)

@admin_controller.route("/empleados/crear", methods=["GET"])
def crear_empleado_form():
    return render_template("admin/crear_empleado.html")

@admin_controller.route("/empleados/crear", methods=["POST"])
def crear_empleado():
    usuario = request.form.get("usuario")
    email = request.form.get("email")
    telefono = request.form.get("telefono")
    direccion = request.form.get("direccion")
    password = generate_password_hash(request.form.get("password"))

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO usuario (usuario, email, telefono, direccion, password, role_id)
        VALUES (?, ?, ?, ?, ?, 2)
    """, (usuario, email, telefono, direccion, password))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_controller.empleados"))

@admin_controller.route("/empleados/eliminar/<int:id>")
def eliminar_empleado(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM usuario WHERE id = ? AND role_id = 2", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_controller.empleados"))

@admin_controller.route("/empleados/editar/<int:id>")
def editar_empleado_form(id):
    conn = get_db_connection()
    empleado = conn.execute("""
        SELECT * FROM usuario WHERE id = ? AND role_id = 2
    """, (id,)).fetchone()
    conn.close()
    return render_template("admin/editar_empleado.html", empleado=empleado)


@admin_controller.route("/empleados/editar/<int:id>", methods=["POST"])
def editar_empleado(id):
    usuario = request.form.get("usuario")
    email = request.form.get("email")
    telefono = request.form.get("telefono")
    direccion = request.form.get("direccion")

    conn = get_db_connection()
    conn.execute("""
        UPDATE usuario
        SET usuario=?, email=?, telefono=?, direccion=?
        WHERE id=? AND role_id=2
    """, (usuario, email, telefono, direccion, id))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_controller.empleados"))


# ------------------------------------
# LISTA DE PROVEEDORES
# ------------------------------------
@admin_controller.route("/proveedores")
def proveedores():
    conn = get_db_connection()
    proveedores = conn.execute("""
        SELECT id, usuario, email, telefono, direccion
        FROM usuario
        WHERE role_id = 4
    """).fetchall()
    conn.close()
    return render_template("admin/proveedores.html", proveedores=proveedores)

@admin_controller.route("/proveedores/crear", methods=["GET"])
def crear_proveedor_form():
    return render_template("admin/crear_proveedor.html")

@admin_controller.route("/proveedores/crear", methods=["POST"])
def crear_proveedor():
    usuario = request.form.get("usuario")
    email = request.form.get("email")
    telefono = request.form.get("telefono")
    direccion = request.form.get("direccion")
    password = generate_password_hash(request.form.get("password"))

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO usuario (usuario, email, telefono, direccion, password, role_id)
        VALUES (?, ?, ?, ?, ?, 4)
    """, (usuario, email, telefono, direccion, password))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_controller.proveedores"))

@admin_controller.route("/proveedores/eliminar/<int:id>")
def eliminar_proveedor(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM usuario WHERE id = ? AND role_id = 4", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_controller.proveedores"))

@admin_controller.route("/proveedores/editar/<int:id>")
def editar_proveedor_form(id):
    conn = get_db_connection()
    proveedor = conn.execute("""
        SELECT * FROM usuario WHERE id = ? AND role_id = 4
    """, (id,)).fetchone()
    conn.close()
    return render_template("admin/editar_proveedor.html", proveedor=proveedor)

@admin_controller.route("/proveedores/editar/<int:id>", methods=["POST"])
def editar_proveedor(id):
    usuario = request.form.get("usuario")
    email = request.form.get("email")
    telefono = request.form.get("telefono")
    direccion = request.form.get("direccion")

    conn = get_db_connection()
    conn.execute("""
        UPDATE usuario
        SET usuario=?, email=?, telefono=?, direccion=?
        WHERE id=? AND role_id=4
    """, (usuario, email, telefono, direccion, id))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_controller.proveedores"))


# ------------------------------------
# LISTAR CATEGORIAS
# ------------------------------------
@admin_controller.route("/categorias")
def categorias():
    conn = get_db_connection()
    categorias = conn.execute("""
        SELECT id, nombre, descripcion FROM categoria
    """).fetchall()
    conn.close()
    return render_template("admin/categorias.html", categorias=categorias)

# ------------------------------------
# FORMULARIO CREAR CATEGORIA
# ------------------------------------
@admin_controller.route("/categorias/crear", methods=["GET"])
def crear_categoria_form():
    return render_template("admin/crear_categoria.html")

# ------------------------------------
# GUARDAR NUEVA CATEGORIA
# ------------------------------------
@admin_controller.route("/categorias/crear", methods=["POST"])
def crear_categoria():
    nombre = request.form.get("nombre")
    descripcion = request.form.get("descripcion")

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO categoria (nombre, descripcion)
        VALUES (?, ?)
    """, (nombre, descripcion))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_controller.categorias"))

# ------------------------------------
# FORMULARIO EDITAR CATEGORIA
# ------------------------------------
@admin_controller.route("/categorias/editar/<int:id>", methods=["GET"])
def editar_categoria_form(id):
    conn = get_db_connection()
    categoria = conn.execute("SELECT * FROM categoria WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template("admin/editar_categoria.html", categoria=categoria)

# ------------------------------------
# ACTUALIZAR CATEGORIA
# ------------------------------------
@admin_controller.route("/categorias/editar/<int:id>", methods=["POST"])
def editar_categoria(id):
    nombre = request.form.get("nombre")
    descripcion = request.form.get("descripcion")

    conn = get_db_connection()
    conn.execute("""
        UPDATE categoria
        SET nombre=?, descripcion=?
        WHERE id=?
    """, (nombre, descripcion, id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_controller.categorias"))

# ------------------------------------
# ELIMINAR CATEGORIA
# ------------------------------------
@admin_controller.route("/categorias/eliminar/<int:id>")
def eliminar_categoria(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM categoria WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_controller.categorias"))
