# Guía de Despliegue y Operación — TaskPilot en PythonAnywhere

Este documento describe el procedimiento oficial y reproducible para desplegar y operar **TaskPilot** en **PythonAnywhere** (plan gratuito), siguiendo la arquitectura aprobada: **Python 3.10**, **Django 5.2.19 LTS**, **SQLite** nativo y separación de datos mutables.

---

## 1. Inventario y Arquitectura de Despliegue

| Componente | Ruta / Configuración | Propósito |
|---|---|---|
| **Código del proyecto** | `/home/<usuario>/taskpilot` | Código fuente versionado de la aplicación. |
| **Directorio de datos** | `/home/<usuario>/taskpilot-data` | Almacenamiento mutable: base SQLite (`db.sqlite3`) y carpeta `media/`. |
| **Archivos estáticos** | `/home/<usuario>/taskpilot/staticfiles` | CSS, iconos y JS recolectados para producción. |
| **Entorno virtual** | `/home/<usuario>/.virtualenvs/taskpilot-env` | Virtualenv aislado con Python 3.10 y dependencias fijadas. |
| **Archivo WSGI** | `/var/www/<usuario>_pythonanywhere_com_wsgi.py` | Punto de entrada del servidor WSGI. |
| **Base de datos** | SQLite (`DATA_DIR/db.sqlite3`) | Persistencia relacional, `timeout=20`, sin WAL. |
| **Multimedia privada** | `DATA_DIR/media/` | Imágenes de tareas protegidas servidas mediante vista Django autenticada. |

---

## 2. Pasos de Despliegue Inicial (Aprovisionamiento)

### Paso 1: Clonar el repositorio
En la consola **Bash** de PythonAnywhere:
```bash
git clone https://github.com/jgregoza/todo_django_mongodb.git /home/<usuario>/taskpilot
cd /home/<usuario>/taskpilot
git checkout v1.0.0
git describe --tags --exact-match
cd /home/<usuario>/taskpilot
```

### Paso 2: Crear el directorio de datos
```bash
mkdir -p /home/<usuario>/taskpilot-data/media
```

### Paso 3: Crear el entorno virtual e instalar dependencias
```bash
mkvirtualenv --python=/usr/bin/python3.10 taskpilot-env
pip install -r requirements.txt
pip check
```

### Paso 4: Configurar variables de entorno (`.env`)
```bash
cp .env.example .env
chmod 600 .env
nano .env
```
Contenido de producción requerido:
```ini
SECRET_KEY=genera-una-clave-larga-aleatoria-y-unica
DEBUG=False
ALLOWED_HOSTS=<usuario>.pythonanywhere.com
DATA_DIR=/home/<usuario>/taskpilot-data
STATIC_ROOT=/home/<usuario>/taskpilot/staticfiles
CSRF_TRUSTED_ORIGINS=https://<usuario>.pythonanywhere.com
```

### Paso 5: Aplicar migraciones y recolectar estáticos
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

*(Opcional) Crear superusuario para el panel `/admin/`:*
```bash
python manage.py createsuperuser
```

---

## 3. Configuración en la Pestaña "Web" de PythonAnywhere

1. **Configuración de código y virtualenv:**
   - **Source code**: `/home/<usuario>/taskpilot`
   - **Working directory**: `/home/<usuario>/taskpilot`
   - **Virtualenv**: `/home/<usuario>/.virtualenvs/taskpilot-env`

2. **Mapeo de archivos estáticos:**
   - **URL**: `/static/`
     **Directory**: `/home/<usuario>/taskpilot/staticfiles`
   - **IMPORTANTE DE SEGURIDAD**: **NO** configurar ningún mapeo para `/media/`. Las imágenes son privadas y se entregan exclusivamente a través de la vista protegida de Django tras comprobar la propiedad del recurso.

3. **Configuración de WSGI:**
   - Abrir el enlace del archivo WSGI (`/var/www/<usuario>_pythonanywhere_com_wsgi.py`).
   - Copiar el contenido de `pythonanywhere_wsgi.py` (asegurando la ruta `/home/<usuario>/taskpilot`).
   - Guardar los cambios.

4. **Recargar la Web App:**
   - Presionar el botón verde **"Reload <usuario>.pythonanywhere.com"**.

---

## 4. Verificación de Despliegue (Smoke Test)

Una vez recargada la aplicación, realizar las siguientes comprobaciones:
1. Acceso anónimo a `https://<usuario>.pythonanywhere.com/` debe redirigir a `/login/` (`302`).
2. Acceso directo a `https://<usuario>.pythonanywhere.com/media/` debe responder `404 Not Found`.
3. Iniciar sesión y crear una tarea con imagen de prueba.
4. Comprobar que la imagen carga en el visor y responde `200` para el propietario.
5. Acceso anónimo a `https://<usuario>.pythonanywhere.com/api/v1/todos/` debe responder `401 JSON`.

---

## 5. Procedimiento de Rollback de Emergencia

El rollback depende de si se trata del primer despliegue de TaskPilot o de una actualización posterior.

### 5.1 Primer despliegue de TaskPilot

Durante el primer despliegue no debe asumirse que existe un tag anterior de TaskPilot. Si la conmutación falla, seguir exclusivamente el procedimiento de rollback de `MASTER_PLAN.md`, secciones 6.5 y 6.6, para recuperar la configuración anterior de la Web App, WSGI, rutas estáticas y entorno virtual.

No improvisar cambios en producción ni restaurar la base de datos como parte automática de este rollback.

### 5.2 Actualizaciones posteriores

Antes de actualizar, registrar el tag que está actualmente desplegado y confirmar que existe un respaldo válido.

Si una actualización posterior falla:

1. Volver al último tag estable que estaba desplegado:
   ```bash
   cd /home/<usuario>/taskpilot
   git checkout <tag-anterior-estable>
   ```
2. Restaurar las dependencias de esa versión:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecutar las verificaciones y recargar la aplicación desde la pestaña **Web** de PythonAnywhere.

### 5.3 Recuperación de datos

El rollback de código no implica restaurar automáticamente SQLite ni los archivos multimedia.

Restaurar datos únicamente cuando exista pérdida o corrupción de información, o cuando una incompatibilidad de datos/migraciones lo justifique y la restauración haya sido autorizada.

La restauración debe realizarse siguiendo el procedimiento del `RUNBOOK.md`, sección 3.2. No retroceder migraciones automáticamente ni reemplazar la base de datos para resolver un simple fallo de código.