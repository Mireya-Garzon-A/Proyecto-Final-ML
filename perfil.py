from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user

from models import User

perfil_bp = Blueprint('perfil', __name__)


@perfil_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    """Ver y editar datos del usuario. Maneja actualización de nombre/email y cambio de contraseña usando formularios simples."""
    if request.method == 'POST':
        # Actualizar perfil (nombre y email)
        if 'update_profile' in request.form:
            new_name = request.form.get('name', '').strip()
            new_email = request.form.get('email', '').strip().lower()

            # Validaciones básicas
            if not new_name or not new_email:
                flash('Nombre y correo no pueden estar vacíos.', 'danger')
                return redirect(url_for('perfil.perfil'))

            # Si cambió el email, verificar unicidad
            if new_email != current_user.email and User.get_by_email(new_email):
                flash('El correo ya está registrado por otro usuario.', 'danger')
                return redirect(url_for('perfil.perfil'))

            current_user.name = new_name
            current_user.email = new_email
            current_user.save()
            # Actualizar la sesión para reflejar el nuevo nombre inmediatamente
            session['usuario'] = current_user.name
            flash('Datos actualizados correctamente.', 'success')
            return redirect(url_for('perfil.perfil'))

        # Cambiar contraseña
        if 'change_password' in request.form:
            current_pwd = request.form.get('current_password', '')
            new_pwd = request.form.get('new_password', '')
            confirm_pwd = request.form.get('confirm_password', '')

            if not current_user.check_password(current_pwd):
                flash('La contraseña actual es incorrecta.', 'danger')
                return redirect(url_for('perfil.perfil'))

            if not new_pwd or new_pwd != confirm_pwd:
                flash('Las contraseñas nuevas no coinciden o están vacías.', 'danger')
                return redirect(url_for('perfil.perfil'))

            current_user.set_password(new_pwd)
            current_user.save()
            flash('Contraseña cambiada correctamente.', 'success')
            return redirect(url_for('perfil.perfil'))

    # GET: renderizar perfil con datos actuales
    return render_template('perfil.html', user=current_user)
