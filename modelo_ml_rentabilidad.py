import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

def entrenar_modelo_rentabilidad(ruta_csv):
    df = pd.read_csv(ruta_csv)
    df.columns = [col.strip().lower() for col in df.columns]

    # Codificar mes como número
    le_mes = LabelEncoder()
    df['mes_cod'] = le_mes.fit_transform(df['mes'])

    # Crear variable objetivo: rentabilidad = 0.6 * precio + 0.4 * volumen
    df['rentabilidad'] = 0.6 * df['precio'] + 0.4 * df['volumen']

    # Variables de entrada
    X = df[['mes_cod', 'año', 'precio', 'volumen']]
    y = df['rentabilidad']

    # Entrenamiento del modelo
    modelo = RandomForestRegressor(n_estimators=100, random_state=42)
    modelo.fit(X, y)

    return modelo, le_mes, df

def predecir_rentabilidad(modelo, le_mes, df):
    df['mes_cod'] = le_mes.transform(df['mes'])
    X_pred = df[['mes_cod', 'año', 'precio', 'volumen']]
    df['rentabilidad_predicha'] = modelo.predict(X_pred)
    mejor_fila = df.loc[df['rentabilidad_predicha'].idxmax()]
    return {
        'mes': mejor_fila['mes'].capitalize(),
        'año': int(mejor_fila['año']),
        'precio': round(mejor_fila['precio'], 2),
        'volumen': round(mejor_fila['volumen'], 2),
        'rentabilidad': round(mejor_fila['rentabilidad_predicha'], 2)
    }