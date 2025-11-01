"""Modelos de la base de datos.

Contiene las clases ORM `User` y `Consulta` empleadas por la aplicación.
Proporciona métodos auxiliares para persistencia y utilidades básicas.
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

class User(db.Model, UserMixin):
    __tablename__ = 'blog_user'
    """Modelo de usuario.

    Campos principales: id, name, email, password, is_admin.
    Métodos: set_password, check_password, save, y selectores estáticos.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(256), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<User {self.email}>'

    def set_password(self, password):
        """Hashea y almacena la contraseña provista.

        Nota: utiliza `werkzeug.security.generate_password_hash`.
        """
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Comprueba que `password` coincida con el hash almacenado.

        Devuelve True si coinciden, False en caso contrario.
        """
        return check_password_hash(self.password, password)

    def save(self):
        """Guarda (insert/commit) el objeto en la base de datos.

        Añade el objeto a la sesión si es nuevo y realiza commit. No
        devuelve valor; si falla lanzará excepción del ORM.
        """
        if not self.id:
            db.session.add(self)
        db.session.commit()

    @staticmethod
    def get_by_id(id):
        """Retorna el usuario por su id (o None si no existe)."""
        return User.query.get(id)

    @staticmethod
    def get_by_email(email):
        """Retorna el usuario cuyo correo coincide con `email` o None."""
        return User.query.filter_by(email=email).first()


class Consulta(db.Model):
    __tablename__ = 'consultas'
    """Modelo para consultas de inversión guardadas por usuarios.

    `query_text` almacena el JSON de la solicitud y `summary` guarda
    metadatos/estimaciones precalculadas como JSON en texto.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('blog_user.id'), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    # 'query' es un nombre reservado a nivel de modelo por Flask-SQLAlchemy (Consulta.query existe como Query property)
    # por eso renombramos la columna a 'query_text' para evitar colisiones.
    query_text = db.Column(db.Text, nullable=True)
    # resumen o metadatos calculados (JSON string) con estimaciones de producción, se guarda por comodidad
    summary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    user = db.relationship('User', backref=db.backref('consultas', lazy='dynamic'))

    def save(self):
        """Inserta o actualiza la consulta en la base de datos."""
        if not self.id:
            db.session.add(self)
        db.session.commit()

    def delete(self):
        """Elimina esta instancia de la base de datos y hace commit."""
        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        return f'<Consulta {self.id} - {self.titulo}>'