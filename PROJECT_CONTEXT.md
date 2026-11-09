# TaskPilot — Contexto del Proyecto

Aplicación web personal de gestión de tareas con autenticación, prioridades, categorías, fechas límite, imágenes adjuntas, estadísticas y API REST. Cada tarea pertenece a un único usuario y los datos nunca cruzan entre cuentas.

- **Producción:** https://jzamora.pythonanywhere.com
- **Repositorio:** https://github.com/jgregoza/todo_django_mongodb (rama `main`)
- **Desplegado:** `e81d0b1` · Python 3.10 · Django 5.2 LTS

## Stack

Django 5.2 (MVT), SQLite vía ORM, Pillow (validación de imágenes), python-dotenv, plantillas Django con Tailwind/Lucide por CDN. Hosting: PythonAnywhere (WSGI). Desarrollo: `coverage` y `ruff` (`requirements-dev.txt`).

## Mapa del repositorio

- `config/`: `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`.
- `todos/`: `models.py`, `selectors.py` (lecturas), `services.py` (mutaciones), `views.py`, `forms.py`, `validators.py`, `urls.py`, `admin.py`, `tests.py`, `migrations/`.
- `templates/`: interfaz web y páginas de error 400/403/404/500.
- `pythonanywhere_wsgi.py` y `seed_data.py` (este último solo para desarrollo).

## Datos y seguridad

- `TodoTask`: `user` (FK obligatoria, CASCADE), `title`, `description`, `priority` (`baja|media|alta`), `category` (texto), `completed`, `due_date`, `image`, timestamps.
- `Category`: registro privado por usuario, con `UniqueConstraint(user, normalized_name)` y nombre normalizado no vacío. Nombres normalizados con `casefold()` y espacios colapsados, máximo 50 caracteres; vacío se convierte en `General`. Siempre se resuelve contra el usuario autenticado (`services.resolve_category`).
- Aislamiento estricto: los recursos ajenos responden 404. La API responde 401 JSON, sin redirecciones HTML.
- CSRF obligatorio en formularios y en las mutaciones de la API; logout solo por POST.
- Imágenes privadas mediante `todo_image` (propietario o staff). Validación con Pillow, límite de 5 MB y formatos JPEG/PNG/WEBP/GIF.
- Producción: `DEBUG=False`, `SECRET_KEY` obligatoria, `ALLOWED_HOSTS` sin comodines, HTTPS, HSTS y cookies seguras.
- API: `/api/v1/todos/`, `/api/v1/todos/<id>/`, `/api/v1/todos/<id>/toggle/`, `/api/v1/todos/stats/` (compatibilidad en `/api/todos/`).

## Comandos

Desarrollo:

```bash
python manage.py migrate
python manage.py runserver
```

