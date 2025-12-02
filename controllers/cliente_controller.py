from flask import Blueprint, render_template, session, redirect, url_for, request
from models.database import get_db_connection
from datetime import datetime
import os

cliente_controller = Blueprint('cliente_controller', __name__, url_prefix='/cliente')


# ----------------------------
# DASHBOARD DE PRODUCTOS
# ----------------------------
@cliente_controller.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    productos = conn.execute("""
        SELECT id, nombre, descripcion, precio, stock, imagen
        FROM producto
    """).fetchall()
    conn.close()

    productos_lista = [dict(p) for p in productos]
    return render_template('cliente/dashboard.html', productos=productos_lista)


# ----------------------------
# AGREGAR PRODUCTO AL CARRITO
# ----------------------------
@cliente_controller.route('/agregar_carrito/<int:producto_id>', methods=['POST'])
def agregar_carrito(producto_id):
    carrito = session.get('carrito', {})
    key = str(producto_id)  # LLAVES SIEMPRE STRING
    carrito[key] = carrito.get(key, 0) + 1
    session['carrito'] = carrito
    return redirect(url_for('cliente_controller.dashboard'))


# ----------------------------
# VER CARRITO
# ----------------------------
@cliente_controller.route('/carrito')
def carrito():
    carrito = session.get('carrito', {})
    if not carrito:
        return render_template('cliente/carrito.html', productos=[], total=0)

    conn = get_db_connection()
    productos = []
    total = 0

    for producto_id_str, cantidad in carrito.items():
        producto_id = int(producto_id_str)
        prod = conn.execute("""
            SELECT id, nombre, precio, imagen
            FROM producto
            WHERE id = ?
        """, (producto_id,)).fetchone()
        if prod:
            prod = dict(prod)
            prod["cantidad"] = cantidad
            prod["subtotal"] = cantidad * prod["precio"]
            total += prod["subtotal"]
            productos.append(prod)
    conn.close()

    return render_template('cliente/carrito.html', productos=productos, total=total)


# ----------------------------
# MOSTRAR FORMULARIO REALIZAR PEDIDO
# ----------------------------
@cliente_controller.route('/realizar_pedido', methods=['GET'])
def mostrar_realizar_pedido():
    carrito = session.get('carrito', {})
    if not carrito:
        return redirect(url_for('cliente_controller.dashboard'))

    conn = get_db_connection()
    productos = []
    total = 0

    for producto_id_str, cantidad in carrito.items():
        producto_id = int(producto_id_str)
        prod = conn.execute("""
            SELECT id, nombre, precio, imagen
            FROM producto
            WHERE id = ?
        """, (producto_id,)).fetchone()
        if prod:
            prod = dict(prod)
            prod["cantidad"] = cantidad
            prod["subtotal"] = cantidad * prod["precio"]
            total += prod["subtotal"]
            productos.append(prod)
    conn.close()

    tipos_pago = ['Efectivo', 'Tarjeta', 'Transferencia']
    return render_template('cliente/realizar_pedido.html', productos=productos, total=total, tipos_pago=tipos_pago)


# ----------------------------
# PROCESAR REALIZAR PEDIDO
# ----------------------------
@cliente_controller.route('/realizar_pedido', methods=['POST'])
def procesar_realizar_pedido():
    carrito = session.get('carrito', {})
    cliente_id = session.get('user_id')

    if not carrito or not cliente_id:
        return redirect(url_for('cliente_controller.dashboard'))

    direccion_entrega = request.form.get('direccion_entrega')
    tipo_pago = request.form.get('tipo_pago')
    comprobante_file = request.files.get('comprobante')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Calcular total
    total = 0
    for producto_id_str, cantidad in carrito.items():
        producto_id = int(producto_id_str)
        precio = cursor.execute("SELECT precio FROM producto WHERE id = ?", (producto_id,)).fetchone()['precio']
        total += precio * cantidad

    # Insertar pedido en estado 'espera'
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO pedido (cliente_id, fecha, total, estado, direccion_entrega)
        VALUES (?, ?, ?, 'espera', ?)
    """, (cliente_id, fecha_actual, total, direccion_entrega))
    pedido_id = cursor.lastrowid

    # Insertar detalle del pedido
    for producto_id_str, cantidad in carrito.items():
        producto_id = int(producto_id_str)
        precio = cursor.execute("SELECT precio FROM producto WHERE id = ?", (producto_id,)).fetchone()['precio']
        cursor.execute("""
            INSERT INTO detalle_pedido (pedido_id, producto_id, cantidad, precio)
            VALUES (?, ?, ?, ?)
        """, (pedido_id, producto_id, cantidad, precio))

    # Guardar comprobante si aplica
    if tipo_pago in ['Tarjeta', 'Transferencia'] and comprobante_file:
        if not os.path.exists('static/pago'):
            os.makedirs('static/pago')

        filename = f"pago_{pedido_id}_{comprobante_file.filename}"
        save_path = os.path.join('static/pago', filename)
        comprobante_file.save(save_path)

        # Guardar en la base de datos el nombre del archivo
        cursor.execute("""
            UPDATE pedido SET comprobante_pago = ? WHERE id = ?
        """, (filename, pedido_id))

    conn.commit()
    conn.close()

    # Limpiar carrito
    session.pop('carrito', None)

    return redirect(url_for('cliente_controller.dashboard'))


# ----------------------------
# VER PEDIDOS DEL CLIENTE
# ----------------------------
@cliente_controller.route('/pedidos')
def pedidos():
    cliente_id = session.get('user_id')
    if not cliente_id:
        return redirect(url_for('auth_controller.login'))

    conn = get_db_connection()
    pedidos = conn.execute("""
        SELECT id, fecha, total, estado, direccion_entrega
        FROM pedido
        WHERE cliente_id = ?
        ORDER BY fecha DESC
    """, (cliente_id,)).fetchall()

    pedidos_detalles = {}
    for pedido in pedidos:
        detalles = conn.execute("""
            SELECT dp.id, pr.nombre, dp.cantidad, dp.precio
            FROM detalle_pedido dp
            JOIN producto pr ON dp.producto_id = pr.id
            WHERE dp.pedido_id = ?
        """, (pedido['id'],)).fetchall()
        pedidos_detalles[pedido['id']] = [dict(d) for d in detalles]

    conn.close()
    return render_template('cliente/pedidos.html', pedidos=pedidos, detalles=pedidos_detalles)
