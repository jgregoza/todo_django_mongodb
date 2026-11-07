# MASTER_PLAN.md — Plan maestro de modernización de TaskPilot

**Proyecto:** TaskPilot (nombre objetivo; el repositorio actual es `todo_django_mongodb`)
**Estado:** Actualizado con las decisiones D1–D9 y la validación técnica del 2026-11-06. **No autoriza implementación.**
**Fecha:** 2026-11-06
**Alcance:** diagnóstico, arquitectura, seguridad, identidad, Git, publicación, despliegue, limpieza y fases.

> Este documento consolida el análisis previo, la validación técnica y las decisiones aprobadas. Su existencia no implica autorización para ejecutar cambios. La implementación requiere aprobación explícita por fase y por entorno. Cada gate es independiente.

**Historial:**

| Versión | Fecha | Cambio |
|---|---|---|
| v1 | 2026-11-06 | Borrador inicial (commit `ce351ee`) |
| v2 | 2026-11-06 | Decisiones D1–D9, validación técnica, plan de publicación y limpieza por gates |

---

## 1. Resumen ejecutivo

TaskPilot es una aplicación Django de gestión personal de tareas con prioridades, categorías, fechas límite, imágenes, estadísticas, autenticación, panel de administración y API JSON. La aplicación funciona, pero su nombre y configuración actuales sugieren una integración MongoDB que no existe: la persistencia real es SQLite mediante Django ORM.

La modernización busca:

- Corregir acceso anónimo, autorización, CSRF y multimedia pública antes del renombrado y del despliegue.
- Consolidar la identidad **TaskPilot** y eliminar referencias y dependencias de MongoDB.
- Validar entradas, archivos y errores; mejorar transacciones, logging y pruebas.
- Documentar arquitectura, seguridad, entorno, despliegue, operación y recuperación.
- Desplegar TaskPilot desde cero en PythonAnywhere y retirar los dos proyectos anteriores mediante cuarentena y purga autorizada.

**Arquitectura confirmada:** Django 5.2.19 LTS + SQLite + PythonAnywhere (plan gratuito) + Git. Sin MongoDB. Sin servicios de pago.

**Decisión de datos:** base nueva y vacía. No se migran datos, usuarios ni multimedia de las aplicaciones anteriores. El backup existente se conserva hasta G7.

**Decisión de limpieza:** Track A. Primero se aprovisiona y conmuta TaskPilot; solo después se pone en cuarentena el código antiguo durante 7 días y, tras la ventana, se purga con autorización independiente.

**Advertencia:** PythonAnywhere no recomienda SQLite como base de producción por depender del sistema de archivos. Se acepta con bajo tráfico, un worker, `timeout`, operaciones cortas, backups y verificación de integridad.

---

## 2. Diagnóstico actual

### 2.1 Arquitectura y funcionalidades

- Monolito Django con arquitectura MVT y una capa de servicios (`todos/services.py`).
- Plantillas renderizadas en servidor; formularios HTML y una API JSON paralela.
- Frontend con Tailwind CSS y Lucide por CDN; Google Fonts.
- Autenticación nativa de Django con sesiones.
- Admin de Django con filtros, badges e imágenes.
- Funcionalidades: CRUD de tareas, prioridades, categorías, fechas límite, imágenes, filtros, búsqueda, estadísticas, registro, login, logout, API y admin.
- Persistencia real: SQLite (`db.sqlite3`) a través del Django ORM.
- MongoDB: configuración y módulo `todos/db.py` presentes, pero nunca inicializados ni utilizados. `todos/db.py` no lo importa ningún otro módulo. Dependencias `pymongo`, `mongoengine` y `dnspython` sin uso real.

**Hallazgo de despliegue:** el dominio `jzamora.pythonanywhere.com` sirve actualmente el proyecto `sample-web-personal-django2` porque el WSGI vivo importa `webpersonal.settings`. El *source* configurado en la Web App apunta a `todo_django_mongodb`, por lo que source y WSGI están desalineados.

### 2.2 Línea base local verificada

| Área | Estado |
|---|---|
| Python local | 3.12.10 |
| Django instalado | 6.1.2 (no ejecutable en PythonAnywhere) |
| Pillow / python-dotenv | 13.0.0 / 1.2.4 |
| Base local | 20 migraciones, 4 tareas, 0 usuarios |
| Multimedia local | No existe `media/`; se crea al subir imágenes |
| Estáticos | `static/` vacío y no versionado; `staticfiles/` generado e ignorado |
| Pruebas | 7 pruebas básicas, sin autorización, CSRF ni uploads |
| CI/CD | No existe |
| Documentación | README, guía antigua de PythonAnywhere y este plan |

**Advertencia sobre la base local y la migración `0003`:** la base local contiene 4 tareas huérfanas y 0 usuarios. No debe utilizarse directamente para validar `0003`, porque la migración hará obligatorio `user` y fallaría con esas filas. La migración se validará desde una **base SQLite temporal y limpia**, aplicando `0001`, `0002` y `0003` en orden.

- La base de producción será nueva y vacía; no se migrarán datos.
- No se asignarán propietarios artificiales a las tareas locales.
- No se eliminará ni sustituirá la base local existente ni sus datos.
- Cualquier sustitución o eliminación de la base local requiere una instrucción independiente.

### 2.3 Git

- Rama local y remota única: `main`.
- `origin`: `https://github.com/jgregoza/todo_django_mongodb.git`.
- Remoto `main` = `01eb960` (código legado, 28 archivos, sin `MASTER_PLAN.md`).
- Local `main` = `ce351ee` = `01eb960` + `MASTER_PLAN.md`; un commit por delante del remoto.
- Sin tags, releases, ramas adicionales, submódulos ni LFS.
- Repositorio público; 0 colaboradores; sin Actions, secrets, webhooks ni branch protection.
- `main` local sin upstream configurado.
- Árbol limpio; 28 archivos versionados en `01eb960`.
- `.env` existe, está ignorado y no está versionado.
- `db.sqlite3`, `.venv/`, `staticfiles/`, `media/` y `__pycache__/` están ignorados.
- No se detectaron tokens, claves privadas, bases ni multimedia en el historial con los patrones revisados.
- Existe una `SECRET_KEY` de respaldo hardcodeada en `config/settings.py`; debe rotarse y eliminarse el fallback.
- El nombre y correo del autor son visibles en los commits; no se reescribe historia por ello.

### 2.4 Hallazgos críticos

| Severidad | Hallazgo |
|---|---|
| Crítica | Usuarios anónimos pueden ver todas las tareas |
| Crítica | Usuarios anónimos pueden editar, alternar o eliminar cualquier tarea por ID |
| Crítica | API pública, sin autenticación obligatoria y con `csrf_exempt` |
| Crítica | Multimedia potencialmente pública si se mantiene el mapping `/media/` |
| Crítica | Django 6.1.2 no puede ejecutarse en Python 3.10 |
| Alta | Tareas sin propietario compartidas entre usuarios |
| Alta | `SECRET_KEY` con fallback hardcodeado |
| Alta | `DEBUG=True` y `ALLOWED_HOSTS=*` por defecto |
| Alta | Logout por `GET` |
| Alta | Sin validación ni límites de imágenes |
| Media | Booleanos mal convertidos (`bool("false")` es `True`) |
| Media | Imágenes anteriores huérfanas al reemplazarlas |
| Media | Sin manejo de errores ni logging estructurado |
| Media | Sin paginación |
| Media | SQLite sin timeout ni configuración de bloqueo |
| Media | `STATICFILES_DIRS` apunta a `static/`, que no se versiona |
| Baja | Registro abierto sin límite de intentos |

