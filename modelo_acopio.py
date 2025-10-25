import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# === Entrenar el modelo de acopio ===
def entrenar_modelo_acopio():
    ruta = os.path.join(BASE_DIR, 'DataSheet', 'Volumen de Acopio Directos - Res 0017 de 2012.csv')
    df = pd.read_csv(ruta, sep=None, engine='python')
    df.columns = [col.strip() for col in df.columns]

    # Identificar columnas
    col_mes = [c for c in df.columns if 'mes' in c.lower()][0]
    col_vol = [c for c in df.columns if 'vol' in c.lower() or 'litros' in c.lower() or 'acopio' in c.lower() or 'total' in c.lower()][0]

    # Agrupar por mes
    df_group = df.groupby(col_mes)[col_vol].mean().reset_index()

    # Codificar meses
    le = LabelEncoder()
    X = le.fit_transform(df_group[col_mes]).reshape(-1, 1)
    y = df_group[col_vol].values

    modelo = LinearRegression()
    modelo.fit(X, y)

    return modelo, le

# === Predecir acopio para un mes específico ===
def predecir_acopio(mes, año=None):
    modelo, le = entrenar_modelo_acopio()
    mes_codificado = le.transform([mes])[0]
    prediccion = modelo.predict([[mes_codificado]])
    return float(prediccion[0])

# === Encontrar el mes con mayor volumen predicho ===
def mejor_mes_para_invertir():
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
             'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    predicciones = {mes: predecir_acopio(mes) for mes in meses}
    mejor_mes = max(predicciones, key=predicciones.get)
    volumen = predicciones[mejor_mes]
    return mejor_mes, volumen