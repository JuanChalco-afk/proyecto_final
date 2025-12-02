from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Debes iniciar sesión.")
            return redirect(url_for('auth_controller.login'))
        return f(*args, **kwargs)
    return wrapper

def role_required(*allowed_roles):
    """Uso: @role_required(1,2)  (1=admin,2=empleado,3=cliente)"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'role_id' not in session:
                flash("Debes iniciar sesión.")
                return redirect(url_for('auth_controller.login'))
            if session.get('role_id') not in allowed_roles:
                flash("No tienes permisos.")
                return redirect(url_for('auth_controller.login'))
            return f(*args, **kwargs)
        return wrapper
    return decorator
