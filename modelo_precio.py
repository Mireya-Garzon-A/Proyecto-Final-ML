import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# === Entrenar el modelo de precios ===
def entrenar_modelo_precio():
    ruta = os.path.join(BASE_DIR, 'DataSheet', 'Precios de Leche - Historico.csv')
    df = pd.read_csv(ruta, sep=None, engine='python')
    df.columns = [col.strip() for col in df.columns]

    # Identificar columnas
    col_mes = [c for c in df.columns if 'mes' in c.lower()][0]
    col_precio = [c for c in df.columns if 'precio' in c.lower() or 'valor' in c.lower()][0]

    # Agrupar por mes
    df_group = df.groupby(col_mes)[col_precio].mean().reset_index()

    # Codificar meses
    le = LabelEncoder()
    X = le.fit_transform(df_group[col_mes]).reshape(-1, 1)
    y = df_group[col_precio].values

    modelo = LinearRegression()
    modelo.fit(X, y)

    return modelo, le

# === Predecir precio para un mes específico ===
def predecir_precio(mes, año=None):
    modelo, le = entrenar_modelo_precio()
    mes_codificado = le.transform([mes])[0]
    prediccion = modelo.predict([[mes_codificado]])
    return float(prediccion[0])
