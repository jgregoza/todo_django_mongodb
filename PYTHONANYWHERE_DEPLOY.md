# Guía de Despliegue de TaskPilot en PythonAnywhere

Esta guía detalla el procedimiento para desplegar **TaskPilot** en **PythonAnywhere** (plan gratuito), utilizando la arquitectura aprobada: **Python 3.10**, **Django 5.2.19 LTS** y **SQLite** con aislamiento seguro de multimedia privada.

---

## 1. Arquitectura de Despliegue

- **Directorio de código**: `/home/<tu-usuario>/taskpilot`
- **Directorio de datos**: `/home/<tu-usuario>/taskpilot-data` (`db.sqlite3` y carpeta `media/`)
- **Archivos estáticos**: `/home/<tu-usuario>/taskpilot/staticfiles`
- **Entorno virtual**: `/home/<tu-usuario>/.virtualenvs/taskpilot-env`
- **Base de datos**: SQLite relacional nativa gestionada por Django ORM.
- **Multimedia privada**: No se mapea en la sección de archivos estáticos del panel Web de PythonAnywhere. Se sirve exclusivamente mediante la vista autenticada de Django para garantizar la privacidad de los usuarios.

---

## 2. Pasos para el Despliegue

### Paso 1: Clonar el repositorio
En la consola **Bash** de PythonAnywhere:
```bash
git clone https://github.com/jgregoza/todo_django_mongodb.git /home/<tu-usuario>/taskpilot
cd /home/<tu-usuario>/taskpilot
```

### Paso 2: Crear el directorio de datos
```bash
mkdir -p /home/<tu-usuario>/taskpilot-data/media
```

### Paso 3: Crear y configurar el entorno virtual (Python 3.10)
```bash
mkvirtualenv --python=/usr/bin/python3.10 taskpilot-env
pip install -r requirements.txt
```

### Paso 4: Configurar variables de entorno (`.env`)
Copia la plantilla y define tus claves seguras:
```bash
cp .env.example .env
chmod 600 .env
nano .env
```
Asegúrate de configurar:
```ini
SECRET_KEY=clave-secreta-larga-y-aleatoria
DEBUG=False
ALLOWED_HOSTS=<tu-usuario>.pythonanywhere.com
DATA_DIR=/home/<tu-usuario>/taskpilot-data
STATIC_ROOT=/home/<tu-usuario>/taskpilot/staticfiles
CSRF_TRUSTED_ORIGINS=https://<tu-usuario>.pythonanywhere.com
```

### Paso 5: Migraciones y recolección de estáticos
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

*(Opcional) Crear superusuario para el panel de administración:*
```bash
python manage.py createsuperuser
```

*(Opcional para pruebas) Sembrar datos asignados a un usuario existente:*
```bash
python seed_data.py <username>
```

---

## 3. Configuración en la pestaña "Web"

1. Ve a la pestaña **Web** del panel de control de PythonAnywhere.
2. Si creas una app nueva: selecciona **Manual configuration** y elige **Python 3.10**.
3. En la sección **Code**:
   - **Source code**: `/home/<tu-usuario>/taskpilot`
   - **Working directory**: `/home/<tu-usuario>/taskpilot`
4. En la sección **Virtualenv**:
   - `/home/<tu-usuario>/.virtualenvs/taskpilot-env`
5. En la sección **Static files**:
   - **URL**: `/static/`
     **Directory**: `/home/<tu-usuario>/taskpilot/staticfiles`
   *(Nota de seguridad: **NO** agregues mapeo estático para `/media/`; las imágenes son privadas y se sirven mediante vistas autenticadas).*
6. En la sección **Code**, haz clic en el enlace del archivo **WSGI configuration file** (`/var/www/<tu-usuario>_pythonanywhere_com_wsgi.py`), reemplaza su contenido por el provisto en `pythonanywhere_wsgi.py` (ajustando la ruta a tu usuario) y guarda los cambios.
7. Haz clic en el botón verde **"Reload <tu-usuario>.pythonanywhere.com"**.

---

## 4. Verificación

Accede a `https://<tu-usuario>.pythonanywhere.com` para comprobar el correcto funcionamiento de TaskPilot.
