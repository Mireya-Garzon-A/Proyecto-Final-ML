from flask import Blueprint, render_template, request
import pandas as pd
import os
from modelo_acopio import entrenar_modelo_acopio, predecir_acopio
from modelo_ml_rentabilidad import entrenar_modelo_rentabilidad, predecir_rentabilidad



inversion_bp = Blueprint('inversion', __name__, template_folder='templates')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def cargar_censo_bovino():
    ruta = os.path.join(BASE_DIR, 'DataSheet', 'CENSO-BOVINO-2025.csv')
    
    # Verificar si el archivo existe
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
    
    # Verificar que el DataFrame no esté vacío
    if df.empty:
        raise ValueError("El DataFrame del censo está vacío")
    
    return df

def cargar_datos_raza():
    # Definición de regiones - asegurando que MAGDALENA esté bien escrito
    region_1 = ['ANTIOQUIA', 'BOGOTÁ DC', 'BOYACÁ', 'CALDAS', 'CAUCA', 'CUNDINAMARCA',
                'NARIÑO', 'QUINDÍO', 'RISARALDA', 'VALLE DEL CAUCA']

    region_2 = ['ARAUCA', 'ATLÁNTICO', 'BOLIVAR', 'CAQUETÁ', 'CASANARE', 'CESAR', 'CÓRDOBA',
                'GUAVIARE', 'HUILA', 'LA GUAJIRA', 'MAGDALENA', 'META', 'NORTE DE SANTANDER',
                'PUTUMAYO', 'SANTANDER', 'SUCRE', 'TOLIMA']

    # Razas por región
    razas_r1 = ['Holstein', 'Simmental Suizo', 'Jersey', 'Normando']
    volumen_r1 = [25, 18, 16, 14]

    razas_r2 = ['Gyr']  # Cambiado a lista para consistencia
    volumen_r2 = [12]

    # Construcción de la tabla completa
    data = []

    for dpto in region_1:
        for raza, litros in zip(razas_r1, volumen_r1):
            data.append({
                'departamento': dpto,
                'razas': raza,
                'volumen diario': litros,
                'region': 1
            })

    for dpto in region_2:
        for raza, litros in zip(razas_r2, volumen_r2):  # Ahora también usa zip
            data.append({
                'departamento': dpto,
                'razas': raza,
                'volumen diario': litros,
                'region': 2
            })

    return pd.DataFrame(data)

def obtener_mejor_mes():
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    precios = [1450, 1480, 1500, 1520, 1490, 1510, 1530, 1620, 1580, 1550, 1500, 1480]
    acopios = [88, 90, 91, 89, 87, 92, 93, 92, 90, 89, 88, 87]

    df = pd.DataFrame({'mes': meses, 'precio': precios, 'acopio': acopios})
    df['rentabilidad'] = df['precio'] / df['acopio']
    
    # Verificar que el DataFrame no esté vacío antes de acceder
    if df.empty:
        return "No disponible", 0, 0
    
    mejor = df.sort_values(by='rentabilidad', ascending=False).iloc[0]
    return mejor['mes'], mejor['precio'], mejor['acopio']

