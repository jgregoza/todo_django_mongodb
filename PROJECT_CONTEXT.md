# TaskPilot — Contexto del Proyecto

## 1. Descripción

TaskPilot es una aplicación web personal de gestión de tareas con autenticación, prioridades, categorías, fechas límite, imágenes adjuntas, estadísticas y una API REST. Cada tarea pertenece a un único usuario y los datos de un usuario nunca son accesibles desde otra cuenta.

La versión de referencia es la desplegada en producción: **`v1.0.0`**, commit **`ff821b9`**.

- **Producción:** https://jzamora.pythonanywhere.com
- **Repositorio:** https://github.com/jgregoza/todo_django_mongodb
- **Estado:** proyecto cerrado en su versión desplegada.

---

## 2. Tecnologías

| Componente | Versión / uso |
|---|---|
| Python | 3.10 (runtime de producción) |
| Django | 5.2.19 LTS |
| Base de datos | SQLite (`db.sqlite3`) mediante Django ORM |
| Pillow | 12.3.0 — validación de imágenes |
| python-dotenv | 1.2.4 — carga de `.env` |
| asgiref | 3.12.1 |
| sqlparse | 0.6.1 |
| Frontend | Plantillas Django, Tailwind CSS y Lucide Icons por CDN |
| Hosting | PythonAnywhere, plan gratuito, servidor WSGI |
| Control de versiones | Git / GitHub |

Herramientas de desarrollo opcionales: `coverage==7.17.2` y `ruff==0.17.4` (`requirements-dev.txt`).

---

## 3. Arquitectura actual

Monolito Django con patrón MVT y separación ligera entre lecturas y escrituras:

- **`config/`**: configuración del proyecto (`settings.py`, `urls.py`, `wsgi.py`, `asgi.py`).
- **`todos/models.py`**: modelo `TodoTask`.
- **`todos/selectors.py`**: consultas y lecturas aisladas por usuario.
- **`todos/services.py`**: mutaciones y transacciones atómicas.
- **`todos/forms.py`** y **`todos/validators.py`**: validación de formularios, imágenes y payloads de API.
- **`todos/views.py`** y **`todos/urls.py`**: vistas web, autenticación, imágenes privadas y API REST.
- **`templates/`**: interfaz web y páginas de error personalizadas (400, 403, 404, 500).
- **`todos/tests.py`**: suite de pruebas automatizadas.

### Modelo de datos

`TodoTask` contiene:

- `user`: clave foránea obligatoria a `User` (`on_delete=CASCADE`).
- `title`, `description`, `priority` (`baja`, `media`, `alta`), `category`, `completed`, `due_date`.
- `image`: imagen opcional almacenada en `DATA_DIR/media/`.
- `created_at`, `updated_at`.

### Persistencia y multimedia

- SQLite con `OPTIONS: {"timeout": 20}` y sin WAL.
- La base y la multimedia viven en `DATA_DIR`, separadas del código.
- Las imágenes no se sirven por una URL pública. Se entregan mediante la vista autenticada `todo_image`, que comprueba que el solicitante sea el propietario o miembro del `staff` y responde `404` si no lo es.

### Seguridad

- Todas las vistas web exigen autenticación; las anónimas redirigen al login.
- La API responde `401 JSON` a clientes no autenticados, sin redirecciones HTML.
- CSRF obligatorio en formularios y en toda mutación de la API; no se usa `@csrf_exempt`.
- Logout exclusivamente por `POST` con CSRF.
- Aislamiento estricto por usuario: los recursos ajenos responden `404`.
- Imágenes validadas con Pillow (`Image.verify()`), límite de 5 MB y formatos `JPEG`, `PNG`, `WEBP` y `GIF`.
- En producción: `DEBUG=False`, `SECRET_KEY` obligatoria, `ALLOWED_HOSTS` sin comodines, HTTPS, cookies seguras, HSTS y cabeceras `nosniff` / `DENY`.

---

## 4. Funcionalidades existentes

- Registro, inicio y cierre de sesión.
- CRUD de tareas con aislamiento por usuario.
- Prioridades (alta, media, baja) y categorías.
- Fechas límite y métricas: total, pendientes, completadas y porcentaje.
- Filtros por estado, prioridad y categoría; búsqueda por texto.
- Paginación de la lista de tareas.
- Imágenes adjuntas con visor modal y entrega privada.
- Panel de administración de Django (`/admin/`).
- API REST JSON versionada en `/api/v1/todos/`, con rutas de compatibilidad en `/api/todos/`.

### Endpoints de la API

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/v1/todos/` | Listar tareas propias; acepta `page`, `per_page`, `status`, `priority`, `category` y `q`. |
| `POST` | `/api/v1/todos/` | Crear una tarea (JSON o multipart con `image`). |
| `GET` | `/api/v1/todos/<id>/` | Obtener una tarea propia. |
| `PUT` | `/api/v1/todos/<id>/` | Actualizar una tarea propia. |
| `DELETE` | `/api/v1/todos/<id>/` | Eliminar una tarea propia y su imagen. |
| `POST` | `/api/v1/todos/<id>/toggle/` | Alternar completada / pendiente. |
| `GET` | `/api/v1/todos/stats/` | Estadísticas personales. |

Todas las rutas exigen sesión autenticada y token CSRF (`X-CSRFToken`) en métodos mutativos.

---

## 5. Configuración de producción

| Parámetro | Valor |
|---|---|
| URL | `https://jzamora.pythonanywhere.com` |
| Versión desplegada | `v1.0.0` (`ff821b9`) |
| Python | 3.10 |
| Django | 5.2.19 LTS |
| Base de datos | SQLite en `DATA_DIR/db.sqlite3` |
| Zona horaria | `America/Managua` |
| Idioma | `es-es` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `jzamora.pythonanywhere.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://jzamora.pythonanywhere.com` |
| Multimedia | `DATA_DIR/media/`, sin mapeo público |