### 2.5 Entorno de PythonAnywhere verificado

| Capacidad / restricción | Estado real |
|---|---|
| Plan | Gratuito: 1 Web App, 1 worker, 2 consolas, 512 MB, 100 CPU-s/día |
| Python disponible | 3.6, 3.7, 3.8, 3.9 y 3.10; **máximo 3.10** |
| Python del venv actual | 3.10.5; pip 22.0.4 |
| SQLite | 3.31.1 (mínimo de Django 5.2: 3.31.0) |
| Dominio | `jzamora.pythonanywhere.com` (se conserva) |
| HTTPS / Force HTTPS | Desactivado |
| WSGI | `/var/www/jzamora_pythonanywhere_com_wsgi.py` (515 B) |
| SSH/SFTP | No disponibles en Free |
| Git por HTTPS | Permitido; repositorio público |
| Herramientas | `sqlite3`, `tar`, `gzip`, `sha256sum`, `git`, `du`, `df`, `find`, `stat`, `gpg`, `openssl`, `mkvirtualenv` |
| Almacenamiento | 309 MB usados de 512 MB; 966 GB libres en el montaje (manda la cuota del plan) |
| Proyecto TODO | 8.7 MB: `.git` 504 KB, `media` 6.1 MB, `staticfiles` 1.8 MB, `db.sqlite3` 139,264 B |
| Proyecto blog | 30 MB (solo se inspeccionó el nivel superior) |
| Venv `todo-env` | 99 MB, Python 3.10.5 |
| Venv `webpersonal` | 92 MB, Python 3.9.13 |
| Mappings actuales | `/static/` → `todo_django_mongodb/staticfiles`; `/media/` → `todo_django_mongodb/media`; `/static/` → `sample-web-personal-django2/webpersonal/static` |
| Source / working dir / venv | `todo_django_mongodb` / `/home/jzamora/` / `todo-env` |
| `/var/www/__pycache__` | `cpython-39` y `cpython-310` del WSGI |
| Logs | Sin tracebacks; solo 404 de estáticos y `/favicon.ico` |

### 2.6 Base de producción verificada

| Dato | Valor |
|---|---|
| Integridad | `ok` |
| `journal_mode` | `delete` |
| Migraciones aplicadas | 20 |
| Usuarios | 1 |
| Tareas | 8 (todas huérfanas: `user IS NULL`) |
| Medios | 3 archivos |
| Estáticos generados | 127 archivos |
| Permisos de `db.sqlite3` | `644` |
| Permisos de `.env` | `664` (debería ser `600`) |
| Claves de `.env` | 5 (solo se registraron nombres) |

**No asumir que la base local representa producción.**

### 2.7 Backup ejecutado y verificado

| Dato | Valor |
|---|---|
| Ruta | `/home/jzamora/backups/20261107T013845Z` |
| Fecha UTC | 2026-11-07T01:38:45Z |
| Tamaño | 6.6 MB |
| Archivos | 23 (base, código, media, estáticos, WSGI, metadatos) |
| Checksums | 22/22 `OK` |
| Restauración | `integrity_check=ok`; `auth_user=1`, `todos_todotask=8`, `django_migrations=20`; media 3 archivos; staticfiles 127 |
| `.env` | Solo nombres, tamaño y permisos; **sin contenido** |
| Retención | Hasta G7 |

---

## 3. Decisiones

### 3.1 Decisiones acordadas

- Backend Django.
- Base de datos SQLite.
- Hosting PythonAnywhere, plan gratuito.
- Control de versiones Git.
- OpenCode como asistente de desarrollo.
- **No implementar MongoDB.**
- Evitar servicios, dependencias y herramientas de pago innecesarias.
- Priorizar seguridad, calidad, documentación y despliegue reproducible.
- No implementar nada hasta aprobar este plan maestro y cada fase.

### 3.2 Identidad y layout objetivo

- Producto: **TaskPilot**.
- Repositorio objetivo: **`taskpilot-django`** (renombrado después del despliegue).
- Directorio de código: `/home/jzamora/taskpilot`.
- Directorio de datos: `/home/jzamora/taskpilot-data` (`db.sqlite3` y `media/`).
- Estáticos: `/home/jzamora/taskpilot/staticfiles` (dentro del proyecto, ignorado por Git).
- Virtualenv: `/home/jzamora/.virtualenvs/taskpilot-env`.
- Base de datos: nueva, vacía, creada con `migrate`.
- Dominio y Web App existentes: se conservan.
- Paquete `config`, app `todos`, modelo `TodoTask` y tablas `todos_todotask`: no se renombran.

### 3.3 Decisiones aprobadas D1–D9

| ID | Decisión | Estado |
|---|---|---|
| **D1** | Django **5.2.19** + Python 3.10. Se acepta y documenta temporalmente el riesgo de Python 3.10 EOL. | Aprobada |
| **D2** | Layout `/home/jzamora/taskpilot` + `/home/jzamora/taskpilot-data`; `staticfiles` dentro del proyecto. | Aprobada |
| **D3** | Conservar migraciones `0001` y `0002`; crear `0003` para hacer obligatorio `user`. | Aprobada |
| **D4** | Cuarentena de **7 días**. | Aprobada |
| **D5** | Conservar el backup `20261107T013845Z` hasta G7; no crear otro. | Aprobada |
| **D6** | Eliminar `/var/www/__pycache__` en G6-L, solo tras verificar su contenido. | Aprobada |
| **D7** | Base de datos nueva y vacía. | Aprobada |
| **D8** | Renombrar el repositorio GitHub **después** del despliegue. | Aprobada |
| **D9** | G6-P, G6, G6-L y G7 mantienen autorización independiente. | Aprobada |

### 3.4 Decisiones todavía abiertas

1. Fecha y ventana concreta para G6.
2. Si el backup se elimina en G7 o se conserva más tiempo.
3. Nombre final y momento exacto del renombrado GitHub (posterior a G6).
4. Vendorizar Tailwind/Lucide/Fonts en una fase posterior (no bloquea v1).
5. Activar “Force HTTPS” en el panel: se hará en la misma ventana que G6.

### 3.5 Datos aún no verificados

- Contenido interno de `sample-web-personal-django2` (solo se inspeccionó el nivel superior; se eliminará completo).
- Contenido exacto de `/var/www/__pycache__` antes de retirarlo (se verificará en G6-L).

---

## 4. Estrategia de identidad, GitHub y secretos

### 4.1 Alcance del renombrado

**Renombrar:** producto, repositorio, carpeta raíz, documentación, marca visible, rutas de despliegue y virtualenv.

**No renombrar:** paquete `config`, app `todos`, modelo `TodoTask`, tablas `todos_todotask` ni historial de migraciones. Renombrar la app o el modelo obliga a tocar migraciones, `contenttypes`, permisos e imports, con riesgo alto y beneficio cosmético.

### 4.2 Lugares afectados

