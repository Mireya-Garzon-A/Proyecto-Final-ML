import matplotlib
matplotlib.use('Agg')  # ✅ Usa backend no interactivo
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# Datos realistas para altitud, frecuencia respiratoria y SpO₂ (%)
data = {
    "Altitud": [0, 500, 1000, 1500, 2000,
                2500, 3000, 3500, 4000, 4500],
    "Frecuencia Respiratoria": [14, 15, 15, 16, 17,
                                18, 20, 22, 24, 26],
    "Saturacion Oxigeno (%)": [98, 97, 96, 95, 93,
                               91, 89, 86, 84, 81]
}

df = pd.DataFrame(data)

# ------------------------
# Variables y modelo
# ------------------------
x = df[["Altitud", "Frecuencia Respiratoria"]]
y = df[["Saturacion Oxigeno (%)"]]

model = LinearRegression()
model.fit(x, y)

# ------------------------
# Función de predicción
# ------------------------
def CalculateOxygen(altitud: float, frecuencia: float) -> float:
    """Devuelve SpO₂ (%) predicho, redondeado a 2 decimales."""
    pred = model.predict([[altitud, frecuencia]])[0][0]
    return round(float(pred), 2)

# ------------------------
# Función para graficar
# ------------------------
def save_plot(altitud: float = None, frecuencia: float = None, spo2: float = None):
    try:
        plt.close("all")
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # --- Subplot 1: Altitud vs SpO₂
        ax = axes[0]
        ax.scatter(df["Altitud"], df["Saturacion Oxigeno (%)"], color="blue",
                   label="Datos reales", alpha=0.7)

        altitudes = np.linspace(df["Altitud"].min(), df["Altitud"].max(), 200)
        preds_alt = model.predict(np.column_stack((altitudes,
                                                   np.full(altitudes.shape, frecuencia if frecuencia else df["Frecuencia Respiratoria"].mean()))))
        ax.plot(altitudes, preds_alt, color="red", label="Tendencia")
        if altitud is not None and spo2 is not None:
            ax.scatter(altitud, spo2, color="green", s=120, edgecolor="black", label="Predicción actual")
        ax.set_title("Altitud vs Saturación de Oxígeno")
        ax.set_xlabel("Altitud (m)")
        ax.set_ylabel("SpO₂ (%)")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # --- Subplot 2: Frecuencia vs SpO₂
        ax = axes[1]
        ax.scatter(df["Frecuencia Respiratoria"], df["Saturacion Oxigeno (%)"], color="blue",
                   label="Datos reales", alpha=0.7)

        freqs = np.linspace(df["Frecuencia Respiratoria"].min(), df["Frecuencia Respiratoria"].max(), 200)
        preds_freq = model.predict(np.column_stack((np.full(freqs.shape, altitud if altitud else df["Altitud"].mean()), freqs)))
        ax.plot(freqs, preds_freq, color="red", label="Tendencia")
        if frecuencia is not None and spo2 is not None:
            ax.scatter(frecuencia, spo2, color="green", s=120, edgecolor="black", label="Predicción actual")
        ax.set_title("Frecuencia vs Saturación de Oxígeno")
        ax.set_xlabel("Frecuencia (resp/min)")
        ax.set_ylabel("SpO₂ (%)")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig("static/images/regresion.png")
        plt.close(fig)

    except Exception as e:
        print(f"Error al generar gráfico: {e}")