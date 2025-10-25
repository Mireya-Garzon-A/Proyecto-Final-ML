from flask import Blueprint, render_template, request
import pandas as pd
import os
import io, base64
import matplotlib.pyplot as plt
from modelo_acopio import predecir_acopio  # importar la función del otro módulo

# Crear el Blueprint
acopio_bp = Blueprint('acopio', __name__, template_folder='templates')

# Ruta base del archivo
DATA_PATH = os.path.join("DataSheet", "Volumen de Acopio Directos - Res 0017 de 2012.csv")

# ==========================
# Función para cargar y limpiar la data
# ==========================
def cargar_datos():
    # Intentar diferentes codificaciones
    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(DATA_PATH, sep=';', encoding=encoding)
            # Si llegamos aquí, la lectura fue exitosa
            break
        except UnicodeDecodeError:
            continue
    
    if df is None:
        raise ValueError("No se pudo leer el archivo con ninguna codificación")

    # Normalizar nombres de columnas: quitar espacios y tildes
    def normalize_col(col):
        import unicodedata
        # Convertir a mayúsculas y quitar espacios
        col = col.strip().upper()
        # Normalizar caracteres (quitar tildes)
        col = unicodedata.normalize('NFKD', col).encode('ASCII', 'ignore').decode('ASCII')
        return col

    df.columns = [normalize_col(c) for c in df.columns]

    # Verificar y renombrar columna ANO/AÑO si es necesario
    if 'ANO' in df.columns:
        df = df.rename(columns={'ANO': 'AÑO'})

    if 'MES' not in df.columns:
        for col in df.columns:
            if 'MES' in col:
                df.rename(columns={col:'MES'}, inplace=True)
                break
        else:
            raise ValueError("Columna faltante: MES")

    # Convertir a tipo correcto
    df['AÑO'] = df['AÑO'].astype(int)
    df['MES'] = df['MES'].astype(str)

    # Convertir columnas de departamentos a float
    for col in df.columns[2:]:
        # Asegurarnos que la columna sea de tipo string primero
        df[col] = df[col].astype(str)
        # Reemplazar 'nd' por 0 y limpiar espacios
        df[col] = df[col].str.strip().replace('nd', '0')
        # Si la columna contiene números con formato español (1.234.567,89)
        if df[col].str.contains('\.').any():
            # Primero quitar puntos de miles
            df[col] = df[col].str.replace('.', '')
        # Reemplazar comas decimales por puntos
        df[col] = df[col].str.replace(',', '.')
        # Convertir a float
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df

# ==========================
# Función para generar gráfico
# ==========================
def generar_grafico(df, anio):
    df_anio = df[df['AÑO'] == anio].copy()
    columnas_deptos = df.columns[2:]
    resumen = df_anio.groupby('MES')[columnas_deptos].sum().sum(axis=1).reset_index(name='VOLUMEN (LITROS)')

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(resumen['MES'], resumen['VOLUMEN (LITROS)'])
    ax.set_title(f'Volumen total de acopio - {anio}')
    ax.set_xlabel('Mes')
    ax.set_ylabel('Volumen (Litros)')
    plt.xticks(rotation=45)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    grafico_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    return grafico_base64

# ==========================
# Ruta principal del análisis
# ==========================
@acopio_bp.route('/analisis_acopio', methods=['GET', 'POST'])
def analisis_acopio():
    try:
        df = cargar_datos()
    except Exception as e:
        import traceback
        error_msg = f"Error cargando datos: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Para ver en la consola del servidor
        return f"Error cargando datos: {str(e)}"

    # Año seleccionado (por defecto último disponible)
    anio = int(request.form.get('anio', df['AÑO'].max()))
    df_anio = df[df['AÑO'] == anio].copy()

    # Estadísticas
    columnas_deptos = df.columns[2:]
    df_anio['TOTAL'] = df_anio[columnas_deptos].sum(axis=1)
    mes_max = df_anio.loc[df_anio['TOTAL'].idxmax()]
    mes_min = df_anio.loc[df_anio['TOTAL'].idxmin()]

    # Gráfico
    grafico_base64 = generar_grafico(df, anio)

    # Predicciones usando modelo externo (capturar errores sin romper la vista)
    try:
        pred_df = predecir_acopio()
        print("✅ Predicciones generadas por el modelo:")
        print(pred_df)
        # Aceptar tanto DataFrame como lista
        if hasattr(pred_df, 'to_dict'):
            predicciones = pred_df.to_dict('records')
            print("✅ Predicciones generadas por el modelo:")
            print(pred_df)
        elif isinstance(pred_df, list):
            predicciones = pred_df
        else:
            predicciones = []
    except Exception as e:
        import traceback
        print(f"Error en predicción: {str(e)}\n{traceback.format_exc()}")
        predicciones = []  # Lista vacía en caso de error

    # Lista de años disponibles
    anios_disponibles = sorted(df['AÑO'].unique())

    # Encontrar los meses con mayor y menor volumen
    resumen_mes = df[df['AÑO'] == anio].copy()
    columnas_deptos = [col for col in df.columns if col not in ['AÑO', 'MES']]
    resumen_mes['TOTAL'] = resumen_mes[columnas_deptos].sum(axis=1)
    
    idx_max = resumen_mes['TOTAL'].idxmax()
    idx_min = resumen_mes['TOTAL'].idxmin()
    
    mes_max_data = resumen_mes.loc[idx_max]
    mes_min_data = resumen_mes.loc[idx_min]

    # Encontrar departamento con mayor y menor aporte para cada mes
    dept_max = columnas_deptos[mes_max_data[columnas_deptos].argmax()]
    dept_min = columnas_deptos[mes_min_data[columnas_deptos].argmin()]

    return render_template(
        'acopio.html',
        año_actual=anio,
        años_disponibles=anios_disponibles,
        mes_mayor=mes_max_data['MES'],
        mes_menor=mes_min_data['MES'],
        dept_mayor=dept_max,
        dept_menor=dept_min,
        vol_mayor=mes_max_data['TOTAL'],
        vol_menor=mes_min_data['TOTAL'],
        grafico=grafico_base64,
        predicciones=predicciones
    )
