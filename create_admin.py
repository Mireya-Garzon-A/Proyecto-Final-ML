from app import app, db
from models import User

# Crear usuario administrador inicial
with app.app_context():
    admin = User(name='Admin', email='admin@example.com')
    admin.set_password('1234')
    db.session.add(admin)
    db.session.commit()
    print("✅ Usuario administrador creado con ID:", admin.id)