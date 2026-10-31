# Guía de Despliegue en PythonAnywhere (Paso a Paso)

Esta aplicación fue configurada y optimizada específicamente para funcionar al 100% en **PythonAnywhere**, incluyendo la subida y visualización de imágenes (`media/`), archivos estáticos (`staticfiles/`) y base de datos persistente.

---

### ¿Por qué SQLite / MySQL nativo en lugar de MongoDB en PythonAnywhere?
1. **Sin servidores externos**: PythonAnywhere no aloja MongoDB localmente. Usar MongoDB requeriría crear un cluster externo en MongoDB Atlas y añadir reglas de red.
2. **Cero latencia**: La base de datos local en PythonAnywhere corre directamente en el almacenamiento del servidor, respondiendo en milisegundos.
3. **Manejo nativo de Imágenes**: Django ORM gestiona el almacenamiento, validación y rutas de imágenes (`ImageField`) de forma transparente junto al panel de administración.
4. **Gratuito y sin límites de red**: Compatible con la cuenta gratuita de PythonAnywhere sin depender de listas de puertos externas.

---

## Pasos para Desplegar en PythonAnywhere

### 1. Clonar el repositorio en PythonAnywhere
1. Inicia sesión en [PythonAnywhere](https://www.pythonanywhere.com/).
2. Ve a la pestaña **Consoles** y abre una consola **Bash**.
3. Clona tu repositorio de GitHub:
   ```bash
   git clone https://github.com/jgregoza/todo_django_mongodb.git
   cd todo_django_mongodb
   ```

---

### 2. Crear y activar el entorno virtual
En la consola Bash de PythonAnywhere ejecuta:
```bash
mkvirtualenv --python=/usr/bin/python3.12 todo-env
pip install -r requirements.txt
```

---

### 3. Migrar la base de datos y recolectar archivos estáticos
Ejecuta en la misma consola:
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python seed_data.py
```
*(Opcional) Crea un administrador para acceder a `/admin/`:*
```bash
python manage.py createsuperuser
```

---

### 4. Configurar la pestaña "Web" en PythonAnywhere
1. Ve a la pestaña **Web** del panel de control de PythonAnywhere.
2. Si no tienes una app web creada, haz clic en **Add a new web app**, selecciona **Manual configuration** y elige **Python 3.12**.
3. En la sección **Code**:
   - **Source code**: `/home/<tu-usuario>/todo_django_mongodb`
   - **Working directory**: `/home/<tu-usuario>/todo_django_mongodb`
4. En la sección **Virtualenv**:
   - Ingresa: `/home/<tu-usuario>/.virtualenvs/todo-env`
5. En la sección **Static files**:
   - Agrega dos mapeos:
     1. **URL**: `/static/`  
        **Directory**: `/home/<tu-usuario>/todo_django_mongodb/staticfiles`
     2. **URL**: `/media/`  
        **Directory**: `/home/<tu-usuario>/todo_django_mongodb/media`
6. En la sección **Code**, haz clic en el enlace del archivo **WSGI configuration file** (`/var/www/<tu-usuario>_pythonanywhere_com_wsgi.py`), borra todo su contenido y pega lo siguiente (reemplazando `<tu-usuario>` por tu usuario):

```python
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

path = '/home/<tu-usuario>/todo_django_mongodb'
if path not in sys.path:
    sys.path.append(path)

env_file = Path(path) / ".env"
if env_file.exists():
    load_dotenv(env_file)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
7. Guarda los cambios (**Save**).

---

### 5. Recargar la aplicación
Regresa a la pestaña **Web** y presiona el botón verde grande:
**"Reload <tu-usuario>.pythonanywhere.com"**

¡Listo! Tu aplicación estará en línea y accesible en:
`https://<tu-usuario>.pythonanywhere.com`
