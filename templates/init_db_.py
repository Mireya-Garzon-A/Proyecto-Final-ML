#!/usr/bin/env python
# init_db.py - Inicializa la base de datos para PythonAnywhere o local

import os
import sys
from pathlib import Path

# Agregar proyecto al path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Configurar entorno para PythonAnywhere si se pasa el flag
if '--pa' in sys.argv:
    os.environ['PYTHONANYWHERE'] = 'true'
    os.environ['PA_DB_USER'] = 'tu_usuario'  # ← AJUSTAR
    os.environ['PA_DB_PASS'] = 'tu_contraseña'  # ← AJUSTAR
    os.environ['PA_DB_HOST'] = 'tu_usuario.mysql.pythonanywhere-services.com'  # ← AJUSTAR
    os.environ['PA_DB_NAME'] = 'tu_usuario$del_campo_al_algoritomo'  # ← AJUSTAR

from app import app, db

def init_db():
    """Crea todas las tablas definidas en los modelos."""
    with app.app_context():
        try:
            print("🔍 Conectando a la base de datos...")
            print(f"   URI: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
            
            print("🛠️  Creando tablas...")
            db.create_all()
            
            print("✅ ¡Base de datos inicializada correctamente!")
            
            # Verificar que la tabla User exista
            from models import User
            count = User.query.count()
            print(f"📊 Usuarios registrados: {count}")
            
        except Exception as e:
            print(f"❌ Error al inicializar la base de datos: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    init_db()