- Carpeta local y workspace.
- Remoto `origin` y `.git/config`.
- Repositorio GitHub (después del despliegue).
- `README.md` y `PYTHONANYWHERE_DEPLOY.md` (rutas, stack y comandos).
- `pythonanywhere_wsgi.py` (ruta absoluta).
- Pestaña Web: source, working dir, venv, WSGI y mappings.
- Virtualenv `todo-env` → `taskpilot-env`.
- Plantillas: “TODO Pro”, “TODO List Pro”.
- `todos/models.py` (docstring).
- `config/settings.py` y `.env.example`: bloques `MONGO_*`.
- `requirements.txt`: dependencias Mongo.
- `todos/db.py`.

### 4.3 Publicación del código correcto

**Regla:** GitHub solo contiene hoy el código legado (`01eb960`). Nunca se desplegará ese commit como TaskPilot. La publicación se hace después de F1–F5 y de la auditoría independiente, con fast-forward y tag anotado.

1. Implementar F1–F5 en `main` mediante commits pequeños.
2. Ejecutar la auditoría independiente (§8.4) y resolver los hallazgos.
3. Verificar antes del push:
   - `git log --all -- .env` vacío.
   - `git grep` de `SECRET_KEY`, `MONGO_URI` y `password` sin valores reales.
   - `git status` limpio y pruebas en verde.
4. `git push origin main`: fast-forward de `01eb960` al nuevo tip; incluye `ce351ee`. **Sin `--force` y sin reescribir historia.**
5. Crear tag anotado en el commit desplegable:
   - `git tag -a v1.0.0 -m "TaskPilot 1.0.0"`
   - `git push origin v1.0.0`
6. Desplegar en PythonAnywhere haciendo checkout de `v1.0.0` (requiere G6-P y G6; G5-P no autoriza el despliegue).
7. Renombrar el repositorio a `taskpilot-django` **después** de G6, con autorización específica (G2-GH). GitHub redirige la URL antigua; actualizar `origin` y la documentación.

**Prohibido:** desplegar `01eb960`, hacer force push, recrear el repositorio o perder el historial.

### 4.4 Git

- Conservar historial; no hacer `force push` ni reescribir pasado.
- Commits convencionales y pequeños.
- Ramas cortas por fase: `chore/`, `feat/`, `fix/`, `docs/`, `security/`.
- El tag de despliegue `v1.0.0` se crea y publica bajo G5-P.
- Los tags/bundles locales de F0 siguen requiriendo G0-T/G0-U; no se ejecutaron.
- Revisar `.gitignore`: `.env`, `.env.*` con excepción `.env.example`, `.venv/`, `db.sqlite3`, `media/`, `staticfiles/`, `__pycache__/`, logs, `backups/`, `.coverage`, `htmlcov/`, `.ruff_cache/`.
- No ignorar migraciones ni documentación.
- `static/` no se versiona, salvo un `.gitkeep` si se conserva `STATICFILES_DIRS`; las plantillas usan CDN.

### 4.5 Secretos

- Rotar la `SECRET_KEY` actual por estar el fallback en el historial.
- Sin fallback en producción: si falta, fallar de forma explícita.
- `.env` nuevo en `/home/jzamora/taskpilot/.env`, permisos `600`, fuera de Git.
- Sin claves `MONGO_URI` ni `MONGO_DB_NAME`.
- No incluir credenciales en Markdown, commits, logs ni chat.
- GitHub: 2FA, token de mínimo privilegio y rotación.
- PythonAnywhere: 2FA, contraseña robusta, consolas no compartidas.

---

## 5. Seguridad

### 5.1 Política objetivo

- Denegar por defecto; solo login y registro son públicos.
- Cada tarea pertenece a un usuario.
- Toda vista web y todo endpoint API exige autenticación, con respuestas diferentes:
  - Las **vistas web** pueden redirigir al login.
  - Los **endpoints API** deben devolver `401` con JSON, sin redirección HTML.
  - No se usará `login_required` en endpoints API si provoca redirecciones HTML.
- Objetos ajenos responden 404 (o el código definido en la matriz).
- CSRF obligatorio en toda escritura, incluida la API; sin `csrf_exempt`.
- Logout solo por POST.
- Multimedia privada servida por Django tras comprobar propietario.
- Validación de entradas y archivos en servidor.
- Errores seguros sin trazas internas.
- Secretos fuera del código.
- `DEBUG=False`, hosts exactos y cookies seguras en producción.

### 5.2 Matriz de autorización

| Recurso | Anónimo | Usuario A | Usuario B | Staff |
|---|---|---|---|---|
| `/` | Login | Sus tareas | Sus tareas | Sus tareas |
| Crear | Login | Propia | Propia | Propia |
| Tarea de A | 302 login / 404 | Permitido | 404 | Admin |
| API | 401 JSON | Solo suyas | Solo suyas | Solo suyas |
| Imagen de A | 302 login / 404 | Permitido | 404 | Admin |
| `/admin/` | Login | Denegado | Denegado | Permitido |
| Logout | No aplica | POST + CSRF | POST + CSRF | POST + CSRF |

Las rutas web pueden redirigir al login; las rutas API responden `401 JSON`. La matriz no autoriza redirecciones HTML en API.

### 5.3 Cambios de seguridad y configuración

**`config/settings.py`:**

- `DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR)))`.
- `DATABASES["default"]["NAME"] = DATA_DIR / "db.sqlite3"`.
- `OPTIONS = {"timeout": 20}`; sin WAL (almacenamiento de red).
- `MEDIA_ROOT = DATA_DIR / "media"`.
- `STATIC_ROOT = Path(os.getenv("STATIC_ROOT", str(BASE_DIR / "staticfiles")))`.
- Eliminar `STATICFILES_DIRS` (o añadir `static/.gitkeep`).
- Eliminar `MONGO_URI` y `MONGO_DB_NAME`.
- `SECRET_KEY` solo desde entorno; fallar si falta con `DEBUG=False`.
- `DEBUG=False` por defecto.
- `ALLOWED_HOSTS` desde entorno; sin `"*"` en producción.
- Bloque `if not DEBUG:` con `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS="DENY"`, `SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https")` y `CSRF_TRUSTED_ORIGINS=["https://jzamora.pythonanywhere.com"]`.

**Multimedia privada:**

- `todos/models.py`: `to_dict()` no usa `self.image.url`; devuelve la URL de la vista privada o se elimina del serializer.
- `todos/views.py`: vista `todo_image` con `@login_required`, `get_object_or_404` y autorización por propietario o staff; `FileResponse` sin exponer la ruta.
- `config/urls.py`: eliminar el `static(settings.MEDIA_URL, ...)`; añadir la ruta privada.
- `todos/admin.py`: `image_preview` apunta a la vista privada.
- `templates/todos/index.html`: usar `{% url 'todo_image' todo.id %}`.

**Autorización y API:**

- `@login_required` solo en vistas web, donde la redirección al login es aceptable.
- Endpoints API con un decorador propio que devuelva `401` y JSON; **no** usar `login_required` en API.
- Operaciones de escritura de la API con CSRF; prohibido `csrf_exempt`.
- Objetos ajenos: `404` (o el código ya definido en la matriz).
- Logout `@require_POST` con CSRF.
- `todos/services.py`: eliminar `Q(user__isnull=True)`; filtrar estrictamente por `request.user`.
- `todos/models.py`: `user` pasa a `null=False`; crear `0003` (D3).
- `0003` se valida sobre una base SQLite temporal y limpia (`0001` → `0002` → `0003`), nunca sobre la base local con tareas huérfanas. No se asignan propietarios artificiales ni se borra la base local.

