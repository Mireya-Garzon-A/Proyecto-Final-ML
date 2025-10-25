from flask import Blueprint, render_template, request
import pandas as pd
import os, io, base64
import matplotlib.pyplot as plt
from modelo_acopio import predecir_acopio

acopio_bp = Blueprint('acopio', __name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@acopio_bp.route('/acopio', methods=['GET', 'POST'])
def mostrar_acopio():
    try:
        # === 1. Cargar datos ===
        archivo = os.path.join(BASE_DIR, 'DataSheet', 'Volumen de Acopio Directos - Res 0017 de 2012.csv')
        df = pd.read_csv(archivo, sep=';', encoding='utf-8', engine='python', na_values=['nd', 'ND'])
        df.columns = [col.strip().lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u') for col in df.columns]

        # === 2. Identificar columnas clave con validación segura ===
        col_mes_candidates = [c for c in df.columns if 'mes' in c]
        if not col_mes_candidates:
            return "<h4 style='color:red;'>⚠️ Error: No se encontró ninguna columna de mes.</h4>"
        col_mes = col_mes_candidates[0]

        col_anio_candidates = [c for c in df.columns if 'año' in c or 'ano' in c]
        if not col_anio_candidates:
            return "<h4 style='color:red;'>⚠️ Error: No se encontró ninguna columna de año.</h4>"
        col_anio = col_anio_candidates[0]

        col_vol = 'nacional' if 'nacional' in df.columns else None
        if not col_vol:
            return "<h4 style='color:red;'>⚠️ Error: No se encontró la columna 'NACIONAL' con el volumen total.</h4>"

        # === 3. Procesar fechas y limpiar volumen ===
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        df['mes_num'] = df[col_mes].str.lower().map(meses)
        df['Año'] = pd.to_numeric(df[col_anio], errors='coerce')
        df['fecha'] = pd.to_datetime(dict(year=df['Año'], month=df['mes_num'], day=1), errors='coerce')
        df[col_vol] = pd.to_numeric(df[col_vol], errors='coerce')

        años_disponibles = sorted(df['Año'].dropna().unique())
        meses_disponibles = sorted(df[col_mes].dropna().unique())

        # === 4. Estadísticas desde enero 2024 ===
        df_2024 = df[df['Año'] >= 2024]
        mes_max_vol = None
        depto_max_vol = None

        if not df_2024.empty:
            vol_por_mes = df_2024.groupby(col_mes)[col_vol].sum().reset_index()
            if not vol_por_mes.empty:
                mes_max_vol = vol_por_mes.sort_values(by=col_vol, ascending=False).iloc[0][col_mes]

        # === Transformar departamentos en filas (excluyendo NACIONAL) ===
        departamentos = [col for col in df.columns if col not in [col_anio, col_mes, 'nacional']]
        df_melt = df.melt(id_vars=[col_anio, col_mes], value_vars=departamentos,
                          var_name='Departamento', value_name='Volumen')
        df_melt['Volumen'] = pd.to_numeric(df_melt['Volumen'], errors='coerce')
        df_melt['Año'] = pd.to_numeric(df_melt[col_anio], errors='coerce')

        df_2024_melt = df_melt[df_melt['Año'] >= 2024]
        if not df_2024_melt.empty:
            vol_por_depto = df_2024_melt.groupby('Departamento')['Volumen'].sum().reset_index()
            if not vol_por_depto.empty:
                depto_max_vol = vol_por_depto.sort_values(by='Volumen', ascending=False).iloc[0]['Departamento']

        # === 5. Generar gráfico comparativo ===
        grafico = None
        if not df_2024.empty and not vol_por_mes.empty:
            vol_por_mes['predicho'] = vol_por_mes[col_mes].str.lower().map(lambda m: predecir_acopio(m))
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(vol_por_mes[col_mes], vol_por_mes[col_vol], label='Volumen real', marker='o', color='blue')
            ax.plot(vol_por_mes[col_mes], vol_por_mes['predicho'], label='Volumen predicho', marker='o', color='orange')
            ax.set_title("Predicción de Acopio por Mes")
            ax.set_xlabel("Mes")
            ax.set_ylabel("Volumen (litros)")
            ax.legend()
            plt.xticks(rotation=45)
            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            grafico = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close(fig)

        # === 6. Procesar formulario del usuario ===
        resultados_usuario = None
        tabla = None
        anio_sel = request.form.get('anio')
        mes_sel = request.form.get('mes')
        depto_sel = request.form.get('departamento')

        df_filtrado = df.copy()
        if anio_sel:
            df_filtrado = df_filtrado[df_filtrado['Año'] == int(anio_sel)]
        if mes_sel:
            df_filtrado = df_filtrado[df_filtrado[col_mes].str.lower() == mes_sel.lower()]
        if depto_sel and depto_sel in df.columns:
            df_filtrado = df_filtrado[[col_anio, col_mes, depto_sel]]
        else:
            df_filtrado = df_filtrado[[col_anio, col_mes, col_vol]]

        if not df_filtrado.empty:
            tabla = df_filtrado.to_html(classes='table table-striped table-sm', index=False)
            resultados_usuario = {
                'anio': anio_sel,
                'mes': mes_sel,
                'depto': depto_sel if depto_sel else 'NACIONAL',
                'volumen': 'Disponible'
            }

        # === 7. Renderizar plantilla ===
        return render_template('acopio.html',
                               mes_max_vol=mes_max_vol,
                               depto_max_vol=depto_max_vol,
                               años_disponibles=años_disponibles,
                               meses_disponibles=meses_disponibles,
                               departamentos=departamentos,
                               resultados_usuario=resultados_usuario,
                               tabla=tabla,
                               grafico=grafico)

    except Exception as e:
        return f"<h4 style='color:red;'>Error en análisis de acopio: {str(e)}</h4>"
