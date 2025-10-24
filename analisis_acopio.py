import pandas as pd
import matplotlib.pyplot as plt

# === 1. Cargar el archivo CSV ===
archivo = "DataSheet/Volumen de Acopio Directos - Res 0017 de 2012.csv"

# Intentamos leer el CSV (detectando separador automáticamente)
df = pd.read_csv(archivo, sep=None, engine='python')

print("🔹 Columnas encontradas:")
print(df.columns)

print("\n🔹 Primeras filas:")
print(df.head())

# === 2. Limpieza y normalización de columnas ===
# Buscamos columnas que representen mes, año y volumen
# (ajustaremos según cómo venga el archivo)
columnas_posibles = ['Mes', 'mes', 'MES', 'Año', 'ANO', 'AÑO', 'Volumen', 'VOLUMEN', 'Total', 'TOTAL']

# Renombrar columnas comunes si es necesario
df.columns = [col.strip() for col in df.columns]

# === 3. Mostrar los meses únicos ===
if 'Mes' in df.columns or 'MES' in df.columns or 'mes' in df.columns:
    col_mes = [c for c in df.columns if c.lower().startswith('mes')][0]
    print("\n🔹 Meses encontrados:")
    print(df[col_mes].unique())
else:
    print("\n⚠️ No se encontró una columna llamada 'Mes' o similar.")

# === 4. Promedio de acopio por mes ===
# Intentamos identificar la columna del volumen
col_vol = [c for c in df.columns if 'vol' in c.lower() or 'litros' in c.lower() or 'acopio' in c.lower() or 'total' in c.lower()]
if col_vol:
    col_vol = col_vol[0]
    col_mes = [c for c in df.columns if 'mes' in c.lower()][0]
    df_group = df.groupby(col_mes)[col_vol].mean().reset_index()
    
    print("\n🔹 Promedio de acopio por mes:")
    print(df_group)
    
    # === 5. Graficar el acopio promedio por mes ===
    plt.figure(figsize=(10,5))
    plt.bar(df_group[col_mes], df_group[col_vol])
    plt.title("Promedio de Acopio de Leche por Mes")
    plt.xlabel("Mes")
    plt.ylabel("Volumen Promedio de Acopio")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
else:
    print("\n⚠️ No se encontró columna de volumen o acopio.")
