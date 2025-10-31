from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta

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
app.secret_key = 'clave_segura_para_sesion'
# Configurar expiración de sesión por inactividad (30 minutos)
app.permanent_session_lifetime = timedelta(minutes=30)

# Configuración de base de datos SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usuarios.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Verificar si ya existe el usuario por email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('El correo electrónico ya está registrado', 'danger')
            return redirect(url_for('register'))

        new_user = User(name=name, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Usuario registrado correctamente. Por favor inicie sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('usuario', None)
    session.pop('last_activity', None)
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('inicio'))


# Endpoint opcional para extender la sesión desde cliente (invocado por JS cuando hay actividad)
@app.route('/keepalive', methods=['POST'])
@login_required
def keepalive():
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

# Menú principal (solo con sesión activa)
@app.route('/menu')
@login_required
def menu():
    return render_template('menu.html')

# datos proyecto
@app.route('/index1')
def index1():
    return render_template('index1.html')

@app.route('/index2')
def index2():
    return render_template('index2.html')

# Crear la base de datos si no existe
with app.app_context():
    db.create_all()

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