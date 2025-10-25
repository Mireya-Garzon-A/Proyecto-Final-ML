import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
import numpy as np

# === 1. Cargar el archivo CSV ===
archivo = "DataSheet/Volumen de Acopio Directos - Res 0017 de 2012.csv"
df = pd.read_csv(archivo, sep=None, engine='python')

# === 2. Limpieza y normalización de columnas ===
df.columns = [col.strip() for col in df.columns]

# === 3. Identificar columnas clave ===
col_mes = [c for c in df.columns if 'mes' in c.lower()][0]
col_vol = [c for c in df.columns if 'vol' in c.lower() or 'litros' in c.lower() or 'acopio' in c.lower() or 'total' in c.lower()][0]

# === 4. Agrupación por mes ===
df_group = df.groupby(col_mes)[col_vol].mean().reset_index()

# === 5. Modelo de Machine Learning ===
# Este modelo usa regresión lineal para estimar el volumen de acopio según el mes.
# Es útil para identificar tendencias estacionales y apoyar decisiones de compra o inversión.

meses = df_group[col_mes].tolist()
le = LabelEncoder()
X = le.fit_transform(meses).reshape(-1, 1)
y = df_group[col_vol].values

modelo = LinearRegression()
modelo.fit(X, y)
y_pred = modelo.predict(X)

# Visualización comparativa
plt.figure(figsize=(10,5))
plt.plot(meses, y, label='Volumen real', marker='o')
plt.plot(meses, y_pred, label='Predicción ML', linestyle='--', color='orange')
plt.title("Predicción de Acopio de Leche por Mes")
plt.xlabel("Mes")
plt.ylabel("Volumen Promedio de Acopio")
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig('static/images/grafico_acopio.png')  # para mostrar en HTML
plt.show()

# Explicación del modelo
print("\n🔹 Modelo de Machine Learning:")
print("   - Tipo: Regresión lineal")
print("   - Coeficiente:", modelo.coef_[0])
print("   - Intercepto:", modelo.intercept_)

# === 6. Estadística desde enero 2024 ===
# Si hay columna de fecha, convertirla
if 'Fecha' in df.columns:
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df_2024 = df[df['Fecha'] >= '2024-01-01']
else:
    df['Año'] = pd.to_datetime(df[col_mes], errors='coerce').dt.year
    df_2024 = df[df['Año'] >= 2024]

# Mes con mayor volumen desde 2024
vol_por_mes = df_2024.groupby(col_mes)[col_vol].sum().reset_index()
mes_max_vol = vol_por_mes.sort_values(by=col_vol, ascending=False).iloc[0]

# Departamento con mayor volumen (si existe)
if 'Departamento' in df_2024.columns:
    vol_por_depto = df_2024.groupby('Departamento')[col_vol].sum().reset_index()
    depto_max_vol = vol_por_depto.sort_values(by=col_vol, ascending=False).iloc[0]
else:
    depto_max_vol = None

# === 7. Preparación para interacción por año (ejemplo para Flask) ===
años_disponibles = sorted(df['Año'].dropna().unique()) if 'Año' in df.columns else []

# === 8. Imprimir resultados ===
print("\n🔹 Mes con mayor volumen desde 2024:", mes_max_vol[col_mes], "-", mes_max_vol[col_vol])
if depto_max_vol is not None:
    print("🔹 Departamento destacado:", depto_max_vol['Departamento'], "-", depto_max_vol[col_vol])
else:
    print("🔹 No se encontró columna de departamento.")
