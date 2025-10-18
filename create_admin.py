from app import app
from database import db
from models import User

# Crear usuario administrador inicial (no duplicar si ya existe)
with app.app_context():
    existing = User.query.filter_by(email='admin@example.com').first()
    if existing:
        print('ℹ️ Usuario administrador ya existe con ID:', existing.id)
    else:
        admin = User(name='Admin', email='admin@example.com')
        admin.set_password('1234')
        db.session.add(admin)
        db.session.commit()
        print("✅ Usuario administrador creado con ID:", admin.id)