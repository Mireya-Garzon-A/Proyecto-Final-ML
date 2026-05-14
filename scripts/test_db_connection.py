"""Script para probar localmente la conexión a la base de datos y ejecutar el seeder.

Uso:
  - Crear un archivo `.env` en la raíz del proyecto con `DATABASE_URL` o las variables
    `MSSQL_USER`, `MSSQL_PASS`, `MSSQL_HOST`, `MSSQL_DB`.
  - Activar tu virtualenv e instalar dependencias: `pip install -r requirements.txt`.
  - Ejecutar: `python scripts/test_db_connection.py`

El script intentará conectar usando SQLAlchemy, ejecutar `SELECT 1`, luego
inicializará la app Flask y mostrará el número de `Departamento` en la BD.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from pathlib import Path
import sys

# Intentar cargar .env explícitamente desde la raíz del repo
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))
    print('Cargado .env desde:', env_path)
else:
    # fallback a comportamiento por defecto (buscar .env en cwd)
    load_dotenv()
    print('No se encontró .env en la raíz; load_dotenv() usado en fallback')

# Obtener DATABASE_URL directamente o construir desde variables MSSQL
url = os.environ.get('DATABASE_URL')
if not url:
    user = os.environ.get('MSSQL_USER')
    pwd = os.environ.get('MSSQL_PASS')
    host = os.environ.get('MSSQL_HOST')
    dbname = os.environ.get('MSSQL_DB')
    if user and pwd and host and dbname:
        # URL para pymssql
        url = f"mssql+pymssql://{user}:{quote_plus(pwd)}@{host}:1433/{dbname}"

if not url:
    print('No se encontró DATABASE_URL ni variables MSSQL_* necesarias. Crea un .env con ellas.')
    sys.exit(2)

print('Usando DATABASE_URL:', url)

try:
    engine = create_engine(url, connect_args={"connect_timeout":10})
    with engine.connect() as conn:
        r = conn.execute(text('SELECT 1')).scalar()
        print('Prueba SELECT 1 ->', r)
except SQLAlchemyError as e:
    print('Error conectando a la BD con SQLAlchemy:')
    print(e)
    sys.exit(3)

# Probar la inicialización de Flask y el seeder
try:
    from app import application
    from database import db
    from models import Departamento
    with application.app_context():
        print('Inicializando tablas (db.create_all)...')
        db.create_all()
        total = Departamento.query.count()
        print('Departamentos en la BD:', total)
except Exception as e:
    print('Error al inicializar la app o consultar modelos:')
    print(e)
    sys.exit(4)

print('Prueba completada correctamente.')
