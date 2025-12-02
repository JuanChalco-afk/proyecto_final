import sqlite3
from flask import current_app
from werkzeug.security import generate_password_hash
import os

def get_db_connection():
    db = sqlite3.connect(current_app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db

def create_tables():
    db_path = current_app.config['DATABASE']
    first_time = not os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.executescript("""
                    
    PRAGMA foreign_keys = ON;

    /* TABLA DE ROLES */
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL
    );

    /* TABLA USUARIO (admin, empleado, cliente, proveedor) */
    CREATE TABLE IF NOT EXISTS usuario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        telefono TEXT,
        direccion TEXT,
        password TEXT NOT NULL,
        role_id INTEGER NOT NULL,
        FOREIGN KEY(role_id) REFERENCES roles(id)
    );

    /* TABLA CATEGORIA */
    CREATE TABLE IF NOT EXISTS categoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        descripcion TEXT
    );

    /* TABLA PRODUCTO (proveedor es usuario con rol proveedor) */
    CREATE TABLE IF NOT EXISTS producto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        precio REAL NOT NULL,
        stock INTEGER DEFAULT 0,
        imagen TEXT,
        proveedor_id INTEGER NOT NULL,
        categoria_id INTEGER NOT NULL,
        FOREIGN KEY(proveedor_id) REFERENCES usuario(id),
        FOREIGN KEY(categoria_id) REFERENCES categoria(id)
    );

    /* TABLA PEDIDO (cliente es usuario con rol cliente) */
    CREATE TABLE IF NOT EXISTS pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        total REAL NOT NULL,
        estado TEXT NOT NULL CHECK (estado IN ('espera', 'confirmado')),
        direccion_entrega TEXT,
        comprobante_pago TEXT,
        FOREIGN KEY(cliente_id) REFERENCES usuario(id)
    );

    /* TABLA DETALLE PEDIDO */
    CREATE TABLE IF NOT EXISTS detalle_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL,
        precio REAL NOT NULL,
        FOREIGN KEY(pedido_id) REFERENCES pedido(id),
        FOREIGN KEY(producto_id) REFERENCES producto(id)
    );

    /* TABLA TIPO DE PAGO */
    CREATE TABLE IF NOT EXISTS tipo_pago (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE
    );

    /* TABLA VENTA */
    CREATE TABLE IF NOT EXISTS venta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL UNIQUE,
        tipo_pago_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        total REAL NOT NULL,
        FOREIGN KEY(pedido_id) REFERENCES pedido(id),
        FOREIGN KEY(tipo_pago_id) REFERENCES tipo_pago(id)
    );

    /* TABLA DETALLE VENTA */
    CREATE TABLE IF NOT EXISTS detalle_venta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL,
        precio REAL NOT NULL,
        FOREIGN KEY(venta_id) REFERENCES venta(id),
        FOREIGN KEY(producto_id) REFERENCES producto(id)
    );

    /* TABLA COMPRA (proveedor es usuario con rol proveedor) */
    CREATE TABLE IF NOT EXISTS compra (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proveedor_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        total REAL NOT NULL,
        FOREIGN KEY(proveedor_id) REFERENCES usuario(id)
    );

    /* TABLA DETALLE COMPRA */
    CREATE TABLE IF NOT EXISTS detalle_compra (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        compra_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL,
        precio REAL NOT NULL,
        FOREIGN KEY(compra_id) REFERENCES compra(id),
        FOREIGN KEY(producto_id) REFERENCES producto(id)
    );
    """)

    conn.commit()

    # ---- Datos iniciales ----
    if first_time:
        try:
            # Roles
            c.execute("INSERT OR IGNORE INTO roles (nombre) VALUES ('admin')")
            c.execute("INSERT OR IGNORE INTO roles (nombre) VALUES ('empleado')")
            c.execute("INSERT OR IGNORE INTO roles (nombre) VALUES ('cliente')")
            c.execute("INSERT OR IGNORE INTO roles (nombre) VALUES ('proveedor')")

            # Administrador por defecto
            hashed = generate_password_hash('admin123')
            c.execute("""
                INSERT OR IGNORE INTO usuario 
                (usuario,email,telefono,direccion,password,role_id) 
                VALUES (?,?,?,?,?,?)
            """, ("admin", "admin@hardnet.local", "000000000", "N/A", hashed, 1))

            # Tipos de pago
            c.execute("INSERT OR IGNORE INTO tipo_pago (nombre) VALUES ('Efectivo')")
            c.execute("INSERT OR IGNORE INTO tipo_pago (nombre) VALUES ('Tarjeta')")
            c.execute("INSERT OR IGNORE INTO tipo_pago (nombre) VALUES ('Transferencia')")

            # Categorías iniciales
            #Nuevas categorías            
            c.execute("INSERT OR IGNORE INTO categoria (nombre,descripcion) VALUES (?,?)",
                    ("Laptop", "Equipos portátiles"))
            c.execute("INSERT OR IGNORE INTO categoria (nombre,descripcion) VALUES (?,?)",
                    ("Hardware", "Componentes internos de PC"))
            
            c.execute("INSERT OR IGNORE INTO categoria (nombre, descripcion) VALUES (?,?)",
                    ("Accesorios", "Accesorios para computadoras"))
            c.execute("INSERT OR IGNORE INTO categoria (nombre, descripcion) VALUES (?,?)",
                    ("Monitores", "Pantallas LED y LCD"))
            c.execute("INSERT OR IGNORE INTO categoria (nombre, descripcion) VALUES (?,?)",
                    ("Impresoras", "Impresoras y multifuncionales"))
            c.execute("INSERT OR IGNORE INTO categoria (nombre, descripcion) VALUES (?,?)",
                    ("Redes", "Equipos de conectividad y redes"))
            c.execute("INSERT OR IGNORE INTO categoria (nombre, descripcion) VALUES (?,?)",
                    ("Periféricos", "Teclados, mouse y más"))

            # Usuario proveedor ejemplo
            hashed_prov = generate_password_hash("prov123")
            c.execute("""
                INSERT OR IGNORE INTO usuario 
                (usuario,email,telefono,direccion,password,role_id) 
                VALUES (?,?,?,?,?,?)
            """, ("techsupply", "tech@sup.com", "77777777", "Av. Central 123", hashed_prov, 4))

            # Productos iniciales
            c.execute("""
                INSERT OR IGNORE INTO producto 
                (nombre, descripcion, precio, stock, imagen, proveedor_id, categoria_id) 
                VALUES (?,?,?,?,?,?,?)
            """, ("HP Pavilion", "Laptop HP 15 pulgadas", 450.0, 5, "hp.png", 2, 1))

            c.execute("""
                INSERT OR IGNORE INTO producto 
                (nombre, descripcion, precio, stock, imagen, proveedor_id, categoria_id) 
                VALUES (?,?,?,?,?,?,?)
            """, ("SSD 512GB", "SSD SATA III 512GB", 120.0, 10, "ssd.png", 2, 2))
            
            
            # PRODUCTO 1
            c.execute("""
                INSERT OR IGNORE INTO producto 
                (nombre, descripcion, precio, stock, imagen, proveedor_id, categoria_id) 
                VALUES (?,?,?,?,?,?,?)
            """, ("Memoria RAM 16GB", "DDR4 3200MHz", 75.0, 20, "ram16.png", 2, 2))
            
            # PRODUCTO 2
            c.execute("""
                INSERT OR IGNORE INTO producto 
                (nombre, descripcion, precio, stock, imagen, proveedor_id, categoria_id) 
                VALUES (?,?,?,?,?,?,?)
            """, ("Mouse Logitech G203", "Mouse gamer RGB", 28.0, 15, "g203.png", 2, 4))
            
            # PRODUCTO 3
            c.execute("""
                INSERT OR IGNORE INTO producto 
                (nombre, descripcion, precio, stock, imagen, proveedor_id, categoria_id) 
                VALUES (?,?,?,?,?,?,?)
            """, ("Teclado Mecánico Redragon K552", "Switch Red, retroiluminado", 45.0, 12, "k552.png", 2, 4))
            
            # PRODUCTO 4
            c.execute("""
                INSERT OR IGNORE INTO producto 
                (nombre, descripcion, precio, stock, imagen, proveedor_id, categoria_id) 
                VALUES (?,?,?,?,?,?,?)
            """, ("Router TP-Link AX1500", "WiFi 6 de alto rendimiento", 89.0, 8, "ax1500.png", 2, 5))
            
            # PRODUCTO 5
            c.execute("""
                INSERT OR IGNORE INTO producto 
                (nombre, descripcion, precio, stock, imagen, proveedor_id, categoria_id) 
                VALUES (?,?,?,?,?,?,?)
            """, ("Auriculares HyperX Cloud II", "Sonido envolvente 7.1", 95.0, 10, "cloud2.png", 2, 4))
            
            # PRODUCTO 6
            c.execute("""
                INSERT OR IGNORE INTO producto 
                (nombre, descripcion, precio, stock, imagen, proveedor_id, categoria_id) 
                VALUES (?,?,?,?,?,?,?)
            """, ("Monitor Samsung 24\"", "Full HD 75Hz", 140.0, 6, "monitor24.png", 2, 6))
            
            # PRODUCTO 7
            c.execute("""
                INSERT OR IGNORE INTO producto 
                (nombre, descripcion, precio, stock, imagen, proveedor_id, categoria_id) 
                VALUES (?,?,?,?,?,?,?)
            """, ("Hub USB 3.0", "4 puertos de alta velocidad", 18.0, 25, "hubusb.png", 2, 3))
            
            # PRODUCTO 8
            c.execute("""
                INSERT OR IGNORE INTO producto 
                (nombre, descripcion, precio, stock, imagen, proveedor_id, categoria_id) 
                VALUES (?,?,?,?,?,?,?)
            """, ("Disco Duro Externo 1TB", "USB 3.0 portátil", 59.0, 14, "hdd1tb.png", 2, 3))


            conn.commit()

        except Exception as e:
            print("Error initializing DB:", e)

    conn.close()
