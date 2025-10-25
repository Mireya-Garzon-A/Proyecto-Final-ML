from flask import Blueprint, render_template, request, jsonify
import pandas as pd
import os
import io, base64
import matplotlib.pyplot as plt

precio_bp = Blueprint('precio', __name__, template_folder='templates')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def cargar_datos():
    file_path = os.path.join(BASE_DIR, 'DataSheet', 'PRECIO_PAGADO_AL_PRODUCTOR_2_-_RES_0017_DE_2012.csv')
    df = pd.read_csv(file_path, sep=';', encoding='utf-8', na_values=['nd', 'ND'], engine='python')
    df.columns = [col.strip().lower() for col in df.columns]

    # Limpiar valores monetarios
    for col in df.columns:
        if col not in ['año', 'mes']:
            df[col] = df[col].astype(str).str.replace('\$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


@precio_bp.route('/precio/datos', methods=['GET'])
def obtener_datos():
    try:
        df = cargar_datos()

        col_anio = [c for c in df.columns if 'año' in c or 'ano' in c][0]
        col_mes = [c for c in df.columns if 'mes' in c][0]

        anio = request.args.get('anio')
        mes = request.args.get('mes')

        df_filtrado = df.copy()
        if anio:
            df_filtrado = df_filtrado[df_filtrado[col_anio] == int(anio)]
        if mes:
            df_filtrado = df_filtrado[df_filtrado[col_mes].str.lower() == mes.lower()]

        datos = df_filtrado.to_dict('records')
        return jsonify(datos)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@precio_bp.route('/precio/mejor-precio-2025', methods=['GET'])
def mejor_precio_2025():
    try:
        df = cargar_datos()
        col_anio = [c for c in df.columns if 'año' in c or 'ano' in c][0]
        col_mes = [c for c in df.columns if 'mes' in c][0]
        col_total = [c for c in df.columns if 'nacional' in c or 'total' in c][0]

        df_2025 = df[df[col_anio] == 2025]
        if df_2025.empty:
            return jsonify({'error': 'No hay datos para 2025'})

        mejor_precio = df_2025[col_total].max()
        registro = df_2025[df_2025[col_total] == mejor_precio].iloc[0]

        return jsonify({'precio': float(mejor_precio), 'mes': registro[col_mes], 'anio': int(registro[col_anio])})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@precio_bp.route('/precio', methods=['GET', 'POST'])
def mostrar_precio():
    try:
        df = cargar_datos()
        col_anio = [c for c in df.columns if 'año' in c or 'ano' in c][0]
        col_mes = [c for c in df.columns if 'mes' in c][0]
        col_total = [c for c in df.columns if 'nacional' in c or 'total' in c][0]

        anios = sorted(df[col_anio].dropna().unique().tolist())
        meses = sorted(df[col_mes].dropna().unique().tolist())

        # Estadísticas desde enero 2024 (compatibilidad con plantilla existente)
        años_disponibles = anios
        df_2024 = df[df[col_anio] >= 2024]
        mes_max_precio = None
        depto_max_precio = None
        col_depto = [c for c in df.columns if 'depart' in c.lower() or 'departamento' in c.lower()]
        col_depto = col_depto[0] if col_depto else None

        if not df_2024.empty:
            if col_mes in df_2024.columns and col_total in df_2024.columns:
                precio_por_mes = df_2024.groupby(col_mes)[col_total].mean().reset_index()
                mes_max_precio = precio_por_mes.sort_values(by=col_total, ascending=False).iloc[0][col_mes]

            if col_depto and col_depto in df_2024.columns:
                precio_por_depto = df_2024.groupby(col_depto)[col_total].mean().reset_index()
                depto_max_precio = precio_por_depto.sort_values(by=col_total, ascending=False).iloc[0][col_depto]

        # Procesar formulario antiguo (compatibilidad con plantilla que envía POST a /precio)
        resultados_usuario = None
        if request.method == 'POST' and request.form.get('anio'):
            try:
                anio_usuario = int(request.form.get('anio'))
                df_filtrado_usuario = df[df[col_anio] == anio_usuario]
                if not df_filtrado_usuario.empty:
                    mes_usuario = df_filtrado_usuario.groupby(col_mes)[col_total].mean().idxmax()
                    depto_usuario = df_filtrado_usuario.groupby(col_depto)[col_total].mean().idxmax() if col_depto else 'No disponible'
                    resultados_usuario = {'anio': anio_usuario, 'mes_precio': mes_usuario, 'depto': depto_usuario}
            except Exception:
                resultados_usuario = None

        anio_sel = request.args.get('anio') or request.form.get('anio')
        mes_sel = request.args.get('mes') or request.form.get('mes')

        df_filtrado = df.copy()
        if anio_sel:
            df_filtrado = df_filtrado[df_filtrado[col_anio] == int(anio_sel)]
        if mes_sel:
            df_filtrado = df_filtrado[df_filtrado[col_mes].str.lower() == mes_sel.lower()]

        grafico = None
        if not df_filtrado.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(df_filtrado[col_mes], df_filtrado[col_total], marker='o', color='darkorange', linewidth=2)
            ax.set_title(f"Precio promedio nacional por litro ({anio_sel if anio_sel else 'Todos los años'})")
            ax.set_xlabel('Mes')
            ax.set_ylabel('Precio (COP)')
            plt.xticks(rotation=45)

            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            grafico = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close(fig)
        # Renderizar plantilla con todas las variables (compatibilidad)
        return render_template('precio.html',
                               anios=anios,
                               meses=meses,
                               grafico=grafico,
                               tabla=df_filtrado.to_html(classes='table table-striped table-sm', index=False),
                               anio_sel=anio_sel,
                               mes_sel=mes_sel,
                               años_disponibles=años_disponibles,
                               mes_max_precio=mes_max_precio,
                               depto_max_precio=depto_max_precio,
                               resultados_usuario=resultados_usuario)
    except Exception as e:
        return f"<h4 style='color:red;'>Error al cargar los datos: {str(e)}</h4>"