**Limpieza:**

- Borrar `todos/db.py`.
- `requirements.txt` con pines exactos (sección 6.10).
- Actualizar `README.md` y `PYTHONANYWHERE_DEPLOY.md`.
- `seed_data.py` solo para desarrollo; no ejecutar en producción.

### 5.4 Política de tareas huérfanas

La base de producción de TaskPilot será nueva y vacía (D7). Por tanto, **no hay tareas huérfanas que migrar en producción**.

- Las tareas huérfanas actuales pertenecen a la aplicación anterior y no se conservan.
- La política de asignación queda limitada a desarrollo y datos de ejemplo.
- `seed_data.py` deberá exigir propietario.
- Si en el futuro se importaran datos, se aplicará el procedimiento de propietario aprobado y trazable antes de migrar.
- No asignar automáticamente a admin, staff, al primer usuario ni a una tarea genérica.

**Base local:** contiene tareas huérfanas y no sirve para validar `0003`. La validación se hará en una base temporal limpia. No se asignarán propietarios artificiales, no se borrará la base local y no se sustituirá sin una instrucción independiente.

---

## 6. PythonAnywhere

### 6.1 Restricciones y capacidades verificadas

Los datos siguientes se verificaron en la cuenta real y sustituyen a las referencias públicas.

| Capacidad / restricción | Estado real |
|---|---|
| Plan y cuotas | Free: 1 Web App, 1 worker, 2 consolas, 512 MB, 100 CPU-s/día |
| SSH/SFTP | No disponibles |
| Tareas programadas | No disponibles en Free |
| Dominio | `jzamora.pythonanywhere.com` |
| Python | 3.6–3.10; máximo 3.10 |
| SQLite | 3.31.1 |
| WSGI | `/var/www/jzamora_pythonanywhere_com_wsgi.py` |
| Git por HTTPS | Permitido |
| Herramientas | `sqlite3`, `tar`, `gzip`, `sha256sum`, `git`, `du`, `df`, `find`, `stat`, `gpg`, `openssl`, `mkvirtualenv` |
| Almacenamiento | 309 MB usados de 512 MB |
| HTTPS | Desactivado; se activará en G6 |
| Consolas | 2; dejar una libre para la ventana |

### 6.2 Free vs. pago

Con la información verificada, las funciones actuales no requieren plan de pago. Dominio propio, SSH/SFTP, más workers, tareas programadas o MySQL requerirían pago. El proyecto se mantiene en el plan gratuito.

### 6.3 Estructura de despliegue

```text
/home/jzamora/taskpilot/            # código, .git, .env, staticfiles/
├── manage.py
├── config/
├── todos/
├── templates/
├── staticfiles/                    # collectstatic (ignorado)
└── .env                            # 600, ignorado

/home/jzamora/taskpilot-data/       # datos persistentes
├── db.sqlite3
└── media/                          # privado, sin mapping
```

- Variables: `DATA_DIR=/home/jzamora/taskpilot-data`, `STATIC_ROOT=/home/jzamora/taskpilot/staticfiles`.
- `MEDIA_ROOT=$DATA_DIR/media`; sin mapping `/media/`.
- WSGI apunta a `/home/jzamora/taskpilot`.
- El código se despliega por tag (`v1.0.0`), no por `main` móvil.
- No se usa estructura `releases/` + `current` en esta versión.

### 6.4 Backup (completado, G0-B)

El backup ya fue creado y verificado; **no se crea otro** (D5).

| Dato | Valor |
|---|---|
| Ruta | `/home/jzamora/backups/20261107T013845Z` |
| Tamaño | 6.6 MB |
| Checksums | 22/22 `OK` |
| Restauración | Base `ok` (1 usuario, 8 tareas, 20 migraciones), media 3, estáticos 127 |
| `.env` | Solo nombres y metadatos; sin contenido |
| Retención | Hasta G7 |

Correcciones aplicadas respecto al borrador anterior:

- La tabla real es `todos_todotask`.
- `journal_mode=delete`.
- `~/backups` no existía y se creó con permisos `700`.
- El bug de `sha256sum "$BK"/* > "$BK/SHA256SUMS"` (autoinclusión) se corrigió generando la lista sin el propio archivo.

El backup se usa solo si se necesita rollback. No se dedica más trabajo a copias externas.

### 6.5 Rollback

El rollback es de **configuración**, no de datos:

1. Restaurar el WSGI anterior copiado al backup durante el primer paso de G6.
2. Restaurar en el panel: source `todo_django_mongodb`, working dir `/home/jzamora/`, venv `todo-env`, mappings antiguos.
3. Revertir la cuarentena (`mv` de vuelta) si ya se ejecutó G6-L.
4. Recargar y verificar.

No se reconcilian datos: la base de TaskPilot es nueva y la aplicación anterior no la lee. Los datos que TaskPilot hubiera recibido permanecen en `/home/jzamora/taskpilot-data` y no se pierden.

### 6.6 Despliegue limpio

**Precondiciones:** F1–F5 completadas, auditoría independiente emitida, `main` publicado y tag `v1.0.0` disponible (G5-P).

1. **G6-P:** clonar el repositorio en `/home/jzamora/taskpilot` y hacer checkout de `v1.0.0`.
2. Crear `/home/jzamora/taskpilot-data` y `/home/jzamora/taskpilot-data/media`.
3. Crear el venv `taskpilot-env` con Python 3.10; instalar `requirements.txt`; `pip check`.
4. Generar `.env` nuevo con `umask 077`: `SECRET_KEY` aleatoria, `DEBUG=False`, `ALLOWED_HOSTS`, `DATA_DIR`, `STATIC_ROOT`; `chmod 600`.
5. `python manage.py migrate` (base nueva; incluye `0003`).
6. `python manage.py collectstatic --noinput`.
7. `python manage.py check` y `check --deploy`.
8. `sqlite3 /home/jzamora/taskpilot-data/db.sqlite3 'PRAGMA integrity_check;'` = `ok`.
9. **G6, primer paso de la sustitución del WSGI:**
   - Copiar el WSGI actualmente activo al directorio de backup existente (`20261107T013845Z`). No se crea otro backup ni se alteran los artefactos ya verificados.
   - Verificar que la copia se realizó correctamente (existencia, tamaño y checksum) antes de tocar el archivo activo.
   - Solo entonces reemplazar el WSGI activo por el de TaskPilot.
10. En el panel: source `/home/jzamora/taskpilot`, working dir `/home/jzamora/taskpilot`, venv `taskpilot-env`, Python 3.10; eliminar los tres mappings antiguos; añadir `/static/` → `/home/jzamora/taskpilot/staticfiles`; **no** añadir `/media/`.
11. Activar “Force HTTPS” y recargar.
12. Ejecutar la matriz de verificación (6.7).
13. No borrar nada todavía; la cuarentena es G6-L.

### 6.7 Verificación

**Antes de G6:**

