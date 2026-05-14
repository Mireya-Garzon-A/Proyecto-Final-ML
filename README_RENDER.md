Despliegue en Render

1) Subir el repositorio a GitHub y conectar el repo en Render.

2) En Render crear un nuevo Web Service:
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:application --bind 0.0.0.0:$PORT`

3) Variables de entorno (en la web service > Environment):
   - `SECRET_KEY`: clave secreta para Flask
   - `DATABASE_URL`: URL de la BD (ej: `mysql+pymysql://user:pass@host:port/dbname` o `postgres://...`)
   - Opcional: `MYSQL_DATABASE_URL` si usas esa variable
   - `SKIP_CREATE_ALL=0` (si deseas que la app cree tablas automáticamente)

4) Archivos estáticos: Flask servirá `static/` automáticamente.

5) Notas importantes:
   - No uses SQLite para datos persistentes en Render (filesystem efímero). Usa una base de datos gestionada y pon su URL en `DATABASE_URL`.
   - Asegúrate de incluir `pymysql` en `requirements.txt` si usas MySQL con `mysql+pymysql://`.
