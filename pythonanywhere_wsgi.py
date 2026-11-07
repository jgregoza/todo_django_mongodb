"""
Archivo de configuración WSGI para PythonAnywhere.
Copia este contenido en tu archivo de configuración WSGI en la pestaña 'Web' de PythonAnywhere:
/var/www/jzamora_pythonanywhere_com_wsgi.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ruta absoluta al proyecto TaskPilot en PythonAnywhere
path = "/home/jzamora/taskpilot"

if path not in sys.path:
    sys.path.append(path)

# Cargar variables de entorno (.env)
env_file = Path(path) / ".env"
if env_file.exists():
    load_dotenv(env_file)

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
