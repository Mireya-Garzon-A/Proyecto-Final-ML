from flask import Blueprint, render_template, request
import pandas as pd
import matplotlib.pyplot as plt
import io, base64, os

# Crear Blueprint
precio_bp = Blueprint('precio', __name__, template_folder='templates')

# Ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def cargar_datos():
    ruta = os.path.join(BASE_DIR, 'DataSheet', 'PRECIO_PAGADO_AL_PRODUCTOR_2_-_RES_0017_DE_2012.csv')
    df = pd.read_csv(ruta, sep=';', encoding='utf-8', na_values=['nd', 'ND'])
    df.columns = [col.strip().lower() for col in df.columns]

    # Limpiar valores monetarios
    for col in df.columns:
        if col not in ['año', 'mes']:
            df[col] = df[col].astype(str).str.replace('$', '', regex=False)\
                                        .str.replace('.', '', regex=False)\
                                        .str.replace(',', '.', regex=False)\
                                        .str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

@precio_bp.route('/precio', methods=['GET', 'POST'])
def precio():
    try:
        df = cargar_datos()

        # Identificar columnas clave
        col_anio = [c for c in df.columns if 'año' in c or 'ano' in c][0]
        col_mes = [c for c in df.columns if 'mes' in c][0]
        col_nacional = [c for c in df.columns if 'nacional' in c][0]
        departamentos = [c for c in df.columns if c not in [col_anio, col_mes, col_nacional]]

        # Filtros del formulario
        anio_sel = request.form.get('anio')
        mes_sel = request.form.get('mes')
        depto_sel = request.form.get('departamento')

        # Determinar columna a graficar
        col_total = depto_sel if depto_sel in df.columns else col_nacional

        # Filtrar datos
        df_filtrado = df.copy()
        if anio_sel:
            df_filtrado = df_filtrado[df_filtrado[col_anio] == int(anio_sel)]
        if mes_sel:
            df_filtrado = df_filtrado[df_filtrado[col_mes].str.lower() == mes_sel.lower()]

        # Precio actual (último valor no nulo)
        precio_actual = df[col_total].dropna().iloc[-1]

        # Mejor precio en 2025
        df_2025 = df[df[col_anio] == 2025]
        mes_max_2025 = None
        depto_max_2025 = None
        if not df_2025.empty:
            precios_por_depto = {col: df_2025[col].max() for col in departamentos}
            depto_max_2025 = max(precios_por_depto, key=precios_por_depto.get)
            mes_max_2025 = df_2025[df_2025[depto_max_2025] == precios_por_depto[depto_max_2025]][col_mes].iloc[0]

        # Crear gráfico
        grafico = None
        if not df_filtrado.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(df_filtrado[col_mes], df_filtrado[col_total], marker='o', color='darkgreen', linewidth=2)
            ax.set_title(f"Precio por litro ({col_total}) - {anio_sel if anio_sel else 'Todos los años'}")
            ax.set_xlabel("Mes")
            ax.set_ylabel("Precio (COP)")
            plt.xticks(rotation=45)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            grafico = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close(fig)

        # Renderizar plantilla
        return render_template(
            'precio.html',
            anios=sorted(df[col_anio].dropna().unique().tolist()),
            meses=sorted(df[col_mes].dropna().unique().tolist()),
            departamentos=departamentos,
            anio_sel=anio_sel,
            mes_sel=mes_sel,
            depto_sel=depto_sel,
            precio_actual=round(precio_actual, 2),
            mes_max_2025=mes_max_2025,
            depto_max_2025=depto_max_2025,
            grafico=grafico,
            tabla=df_filtrado.to_html(classes='table table-striped table-sm', index=False) if not df_filtrado.empty else None
        )

    except Exception as e:
        return f"<h4 style='color:red;'>Error al procesar los datos: {str(e)}</h4>"