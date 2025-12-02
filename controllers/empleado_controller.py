from flask import Blueprint, render_template, request, redirect, url_for,flash
from models.database import get_db_connection
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import send_file
import datetime

empleado_controller = Blueprint('empleado_controller', __name__, url_prefix='/empleado')

# ----------------------------
# DASHBOARD empleado = VER PRODUCTOS
# ----------------------------
@empleado_controller.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    productos = conn.execute("""
        SELECT id, nombre, descripcion, precio, stock, imagen
        FROM producto
    """).fetchall()
    conn.close()

    productos_lista = [dict(p) for p in productos]
    return render_template('empleado/productos.html', productos=productos_lista)

# ----------------------------
# FORMULARIO AGREGAR PRODUCTO
# ----------------------------
@empleado_controller.route('/agregar_producto', methods=['GET'])
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
    return render_template("empleado/agregar_producto.html", proveedores=proveedores, categorias=categorias)


# ----------------------------
# GUARDAR PRODUCTO EN BD
# ----------------------------
@empleado_controller.route('/agregar_producto', methods=['POST'])
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

    return redirect(url_for("empleado_controller.dashboard"))


# ----------------------------
# LISTAR TODAS LAS VENTAS
# ----------------------------
@empleado_controller.route('/ventas')
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

    return render_template("empleado/ventas.html", ventas=ventas, detalles=detalles)


# ------------------------------------
# GENERAR REPORTE PDF DE TODAS LAS VENTAS
# ------------------------------------
@empleado_controller.route("/ventas/reporte")
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


# ------------------------------------------
# VER LISTA DE PEDIDOS PENDIENTES
# ------------------------------------------
@empleado_controller.route("/empleado/pedidos")
def listar_pedidos():
    conn = get_db_connection()
    pedidos = conn.execute("""
        SELECT p.*, u.usuario AS cliente 
        FROM pedido p
        JOIN usuario u ON p.cliente_id = u.id
        WHERE p.estado = 'espera'
        ORDER BY p.fecha DESC
    """).fetchall()
    conn.close()

    return render_template("empleado/aprobar_pedidos.html", pedidos=pedidos)


# ------------------------------------------
# APROBAR PEDIDO → PASA A VENTA
# ------------------------------------------
@empleado_controller.route("/empleado/pedidos/aprobar/<int:pedido_id>", methods=["POST"])
def aprobar_pedido(pedido_id):
    conn = get_db_connection()

    # Obtener pedido y sus detalles
    pedido = conn.execute("SELECT * FROM pedido WHERE id = ?", (pedido_id,)).fetchone()
    detalles = conn.execute("SELECT * FROM detalle_pedido WHERE pedido_id = ?", (pedido_id,)).fetchall()

    # Cambiar estado
    conn.execute("UPDATE pedido SET estado = 'confirmado' WHERE id = ?", (pedido_id,))

    # Registrar la venta
    conn.execute("""
        INSERT INTO venta (pedido_id, tipo_pago_id, fecha, total)
        VALUES (?, ?, ?, ?)
    """, (pedido_id, 1, datetime.now().strftime("%Y-%m-%d"), pedido["total"]))

    venta_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Registrar detalle venta
    for d in detalles:
        conn.execute("""
            INSERT INTO detalle_venta (venta_id, producto_id, cantidad, precio)
            VALUES (?, ?, ?, ?)
        """, (venta_id, d["producto_id"], d["cantidad"], d["precio"]))

    conn.commit()
    conn.close()

    flash("Pedido aprobado correctamente.", "success")
    return redirect(url_for("empleado_controller.listar_pedidos"))
