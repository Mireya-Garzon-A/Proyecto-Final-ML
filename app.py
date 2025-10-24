from flask import Flask, render_template, request, redirect, url_for, session, flash
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import pandas as pd
import io, base64
import matplotlib.pyplot as plt
import os


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

#=======================
# ANÁLISIS DE ACOPIO DE LECHE
# =======================


@app.route('/acopio', methods=['GET', 'POST'])
@login_required
def acopio():
    try:
        # Ruta del archivo (ajustada a tu estructura)
        file_path = os.path.join(BASE_DIR, 'DataSheet', 'Volumen de Acopio Directos - Res 0017 de 2012.csv')

        # Leer CSV con separador ';' y manejar 'nd' como NaN
        df = pd.read_csv(file_path, sep=';', na_values=['nd', 'ND'])

        # Normalizar nombres de columnas
        df.columns = [col.strip().lower() for col in df.columns]

        # Buscar columnas clave (año, mes, nacional)
        col_anio = [c for c in df.columns if 'año' in c or 'ano' in c][0]
        col_mes = [c for c in df.columns if 'mes' in c][0]
        col_total = [c for c in df.columns if 'nacional' in c][0]

        # Obtener opciones únicas
        anios = sorted(df[col_anio].dropna().unique().tolist())
        meses = sorted(df[col_mes].dropna().unique().tolist())

        # Filtros seleccionados
        anio_sel = request.form.get('anio')
        mes_sel = request.form.get('mes')

        # Aplicar filtros
        df_filtrado = df.copy()
        if anio_sel:
            df_filtrado = df_filtrado[df_filtrado[col_anio] == int(anio_sel)]
        if mes_sel:
            df_filtrado = df_filtrado[df_filtrado[col_mes].str.lower() == mes_sel.lower()]

        # Crear gráfico solo si hay datos
        grafico = None
        if not df_filtrado.empty:
            import io, base64
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(7, 4))
            ax.bar(df_filtrado[col_mes], df_filtrado[col_total], color='seagreen')
            ax.set_title(f"Volumen Nacional de Acopio - {anio_sel if anio_sel else 'Todos los años'}")
            ax.set_xlabel("Mes")
            ax.set_ylabel("Litros")
            plt.xticks(rotation=45)

            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            grafico = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close(fig)

        # Enviar datos al template
        return render_template('acopio.html',
                               anios=anios,
                               meses=meses,
                               grafico=grafico,
                               tabla=df_filtrado.head(20).to_html(classes='table table-striped table-sm', index=False),
                               anio_sel=anio_sel,
                               mes_sel=mes_sel)

    except Exception as e:
        return f"<h4 style='color:red;'>Error al cargar los datos: {str(e)}</h4>"
    
# Ejecutar la app
if __name__ == '__main__':
    app.run(debug=True, port=5000)