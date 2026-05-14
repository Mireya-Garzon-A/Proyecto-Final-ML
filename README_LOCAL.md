Pruebas locales de la conexión a la base de datos

1) Copia `.env.example` a `.env` y rellena con tus valores (DATABASE_URL o MSSQL_*).

2) Crear y activar virtualenv e instalar dependencias:

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows PowerShell
pip install --upgrade pip
pip install -r requirements.txt
```

3) Ejecutar el script de prueba:

```bash
python scripts/test_db_connection.py
```

Salida esperada:
- `Prueba SELECT 1 -> 1` (conexión correcta)
- `Inicializando tablas (db.create_all)...`
- `Departamentos en la BD: N` (N=0 o >0 según estado)

Si falla la conexión, revisa:
- Que la URL/credenciales sean correctas.
- Que el host acepte conexiones externas.
- Logs y errores mostrados en la consola.
