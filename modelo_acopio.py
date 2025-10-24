import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split

# Entrenamiento del modelo
def entrenar_modelo_acopio(ruta_csv):
    df = pd.read_csv(ruta_csv, sep=None, engine='python')
    df.columns = [col.strip().lower() for col in df.columns]

    col_mes = [c for c in df.columns if 'mes' in c][0]
    col_ano = [c for c in df.columns if 'año' in c or 'ano' in c][0]
    col_vol = [c for c in df.columns if 'vol' in c or 'acopio' in c or 'litros' in c or 'total' in c][0]
    col_depto = [c for c in df.columns if 'depto' in c or 'departamento' in c][0]

    df = df[[col_mes, col_ano, col_depto, col_vol]].dropna()

    le_mes = LabelEncoder()
    le_depto = LabelEncoder()
    df['mes_cod'] = le_mes.fit_transform(df[col_mes])
    df['depto_cod'] = le_depto.fit_transform(df[col_depto])

    X = df[['mes_cod', col_ano, 'depto_cod']]
    y = df[col_vol]

    modelo = RandomForestRegressor(n_estimators=100, random_state=42)
    modelo.fit(X, y)

    return modelo, le_mes, le_depto

# Predicción
def predecir_acopio(modelo, le_mes, le_depto, mes, año, departamento):
    mes_cod = le_mes.transform([mes])[0]
    depto_cod = le_depto.transform([departamento])[0]
    X_pred = [[mes_cod, año, depto_cod]]
    return modelo.predict(X_pred)[0]