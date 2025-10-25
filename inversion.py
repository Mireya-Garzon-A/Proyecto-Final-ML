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

def cargar_acopio():
    """Carga el CSV de acopio y devuelve un DataFrame limpio."""
    ruta = os.path.join(BASE_DIR, 'DataSheet', 'Volumen de Acopio Directos - Res 0017 de 2012.csv')
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"Archivo de acopio no encontrado: {ruta}")
    df = pd.read_csv(ruta, sep=';', encoding='utf-8')
    # Normalizar nombres de columnas
    df.columns = [c.strip() for c in df.columns]
    # Limpiar columna NACIONAL y las columnas de departamentos: quitar puntos miles y 'nd'
    def clean_num(x):
        if pd.isna(x):
            return pd.NA
        s = str(x).strip()
        if s.lower() in ('nd', ''):
            return pd.NA
        # quitar puntos de miles y espacios
        s = s.replace('.', '').replace(' ', '')
        try:
            return float(s)
        except Exception:
            return pd.NA

    for col in df.columns:
        if col.lower() not in ('año', 'ano', 'mes'):
            df[col] = df[col].apply(clean_num)
    return df

def mejores_meses_acopio(n_top=3, departamento=None):
    """Devuelve los n_top meses con mayor acopio promedio. Si departamento es None usa NACIONAL, si no usa la columna del departamento."""
    try:
        df_acopio = cargar_acopio()
    except Exception:
        return []
    col = 'NACIONAL' if departamento is None else departamento.upper()
    if col not in df_acopio.columns:
        # intenta buscar coincidencia sin tildes/espacios
        cols_clean = {c.upper().replace(' ', ''): c for c in df_acopio.columns}
        key = col.replace(' ', '')
        if key in cols_clean:
            col = cols_clean[key]
        else:
            return []
    # Agrupar por mes y calcular media
    df2 = df_acopio[['mes', col]].copy()
    df2 = df2.dropna(subset=[col])
    if df2.empty:
        return []
    grouped = df2.groupby('mes', sort=False)[col].mean()
    top = grouped.sort_values(ascending=False).head(n_top)
    # Devolver lista de dicts con mes y valor para facilitar visualización
    return [{'mes': m, 'valor': float(v)} for m, v in top.items()]

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

        # Generar tabla HTML del censo para mostrar en el modal
        try:
            tabla_censo_df = df_censo.copy()
            # Mejorar nombres de columnas para visualización
            tabla_censo_df.columns = [c.title() for c in tabla_censo_df.columns]
            tabla_censo = tabla_censo_df.to_html(classes="table table-striped table-sm table-hover",
                                                 index=False, border=0, justify="center", na_rep="")
        except Exception:
            tabla_censo = "<p class='text-danger'>No fue posible cargar la tabla del censo.</p>"

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

        # Si usuario indicó raza y número de vacas, calcular mejor departamento/region y meses recomendados
        mejor_depto = None
        mejor_region = None
        meses_recomendados = []
        meses_depto = []
        lista_mejores_departamentos = []
        show_modal_analisis = False
        input_error = None
        lista_mejores_info = []
        if raza_sel and num_vacas:
            try:
                num_vacas_int = int(num_vacas)
                if num_vacas_int <= 0:
                    raise ValueError("El número de vacas debe ser mayor que 0")
            except Exception:
                num_vacas_int = None
                input_error = "Ingrese un número válido de vacas (entero mayor que 0)."

            if num_vacas_int and raza_sel:
                # departamentos que tienen esa raza
                df_razas_sel = df_raza[df_raza['razas'] == raza_sel]
                if not df_razas_sel.empty:
                    # mejor departamento: el que tenga mayor 'volumen diario' por vaca
                    df_sorted = df_razas_sel.sort_values(by='volumen diario', ascending=False)
                    # top 3 departamentos para esta raza
                    lista_mejores_departamentos = df_sorted['departamento'].head(3).tolist()
                    mejor_row = df_sorted.iloc[0]
                    mejor_depto = mejor_row['departamento']
                    mejor_region = int(mejor_row['region']) if 'region' in mejor_row else None

                    # cálculo producción estimada para ese departamento
                    volumen_por_vaca = float(mejor_row['volumen diario'])
                    produccion_diaria = volumen_por_vaca * num_vacas_int
                    produccion_mensual = produccion_diaria * 30

                    # mejores meses según acopio: a nivel nacional y para el departamento seleccionado
                    meses_recomendados = mejores_meses_acopio(n_top=3, departamento=None)
                    meses_depto = mejores_meses_acopio(n_top=3, departamento=mejor_depto)

                    # calcular máximos para visualización (evitar división por cero)
                    meses_recomendados_max = max([m['valor'] for m in meses_recomendados]) if meses_recomendados else 0
                    meses_depto_max = max([m['valor'] for m in meses_depto]) if meses_depto else 0

                    # Añadir porcentaje relativo para facilitar render en template (0-100)
                    if meses_recomendados_max > 0:
                        for m in meses_recomendados:
                            m['pct'] = (m['valor'] / meses_recomendados_max) * 100
                    else:
                        for m in meses_recomendados:
                            m['pct'] = 0

                    if meses_depto_max > 0:
                        for m in meses_depto:
                            m['pct'] = (m['valor'] / meses_depto_max) * 100
                    else:
                        for m in meses_depto:
                            m['pct'] = 0

                    # pasar los resultados a variables que la plantilla espera
                    # (si ya existen, sobreescribimos para mostrar info más útil)
                    volumen_diario = produccion_diaria
                    volumen_mensual = produccion_mensual
                    # construir lista con info por departamento (producción estimada para la cantidad dada)
                    for _, row in df_sorted.head(3).iterrows():
                        vpv = float(row['volumen diario'])
                        depto = row['departamento']
                        region = int(row['region']) if 'region' in row else None
                        prod_diaria = vpv * num_vacas_int
                        prod_mensual = prod_diaria * 30
                        lista_mejores_info.append({
                            'departamento': depto,
                            'region': region,
                            'volumen_por_vaca': vpv,
                            'prod_diaria': prod_diaria,
                            'prod_mensual': prod_mensual
                        })
                else:
                    mejor_depto = None
                    mejor_region = None

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
                               recomendacion=recomendacion,
                               tabla_censo=tabla_censo,
                               mejor_depto=mejor_depto,
                               mejor_region=mejor_region,
                               meses_recomendados=meses_recomendados,
                               meses_depto=meses_depto,
                               lista_mejores_departamentos=lista_mejores_departamentos,
                               lista_mejores_info=lista_mejores_info,
                               input_error=input_error,
                               meses_recomendados_max=meses_recomendados_max if 'meses_recomendados_max' in locals() else 0,
                               meses_depto_max=meses_depto_max if 'meses_depto_max' in locals() else 0)
    except Exception as e:
        return f"<h4 style='color:red;'>Error en inversión: {str(e)}</h4>"