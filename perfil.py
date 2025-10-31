from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user

from models import User, Consulta
# importar estadísticas por raza para estimar producción (litros/vaca/día)
from inversion import BREED_STATS
from database import db
import json
from datetime import datetime

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
    # Creación manual de consultas fue deshabilitada para simplificar el flujo.
    # Las consultas se generan y guardan desde la vista de inversión mediante POST a /mis-consultas/guardar.
    flash('Creación manual de consultas deshabilitada. Usa la vista de Inversión y guarda desde allí.', 'info')
    return redirect(url_for('perfil.mis_consultas'))


@perfil_bp.route('/mis-consultas/guardar', methods=['POST'])
@login_required
def guardar_consulta():
    """Guarda una consulta generada desde la vista /inversion.
    Espera un campo 'query' con JSON que contiene al menos: raza, num_vacas, departamentos, precios_departamentos, anio.
    También acepta 'titulo' y 'descripcion' opcionales.
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
        prod_info = None

    # crear objeto Consulta y persistir (con control de máximo 10 consultas por usuario)
    try:
        # si el usuario tiene >=10 consultas, eliminar las más antiguas para dejar espacio (política: FIFO)
        existing_count = Consulta.query.filter_by(user_id=current_user.id).count()
        if existing_count >= 10:
            # número a eliminar para dejar 9 y permitir la nueva -> eliminar existing_count - 9
            to_remove = existing_count - 9
            oldest = Consulta.query.filter_by(user_id=current_user.id).order_by(Consulta.created_at.asc()).limit(to_remove).all()
            for o in oldest:
                o.delete()

        c = Consulta(user_id=current_user.id, titulo=titulo, descripcion=descripcion, query_text=json.dumps(payload, ensure_ascii=False), summary=json.dumps(prod_info, ensure_ascii=False) if prod_info else None)
        c.save()
        flash('Consulta guardada correctamente.', 'success')
        return redirect(url_for('perfil.mis_consultas'))
    except Exception as e:
        # log básico
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
    # Endpoint eliminado: edición de consultas fue deshabilitada en este despliegue.
    flash('Edición de consultas deshabilitada.', 'info')
    return redirect(url_for('perfil.mis_consultas'))


@perfil_bp.route('/mis-consultas/<int:cid>/eliminar', methods=['POST'])
@login_required
def eliminar_consulta(cid):
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
