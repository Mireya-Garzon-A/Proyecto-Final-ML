#!/usr/bin/env python3
"""Inicializa la base de datos usando la configuración actual de `app`.

Este script asume que `app.py` configura `SQLALCHEMY_DATABASE_URI`.
Para PythonAnywhere la app usará SQLite en `instance/database.db`.
"""
import sys
from pathlib import Path

# Asegurar que el directorio del proyecto esté en el path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app import app
from database import db

def init_db():
    with app.app_context():
        print("URI de base de datos:", app.config.get('SQLALCHEMY_DATABASE_URI'))
        print("Creando tablas...")
        db.create_all()
        print("Base de datos inicializada correctamente.")

if __name__ == '__main__':
    init_db()
