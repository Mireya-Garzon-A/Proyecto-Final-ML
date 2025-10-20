from flask import Flask, render_template, request, redirect, url_for, session, flash
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import pandas as pd


# Inicialización
BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(BASE_DIR / 'templates'), static_folder=str(BASE_DIR / 'static'))
app.secret_key = 'clave_segura_para_sesion'

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
    error = None
    if request.method == 'POST':
        # El campo "usuario" en el formulario es el correo electrónico
        email = request.form['usuario']
        contrasena = request.form['contrasena']

        # Buscar usuario por email (correo electrónico)
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(contrasena):
            login_user(user)
            session['usuario'] = user.name
            flash('¡Bienvenido/a! Has iniciado sesión correctamente.', 'success')
            return redirect(url_for('menu'))
        else:
            error = 'Correo electrónico o contraseña incorrectos'
    
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
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('inicio'))

# Menú principal (solo con sesión activa)
@app.route('/menu')
@login_required
def menu():
    return render_template('menu.html')

# Casos de uso
@app.route('/index1')
def index1():
    return render_template('index1.html')

# Crear la base de datos si no existe
with app.app_context():
    db.create_all()

# Ejecutar la app
if __name__ == '__main__':
    app.run(debug=True, port=5000)