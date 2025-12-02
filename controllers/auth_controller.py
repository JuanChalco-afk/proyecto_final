from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from models.database import get_db_connection
import sqlite3

bp = Blueprint('auth_controller', __name__)

# ---------------- HOME (página inicial con botón "Ingresar") ----------------
@bp.route('/')
def home():
    # renderiza view/dashboard/index.html que es la página inicial blanca con botón
    return render_template('dashboard/index.html')

# ---------------- LOGIN ----------------
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email  = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM usuario WHERE email = ?", (email ,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            # Guardar sesión
            session['user_id'] = user['id']
            session['role_id'] = user['role_id']
            session['usuario'] = user['usuario']

            # Redirigir según rol:
            if user['role_id'] == 1:      # admin
                return redirect(url_for('auth_controller.admin_dashboard'))
            elif user['role_id'] == 2:    # empleado
                return redirect(url_for('auth_controller.empleado_dashboard'))
            elif user['role_id'] == 3:    # cliente
                return redirect(url_for('auth_controller.cliente_dashboard'))
            else:
                flash("Rol no reconocido. Contacta al administrador.")
                return redirect(url_for('auth_controller.login'))
        else:
            flash("Correo  o contraseña incorrectos.")
            return redirect(url_for('auth_controller.login'))

    return render_template('auth/login.html')

# ---------------- REGISTRO CLIENTE ----------------
@bp.route('/registro', methods=['GET', 'POST'])
def registro_cliente():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        email = request.form.get('email', '').strip()
        telefono = request.form.get('telefono', '').strip()
        direccion = request.form.get('direccion', '').strip()
        password_raw = request.form.get('password', '').strip()

        if not usuario or not email or not telefono or not direccion or not password_raw:
            flash("Completa todos los campos.")
            return redirect(url_for('auth_controller.registro_cliente'))

        hashed = generate_password_hash(password_raw)

        conn = get_db_connection()
        try:
            # Rol cliente = 3
            conn.execute("""
                INSERT INTO usuario (usuario, email, telefono, direccion, password, role_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (usuario, email, telefono, direccion, hashed, 3))
            conn.commit()

            flash("Cuenta creada correctamente. Ya puedes iniciar sesión.")
            return redirect(url_for('auth_controller.login'))

        except sqlite3.IntegrityError:
            flash("El usuario o correo ya está registrado.")
            return redirect(url_for('auth_controller.registro_cliente'))

        finally:
            conn.close()

    return render_template('auth/registro_cliente.html')


# ---------------- DASHBOARDS ----------------
@bp.route('/admin')
def admin_dashboard():
    # protegido de forma simple: si no hay sesión redirige a login
    if 'user_id' not in session:
        flash("Debes iniciar sesión.")
        return redirect(url_for('auth_controller.login'))
    return render_template('admin/dashboard.html')

@bp.route('/cliente')
def cliente_dashboard():
    if 'user_id' not in session:
        flash("Debes iniciar sesión.")
        return redirect(url_for('auth_controller.login'))
    return redirect(url_for('cliente_controller.dashboard'))


@bp.route('/empleado')
def empleado_dashboard():
    if 'user_id' not in session:
        flash("Debes iniciar sesión.")
        return redirect(url_for('auth_controller.login'))
    return render_template('empleado/dashboard.html')

# ---------------- LOGOUT (opcional) ----------------
@bp.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada.")
    return redirect(url_for('auth_controller.home'))