### Variables de entorno

El archivo `.env` reside únicamente en el servidor, está excluido de Git y debe tener permisos `600`. Nunca se documenta su contenido.

| Variable | Valor / función |
|---|---|
| `SECRET_KEY` | Clave secreta de Django; obligatoria con `DEBUG=False`. |
| `DEBUG` | `False` en producción. |
| `ALLOWED_HOSTS` | `jzamora.pythonanywhere.com`. |
| `DATA_DIR` | `/home/jzamora/taskpilot-data`. |
| `STATIC_ROOT` | `/home/jzamora/taskpilot/staticfiles`. |
| `CSRF_TRUSTED_ORIGINS` | `https://jzamora.pythonanywhere.com`. |

### Advertencias esperadas de `check --deploy`

`python manage.py check --deploy` solo debe mostrar:

- `security.W005`: `SECURE_HSTS_INCLUDE_SUBDOMAINS = False`.
- `security.W021`: `SECURE_HSTS_PRELOAD = False`.

Ambas son intencionales: el dominio es un subdominio compartido de PythonAnywhere y no debe imponer HSTS ni precarga a otros subdominios de la plataforma. Cualquier otra advertencia debe revisarse.

---

## 6. Rutas de despliegue

| Componente | Ruta |
|---|---|
| Código | `/home/jzamora/taskpilot` |
| Datos mutables | `/home/jzamora/taskpilot-data` |
| Base de datos | `/home/jzamora/taskpilot-data/db.sqlite3` |
| Multimedia | `/home/jzamora/taskpilot-data/media/` |
| Estáticos | `/home/jzamora/taskpilot/staticfiles` |
| Virtualenv | `/home/jzamora/.virtualenvs/taskpilot-env` |
| WSGI | `/var/www/jzamora_pythonanywhere_com_wsgi.py` |
| Logs | `/var/log/jzamora.pythonanywhere.com.*.log` |
| Backups | `/home/jzamora/backups/` |

En la pestaña **Web** de PythonAnywhere:

- **Source code:** `/home/jzamora/taskpilot`
- **Working directory:** `/home/jzamora/taskpilot`
- **Virtualenv:** `/home/jzamora/.virtualenvs/taskpilot-env`
- **Mapping estático:** `/static/` → `/home/jzamora/taskpilot/staticfiles`
- **Sin mapping para `/media/`**

---

## 7. Mantenimiento básico

### Recargar la aplicación

Desde la pestaña **Web** de PythonAnywhere, pulsar **Reload**. También puede forzarse el reinicio con:

```bash
touch /var/www/jzamora_pythonanywhere_com_wsgi.py
```

### Revisar logs

```bash
tail -n 100 -f /var/log/jzamora.pythonanywhere.com.error.log
```

### Verificar la configuración

```bash
cd /home/jzamora/taskpilot
python manage.py check
python manage.py check --deploy
python manage.py showmigrations
```

### Comprobar la integridad de SQLite

```bash
sqlite3 /home/jzamora/taskpilot-data/db.sqlite3 "PRAGMA integrity_check;"
```

Debe devolver `ok`.

### Crear un respaldo

```bash
set -e
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_DIR="/home/jzamora/backups/$TIMESTAMP"
DATA_DIR="/home/jzamora/taskpilot-data"

mkdir "$BACKUP_DIR"
sqlite3 "$DATA_DIR/db.sqlite3" ".backup '$BACKUP_DIR/db.sqlite3'"
tar -czf "$BACKUP_DIR/media.tar.gz" -C "$DATA_DIR" media
cd "$BACKUP_DIR"
sha256sum db.sqlite3 media.tar.gz > SHA256SUMS
```

Conservar juntos `db.sqlite3`, `media.tar.gz` y `SHA256SUMS`.

### Restaurar un respaldo

1. Verificar checksums e integridad:

   ```bash
   cd /home/jzamora/backups/<TIMESTAMP>
   sha256sum -c SHA256SUMS
   sqlite3 db.sqlite3 "PRAGMA integrity_check;"
   tar -tzf media.tar.gz > /dev/null
   ```

2. Crear un respaldo del estado actual antes de sustituir nada.
3. Detener la aplicación o trabajar sin escrituras concurrentes.
4. Reemplazar `db.sqlite3` y `media/` por los del respaldo, conservando copias temporales de los anteriores.
5. Recargar la aplicación y comprobar tareas, imágenes y logs.

No restaurar datos como parte automática de un rollback de código.

### Actualizar el código desplegado

```bash
cd /home/jzamora/taskpilot
git fetch --tags
git checkout <tag>
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check
touch /var/www/jzamora_pythonanywhere_com_wsgi.py
```

Si una actualización falla, volver al tag estable anterior y reinstalar sus dependencias.

### Verificación local antes de publicar

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
ruff check .
```

---

## 8. Estructura del repositorio

```text
taskpilot/
├── manage.py
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .env.example
├── .gitignore
├── PROJECT_CONTEXT.md
├── pythonanywhere_wsgi.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── todos/
│   ├── models.py
│   ├── selectors.py
│   ├── services.py
│   ├── forms.py
│   ├── validators.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── tests.py
│   └── migrations/
├── templates/
│   ├── todos/
│   ├── 400.html
│   ├── 403.html
│   ├── 404.html
│   └── 500.html
└── seed_data.py
```

`seed_data.py` es una utilidad opcional para desarrollo local; no se ejecuta en producción.