def generar_analisis_censo(df):
    # Verificar que el DataFrame no esté vacío
    if df.empty:
        return {
            'mayores': [],
            'menores': [],
            'distribucion': {},
            'depto_max': {'nombre': 'No disponible', 'cantidad': 0},
            'depto_min': {'nombre': 'No disponible', 'cantidad': 0}
        }
    
    grupos = ['terneras < 1 año', 'hembras 1 - 2 años', 'hembras 2 - 3 años', 'hembras > 3 años']
    
    # Verificar que las columnas existan en el DataFrame
    grupos_existentes = [g for g in grupos if g in df.columns]
    
    if not grupos_existentes:
        raise ValueError("No se encontraron las columnas de grupos en el DataFrame")
    
    mayores = []
    menores = []

    for g in grupos_existentes:
        # Verificar que la columna no esté vacía
        if df[g].notna().any():
            try:
                depto_max = df.loc[df[g].idxmax()]
                depto_min = df.loc[df[g].idxmin()]
                mayores.append({'grupo': g, 'departamento': depto_max['departamento'], 'cantidad': int(depto_max[g])})
                menores.append({'grupo': g, 'departamento': depto_min['departamento'], 'cantidad': int(depto_min[g])})
            except (ValueError, KeyError):
                # Si hay error, omitir este grupo
                continue

    total_nacional = df[grupos_existentes].sum()
    total_general = total_nacional.sum()
    
    if total_general > 0:
        distribucion = {g: round(total_nacional[g] / total_general * 100, 2) for g in grupos_existentes}
    else:
        distribucion = {g: 0 for g in grupos_existentes}

    # Verificar si existe la columna 'total bovinos'
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
        mes_sel = request.form.get('mes')
        ano_sel = request.form.get('ano')
        volumen_predicho = None

        region = None
        departamentos_region = []
        razas_region = []
        volumen_diario = None
        volumen_mensual = None
        mejor_mes = None
        precio_mes = None
        acopio_mes = None
        recomendacion = None

        if depto_sel:
            # Verificar que el departamento existe en el DataFrame
            depto_filtrado = df_raza[df_raza['departamento'] == depto_sel]
            if not depto_filtrado.empty:
                region = depto_filtrado['region'].iloc[0]
                departamentos_region = df_raza[df_raza['region'] == region]['departamento'].unique().tolist()
                
                # Obtener razas de la región de forma segura
                razas_filtradas = df_raza[df_raza['region'] == region][['razas', 'volumen diario']].drop_duplicates()
                if not razas_filtradas.empty:
                    razas_region = razas_filtradas.to_dict('records')

        if raza_sel and num_vacas and num_vacas.isdigit():
            num_vacas = int(num_vacas)
            
            # Verificar que la raza existe en el DataFrame
            raza_filtrada = df_raza[df_raza['razas'] == raza_sel]
            if not raza_filtrada.empty:
                volumen_raza = raza_filtrada['volumen diario'].iloc[0]
                volumen_diario = volumen_raza * num_vacas
                volumen_mensual = volumen_diario * 30

                mejor_mes, precio_mes, acopio_mes = obtener_mejor_mes()
                recomendacion = f"📅 El mejor mes para vender es {mejor_mes}, porque el precio fue alto (${precio_mes} COP/litro) y el volumen de acopio fue estable ({acopio_mes} millones de litros)."
            else:
                recomendacion = "⚠️ La raza seleccionada no está disponible para este departamento."


        # === Predicción de acopio mensual usando ML ===
        mes_sel = request.form.get('mes')
        ano_sel = request.form.get('ano')
        volumen_predicho = None

        if mes_sel and ano_sel and depto_sel:
            try:
                ano_int = int(ano_sel)
                ruta_modelo = os.path.join(BASE_DIR, 'DataSheet', 'Volumen de Acopio Directos - Res 0017 de 2012.csv')
                modelo, le_mes, le_depto = entrenar_modelo_acopio(ruta_modelo)
                volumen_predicho = predecir_acopio(modelo, le_mes, le_depto, mes_sel, ano_int, depto_sel)
            except ValueError:
                print("⚠️ Año inválido: no se puede convertir a entero.")
            except Exception as e:
                print(f"⚠️ Error en predicción ML: {str(e)}")
        #======================================================================
        # === Predicción de rentabilidad usando ML ===
        ruta_csv = os.path.join(BASE_DIR, 'DataSheet', 'Acopio_Precio_24Meses.csv')
        try:
            modelo, le_mes, df_rentabilidad = entrenar_modelo_rentabilidad(ruta_csv)
            mejor_mes_data = predecir_rentabilidad(modelo, le_mes, df_rentabilidad)
        except Exception as e:
            print(f"⚠️ Error en modelo ML: {str(e)}")
            mejor_mes_data = None

        #======================================================================

        return render_template('inversion.html',
                               analisis=analisis,
                               tabla_censo=df_censo.to_html(classes='table table-bordered table-sm', index=False),
                               departamentos=departamentos,
                               depto_sel=depto_sel,
                               region=region,
                               departamentos_region=departamentos_region,
                               razas_region=razas_region,
                               raza_sel=raza_sel,
                               num_vacas=num_vacas,
                               volumen_diario=volumen_diario,
                               volumen_mensual=volumen_mensual,
                               mejor_mes=mejor_mes,
                               precio_mes=precio_mes,
                               acopio_mes=acopio_mes,
                               recomendacion=recomendacion,
                               volumen_predicho=volumen_predicho,
                               mes_sel=mes_sel,
                                ano_sel=ano_sel,
                                mejor_mes_data=mejor_mes_data
                               )

    except Exception as e:
        # Agregar más detalles del error para debugging
        error_details = f"Error al procesar los datos: {str(e)}"
        print(f"ERROR DETALLADO: {error_details}")  # Para ver en consola
        return f"<h4 style='color:red;'>{error_details}</h4>"