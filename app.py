from flask import Flask
from config import Config
from models.database import create_tables

def create_app():
    app = Flask(
        __name__,
        template_folder='views',   # <-- carpeta para tus HTML
        static_folder='static'     # <-- carpeta para archivos estáticos
    )

    app.config.from_object(Config)

    # Blueprints
    from controllers.auth_controller import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    from controllers.cliente_controller import cliente_controller
    app.register_blueprint(cliente_controller, url_prefix='/cliente')
    
    from controllers.pedido_controller import pedido_controller
    app.register_blueprint(pedido_controller, url_prefix='/aprobar_pedidos')

    from controllers.admin_controller import admin_controller
    app.register_blueprint(admin_controller, url_prefix='/admin')
    
    from controllers.empleado_controller import empleado_controller
    app.register_blueprint(empleado_controller, url_prefix='/empleado')
    
    # Crear tablas si no existen
    with app.app_context():
        create_tables()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
