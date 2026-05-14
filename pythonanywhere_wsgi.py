"""
Snippet WSGI para PythonAnywhere.

Pegar el contenido de este archivo dentro del editor WSGI de PythonAnywhere
en la sección Web -> WSGI configuration file.

Rutas ya ajustadas para el usuario `delcampoalalgortimo` y virtualenv
`/home/delcampoalalgortimo/venvs/proyecto-ml`. Si tu virtualenv tiene otra
ruta, actualiza `venv_path` antes de pegar.
"""
import sys
import os

project_home = os.environ.get('PA_PROJECT_HOME', '/home/delcampoalalgortimo/Proyecto-Final-ML')
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Indicar que estamos en PythonAnywhere para que `app.py` use SQLite
os.environ.setdefault('PYTHONANYWHERE', 'true')
os.environ.setdefault('SECRET_KEY', os.environ.get('SECRET_KEY', 'pon_aqui_una_clave_segura'))

# Activar virtualenv (ajusta si tu virtualenv está en otra ruta)
venv_path = os.environ.get('PA_VENV_PATH', '/home/delcampoalalgortimo/venvs/proyecto-ml')
activate_this = os.path.join(venv_path, 'bin', 'activate_this.py')
if os.path.exists(activate_this):
    with open(activate_this) as f:
        exec(f.read(), dict(__file__=activate_this))
else:
    # En caso de que no exista activate_this.py (entornos modernos), intentar usar activate
    activate_sh = os.path.join(venv_path, 'bin', 'activate')
    if os.path.exists(activate_sh):
        # No podemos "source" un shell script aquí, pero PythonAnywhere
        # suele activar el venv automáticamente si se configura en el panel Web.
        pass

# Importar la aplicación WSGI
from app import application