Verificación obligatoria antes de commit:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
ruff check .
git diff --check
```

## CI

`.github/workflows/ci.yml` ejecuta en cada push o PR a `main`: `check`, `makemigrations --check`, `test` y `ruff`. No usa secretos: `DEBUG=True` (para evitar redirecciones HTTPS en tests), `SECRET_KEY` dummy y `DATA_DIR` temporal.

## Despliegue automático (plan gratuito, sin SSH)

El plan gratuito de PythonAnywhere no incluye SSH, por lo que el despliegue
se orquesta con un **marcador** y una **tarea programada diaria** (09:00 UTC):

1. `CI` (existente) termina en verde sobre `main`.
2. `.github/workflows/deploy.yml` escribe el SHA aprobado en
   `~/taskpilot-data/last_ci_ok_sha` mediante la Files API (POST multipart).
3. La tarea programada
   `/home/jzamora/.virtualenvs/taskpilot-env/bin/python /home/jzamora/taskpilot/deploy_task.py`
   ejecuta el despliegue:
   - lee el marcador y verifica que el SHA siga en la historia de `main`;
   - aborta si `HEAD` ya está en ese SHA (salvo `--force`);
   - `git fetch` + `git merge --ff-only <sha>` (nunca retrocede ni diverge);
   - `pip install -r requirements.txt` solo si cambió `requirements.txt`;
   - respaldo SQLite con rotación (3 copias) + `PRAGMA integrity_check`;
   - `migrate --noinput` y `collectstatic --noinput`;
   - recarga la web app por la API con `$API_TOKEN`;
   - escribe `last_deployed_sha` y un log.

Credenciales: secret `PA_API_TOKEN` y variable `PA_USERNAME` en GitHub. En el
servidor no se almacena ningún secreto (`$API_TOKEN` está pre-poblado en
consolas y tareas).

Límites del plan gratuito relevantes: una tarea diaria (hasta 24 h de retraso),
100 CPU-s/día, 512 MiB de disco (la rotación de backups es obligatoria) y la
web app caduca mensualmente y debe renovarse.

Despliegue manual inmediato: `python ~/taskpilot/deploy_task.py` en la consola
Bash (o con `--force` para re-ejecutar). Rollback: `git revert` en `main`
(pasa por CI y por el flujo normal); evita `git checkout`, que deja el clon en
*detached HEAD* y bloquea el `merge --ff-only` de la tarea.

Opciones del script: `--check`, `--dry-run`, `--sha <sha>`, `--force`.

## Despliegue en PythonAnywhere

| Componente | Ruta |
|---|---|
| Código | `/home/jzamora/taskpilot` |
| Datos, BD y media | `/home/jzamora/taskpilot-data/` |
| Estáticos | `/home/jzamora/taskpilot/staticfiles` |
| Virtualenv | `/home/jzamora/.virtualenvs/taskpilot-env` |
| WSGI | `/var/www/jzamora_pythonanywhere_com_wsgi.py` |
| Logs | `/var/log/jzamora.pythonanywhere.com.*.log` |
| Backups | `/home/jzamora/backups/` |

Runbook:

1. Crear y verificar el respaldo de la BD (ver sección Respaldos).
2. `cd /home/jzamora/taskpilot && git pull --ff-only`
3. `source /home/jzamora/.virtualenvs/taskpilot-env/bin/activate`
4. `pip install -r requirements.txt` solo si cambiaron las dependencias.
5. `python manage.py migrate`
6. `python manage.py collectstatic --noinput`
7. Web → **Reload** (o `touch /var/www/jzamora_pythonanywhere_com_wsgi.py`).
8. Smoke: `/`, `/login/`, 404, filtros y consola sin errores.

- El clon de producción es **shallow** y quedó en `main` con tracking a `origin/main`. Si `pull` se queja de la profundidad: `git fetch --unshallow`.
- `check --deploy` solo debe mostrar `security.W005` y `security.W021` (intencionales por el subdominio compartido de PythonAnywhere).
- Rollback: `git checkout <commit-anterior>` y Reload. No restaurar la BD como parte de un rollback de código.

## Respaldos

```bash
BK=/home/jzamora/backups/db_$(date -u +%Y%m%dT%H%M%SZ).sqlite3
sqlite3 /home/jzamora/taskpilot-data/db.sqlite3 ".backup '$BK'"
sqlite3 "$BK" "PRAGMA integrity_check;"
sqlite3 "$BK" "SELECT (SELECT COUNT(*) FROM auth_user), (SELECT COUNT(*) FROM todos_todotask);"
```

Restaurar: verificar checksum e integridad, respaldar el estado actual, detener escrituras, reemplazar `db.sqlite3` y `media/`, recargar y comprobar.

## Cómo pedir cambios

Sesión nueva por solicitud, con este brief:

```text
Objetivo: <1-2 frases>
Criterios de aceptación: <bullets>
Zonas probables: <archivos>
Restricciones: sin dependencias / sin docs / sin tocar modelos...
Verificación: check, makemigrations --check, test, ruff, git diff --check
```

Reglas con varias herramientas (Antigravity u otros agentes): un solo dueño del repositorio a la vez, commit antes de cambiar de herramienta, nada de agentes en paralelo sobre la misma rama y despliegue ejecutado manualmente en la consola de PythonAnywhere.

## Convenciones

- Sin dependencias ni frameworks nuevos.
- Sin `@csrf_exempt` ni relajar autenticación o CSRF.
- Migraciones reversibles y nunca destructivas.
- Tests junto al cambio; ruff con línea de 100 (`E501` ignorado).
- `seed_data.py` es solo para desarrollo.
