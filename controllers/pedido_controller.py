from flask import Blueprint, render_template, redirect, url_for, request, flash
from models.database import get_db_connection
from datetime import datetime

pedido_controller = Blueprint('pedido_controller', __name__)

# ------------------------------------------
# VER LISTA DE PEDIDOS PENDIENTES
# ------------------------------------------
@pedido_controller.route("/admin/pedidos")
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

    return render_template("admin/aprobar_pedidos.html", pedidos=pedidos)


# ------------------------------------------
# APROBAR PEDIDO → PASA A VENTA
# ------------------------------------------
@pedido_controller.route("/admin/pedidos/aprobar/<int:pedido_id>", methods=["POST"])
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
    return redirect(url_for("pedido_controller.listar_pedidos"))
