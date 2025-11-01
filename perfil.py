"""Blueprint de perfil de usuario.

Contiene vistas para ver/editar el perfil del usuario, gestionar consultas
y funcionalidades administrativas (listar usuarios, cambiar contraseñas,
promover/revocar admin y eliminar usuarios). Las importaciones que dependen
de otros módulos pesados se realizan de forma perezosa dentro de las funciones
para evitar dependencias circulares en tiempo de importación.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user

from models import User, Consulta
from database import db
import json
from datetime import datetime

perfil_bp = Blueprint('perfil', __name__)


@perfil_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    """Ver y actualizar los datos del usuario.

    Soporta dos acciones por POST:
    - update_profile: actualizar nombre y correo (valida unicidad del email)
    - change_password: cambiar contraseña verificando la actual y la confirmación
    """
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


@perfil_bp.route('/mis-consultas')
@login_required
def mis_consultas():
    """Página para mostrar las consultas guardadas del usuario.
    Actualmente muestra un listado vacío (placeholder). Más adelante se puede enlazar a la base de datos.
    """
    # Recuperar consultas del usuario
    consultas_guardadas = Consulta.query.filter_by(user_id=current_user.id).order_by(Consulta.created_at.desc()).all()
    return render_template('mis_consultas.html', consultas=consultas_guardadas)


@perfil_bp.route('/mis-consultas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_consulta():
    """Punto de entrada para crear una nueva consulta.

    En este despliegue la creación manual está deshabilitada: se informa
    al usuario y se redirige al listado de consultas. Mantener esta ruta
    facilita redirecciones desde la UI sin romper enlaces antiguos.
    """
    flash('Creación manual de consultas deshabilitada. Usa la vista de Inversión y guarda desde allí.', 'info')
    return redirect(url_for('perfil.mis_consultas'))


@perfil_bp.route('/mis-consultas/guardar', methods=['POST'])
@login_required
def guardar_consulta():
    """Guardar una consulta enviada desde la vista de Inversión.

    Valida el payload JSON, autogenera un título si falta, calcula una
    estimación de producción (prod_info) y persiste la consulta. Mantiene
    una política FIFO para no almacenar más de 10 consultas por usuario.
    """
    # leer campos
    titulo = request.form.get('titulo', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    query_raw = request.form.get('query', '').strip()

    if not query_raw:
        flash('No se recibieron datos para guardar la consulta.', 'danger')
        return redirect(request.referrer or url_for('inversion.inversion'))

    # validar JSON
    try:
        payload = json.loads(query_raw)
    except Exception:
        flash('Formato de datos inválido. Asegúrate de enviar JSON válido.', 'danger')
        return redirect(request.referrer or url_for('inversion.inversion'))

    # autogenerar título si falta
    if not titulo:
        raza = payload.get('raza') or 'SinRaza'
        nv = payload.get('num_vacas') or payload.get('numVacas') or ''
        titulo = f"Consulta inversión - {raza} - {nv}"

    # --- construir prod_info similar a la vista de ver_consulta ---
    prod_info = None
    try:
        # Importar estadísticas de razas localmente. Si no están disponibles,
        # usamos un diccionario vacío (no es crítico para guardar la consulta).
        try:
            from inversion import BREED_STATS
        except Exception:
            BREED_STATS = {}
        raza = (payload.get('raza') or '').strip() if payload.get('raza') else None
        num_vacas = payload.get('num_vacas') or payload.get('numVacas') or None
        try:
            nv = int(num_vacas) if num_vacas is not None else None
        except Exception:
            nv = None

        litros_por_vaca = None
        if raza:
            bkey = next((k for k in BREED_STATS.keys() if str(k).strip().lower() == raza.strip().lower()), None)
            bstats = BREED_STATS.get(bkey) if bkey else BREED_STATS.get(raza) or BREED_STATS.get(raza.strip())
            if bstats:
                try:
                    litros_por_vaca = float(bstats.get('avg', 0.0))
                except Exception:
                    litros_por_vaca = None

        if litros_por_vaca and nv:
            litros_diario_total = litros_por_vaca * nv
            litros_mensual_total = litros_diario_total * 30
            litros_por_vaca_mensual = litros_por_vaca * 30

            precios = payload.get('precios_departamentos') or []
            deptos = []
            if isinstance(precios, list):
                for p in precios:
                    dept = p.get('departamento') or ''
                    precio_val = None
                    try:
                        precio_val = float(p.get('precio')) if p.get('precio') is not None else None
                    except Exception:
                        precio_val = None
                    deptos.append({'departamento': dept, 'precio': precio_val})

            prod_info = {
                'litros_diario_total': litros_diario_total,
                'litros_mensual_total': litros_mensual_total,
                'litros_por_vaca_diario': litros_por_vaca,
                'litros_por_vaca_mensual': litros_por_vaca_mensual,
                'por_departamento': deptos
            }
    except Exception:
        # Si ocurre algún error al calcular prod_info, continuamos sin la estimación
        prod_info = None

    # crear objeto Consulta y persistir (con control de máximo 10 consultas por usuario)
    try:
        # Política FIFO: eliminar consultas antiguas si el usuario tiene >=10
        existing_count = Consulta.query.filter_by(user_id=current_user.id).count()
        if existing_count >= 10:
            to_remove = existing_count - 9
            oldest = Consulta.query.filter_by(user_id=current_user.id).order_by(Consulta.created_at.asc()).limit(to_remove).all()
            for o in oldest:
                o.delete()

        c = Consulta(
            user_id=current_user.id,
            titulo=titulo,
            descripcion=descripcion,
            query_text=json.dumps(payload, ensure_ascii=False),
            summary=json.dumps(prod_info, ensure_ascii=False) if prod_info else None,
        )
        c.save()
        flash('Consulta guardada correctamente.', 'success')
        return redirect(url_for('perfil.mis_consultas'))
    except Exception:
        # Si la persistencia falla, mostramos un mensaje y redirigimos.
        try:
            import traceback, os
            log_dir = os.path.join(os.path.dirname(__file__), 'instance')
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, 'guardar_consulta_error.log'), 'a', encoding='utf-8') as f:
                f.write(f"--- {datetime.utcnow().isoformat()} ---\n")
                f.write(traceback.format_exc())
        except Exception:
            pass
        flash('Ocurrió un error al guardar la consulta. Revisa los logs.', 'danger')
        return redirect(request.referrer or url_for('inversion.inversion'))


@perfil_bp.route('/mis-consultas/<int:cid>/editar', methods=['GET', 'POST'])
@login_required
def editar_consulta(cid):
    """Edición de consultas (deshabilitada).

    Por compatibilidad con rutas antiguas se mantiene el endpoint pero
    la funcionalidad de edición no está disponible; se informa al
    usuario y se redirige al listado de consultas.
    """
    flash('Edición de consultas deshabilitada.', 'info')
    return redirect(url_for('perfil.mis_consultas'))


@perfil_bp.route('/mis-consultas/<int:cid>/eliminar', methods=['POST'])
@login_required
def eliminar_consulta(cid):
    """Eliminar una consulta propia del usuario.

    Comprueba permisos (solo el propietario puede eliminar) y borra la
    consulta si está autorizado.
    """
    c = Consulta.query.get_or_404(cid)
    if c.user_id != current_user.id:
        flash('No tienes permiso para eliminar esta consulta.', 'danger')
        return redirect(url_for('perfil.mis_consultas'))
    c.delete()
    flash('Consulta eliminada.', 'info')
    return redirect(url_for('perfil.mis_consultas'))


@perfil_bp.route('/mis-consultas/<int:cid>')
@login_required
def ver_consulta(cid):
    """Mostrar una consulta guardada y su estimación de producción.

    Solo el propietario puede ver la consulta. Se parsea el JSON
    almacenado y se intenta calcular una estimación de producción
    basada en estadística de razas (si está disponible).
    """
    c = Consulta.query.get_or_404(cid)
    if c.user_id != current_user.id:
        flash('No tienes permiso para ver esta consulta.', 'danger')
        return redirect(url_for('perfil.mis_consultas'))
    # Parsear el JSON almacenado para pasar datos ya procesados a la plantilla
    consulta_data = None
    if c.query_text:
        try:
            consulta_data = json.loads(c.query_text)
        except Exception:
            consulta_data = None
    # Calcular estimación de producción y de ventas
    prod_info = None
    try:
        # Importar estadísticas de razas localmente; si no están disponibles,
        # la estimación de producción se omite.
        try:
            from inversion import BREED_STATS
        except Exception:
            BREED_STATS = {}
        if consulta_data:
            raza = (consulta_data.get('raza') or '').strip() if consulta_data.get('raza') else None
            num_vacas = consulta_data.get('num_vacas') or consulta_data.get('numVacas') or None
            try:
                nv = int(num_vacas) if num_vacas is not None else None
            except Exception:
                nv = None

            # tomar valor promedio por vaca si existe en BREED_STATS
            litros_por_vaca = None
            if raza:
                bkey = next((k for k in BREED_STATS.keys() if str(k).strip().lower() == raza.strip().lower()), None)
                bstats = BREED_STATS.get(bkey) if bkey else BREED_STATS.get(raza) or BREED_STATS.get(raza.strip())
                if bstats:
                    try:
                        litros_por_vaca = float(bstats.get('avg', 0.0))
                    except Exception:
                        litros_por_vaca = None

            if litros_por_vaca and nv:
                # estimaciones
                litros_diario_total = litros_por_vaca * nv
                litros_mensual_total = litros_diario_total * 30
                litros_por_vaca_mensual = litros_por_vaca * 30

                # preparar lista de precios por departamento si están presentes
                precios = consulta_data.get('precios_departamentos') or []
                deptos = []
                if isinstance(precios, list):
                    for p in precios:
                        dept = p.get('departamento') or ''
                        precio_val = None
                        try:
                            precio_val = float(p.get('precio')) if p.get('precio') is not None else None
                        except Exception:
                            precio_val = None
                        deptos.append({'departamento': dept, 'precio': precio_val})

                prod_info = {
                    'litros_diario_total': litros_diario_total,
                    'litros_mensual_total': litros_mensual_total,
                    'litros_por_vaca_diario': litros_por_vaca,
                    'litros_por_vaca_mensual': litros_por_vaca_mensual,
                    'por_departamento': deptos
                }
            else:
                prod_info = None
    except Exception:
        prod_info = None

    return render_template('mis_consulta_view.html', consulta=c, consulta_data=consulta_data, prod_info=prod_info)


# -----------------------------
# Rutas de administración (solo accesible al administrador)
# -----------------------------
@perfil_bp.route('/admin/users')
@login_required
def admin_users():
    """Listar todos los usuarios (solo administrador)."""
    # Permitir si el usuario actual tiene email admin@example.com o flag is_admin
    if not (current_user.email == 'admin@example.com' or getattr(current_user, 'is_admin', False)):
        flash('No tienes permiso para acceder a la administración.', 'danger')
        return redirect(url_for('perfil.perfil'))

    users = User.query.order_by(User.id.asc()).all()
    return render_template('admin_users.html', users=users)


@perfil_bp.route('/admin/users/<int:uid>/change-password', methods=['POST'])
@login_required
def admin_change_password(uid):
    """Cambiar la contraseña de un usuario (acción realizada por administrador)."""
    if not (current_user.email == 'admin@example.com' or getattr(current_user, 'is_admin', False)):
        flash('No tienes permiso para realizar esta acción.', 'danger')
        return redirect(url_for('perfil.perfil'))

    new_pwd = request.form.get('new_password', '').strip()
    confirm_pwd = request.form.get('confirm_password', '').strip()

    if not new_pwd or new_pwd != confirm_pwd:
        flash('Las contraseñas no coinciden o están vacías.', 'danger')
        return redirect(url_for('perfil.admin_users'))

    u = User.query.get_or_404(uid)
    try:
        u.set_password(new_pwd)
        u.save()
        flash(f'Contraseña actualizada para {u.email}.', 'success')
    except Exception:
        flash('Ocurrió un error al actualizar la contraseña. Revisa los logs.', 'danger')

    return redirect(url_for('perfil.admin_users'))


@perfil_bp.route('/admin/users/<int:uid>/toggle-admin', methods=['POST'])
@login_required
def admin_toggle_admin(uid):
    """Conceder o revocar privilegios de administrador a un usuario (solo admin)."""
    if not (current_user.email == 'admin@example.com' or getattr(current_user, 'is_admin', False)):
        flash('No tienes permiso para realizar esta acción.', 'danger')
        return redirect(url_for('perfil.perfil'))

    u = User.query.get_or_404(uid)

    # No permitir que el administrador cambie su propio rol desde aquí
    if u.id == current_user.id:
        flash('No puedes cambiar tu propio rol de administrador desde esta interfaz.', 'danger')
        return redirect(url_for('perfil.admin_users'))

    # Si se intenta revocar admin, asegurar que quede al menos un admin
    if u.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            flash('No se puede revocar los privilegios del último administrador.', 'danger')
            return redirect(url_for('perfil.admin_users'))

    try:
        u.is_admin = not bool(u.is_admin)
        db.session.commit()
        estado = 'concedidos' if u.is_admin else 'revocados'
        flash(f'Privilegios de administrador {estado} para {u.email}.', 'success')
    except Exception:
        db.session.rollback()
        flash('Ocurrió un error al actualizar el rol. Revisa los logs.', 'danger')

    return redirect(url_for('perfil.admin_users'))


@perfil_bp.route('/admin/users/<int:uid>/delete', methods=['POST'])
@login_required
def admin_delete_user(uid):
    """Eliminar un usuario (solo administrador)."""
    if not (current_user.email == 'admin@example.com' or getattr(current_user, 'is_admin', False)):
        flash('No tienes permiso para realizar esta acción.', 'danger')
        return redirect(url_for('perfil.perfil'))

    u = User.query.get_or_404(uid)

    # Protecciones básicas
    if u.id == current_user.id:
        flash('No puedes eliminar tu propio usuario desde aquí.', 'danger')
        return redirect(url_for('perfil.admin_users'))

    if u.email == 'admin@example.com':
        flash('El usuario administrador principal no puede ser eliminado.', 'danger')
        return redirect(url_for('perfil.admin_users'))

    try:
        # eliminar usuario y confirmar
        db.session.delete(u)
        db.session.commit()
        flash(f'Usuario {u.email} eliminado correctamente.', 'info')
    except Exception:
        db.session.rollback()
        flash('Ocurrió un error al eliminar el usuario. Revisa los logs.', 'danger')

    return redirect(url_for('perfil.admin_users'))