- `manage.py check` y `check --deploy` sin errores críticos.
- `migrate` sin pendientes; integridad `ok`.
- `collectstatic` completo; `pip check` limpio.
- Backup G0-B íntegro y verificado. La copia del WSGI vigente **no** es una precondición previa: se realiza dentro de G6, antes del reemplazo.
- `du -sh` coherente con la cuota.

**Durante G6, antes del reemplazo:**

- Copia del WSGI vigente realizada en el backup existente.
- Existencia, tamaño y checksum de la copia verificados.
- Solo entonces se reemplaza el archivo activo.

**Después de G6:**

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://jzamora.pythonanywhere.com/
curl -sS -o /dev/null -w "%{http_code}\n" https://jzamora.pythonanywhere.com/.env
curl -sS -o /dev/null -w "%{http_code}\n" https://jzamora.pythonanywhere.com/db.sqlite3
curl -sS -o /dev/null -w "%{http_code}\n" https://jzamora.pythonanywhere.com/media/
```

- `/` → 200 o 302 a login.
- `.env`, `db.sqlite3` y `/media/` → 404.
- Estático de TaskPilot → 200.
- Registro, login, CRUD y logout POST funcionan.
- Subida de imagen y visualización autenticada funcionan.
- Otro usuario recibe 404/403 en tarea e imagen ajenas.
- Base nueva: 0 usuarios y 0 tareas antes del registro; integridad `ok`.
- `showmigrations` sin pendientes.
- Logs sin `ImportError` ni 500 repetidos.

### 6.8 Cuarentena (G6-L, 7 días)

Solo tras verificar G6. Ejecutar desde una consola **sin** `todo-env` activo.

```bash
set -euo pipefail
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
Q="$HOME/.quarantine-$STAMP"
install -d -m 700 "$Q"

mv "$HOME/todo_django_mongodb"         "$Q/"
mv "$HOME/sample-web-personal-django2" "$Q/"
mv "$HOME/.virtualenvs/todo-env"       "$Q/"
mv "$HOME/.virtualenvs/webpersonal"    "$Q/"

# Solo tras verificar su contenido:
mv /var/www/__pycache__                "$Q/www-pycache"

