import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, accuracy_score, classification_report

# ----------------------------------------
# Cargar los datos desde archivo CSV
# Abandonada: 1 = Sí fue abandonada, 0 = No fue abandonada
data = pd.read_csv('./DataSheet/data.csv', delimiter=';')

# Verificar estructura
print("=== Vista previa del dataset ===")
print(data.head())
print(data.info())

# Codificar variable categórica 'TipoMascota'
data = pd.get_dummies(data, columns=['tipo_mascota'], drop_first=True)

# Separar variables independientes y dependiente
x = data.drop('abandono', axis=1)
y = data['abandono']

# Dividir en entrenamiento y prueba (80/20) con estratificación
x_train, x_test, y_train, y_test = train_test_split(
    x, y, test_size=0.2, random_state=42, stratify=y
)

# Estandarizar variables numéricas
scaler = StandardScaler()
x_train_scaled = scaler.fit_transform(x_train)
x_test_scaled = scaler.transform(x_test)

# Crear y entrenar el modelo de regresión logística
logistic_model = LogisticRegression()
logistic_model.fit(x_train_scaled, y_train)

# ----------------------------------------
# Función para evaluar el modelo
def evaluate():
    """
    Evalúa el modelo con métricas estándar y genera imagen de matriz de confusión.
    """
    y_pred = logistic_model.predict(x_test_scaled)

    # Matriz de confusión
    conf_matrix = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(6, 4))
    sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues', cbar=False,
                xticklabels=['No', 'Sí'], yticklabels=['No', 'Sí'])
    plt.xlabel("Predicción")
    plt.ylabel("Real")
    plt.title("Matriz de Confusión")
    plt.tight_layout()
    plt.savefig("./static/matriz_confusion.png")  # Guarda en carpeta 'static'
    plt.close()

    # Reporte de clasificación
    print("=== Reporte de Clasificación ===")
    print(classification_report(y_test, y_pred, target_names=["No", "Sí"]))

    # Exactitud
    accuracy = accuracy_score(y_test, y_pred)
    print(f'=== Exactitud del modelo: {accuracy:.4f}')

    return {
        'accuracy': accuracy,
        'classification_report': classification_report(y_test, y_pred, output_dict=True),
        'confusion_matrix': conf_matrix.tolist()
    }

# ----------------------------------------
# Función para predecir “Sí”/“No” con probabilidad
def predict_label(features, threshold=0.5):
    """
    Predice "Sí" o "No" con probabilidad, dado un vector de características.
    
    Parámetros:
    - features: array o Series con las características del individuo
    - threshold: umbral de decisión (por defecto 0.5)
    
    Retorna:
    - etiqueta: "Sí" o "No"
    - probabilidad de clase positiva
    """
    features_scaled = scaler.transform([features])
    prob = logistic_model.predict_proba(features_scaled)[0][1]
    label = "Sí" if prob >= threshold else "No"
    return label, round(prob, 4)

# ----------------------------------------
# Ejecutar evaluación y ejemplo de predicción
if __name__ == "__main__":
    resultados = evaluate()

    # Usar un ejemplo real del test
    muestra = x_test.iloc[0]
    etiqueta, prob = predict_label(muestra)
    print(f"\nPredicción ejemplo:")
    print(f"Etiqueta: {etiqueta}")
    print(f"Probabilidad: {prob}")
