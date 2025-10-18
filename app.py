from flask import Flask, render_template, request, redirect, url_for, session, flash
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import pandas as pd
import Reg_Logis as ReLogistica
import Relineal

# Inicialización
# use absolute paths for templates and static to avoid issues when cwd changes
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

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['usuario']
        contrasena = request.form['contrasena']

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(contrasena):
            login_user(user)
            session['usuario'] = user.name
            return redirect(url_for('menu'))
        else:
            error = 'Usuario o contraseña incorrectos'
    return render_template('login.html', error=error)

#======================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('El correo ya está registrado', 'danger')
            return redirect(url_for('register'))

        new_user = User(name=name, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Usuario registrado correctamente. Por favor inicie sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')
#====================================================



# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('usuario', None)
    return redirect(url_for('inicio'))

# Menú principal (solo con sesión activa)
@app.route('/menu')
@login_required
def menu():
    return render_template('menu.html')

# Casos de uso
@app.route('/index1')
@login_required
def index1():
    return render_template('index1.html')

@app.route('/index2')
@login_required
def index2():
    return render_template('index2.html')

@app.route('/index3')
@login_required
def index3():
    return render_template('index3.html')

@app.route('/index4')
@login_required
def index4():
    return render_template('index4.html')

# Regresión Lineal
@app.route('/conceptos')
@login_required
def conceptos():
    return render_template('conceptos.html')

@app.route('/LR', methods=["GET", "POST"])
@login_required
def LR():
    calculateResult = None
    if request.method == "POST":
        try:
            altitud = float(request.form["altitud"])
            frecuencia = float(request.form["frecuencia"])
            calculateResult = Relineal.CalculateOxygen(altitud, frecuencia)

            import time
            time.sleep(0.1)
            Relineal.save_plot(altitud, frecuencia, calculateResult)
        except ValueError:
            return "Por favor ingrese valores numéricos válidos"
        except Exception as e:
            return f"Error: {str(e)}"

    return render_template("rl.html", result=calculateResult)

# Regresión Logística
ReLogistica.evaluate()

@app.route('/conceptos_reg_logistica')
@login_required
def conceptos_reg_logistica():
    return render_template('conceptos_reg_logistica.html')

@app.route('/ejercicio_reg_logistica', methods=['GET', 'POST'])
@login_required
def ejercicio_reg_logistica():
    result = None
    if request.method == 'POST':
        try:
            edad = float(request.form['edad'])
            tiempo = float(request.form['tiempo'])
            tipo = request.form['tipo'].lower()
            visitas = float(request.form['visitas'])

            entrada = pd.DataFrame([{
                "edad_mascota": edad,
                "tiempo_adopcion": tiempo,
                "visitas_recibidas": visitas,
                "tipo_mascota": tipo
            }])

            entrada = pd.get_dummies(entrada, columns=["tipo_mascota"], drop_first=True)

            for col in ReLogistica.x.columns:
                if col not in entrada.columns:
                    entrada[col] = 0
            entrada = entrada[ReLogistica.x.columns]

            features = entrada.values[0]
            etiqueta, probabilidad = ReLogistica.predict_label(features)

            result = {
                "etiqueta": etiqueta,
                "probabilidad": probabilidad
            }

        except ValueError:
            result = {"error": "Por favor ingrese valores válidos"}
        except Exception as e:
            result = {"error": f"Error: {str(e)}"}

    return render_template('ejercicio_reg_logistica.html', result=result)

# Cargar datos CSV
try:
    data = pd.read_csv('./DataSheet/data.csv', delimiter=';')
except FileNotFoundError:
    print("Error: El archivo data.csv no se encontró.")
except Exception as e:
    print(f"Error al cargar datos: {e}")

# Crear la base de datos si no existe
with app.app_context():
    db.create_all()

# Ejecutar la app
if __name__ == '__main__':
    app.run(debug=True, port=5000)