echo "QUARANTINE=$Q"
du -sh "$HOME"
```

- `/var/www/jzamora_pythonanywhere_com_wsgi.py` **no se borra**: ya fue reemplazado en G6.
- `README.txt` y los logs se conservan.
- La cuarentena es reversible con `mv`.
- Ventana: 7 días desde G6-L.

### 6.9 Purga (G7)

Tras 7 días y con la aplicación estable:

```bash
rm -rf "$HOME/.quarantine-<STAMP>"
du -sh "$HOME"
```

Inventario eliminado (≈229.7 MB):

| Recurso | Tamaño |
|---|---|
| `todo_django_mongodb` | 8.7 MB |
| `sample-web-personal-django2` | 30 MB |
| `.virtualenvs/todo-env` | 99 MB |
| `.virtualenvs/webpersonal` | 92 MB |
| `/var/www/__pycache__` | ~1 KB |

- El backup `20261107T013845Z` se conserva hasta que G7 autorice su borrado.
- No se borran la Web App, el dominio, `taskpilot`, `taskpilot-data` ni los logs.
- HOME quedará en ≈79 MB usados y ≈433 MB libres, suficiente para el venv nuevo.

### 6.10 Dependencias exactas

```txt
Django==5.2.19
Pillow==12.3.0
python-dotenv==1.2.4
asgiref==3.12.1
sqlparse==0.6.1
```

| Paquete | Requisito | Motivo |
|---|---|---|
| Django 5.2.19 | `>=3.10` | Última 5.2 LTS; SQLite ≥ 3.31.0 |
| Pillow 12.3.0 | `>=3.10` | Wheels `cp310`; 13.0.0 exige ≥3.11 |
| python-dotenv 1.2.4 | `>=3.10` | Compatible |
| asgiref 3.12.1 | `>=3.10` | 3.13.0 exige ≥3.11; no subir |
| sqlparse 0.6.1 | `>=3.10` | Compatible |

Sin `pymongo`, `mongoengine` ni `dnspython`.

---

## 7. Documentación y estructura

### 7.1 Documentos

| Archivo | Contenido |
|---|---|
| `README.md` | Producto, características, stack, instalación, comandos, enlaces |
| `ARCHITECTURE.md` | Diagramas, capas, modelo, auth, API, medios, SQLite/PA, ADRs |
| `SECURITY.md` | Amenazas, authz, CSRF, IDOR, uploads, secretos, cabeceras, incidentes |
| `DEPLOYMENT.md` | Inventario, backup, deploy por tag, WSGI, env, migraciones, verificación y rollback |
| `ENVIRONMENT.md` | Variables, dev/prod, `.env`, `DATA_DIR`, rotación |
| `CHANGELOG.md` | Keep a Changelog, SemVer, `1.0.0` |
| `CONTRIBUTING.md` | Ramas, commits, PR, pruebas, migraciones, secretos |
| `RUNBOOK.md` | Salud, logs, reload, backup/restore, rollback, SQLite, 502, estáticos, disco |
| `docs/adr/` | Decisiones SQLite, no MongoDB, PA, authz/media y API |

### 7.2 Estructura

```text
taskpilot/
├── manage.py
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── ARCHITECTURE.md
├── SECURITY.md
├── DEPLOYMENT.md
├── ENVIRONMENT.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── RUNBOOK.md
├── config/
│   ├── settings.py            # o settings/{base,dev,prod}.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── todos/
│   ├── models.py
│   ├── forms.py
│   ├── validators.py
│   ├── services.py
│   ├── selectors.py
│   ├── views/
│   ├── urls.py
│   ├── admin.py
│   ├── management/commands/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_todotask_user.py
│   │   └── 0003_alter_todotask_user.py   # user NOT NULL
│   └── tests/
├── templates/{todos,errors}/
├── static/                    # opcional; si existe, con .gitkeep
├── docs/adr/
└── .github/workflows/ci.yml
```

- Eliminar `todos/db.py`.
- Sustituir `PYTHONANYWHERE_DEPLOY.md` por `DEPLOYMENT.md`.
- Si se dividen los settings, actualizar `config/wsgi.py` y el WSGI de PythonAnywhere.
- Dependencias de producción: Django, Pillow, python-dotenv, asgiref y sqlparse, con versiones fijadas.
- Desarrollo opcional: `coverage`, `ruff`. Sin DRF, Celery, Redis, Sentry ni servicios externos sin aprobación.

### 7.3 Credenciales

Documentar ubicación y rotación, nunca valores: GitHub (cuenta, 2FA, PAT/SSH), PythonAnywhere (cuenta, 2FA, Web, WSGI, venv, API token), `.env` (permisos 600), SQLite (archivo, backups), dominio/WSGI y backups. No incluir secretos en Markdown, Git, logs ni chat.

---

## 8. Fases de ejecución

El orden prioriza la seguridad: F1 corrige autenticación, autorización y exposición de datos antes de F2 (identidad y limpieza de MongoDB). La numeración de gates sigue el orden de ejecución.

### 8.1 F0 — Operaciones separadas y autorizaciones

| Operación | Tipo | Estado | Autorización | No autoriza |
|---|---|---|---|---|
| F0.1 Inventario | Solo lectura | **Completado** | G0 | Backup, tag, bundle, código, Git, GitHub o producción |
| F0.2 Backup | Escritura de respaldo | **Completado** (`20261107T013845Z`) | G0-B | Tag, bundle, cambios de app/base o deploy |
| F0.3 Tag local | Escritura local de Git | No ejecutado | G0-T | Push, bundle, renombrado o deploy |
| F0.4 Bundle local | Escritura local de Git | No ejecutado | G0-U | Push, tag, renombrado o deploy |

G0 no autoriza automáticamente backup, tag ni bundle. Cada operación de escritura requiere una autorización separada y registrada.

### 8.2 Fases

| Fase | Gate | Objetivo y cambios | Depende | Pruebas / aceptación | Impacto |
|---|---|---|---|---|---|
| **F0** | G0; G0-B completado | Gobernanza: inventario, baseline, backup y decisiones. | — | Inventario completo; backup con checksums, integridad y restauración probada. | Escritura de respaldo; no modifica la app ni la base. |
| **F1** | G1 | Seguridad I: login obligatorio, propiedad estricta, 404, CSRF, logout POST, API 401 JSON, multimedia privada, settings seguros, `0003`, rotación de clave. | F0 | Suite F1 (§8.3): 401 JSON en API, 302 en web, IDOR 404, CSRF 403, imágenes privadas, `0003` en base temporal limpia, `check --deploy`. | Alto: código, migraciones y pruebas. |
| **F2** | G2 | Identidad TaskPilot: renombrar carpeta local, quitar MongoDB y dependencias, actualizar docs/marca, fijar versiones. El rename de GitHub se difiere a G2-GH. | F1 aceptada | Cero refs Mongo, `check`, tests, `makemigrations --check`. | Rutas locales y documentación; sin producción. |
| **F3** | G3 | Seguridad II: formularios/JSON, uploads, transacciones, errores, logging, SQLite. | F1 | Entradas inválidas, imágenes, transacciones, errores, integridad. | Medio: migraciones y pruebas. |
| **F4** | G4 | Calidad: módulos, API versionada, paginación, tests, cobertura, lint. | F1 y F3 | Suite verde, cobertura ≥80 % crítico, API documentada. | Bajo. |
| **F5** | G5 | Documentación completa, ADRs, entorno, runbook y changelog. | F1–F4 | Comandos reproducibles, sin secretos, enlaces válidos. | Ninguno. |
| **F5-P** | G5-P | Publicación: push de `main` y tag `v1.0.0`. | F5 + auditoría independiente (§8.4) | Fast-forward, tag anotado, escaneo de secretos, informe de auditoría emitido y hallazgos críticos/altos resueltos o aceptados. | GitHub. |
| **F6-P** | G6-P | Aprovisionamiento: clone por tag, `taskpilot-data`, venv, `.env`, base nueva, `migrate`, `collectstatic`, checks. | F5-P | `check`, `check --deploy`, integridad `ok`, `pip check`. | Escritura en PA; no toca Web App ni borra nada. |
| **F6** | G6 | Conmutación: WSGI, source, venv, mappings, HTTPS, reload. | F6-P | Matriz funcional/seguridad; rollback listo. | Alto: producción. |
| **F6-L** | G6-L | Cuarentena de ambos proyectos, ambos venvs y `__pycache__`. | F6 estable | App responde; rutas antiguas en cuarentena; reversible. | Reversible (`mv`). |
| **F7** | G7 | Cierre: purga de cuarentena, decisión sobre el backup y monitoreo. | F6-L + 7 días | Estabilidad, `du`, backup verificado. | Destructivo autorizado. |

**Ruta crítica:** F0 → F1 → F2 → F3 → F4 → F5 → F5-P → F6-P → F6 → F6-L → F7.
**Ruta crítica de seguridad:** F0 → F1 → F3 → F6.
**Nota:** F2 (identidad y MongoDB) no bloquea F1 ni F3. El rename de GitHub ocurre después de F6.

### 8.3 Pruebas mínimas de F1

Se ejecutan en local, sin producción y sin usar la base local existente para `0003`.

| Caso | Resultado esperado |
|---|---|
| Web anónima `/` | `302` al login |
| API anónima `GET /api/todos/` | **`401` JSON**, `Content-Type: application/json`, sin `Location` |
| API anónima `POST` con token CSRF válido | `401` JSON; sin efectos |
| API autenticada como A | Solo tareas de A |
| API autenticada como B sobre tarea de A | `404` (o código de la matriz) |
| POST web sin CSRF | `403` |
| POST API sin CSRF | `403` (el middleware CSRF actúa antes de la autenticación) |
| Logout por `GET` | `405` |
| Logout por `POST` con CSRF | `302`/`200` |
| Imagen de A solicitada por A | `200` |
| Imagen de A solicitada por B | `404` |
| Imagen de A solicitada por anónimo | `302` al login (vista web) |
| `csrf_exempt` en API | Ausente |
| Migración `0003` en base temporal | `0001` → `0002` → `0003` sin error; `todos_todotask.user_id` con `NOT NULL` |
| Base local `db.sqlite3` | Intacta; no se usa para validar `0003` |

Notas:

- Para comprobar `401` en un `POST` anónimo hay que enviar un token CSRF válido; sin token, Django devuelve `403` antes de llegar a la autenticación.
- La prueba de `0003` crea una base SQLite temporal y limpia, aplica las tres migraciones y verifica el esquema. **No** se asignan propietarios artificiales, no se borra la base local y no se sustituye sin instrucción independiente.
- La suite completa se ejecuta una vez por fase. La auditoría usa pruebas puntuales, no una segunda suite completa sin justificación.

### 8.4 Auditoría independiente de Antigravity (previa a G5-P)

La auditoría es una verificación de solo lectura. **No crea un gate nuevo** y no autoriza cambios ni despliegues.

**OpenCode:**

- Implementa el código.
- Ejecuta las pruebas automatizadas de cada fase.
- Corrige los errores encontrados.
- Entrega un resumen breve con archivos modificados, pruebas ejecutadas, resultados y limitaciones.

**Antigravity (Gemini):**

- Actúa como auditor independiente de solo lectura.
- Revisa después de F1–F5 y antes de G5-P.
- No vuelve a analizar todo el repositorio.
- No modifica archivos, código, dependencias, configuración ni datos.
- No instala paquetes ni ejecuta comandos en PythonAnywhere.
- Puede revisar los resultados de OpenCode y ejecutar pruebas puntuales en un entorno local controlado, con bases temporales fuera del proyecto, siempre que no altere datos de trabajo ni archivos del proyecto.

**Material mínimo:**

1. Resumen de cambios y resultados de pruebas de OpenCode.
2. Secciones pertinentes de `MASTER_PLAN.md`.
3. Configuración relevante de Django.
4. Vistas web y API, servicios, modelos y URLs.
5. Migraciones `0001`, `0002` y `0003`.
6. Pruebas de autenticación, propiedad, CSRF e imágenes.
7. Plantillas o archivos de administración que gestionen imágenes, cuando sean pertinentes.
8. Dependencias de producción.

**Exclusiones:** no facilitar `.env`, claves API, contraseñas, secretos, bases de datos reales, multimedia, backups ni tokens.

**Alcance:** autenticación y respuestas HTTP; aislamiento de tareas entre usuarios; protección de API y CSRF; acceso a imágenes privadas; migraciones y consistencia del modelo; configuración de seguridad y exposición de secretos.

**Resultado exigido:** informe breve con hallazgos clasificados por severidad, archivo y ubicación, evidencia y recomendación. Antigravity no corrige los hallazgos; las correcciones corresponden a OpenCode y requieren la autorización de implementación aplicable. La auditoría no duplica la suite completa: aporta verificación independiente.

---

## 9. Clasificación de comandos y operaciones

| Categoría | Ejemplos | Estado actual |
|---|---|---|
| **Solo lectura** | Inventario, `git status`, `git log`, `git remote -v`, `git ls-remote`, `ls`, `du`, `pip freeze`, `PRAGMA integrity_check`, `SELECT count(*)`, `check`, `showmigrations`, `curl` GET | Permitido con alcance autorizado; no incluye backup |
| **Cambios locales** | Editar archivos, backup local, instalar dependencias, pruebas, migraciones locales, `collectstatic`, renombrar carpeta, commits, tags, ramas, bundles | Requiere gate específico: G0-B, G0-T, G0-U, G1, G2, G5-P, etc. |
| **Cambios en GitHub** | Push, tags, renombrar repositorio, configuración, tokens, branch protection | G5-P para push/tag; G2-GH para renombrar; G0-T/G0-U no autorizan push |
| **Cambios en producción (no destructivos)** | Crear `taskpilot`, venv, `.env`, base nueva, `collectstatic`, reemplazar WSGI, mappings, reload | G6-P y G6, con ventana obligatoria |
| **Eliminación / cuarentena** | `mv` de proyectos y venvs a cuarentena; `rm -rf` de cuarentena; borrar `/var/www/__pycache__` | G6-L (cuarentena) y G7 (purga); nunca dentro de G6-P o G6 |
| **Datos** | Migrar datos, asignar huérfanas, borrar base o multimedia | No aplica: base nueva y vacía; cualquier excepción requiere gate propio |

La creación y corrección de `MASTER_PLAN.md` no autoriza ninguna de estas operaciones.

---

## 10. Approval Gates

La numeración sigue el orden de ejecución. **Cada gate es independiente** y requiere confirmación explícita y registrada.

| Gate | Autorización explícita necesaria | Autoriza | No autoriza | Evidencia previa |
|---|---|---|---|---|
| **G0** | Aprobar este plan maestro y el orden de fases | F0.1: inventario de solo lectura | Backup, tag, bundle, código, Git, GitHub o producción | Plan revisado |
| **G0-B** | Autorizar backup y alcance | F0.2: backup, checksums y restauración | Tag, bundle, cambios de app/base o deploy | G0 y ventana si es producción. **Ejecutado** |
| **G0-T** | Autorizar tag local | F0.3 | Push, bundle, renombrado o deploy | G0 y árbol limpio |
| **G0-U** | Autorizar bundle local | F0.4 | Push, tag, renombrado o deploy | G0 y árbol limpio |
| **G1** | Aprobar F1: seguridad de autenticación y autorización | Código auth/authz, CSRF, multimedia privada, `0003`, pruebas | Producción | F0 y diseño de autorización aprobado |
| **G2** | Aprobar F2: identidad local y limpieza MongoDB | Renombrar carpeta local, quitar Mongo, marca/docs, commits | Producción ni rename de GitHub | F1 aceptada, backup verificado y repo limpio |
| **G3** | Aprobar F3: robustez | Validación, uploads, transacciones, errores, logging y migraciones locales | Producción | F1 aceptada |
| **G4** | Aprobar F4: calidad | Refactor, API, pruebas, lint y cobertura | Producción | F1 y F3 aceptadas |
| **G5** | Aprobar F5: documentación | Documentación y ADRs | Producción ni GitHub | F1–F4 |
| **G5-P** | Aprobar publicación | Push de `main` por fast-forward y tag `v1.0.0` | Deploy ni renombrado de GitHub | F1–F5, auditoría independiente emitida, árbol limpio y escaneo de secretos |
| **G6-P** | Aprobar aprovisionamiento | Crear `taskpilot`, `taskpilot-data`, venv, `.env`, base nueva, `collectstatic`, checks | Cambiar Web App/WSGI, borrar o cuarentenar | G5-P completado; tag `v1.0.0` disponible |
| **G6** | Aprobar ventana de producción | Reemplazar WSGI, source, venv, mappings, HTTPS y reload; rollback listo | Cuarentena, purga, renombrar GitHub | F6-P verificado |
| **G6-L** | Aprobar cuarentena | `mv` de ambos proyectos, ambos venvs y `__pycache__` verificado | Borrar la cuarentena | G6 estable y verificado |
| **G7** | Aprobar cierre y purga | `rm -rf` de cuarentena, decisión sobre backup y monitoreo | Borrar dominio, Web App o datos de TaskPilot | 7 días de estabilidad y backup verificado |
| **G2-GH** | Aprobar renombrado de GitHub posterior al despliegue | Renombrar repo a `taskpilot-django` y actualizar `origin` | Cambios de código o producción | G6 estable |

**G6-P, G6, G6-L y G7 no están autorizados.** G0-B se ejecutó; G0-T y G0-U no. La aprobación del diseño no equivale a autorización de implementación.

---

## 11. Riesgos y criterios globales

### 11.1 Riesgos

| Riesgo | Mitigación |
|---|---|
| Python 3.10 EOL (oct. 2026) | Riesgo aceptado en D1; Django 5.2 LTS lo soporta hasta abril 2028; revisar cuando PA ofrezca ≥3.11 |
| Django 6.x incompatible con Python 3.10 | Fijar `Django==5.2.19`; no actualizar a 6.x |
| Borrar el blog antes de cambiar el WSGI | Orden estricto G6 → G6-L |
| Sin URL de staging | Ventana de mantenimiento y rollback de configuración |
| Pérdida irreversible | Cuarentena con `mv`; purga solo en G7 |
| SQLite sobre almacenamiento de red | `timeout=20`, sin WAL, operaciones cortas |
| HTTPS mal configurado | Activar Force HTTPS y `SECURE_PROXY_SSL_HEADER` juntos |
| Cuota mal calculada | 309 MB usados; tras la limpieza ≈79 MB usados y ≈433 MB libres |
| Multimedia pública | Sin mapping `/media/`; `FileResponse` autenticado |
| Imágenes rotas tras quitar `/media/` | Implementar la vista privada en F1 antes de G6 |
| `STATICFILES_DIRS` inexistente | Eliminar la entrada o añadir `.gitkeep` |
| Secretos expuestos | Rotación, `.env` 600, escaneo y 2FA |
| Repo renombrado con clone antiguo | Actualizar `origin` en G2-GH; GitHub redirige |
| Backup no restaurable | Checksums, `integrity_check` y prueba ya realizadas |
| Tag/clon incorrecto | Desplegar por `v1.0.0`, nunca por `01eb960` |
| Rollback pierde escrituras nuevas | Los datos de TaskPilot permanecen en `taskpilot-data`; no se reconcilian con la app antigua |

### 11.2 Criterios globales de aceptación

- Sin acceso anónimo salvo login/registro.
- API anónima responde `401 JSON`; las vistas web pueden redirigir al login.
- Sin acceso cruzado entre usuarios.
- CSRF en todas las escrituras, incluida la API; logout POST.
- Multimedia privada y uploads validados.
- `0003` validada en una base SQLite temporal y limpia; base local intacta.
- Copia del WSGI vigente verificada antes del reemplazo.
- Auditoría independiente emitida antes de G5-P; hallazgos críticos/altos resueltos o aceptados.
- Sin secretos en repo, historial, docs ni logs.
- `DEBUG=False`, hosts exactos y HTTPS en producción.
- Cero referencias y dependencias MongoDB.
- Django 5.2.19 y Python 3.10 documentados; riesgo EOL registrado.
- Base nueva: 0 usuarios y 0 tareas; `PRAGMA integrity_check=ok`.
- `/.env`, `/db.sqlite3` y `/media/` responden 404.
- Backup conservado y verificado; sin copias externas nuevas.
- Cuarentena de 7 días antes de la purga.
- `check --deploy` sin advertencias críticas.
- Documentación completa y sin credenciales.
- Rollback documentado y, si la ventana lo permite, ensayado.
- G6-P, G6, G6-L y G7 autorizados por separado.

### 11.3 No-go

No se cierra la modernización si hay acceso cruzado, secreto expuesto, backup sin prueba de restauración, `DEBUG=True`, multimedia privada pública, base con datos inesperados, errores 500 repetidos, mappings apuntando a rutas eliminadas, Django distinto de 5.2.19, API que redirige en lugar de devolver `401 JSON`, `0003` validada sobre la base local o con propietarios artificiales, WSGI reemplazado sin copia verificada, G5-P ejecutado sin auditoría independiente, o cualquier fase ejecutada sin su gate.

---

## 12. Próximo paso

**Estado actual:**

- **F1–F5 no ejecutadas.**
- **Auditoría independiente de Antigravity pendiente**, después de F1–F5 y antes de G5-P.
- **G0-B ejecutado.**
- **G0-T y G0-U no autorizados.**
- **G0 correspondiente a v2 pendiente de aprobación.**
- **G1 y todos los demás gates conservan su estado independiente.**

**Secuencia:**

1. Revisar y aprobar explícitamente **G0 para v2**.
2. Solo después, solicitar **G1** para ejecutar F1 (seguridad).
3. Tras F1–F5, ejecutar la auditoría independiente (§8.4) y resolver los hallazgos bajo la autorización de la fase correspondiente.
4. Solicitar **G5-P** para publicar `main` y el tag `v1.0.0`.
5. Solo entonces solicitar **G6-P**, seguido de **G6**, **G6-L** y **G7**, cada uno por separado.
6. El renombrado de GitHub (**G2-GH**) se solicita después de G6.

Ninguna autorización de esta actualización permite implementar, publicar, desplegar ni modificar PythonAnywhere o GitHub. **G6-P, G6, G6-L y G7 siguen sin autorización.**

---

## Apéndice A — Registro de decisiones

| ID | Fecha | Decisión |
|---|---|---|
| D1 | 2026-11-06 | Django 5.2.19 + Python 3.10; riesgo EOL aceptado temporalmente |
| D2 | 2026-11-06 | `/home/jzamora/taskpilot` + `/home/jzamora/taskpilot-data`; `staticfiles` dentro del proyecto |
| D3 | 2026-11-06 | Conservar `0001`/`0002`; añadir `0003` para `user` obligatorio |
| D4 | 2026-11-06 | Cuarentena de 7 días |
| D5 | 2026-11-06 | Conservar backup hasta G7; no crear otro |
| D6 | 2026-11-06 | Eliminar `/var/www/__pycache__` en G6-L tras verificar contenido |
| D7 | 2026-11-06 | Base nueva y vacía |
| D8 | 2026-11-06 | Renombrar GitHub después del despliegue |
| D9 | 2026-11-06 | Gates G6-P, G6, G6-L y G7 independientes |

## Apéndice B — Cambios de código requeridos

| Archivo | Cambio |
|---|---|
| `config/settings.py` | `DATA_DIR`, DB externa, `STATIC_ROOT`, `MEDIA_ROOT`, sin Mongo, `SECRET_KEY` obligatoria, `DEBUG=False`, hosts, seguridad, `timeout` |
| `config/urls.py` | Quitar servicio `/media/`; añadir vista privada de imagen |
| `todos/models.py` | `user` no nulo; `to_dict()` sin `.image.url` |
| `todos/views.py` | `login_required` en vistas web; API 401 JSON sin `login_required`; sin `csrf_exempt`; logout POST; vista `todo_image` |
| `todos/services.py` | Filtro estricto por propietario; sin `Q(user__isnull=True)` |
| `todos/admin.py` | Preview de imagen por vista privada |
| `templates/todos/index.html` | URLs de imagen por `{% url %}` |
| `todos/migrations/0003_*.py` | `user` obligatorio |
| `requirements.txt` | Pines exactos; sin Mongo |
| `.env.example` | Sin Mongo; `DATA_DIR` y `STATIC_ROOT` |
| `pythonanywhere_wsgi.py` | Ruta absoluta `/home/jzamora/taskpilot` |
| `todos/db.py` | Eliminar |
| `todos/tests.py` | Adaptar a autenticación y propiedad |
| `seed_data.py` | Solo desarrollo; propietario obligatorio |
| `README.md`, `PYTHONANYWHERE_DEPLOY.md` | Rutas, stack y comandos actualizados |

## Apéndice C — Inventario de recursos a retirar

| Recurso | Ruta | Tamaño | Fase |
|---|---|---|---|
| Proyecto TODO | `/home/jzamora/todo_django_mongodb` | 8.7 MB | G6-L |
| Proyecto blog | `/home/jzamora/sample-web-personal-django2` | 30 MB | G6-L |
| Venv TODO | `/home/jzamora/.virtualenvs/todo-env` | 99 MB | G6-L |
| Venv blog | `/home/jzamora/.virtualenvs/webpersonal` | 92 MB | G6-L |
| Caché WSGI | `/var/www/__pycache__` | ~1 KB | G6-L |
| Backup | `/home/jzamora/backups/20261107T013845Z` | 6.6 MB | Conservar hasta G7 |

No se eliminan: dominio, Web App, WSGI (se reemplaza), logs ni `README.txt`.

## Apéndice D — Estado de autorizaciones

| Gate | Estado |
|---|---|
| G0 | v2 pendiente de aprobación explícita (G0 de v1 aprobado) |
| G0-B | Ejecutado |
| G0-T | No autorizado |
| G0-U | No autorizado |
| G1 | No autorizado |
| G2 | No autorizado |
| G2-GH | No autorizado |
| G3 | No autorizado |
| G4 | No autorizado |
| G5 | No autorizado |
| G5-P | No autorizado |
| G6-P | No autorizado |
| G6 | No autorizado |
| G6-L | No autorizado |
| G7 | No autorizado |
| Auditoría independiente (§8.4) | Pendiente de F1–F5; no es un gate |

**F1–F5 no ejecutadas.** La auditoría de Antigravity se realizará después de F1–F5 y antes de G5-P. Ninguna autorización de esta actualización habilita implementación, publicación o despliegue.
