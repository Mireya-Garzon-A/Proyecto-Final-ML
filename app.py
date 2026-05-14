"""Aplicación Flask principal.

Este módulo inicializa la app Flask, configura la base de datos, el
login manager y registra los blueprints de las distintas partes de la
aplicación (acopio, precio, inversión, perfil).

Contiene además rutas públicas simples como `/`, `/login`, `/register`
y utilidades de sesión.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

from inversion import inversion_bp
from acopio import acopio_bp
from precio import precio_bp
from perfil import perfil_bp

import pandas as pd
import io, base64
import matplotlib.pyplot as plt
import os


# Inicialización
BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(BASE_DIR / 'templates'), static_folder=str(BASE_DIR / 'static'))
# Cargar variables de entorno desde .env en la raíz del proyecto (útil para desarrollo local)
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))
    try:
        print(f'Loaded .env from {env_path}')
    except Exception:
        pass
    # Strip accidental surrounding quotes from important env vars
    for k in ('DATABASE_URL', 'MYSQL_DATABASE_URL', 'SECRET_KEY', 'PA_PROJECT_HOME', 'PA_VENV_PATH'):
        v = os.environ.get(k)
        if v and ((v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'"))):
            os.environ[k] = v[1:-1]
            try:
                print(f'Stripped quotes for env var {k}')
            except Exception:
                pass
app.secret_key = os.environ.get('SECRET_KEY', 'clave_segura_para_sesion')  # 🔹 Usar variable de entorno
# Configurar expiración de sesión por inactividad (30 minutos)
app.permanent_session_lifetime = timedelta(minutes=30)

# Configuración de base de datos:
# - Si `PYTHONANYWHERE` == 'true' usamos SQLite en `instance/database.db`.
# - Si existe `MYSQL_DATABASE_URL` lo respetamos (útil para despliegues con MySQL).
# - Si no, por defecto local usamos la conexión a XAMPP/MySQL existente.
# Prefer generic `DATABASE_URL` (used by Render) then `MYSQL_DATABASE_URL`.
# WARNING: If you plan to use SQLite on Render note that the filesystem is
# ephemeral between deploys — use an external DB for persistent data.
database_url = os.environ.get('DATABASE_URL')
mysql_url = os.environ.get('MYSQL_DATABASE_URL')

# Asegurar que la carpeta `instance` exista (necesaria para SQLite y logs)
instance_dir = BASE_DIR / 'instance'
try:
    instance_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

pa_flag = os.environ.get('PYTHONANYWHERE', '').lower()
# If running on PythonAnywhere, keep existing SQLite behavior (dev-friendly)
if pa_flag == 'true':
    sqlite_path = instance_dir / 'database.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{sqlite_path}"
# Prefer DATABASE_URL (Render/Postgres/Heroku style), then MYSQL_DATABASE_URL
elif database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
elif mysql_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = mysql_url
else:
    # conexión por defecto a XAMPP en localhost (solo para desarrollo local)
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'mysql+pymysql://root:@localhost:3306/del_campo_al_algoritomo?charset=utf8mb4'
    )

# Recomendaciones de engine para entornos remotos (mejor logging y resiliencia)
app.config.setdefault('SQLALCHEMY_ENGINE_OPTIONS', {})
app.config['SQLALCHEMY_ENGINE_OPTIONS'].update({
    'pool_pre_ping': True,
    'pool_recycle': 280,
    'pool_timeout': 30,
})

import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
import sys

# En entornos como Render (cuentas gratuitas) no puedes acceder a archivos en disco
# fácilmente; emitir logs a stdout/stderr permite verlos desde el panel "Logs".
root_logger = logging.getLogger()
if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
root_logger.setLevel(logging.INFO)
app.logger.handlers = root_logger.handlers
app.logger.setLevel(logging.INFO)

# Registrar excepciones no manejadas para que aparezcan en los logs de Render
from werkzeug.exceptions import HTTPException


@app.errorhandler(Exception)
def handle_exception(e):
    # If it's an HTTPException (404, 401, etc.), return it unchanged
    if isinstance(e, HTTPException):
        return e
    # Log completo de la excepción
    app.logger.exception('Unhandled exception:')
    # Respuesta genérica (no exponer detalles en producción)
    return ("Internal server error", 500)


# Serve favicon if present, otherwise return empty 204 so it doesn't raise 500
@app.route('/favicon.ico')
def favicon():
    try:
        fav_path = os.path.join(app.static_folder or '', 'favicon.ico')
        if os.path.exists(fav_path):
            return app.send_static_file('favicon.ico')
    except Exception:
        app.logger.exception('Error serving favicon')
    return ('', 204)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Filtro Jinja para formatear fechas en hora local de Colombia (America/Bogota)
def format_colombia(value, fmt="%Y-%m-%d %H:%M"):
    """Convierte un datetime (naive o timezone-aware) a la zona America/Bogota y lo formatea.

    - Si el valor es None devuelve cadena vacía.
    - Si el datetime es naive se asume que está en UTC.
    - Usa pytz para asegurar compatibilidad con las dependencias del proyecto.
    """
    if not value:
        return ''
    try:
        tz_target = pytz.timezone('America/Bogota')
        # Si es naive, asumir UTC
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            value = pytz.UTC.localize(value)
        local = value.astimezone(tz_target)
        return local.strftime(fmt)
    except Exception:
        try:
            # fallback simple
            return value.strftime(fmt)
        except Exception:
            return str(value)

# Registrar filtro en Jinja
app.jinja_env.filters['format_colombia'] = format_colombia

# Inicializar base de datos usando la instancia compartida
from database import db
db.init_app(app)

# Importar modelo después de inicializar db (evita import circular)
with app.app_context():
    from models import User

# Configurar Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Página de inicio pública
@app.route('/')
def inicio():
    return render_template('inicio.html')

# Login CORREGIDO - usuario = email
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Manejador de autenticación.

    El formulario envía 'usuario' (email) y 'contrasena'. Si la
    autenticación es correcta se inicia sesión y se refresca
    `session['last_activity']`.
    """
    import traceback
    error = None
    if request.method == 'POST':
        try:
            # El campo "usuario" en el formulario es el correo electrónico
            email = request.form['usuario']
            contrasena = request.form['contrasena']

            # Buscar usuario por email (correo electrónico)
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(contrasena):
                login_user(user)
                session['usuario'] = user.name
                # Marcar sesión como permanente y registrar última actividad
                session.permanent = True
                session['last_activity'] = datetime.utcnow().timestamp()
                # Mostrar mensaje de bienvenida personalizado con el nombre del usuario
                flash(f'¡Bienvenido/a, {user.name}! Has iniciado sesión correctamente.', 'success')
                # Redirigir al inicio en lugar de al menú principal
                return redirect(url_for('inicio'))
            else:
                error = 'Correo electrónico o contraseña incorrectos'
        except Exception as e:
            tb = traceback.format_exc()
            try:
                log_dir = os.path.join(Path(__file__).resolve().parent, 'instance')
                os.makedirs(log_dir, exist_ok=True)
                with open(os.path.join(log_dir, 'login_error.log'), 'a', encoding='utf-8') as f:
                    f.write('\n--- ERROR en /login ---\n')
                    f.write(tb)
            except Exception:
                pass
            # En modo debug devolver traceback para ayuda local
            if app.debug:
                return f"<pre>{tb}</pre>"
            error = 'Ocurrió un error al intentar iniciar sesión. Revisa el log en instance/login_error.log.'
    
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registrar un nuevo usuario.

    POST: valida que el correo no esté registrado, crea la instancia
    `User`, guarda la contraseña hasheada y redirige al login.
    GET: renderiza el formulario de registro.
    """
    if request.method == 'POST':
        # Nombres y apellidos separados
        primer_nombre = request.form.get('primer_nombre')
        segundo_nombre = request.form.get('segundo_nombre')
        primer_apellido = request.form.get('primer_apellido')
        segundo_apellido = request.form.get('segundo_apellido')
        # Construir `name` para compatibilidad con otras partes del sistema
        name = f"{primer_nombre} {' ' + segundo_nombre if segundo_nombre else ''} {primer_apellido} {' ' + segundo_apellido if segundo_apellido else ''}".strip()
        email = request.form['email']
        password = request.form['password']
        plan = request.form.get('plan', 'free')
        payment_method = request.form.get('payment_method', 'none')
        tipo_documento = request.form.get('tipo_documento')
        numero_documento = request.form.get('numero_documento')
        telefono = request.form.get('telefono')

        # Verificar si ya existe el usuario por email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('El correo electrónico ya está registrado', 'danger')
            return redirect(url_for('register'))

        new_user = User(name=name, email=email)
        # Asignar campos adicionales de identificación
        new_user.primer_nombre = primer_nombre
        new_user.segundo_nombre = segundo_nombre
        new_user.primer_apellido = primer_apellido
        new_user.segundo_apellido = segundo_apellido
        new_user.tipo_documento = tipo_documento
        new_user.numero_documento = numero_documento
        new_user.telefono = telefono
        new_user.set_password(password)

        # Si seleccionó un plan de pago, simulamos el cobro y asignamos rol temporal
        if plan in ('pago1', 'pago2'):
            # simulación: aceptar cualquier método y dar suscripción por 30 días
            try:
                new_user.role = 'pago1' if plan == 'pago1' else 'pago2'
                new_user.subscription_expires = datetime.utcnow() + timedelta(days=30)
            except Exception:
                # si falla asignación, dejar en free
                new_user.role = 'free'
                new_user.subscription_expires = None
        else:
            new_user.role = 'free'
            new_user.subscription_expires = None

        db.session.add(new_user)
        db.session.commit()
        flash('Usuario registrado correctamente. Por favor inicie sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    """Cerrar la sesión del usuario actual.

    Limpia las claves de sesión y redirige al inicio mostrando un flash
    informativo.
    """
    logout_user()
    session.pop('usuario', None)
    session.pop('last_activity', None)
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('inicio'))


# Endpoint opcional para extender la sesión desde cliente (invocado por JS cuando hay actividad)
@app.route('/keepalive', methods=['POST'])
@login_required
def keepalive():
    """Extiende la sesión del usuario (ping desde el cliente).

    Este endpoint es invocado por JavaScript de la UI para actualizar
    `session['last_activity']` y evitar expiraciones mientras el
    usuario está activo. Devuelve 204 en éxito.
    """
    try:
        session['last_activity'] = datetime.utcnow().timestamp()
        return ('', 204)
    except Exception:
        return jsonify({'ok': False}), 500


@app.before_request
def session_timeout_handler():
    # No aplicamos para endpoints estáticos o si no hay sesión
    try:
        if 'usuario' not in session and not current_user.is_authenticated:
            return None
    except Exception:
        # en caso de fallo al leer current_user, no cortar el request
        return None

    # Obtener última actividad
    last = session.get('last_activity')
    now_ts = datetime.utcnow().timestamp()
    if last:
        elapsed = now_ts - float(last)
        # 1800 segundos = 30 minutos
        if elapsed > 1800:
            try:
                logout_user()
            except Exception:
                pass
            session.clear()
            flash('Tu sesión expiró por inactividad. Por favor inicia sesión de nuevo.', 'warning')
            return redirect(url_for('login'))

    # Actualizar last_activity para cada request válida
    session['last_activity'] = now_ts
    # Verificar expiración de suscripción y degradar rol si corresponde
    try:
        if current_user.is_authenticated:
            expires = getattr(current_user, 'subscription_expires', None)
            if expires is not None:
                # Si expiró, degradar a 'free'
                try:
                    if expires and expires < datetime.utcnow():
                        current_user.role = 'free'
                        current_user.subscription_expires = None
                        db.session.commit()
                        flash('Tu suscripción expiró y tu cuenta fue degradada a Free.', 'info')
                except Exception:
                    pass
    except Exception:
        pass

# Menú principal (solo con sesión activa)
@app.route('/menu')
@login_required
def menu():
    # Redirigimos al inicio ya que la plantilla 'menu.html' se ha eliminado
    return redirect(url_for('inicio'))

# datos proyecto
@app.route('/index1')
def index1():
    return render_template('index1.html')

@app.route('/index2')
def index2():
    return render_template('index2.html')

# Crear la base de datos si no existe
with app.app_context():
    # Crear tablas en la BD al arrancar, pero no fallar el arranque si la BD
    # no está disponible (p. ej. durante despliegue). Se registra el error.
    if os.environ.get('SKIP_CREATE_ALL') != '1':
        try:
            db.create_all()
        except Exception as e:
            # Registrar error y seguir adelante para que Gunicorn no muera
            try:
                import traceback
                log_dir = os.path.join(Path(__file__).resolve().parent, 'instance')
                os.makedirs(log_dir, exist_ok=True)
                with open(os.path.join(log_dir, 'db_init_error.log'), 'a', encoding='utf-8') as f:
                    f.write('\n--- DB INIT ERROR ---\n')
                    f.write(traceback.format_exc())
            except Exception:
                pass
            # También emitir a stdout/stderr para que Render lo capture
            import sys
            print('WARNING: db.create_all() falló, continuar arranque. Error:', file=sys.stderr)
            import traceback
            traceback.print_exc()
        else:
            # Seeder: cargar datos iniciales si las tablas están vacías
            def seed_initial_data():
                try:
                    from models import Departamento, User
                    # Cargar departamentos si la tabla está vacía
                    if Departamento.query.first() is None:
                        departamentos = [
                            'Amazonas','Antioquia','Arauca','Atlántico','Bolívar','Boyacá','Caldas','Caquetá',
                            'Casanare','Cauca','Cesar','Chocó','Córdoba','Cundinamarca','Guainía','Guaviare',
                            'Huila','La Guajira','Magdalena','Meta','Nariño','Norte de Santander','Putumayo',
                            'Quindío','Risaralda','San Andrés y Providencia','Santander','Sucre','Tolima',
                            'Valle del Cauca','Vaupés','Vichada','Bogotá D.C.'
                        ]
                        for name in departamentos:
                            d = Departamento(name=name)
                            db.session.add(d)
                        db.session.commit()

                    # Crear un usuario admin por defecto si no existe ninguno
                    if User.query.filter_by(is_admin=True).first() is None:
                        admin_email = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@example.com')
                        admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD')
                        if admin_password:
                            admin = User(name='Administrador', email=admin_email, is_admin=True,
                                         primer_nombre='Admin', primer_apellido='User')
                            admin.set_password(admin_password)
                            db.session.add(admin)
                            db.session.commit()
                except Exception:
                    try:
                        log_dir = os.path.join(Path(__file__).resolve().parent, 'instance')
                        os.makedirs(log_dir, exist_ok=True)
                        with open(os.path.join(log_dir, 'seed_error.log'), 'a', encoding='utf-8') as f:
                            import traceback
                            f.write('\n--- SEED ERROR ---\n')
                            f.write(traceback.format_exc())
                    except Exception:
                        pass

            seed_initial_data()

# Política de tratamiento de datos
@app.route("/politica-datos")
def politica_datos():
    return render_template("politica_datos.html")
#===================================================================================




# =======================
# REGISTRO DE BLUEPRINTS
# =======================

# ✅ Registro de blueprints
app.register_blueprint(acopio_bp)
app.register_blueprint(precio_bp)
app.register_blueprint(inversion_bp)
app.register_blueprint(perfil_bp)

# ✅ Ejecución de la app
if __name__ == '__main__':
    app.run(debug=True, port=5000)

# =============================================================================
# 🔹 COMPATIBILIDAD PYTHONANYWHERE (WSGI)
# =============================================================================
# Esta línea es requerida para que PythonAnywhere encuentre tu aplicación Flask.
# El archivo WSGI debe importar 'application', no 'app'.
application = app