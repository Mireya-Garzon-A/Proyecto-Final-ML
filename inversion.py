from flask import Blueprint, render_template, request
import pandas as pd
import os

from modelo_acopio import predecir_acopio
from modelo_precio import predecir_precio

inversion_bp = Blueprint('inversion', __name__, template_folder='templates')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def cargar_censo_bovino():
    ruta = os.path.join(BASE_DIR, 'DataSheet', 'CENSO-BOVINO-2025.csv')
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
    df = pd.read_csv(ruta, sep=';', encoding='utf-8')
    df.columns = [col.strip().lower() for col in df.columns]
    for col in df.columns:
        if col != 'departamento':
            df[col] = df[col].astype(str).str.replace('.', '', regex=False)\
                                       .str.replace(',', '.', regex=False)\
                                       .str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce')
    if df.empty:
        raise ValueError("El DataFrame del censo está vacío")
    return df

def cargar_datos_raza():
    region_1 = ['ANTIOQUIA', 'BOGOTÁ DC', 'BOYACÁ', 'CALDAS', 'CAUCA', 'CUNDINAMARCA',
                'NARIÑO', 'QUINDÍO', 'RISARALDA', 'VALLE DEL CAUCA']
    region_2 = ['ARAUCA', 'ATLÁNTICO', 'BOLIVAR', 'CAQUETÁ', 'CASANARE', 'CESAR', 'CÓRDOBA',
                'GUAVIARE', 'HUILA', 'LA GUAJIRA', 'MAGDALENA', 'META', 'NORTE DE SANTANDER',
                'PUTUMAYO', 'SANTANDER', 'SUCRE', 'TOLIMA']
    razas_r1 = ['Holstein', 'Simmental Suizo', 'Jersey', 'Normando']
    volumen_r1 = [25, 18, 16, 14]
    razas_r2 = ['Gyr']
    volumen_r2 = [12]
    data = []
    for dpto in region_1:
        for raza, litros in zip(razas_r1, volumen_r1):
            data.append({'departamento': dpto, 'razas': raza, 'volumen diario': litros, 'region': 1})
    for dpto in region_2:
        for raza, litros in zip(razas_r2, volumen_r2):
            data.append({'departamento': dpto, 'razas': raza, 'volumen diario': litros, 'region': 2})
    return pd.DataFrame(data)

def obtener_mejor_mes():
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    precios = [1450, 1480, 1500, 1520, 1490, 1510, 1530, 1620, 1580, 1550, 1500, 1480]
    acopios = [88, 90, 91, 89, 87, 92, 93, 92, 90, 89, 88, 87]
    df = pd.DataFrame({'mes': meses, 'precio': precios, 'acopio': acopios})
    df['rentabilidad'] = df['precio'] / df['acopio']
    if df.empty:
        return "No disponible", 0, 0
    mejor = df.sort_values(by='rentabilidad', ascending=False).iloc[0]
    return mejor['mes'], mejor['precio'], mejor['acopio']

def generar_analisis_censo(df):
    grupos = ['terneras < 1 año', 'hembras 1 - 2 años', 'hembras 2 - 3 años', 'hembras > 3 años']
    grupos_existentes = [g for g in grupos if g in df.columns]
    mayores = []
    menores = []
    for g in grupos_existentes:
        if df[g].notna().any():
            try:
                depto_max = df.loc[df[g].idxmax()]
                depto_min = df.loc[df[g].idxmin()]
                mayores.append({'grupo': g, 'departamento': depto_max['departamento'], 'cantidad': int(depto_max[g])})
                menores.append({'grupo': g, 'departamento': depto_min['departamento'], 'cantidad': int(depto_min[g])})
            except (ValueError, KeyError):
                continue
    total_nacional = df[grupos_existentes].sum()
    total_general = total_nacional.sum()
    distribucion = {g: round(total_nacional[g] / total_general * 100, 2) for g in grupos_existentes} if total_general > 0 else {g: 0 for g in grupos_existentes}
    if 'total bovinos' in df.columns and df['total bovinos'].notna().any():
        depto_total_max = df.loc[df['total bovinos'].idxmax()]
        depto_total_min = df.loc[df['total bovinos'].idxmin()]
        depto_max_info = {'nombre': depto_total_max['departamento'], 'cantidad': int(depto_total_max['total bovinos'])}
        depto_min_info = {'nombre': depto_total_min['departamento'], 'cantidad': int(depto_total_min['total bovinos'])}
    else:
        depto_max_info = {'nombre': 'No disponible', 'cantidad': 0}
        depto_min_info = {'nombre': 'No disponible', 'cantidad': 0}
    return {
        'mayores': mayores,
        'menores': menores,
        'distribucion': distribucion,
        'depto_max': depto_max_info,
        'depto_min': depto_min_info
    }

@inversion_bp.route('/inversion', methods=['GET', 'POST'])
def inversion():
    try:
        df_censo = cargar_censo_bovino()
        df_raza = cargar_datos_raza()
        analisis = generar_analisis_censo(df_censo)

        departamentos = df_raza['departamento'].unique().tolist()
        depto_sel = request.form.get('departamento')
        raza_sel = request.form.get('raza')
        num_vacas = request.form.get('num_vacas')

        volumen_diario = None
        volumen_mensual = None
        mejor_mes = None
        precio_mes = None
        acopio_mes = None
        volumen_predicho = None
        precio_predicho = None
        rentabilidad_predicha = None
        recomendacion = None

        if depto_sel:
            depto_filtrado = df_raza[df_raza['departamento'] == depto_sel]

            if raza_sel and num_vacas:
                raza_info = depto_filtrado[depto_filtrado['razas'] == raza_sel]
                if not raza_info.empty:
                    volumen_diario = raza_info['volumen diario'].values[0]
                    volumen_mensual = volumen_diario * int(num_vacas) * 30

            mejor_mes, precio_mes, acopio_mes = obtener_mejor_mes()

            try:
                volumen_predicho = predecir_acopio(mejor_mes)
                precio_predicho = predecir_precio(mejor_mes)
                rentabilidad_predicha = precio_predicho / volumen_predicho
                recomendacion = f"📌 En {mejor_mes} se espera un acopio de {volumen_predicho:.2f} litros y un precio de {precio_predicho:.2f} COP/litro. Rentabilidad estimada: {rentabilidad_predicha:.2f} COP/litro. Es un mes óptimo para invertir en producción lechera."
            except Exception as e:
                recomendacion = f"No se pudo generar la predicción: {str(e)}"

        return render_template('inversion.html',
                               departamentos=departamentos,
                               razas=df_raza['razas'].unique().tolist(),
                               analisis=analisis,
                               depto_sel=depto_sel,
                               raza_sel=raza_sel,
                               num_vacas=num_vacas,
                               volumen_diario=volumen_diario,
                               volumen_mensual=volumen_mensual,
                               mejor_mes=mejor_mes,
                               precio_mes=precio_mes,
                               acopio_mes=acopio_mes,
                               volumen_predicho=volumen_predicho,
                               precio_predicho=precio_predicho,
                               rentabilidad_predicha=rentabilidad_predicha,
                               recomendacion=recomendacion)
    except Exception as e:
        return f"<h4 style='color:red;'>Error en inversión: {str(e)}</h4>"