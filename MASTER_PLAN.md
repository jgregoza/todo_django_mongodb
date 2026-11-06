# MASTER_PLAN.md — Plan maestro de modernización de TaskPilot

**Proyecto:** TaskPilot (nombre objetivo; el repositorio actual es `todo_django_mongodb`)
**Estado:** Borrador para revisión y aprobación. **No autoriza implementación.**
**Fecha:** 2026-11-06
**Alcance:** diagnóstico, arquitectura, seguridad, identidad, Git, despliegue, documentación y fases.

> Este documento consolida las cuatro partes del análisis previo. Su existencia no implica autorización para ejecutar cambios. La implementación requiere aprobación explícita por fase y por entorno.

---

## 1. Resumen ejecutivo

TaskPilot es una aplicación Django de gestión personal de tareas con prioridades, categorías, fechas límite, imágenes, estadísticas, autenticación, panel de administración y API JSON. La aplicación funciona, pero su nombre y configuración actuales sugieren una integración MongoDB que no existe: la persistencia real es SQLite mediante Django ORM.

La modernización busca:

- Priorizar la corrección de acceso anónimo, autorización, CSRF y multimedia pública antes del renombrado y la limpieza de MongoDB.
- Consolidar la identidad **TaskPilot** y eliminar referencias a MongoDB.
- Corregir los graves problemas de autenticación, autorización, CSRF y privacidad de imágenes.
- Validar entradas, archivos y errores; mejorar transacciones, logging y pruebas.
- Documentar arquitectura, seguridad, entorno, despliegue, operación y recuperación.
- Desplegar de forma limpia y reversible en PythonAnywhere, conservando datos y posibilitando rollback.

**Decisión de arquitectura confirmada:** Django + SQLite + PythonAnywhere + Git. Sin MongoDB. Sin servicios de pago innecesarios.

**Advertencia:** PythonAnywhere indica que SQLite no es recomendado como base de producción por depender del sistema de archivos. Se mantiene por decisión del proyecto, con bajo tráfico, un solo worker cuando la cuenta lo permita, timeout, operaciones cortas, respaldos y verificación de integridad. Las capacidades reales de la cuenta deben verificarse.

---

## 2. Diagnóstico actual

### 2.1 Arquitectura y funcionalidades

- Monolito Django con arquitectura MVT y una capa de servicios (`todos/services.py`).
- Plantillas renderizadas en servidor; formularios HTML y una API JSON paralela.
- Frontend con Tailwind CSS y Lucide por CDN.
- Autenticación nativa de Django con sesiones.
- Admin de Django con filtros, badges e imágenes.
- Funcionalidades presentes: CRUD de tareas, prioridades, categorías, fechas límite, imágenes, filtros, búsqueda, estadísticas, registro, login, logout, API y admin.
- Persistencia real: SQLite (`db.sqlite3`) a través de Django ORM.
- MongoDB: configuración y módulo `todos/db.py` presentes, pero nunca inicializados ni utilizados. Dependencias `pymongo`, `mongoengine` y `dnspython` sin uso real.

### 2.2 Línea base verificada

| Área | Estado |
|---|---|
| Python local | 3.12.10 |
| Django instalado | 6.1.2 |
| Pillow / python-dotenv | 13.0.0 / 1.2.4 |
| Base local | 20 migraciones, 4 tareas, 0 usuarios |
| Multimedia local | No existe `media/`; se crea al subir imágenes |
| Estáticos | `static/` vacío; `staticfiles/` generado e ignorado |
| Pruebas | 7 pruebas básicas, sin autorización, CSRF ni uploads |
| CI/CD | No existe |
| Documentación | Solo README y guía antigua de PythonAnywhere |

### 2.3 Git

- Rama local y remota única: `main`.
- Sin tags.
- Dos commits; `HEAD` local y remoto en `01eb960`.
- `origin`: `https://github.com/jgregoza/todo_django_mongodb.git`.
- `main` sin upstream configurado.
- Árbol de trabajo limpio; 28 archivos versionados.
- Sin submódulos, LFS ni ramas adicionales.
- `.env` existe, está ignorado y no está versionado.
- `db.sqlite3`, `.venv/`, `staticfiles/`, `media/` y `__pycache__/` están ignorados.
- No se detectaron tokens, claves privadas, bases de datos ni multimedia en el historial con los patrones revisados.
- Sí existe una `SECRET_KEY` de respaldo hardcodeada en `config/settings.py` en ambos commits; debe rotarse y eliminarse el fallback.
- El nombre y correo del autor son visibles en los commits; no se recomienda reescribir historia solo por ello.
- Verificar en GitHub si el repositorio es público o privado.

### 2.4 Hallazgos críticos

| Severidad | Hallazgo |
|---|---|
| Crítica | Usuarios anónimos pueden ver todas las tareas |
| Crítica | Usuarios anónimos pueden editar, alternar o eliminar cualquier tarea por ID |
| Crítica | API pública, sin autenticación obligatoria y con `csrf_exempt` |
| Crítica | Multimedia potencialmente pública si se mantiene el mapping `/media/` |
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
| Baja | Registro abierto sin límite de intentos |

### 2.5 Datos que deben verificarse

- Plan real de PythonAnywhere, sistema operativo/imagen, versión de Python, rama US/EU y dominio.
- Cuotas reales: almacenamiento, CPU, workers, consolas, tareas programadas, SSH/SFTP y límites de backup.
- Herramientas disponibles en la cuenta (`sqlite3`, `tar`, `gpg` u `openssl`, `sha256sum`, `git`, activación de venv).
- Rutas reales del proyecto, virtualenv, WSGI, logs, `.env`, base y multimedia.
- Mappings de estáticos y multimedia.
- Existencia, tamaño y permisos de `media/`; espacio libre para backups.
- Número real de usuarios, tareas, tareas huérfanas y archivos multimedia en producción.
- Visibilidad del repositorio en GitHub.
- Claves reales presentes en `.env` (solo nombres, nunca valores).
- Existencia, restaurabilidad y capacidad de descarga externa de backups actuales.
- Estado real de HTTPS y certificados.

**No asumir que la base local representa producción.**

---

## 3. Decisiones

### 3.1 Decisiones acordadas o confirmadas conceptualmente

- Backend Django.
- Base de datos SQLite.
- Hosting PythonAnywhere.
- Control de versiones Git.
- OpenCode como asistente de desarrollo.
- **No implementar MongoDB.**
- Evitar servicios, dependencias y herramientas de pago innecesarias.
- Priorizar seguridad, calidad, documentación y despliegue reproducible.
- No implementar nada hasta aprobar este plan maestro y cada fase.

### 3.2 Identidad objetivo

- Producto: **TaskPilot**.
- Repositorio propuesto: **`taskpilot-django`**.
- Directorio de despliegue propuesto: `taskpilot`.
- Virtualenv propuesto: `taskpilot-env`.
- El renombrado real requiere aprobación específica (Gate G2) y se ejecuta en F2, después de F1 (seguridad), salvo repriorización explícita.

### 3.3 Recomendaciones y decisiones pendientes de aprobación

1. **Identidad TaskPilot (G2):** adoptar el nombre y renombrar el repositorio a `taskpilot-django`, después de F1 (seguridad).
2. **Etiquetas internas:** mantener `config` y `todos` para no tocar migraciones.
3. **Multimedia privada:** sin mapping público `/media/`; servir solo con autorización.
4. **API de sesión con CSRF:** sin API pública ni DRF en esta etapa.
5. **SQLite:** aceptar el riesgo documentado y sus mitigaciones (timeout, un solo worker cuando la cuenta lo permita, backups, integridad).
6. **PythonAnywhere:** verificar en la cuenta real plan, cuotas, herramientas, almacenamiento y dominio antes de aceptar el plan gratuito; no tratar los datos públicos como garantía.
7. **Retención de backups y releases:** 7, 30 o 90 días.
8. **Cifrado y destino del backup:** elegir GPG u OpenSSL, definir almacenamiento externo, responsable y custodia; el `.env` externo debe estar cifrado.
9. **Prueba de restauración:** definir frecuencia, responsable y evidencia; ningún backup es válido sin prueba.
10. **Rollback con escrituras nuevas:** aprobar la política de congelar, exportar y reconciliar datos; no restaurar a ciegas.
11. **Django:** mantener 6.1.2 durante la modernización y evaluar LTS en una fase separada.
12. **Herramientas opcionales:** `ruff`, `coverage` y CI.
13. **Tareas huérfanas:** identificar, proponer y aprobar un propietario antes de la migración; no asignar automáticamente.
14. **Rotación de secretos:** política de `SECRET_KEY` y credenciales.
15. **Alcance de F0:** confirmar que G0 solo autoriza inventario; backup, tag y bundle requieren G0-B, G0-T y G0-U.

### 3.4 Datos aún no verificados

Los indicados en la sección 2.5, incluidas las cuotas, herramientas y capacidades reales de PythonAnywhere.

---

## 4. Estrategia de identidad, GitHub y secretos

### 4.1 Alcance del renombrado

**Renombrar:** producto, repositorio, carpeta raíz, documentación, marca visible, rutas de despliegue y virtualenv.

**No renombrar en F2:** paquete `config`, app `todos`, modelo `TodoTask`, tablas `todos_todotask` ni historial de migraciones. Renombrar la app o el modelo obliga a tocar migraciones, `contenttypes`, permisos e imports, con riesgo alto y beneficio cosmético.

### 4.2 Lugares afectados

- Carpeta local y workspace.
- Remoto `origin` y `.git/config`.
- Repositorio GitHub.
- `README.md` (título, árbol y URL absoluta `file:///C:/Users/...`).
- `PYTHONANYWHERE_DEPLOY.md` (clon, `cd`, rutas de source, estáticos y multimedia).
- `pythonanywhere_wsgi.py` (comentario de ruta).
- Pestaña Web de PythonAnywhere: source, working dir, venv, WSGI, mappings.
- Virtualenv `todo-env`.
- Plantillas: “TODO Pro”, “TODO List Pro”.
- `todos/models.py` (docstring).
- `config/settings.py` y `.env.example`: bloques `MONGO_*`.
- `requirements.txt`: dependencias Mongo.
- `todos/db.py`.

### 4.3 Procedimiento de renombrado (F2, Gate G2)

Este procedimiento se ejecuta después de F1 (seguridad) y de la aprobación G2.

1. Aprobar nombre y alcance (G2).
2. Confirmar árbol limpio y backup verificado (G0-B).
3. Crear tag local (G0-T) y bundle local (G0-U) solo con autorización específica; G0 no los autoriza.
4. Renombrar el repositorio en GitHub (G2).
5. Actualizar `origin`, hacer `fetch` y configurar upstream (G2).
6. Renombrar la carpeta local (G2).
7. Actualizar documentación, plantillas, WSGI y `.env.example` (G2).
8. Eliminar MongoDB y dependencias (G2).
9. Verificar `check`, pruebas y `makemigrations --check` (G2).
10. Hacer commits pequeños (G2).
11. Actualizar el clon y la configuración de PythonAnywhere solo en F6, con autorización de producción; G2 no autoriza producción.
12. Conservar el despliegue anterior para rollback.

### 4.4 Git

- Conservar historial; no hacer `force push` ni reescribir pasado.
- Commits convencionales y pequeños.
- Ramas cortas por fase: `chore/`, `feat/`, `fix/`, `docs/`, `security/`.
- No crear tags, bundles ni ramas hasta autorización; el tag local requiere G0-T y el bundle local requiere G0-U.
- Revisar `.gitignore`: `.env`, `.env.*` con excepción `.env.example`, `.venv/`, `db.sqlite3`, `media/`, `staticfiles/`, `__pycache__/`, logs, `backups/`, `.coverage`, `htmlcov/`, `.ruff_cache/`.
- No ignorar migraciones ni documentación.

### 4.5 Secretos

- Rotar la `SECRET_KEY` actual por estar el fallback en el historial.
- Sin fallback en producción: si falta, fallar de forma explícita.
- `.env` con permisos `600`, fuera de Git y de directorios públicos.
- La copia externa del `.env` debe estar cifrada; la passphrase o clave se guarda fuera del backup.
- Verificar descifrado y checksum sin imprimir valores.
- Documentar ubicación y rotación, nunca valores.
- No incluir credenciales en Markdown, commits, logs ni chat.
- GitHub: 2FA, token de mínimo privilegio y rotación.
- PythonAnywhere: 2FA, contraseña robusta, consolas no compartidas.

---

## 5. Seguridad

### 5.1 Política objetivo

- Denegar por defecto; solo login y registro son públicos.
- Cada tarea pertenece a un usuario.
- Toda vista y API exige autenticación.
- Objetos ajenos responden 404.
- CSRF obligatorio en toda escritura.
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
| Tarea de A | 404/401 | Permitido | 404 | Admin |
| API | 401 JSON | Solo suyas | Solo suyas | Solo suyas |
| Imagen de A | 401/404 | Permitido | 404 | Admin |
| `/admin/` | Login | Denegado | Denegado | Permitido |
| Logout | No aplica | POST + CSRF | POST + CSRF | POST + CSRF |

### 5.3 Cambios de seguridad

- Añadir `login_required` a vistas y un decorador JSON para API.
- Filtrar siempre por `request.user`; eliminar `Q(user__isnull=True)`.
- Usar `get_object_or_404` con queryset filtrado.
- Asignar tareas huérfanas solo con propietario aprobado y trazable (`assign_orphan_tasks --owner ... --dry-run`); migrar `user` a `null=False` después de verificar.
- Actualizar `seed_data.py` para exigir propietario.
- Eliminar `csrf_exempt`; API con `X-CSRFToken`.
- Logout `@require_POST` y formulario CSRF.
- Proteger multimedia y retirar mapping público `/media/`.
- Rotar `SECRET_KEY`.
- Endurecer producción: `DEBUG=False`, hosts exactos, `CSRF_TRUSTED_ORIGINS`, cookies seguras, `nosniff`, `X-Frame-Options`, referrer policy, HTTPS.
- Validar imágenes: tamaño máximo, JPEG/PNG/WebP, verificación Pillow, re-codificación, límite de píxeles, UUID, permisos, sin SVG/HTML.
- Usar transacciones y borrar archivos antiguos tras commit.
- Implementar `cleanup_orphan_media --dry-run`.
- SQLite con timeout, evaluación de WAL y operaciones cortas.
- Logging de seguridad y errores sin secretos.
- Páginas 400/403/404/500.

### 5.4 Política de tareas huérfanas y migración de datos

1. **Inventario:** listar tareas con `user IS NULL`; incluir ID, título, fecha, estado e imagen; no modificar.
2. **Propuesta:** el responsable funcional propone un propietario por tarea o un criterio de asignación.
3. **Aprobación:** el propietario del proyecto aprueba explícitamente la lista o el criterio, con referencia trazable (ticket, correo o registro). Sin aprobación no se migra.
4. **Backup:** backup verificado antes de cualquier escritura.
5. **Dry-run:** ejecutar `assign_orphan_tasks --owner <usuario> --dry-run` y revisar el resultado.
6. **Asignación:** ejecutar sin dry-run solo con la aprobación y el backup.
7. **Verificación:** confirmar cero tareas huérfanas y conteos correctos.
8. **Código estricto:** desplegar `null=False` solo después de la asignación verificada.
9. **Post-check:** probar aislamiento; si falla, rollback según 6.8.

No asignar automáticamente a admin, staff, al primer usuario ni a una tarea genérica. La aprobación del propietario debe quedar registrada antes de ejecutar la migración.

---

## 6. PythonAnywhere

### 6.1 Restricciones y capacidades de PythonAnywhere (pendientes de verificación)

Los datos de esta sección son referencias públicas, no garantías permanentes. Deben verificarse en la cuenta real antes de F0.2 y F6: plan contratado, cuotas, herramientas, almacenamiento, sistema operativo, versión de Python, dominio, SSH/SFTP, tareas programadas, workers, consolas, CPU y límites de backup. Si difieren, el plan y la aceptación de riesgos se actualizan.

| Capacidad / restricción | Referencia pública | Estado real |
|---|---|---|
| Plan contratado y cuotas | Free: 1 web app, 1 worker, 2 consolas, 512 MB, 100 CPU-s/día | Pendiente de verificación |
| SSH/SFTP y tareas programadas | No disponibles en Free, según referencia | Pendiente de verificación |
| Dominio | `<usuario>.pythonanywhere.com`; dominio propio requiere pago | Pendiente de verificación |
| Sistema operativo y Python | Varía por cuenta/imagen | Pendiente de verificación |
| WSGI | `/var/www/<usuario>_pythonanywhere_com_wsgi.py` | Pendiente de verificación |
| Git por HTTPS | Permitido; repositorio privado requiere token de solo lectura | Pendiente de verificación |
| Herramientas | `sqlite3`, `tar`, `gpg` u `openssl`, `sha256sum`, `git`, activación de venv | Pendiente de verificación |
| Almacenamiento de backups | Espacio libre y posibilidad de descarga externa | Pendiente de verificación |
| `media/` | Existencia, tamaño y permisos | Pendiente de verificación |
| HTTPS / Force HTTPS | Disponible según referencia | Pendiente de verificación |
| SQLite | Disponible, pero no recomendado para producción según referencia | Pendiente de verificación |

No se asume ninguna cuota, herramienta ni capacidad como garantía hasta verificarla en la cuenta real.

### 6.2 Free vs. pago (condicionado a verificación)

Con la información pública disponible, las funciones actuales no requieren plan de pago. Esto debe confirmarse en la cuenta real antes de aceptar el riesgo. Dominio propio, SSH/SFTP, más workers, tareas programadas o MySQL pueden requerir pago. El nombre TaskPilot no cambia la URL gratuita según la referencia pública, pero la URL y el dominio deben verificarse.

### 6.3 Estructura de despliegue propuesta

```text
/home/<usuario>/apps/taskpilot/
├── releases/
│   └── <timestamp>/
└── current -> releases/<timestamp>

/home/<usuario>/apps/taskpilot-data/
├── db.sqlite3
└── media/

/home/<usuario>/apps/taskpilot-static/
```

- Datos fuera de las releases para no perderlos al desplegar.
- `DATA_DIR` y `STATIC_ROOT` por variable de entorno.
- WSGI apunta a `current`.
- Estáticos en ruta fija.
- Multimedia privada sin mapping público.
- Las rutas, mappings y permisos reales deben verificarse en la cuenta antes de F6; esta estructura es una propuesta.

### 6.4 Respaldo (requiere G0-B)

No ejecutar este procedimiento sin autorización explícita de backup. Si el backup es de producción, indicar ventana y alcance. El backup es una escritura: crea archivos y consume almacenamiento, aunque no modifica la aplicación ni la base. Los comandos siguientes son una plantilla: adaptar rutas y mecanismo de virtualenv a lo verificado en la cuenta. No guardar la passphrase de cifrado en el backup, el repositorio ni la documentación. Ajustar `OLD`, la ruta del WSGI y el virtualenv a los valores reales verificados; no asumir `todo_django_mongodb` ni `todo-env` después de un renombrado.

#### 6.4.1 Preflight de herramientas y alcance

Verificar en la cuenta real antes de depender de ellas:

- `sqlite3`, `tar`, `sha256sum` y `git`.
- `gpg` u `openssl` para cifrar `.env`.
- Mecanismo real de activación del virtualenv (`workon`, ruta absoluta o `source`).
- Existencia de `db.sqlite3`, `.env` y WSGI; presencia o ausencia de `media/`.
- Espacio libre suficiente para el backup y la copia externa.

```bash
set -euo pipefail

for t in sqlite3 tar sha256sum git; do
  command -v "$t" >/dev/null 2>&1 || { echo "FALTA: $t"; exit 1; }
done

if command -v gpg >/dev/null 2>&1; then
  ENC="gpg"
elif command -v openssl >/dev/null 2>&1; then
  ENC="openssl"
else
  echo "FALTA: gpg u openssl para cifrar .env"
  exit 1
fi

OLD="$HOME/todo_django_mongodb"
[ -f "$OLD/db.sqlite3" ] || { echo "FALTA: db.sqlite3"; exit 1; }
[ -f "$OLD/.env" ] || { echo "FALTA: .env"; exit 1; }
# Verificar el mecanismo real del virtualenv antes de usarlo.
```

Los bloques 6.4.2 y 6.4.3 reutilizan `OLD`, `ENC` y `BK`; ejecutarlos en la misma sesión o exportar esas variables.

#### 6.4.2 Copia y verificación

```bash
set -euo pipefail

STAMP=$(date +%Y%m%d-%H%M%S)
BK="$HOME/backups/$STAMP"
mkdir -p "$BK"

# Base SQLite: copia consistente y verificación.
sqlite3 "$OLD/db.sqlite3" ".backup '$BK/db.sqlite3'"
sqlite3 "$BK/db.sqlite3" 'PRAGMA integrity_check;' | tee "$BK/db-integrity.txt"
grep -qx 'ok' "$BK/db-integrity.txt" || { echo "ERROR: integrity_check no devolvió ok"; exit 1; }

# Multimedia: puede no existir.
if [ -d "$OLD/media" ]; then
  tar -czf "$BK/media.tar.gz" -C "$OLD" media
  tar -tzf "$BK/media.tar.gz" >/dev/null
  echo "media=presente" > "$BK/media-status.txt"
else
  echo "media=ausente" > "$BK/media-status.txt"
fi

# .env: cifrado desde el origen; no crear copia externa en claro.
if [ "$ENC" = "gpg" ]; then
  gpg --symmetric --cipher-algo AES256 --output "$BK/env.backup.gpg" "$OLD/.env"
else
  openssl enc -aes-256-cbc -pbkdf2 -salt -in "$OLD/.env" -out "$BK/env.backup.enc"
fi

cp "/var/www/<usuario>_pythonanywhere_com_wsgi.py" "$BK/wsgi.py"
git -C "$OLD" rev-parse HEAD > "$BK/commit.txt"

# pip freeze: usar el virtualenv real, por ejemplo:
# "$HOME/.virtualenvs/todo-env/bin/pip" freeze > "$BK/pip-freeze.txt"

sha256sum "$BK"/* > "$BK/SHA256SUMS"
sha256sum -c "$BK/SHA256SUMS"
```

- La copia externa del `.env` es el archivo cifrado (`.gpg` o `.enc`); no descargar el `.env` original.
- Descargar también `SHA256SUMS` y verificar el checksum después de la descarga.
- El backup no es válido hasta que pase la prueba de restauración.

#### 6.4.3 Prueba de restauración

```bash
set -euo pipefail

TMP=$(mktemp -d)
sqlite3 "$BK/db.sqlite3" ".backup '$TMP/db.sqlite3'"
sqlite3 "$TMP/db.sqlite3" 'PRAGMA integrity_check;' | grep -qx 'ok'
if [ -f "$BK/media.tar.gz" ]; then
  tar -tzf "$BK/media.tar.gz" >/dev/null
fi

if [ "$ENC" = "gpg" ]; then
  gpg --decrypt "$BK/env.backup.gpg" >/dev/null
else
  openssl enc -d -aes-256-cbc -pbkdf2 -in "$BK/env.backup.enc" -out /dev/null
fi

rm -rf "$TMP"
```

- No imprimir el contenido de `.env`.
- Comparar conteos de tablas críticas entre producción y la restauración cuando sea posible.
- Registrar fecha, responsable, resultado y ubicación del backup.

### 6.5 Restauración y rollback de datos (requiere autorización de producción)

1. Declarar mantenimiento y detener escrituras.
2. Si la versión nueva recibió escrituras, exportar o identificar los datos nuevos antes de tocar la base (ver 6.8).
3. Verificar checksums y `PRAGMA integrity_check` del backup.
4. Descifrar `.env` solo a un archivo temporal con permisos `600` o al destino final; nunca imprimir valores.
5. Restaurar SQLite a un archivo temporal, verificar integridad y conteos; luego sustituir con la aplicación detenida.
6. Restaurar `media/` si el backup lo contiene; si no, registrar la ausencia.
7. Restaurar WSGI y `.env`; activar el virtualenv antiguo.
8. Migrar solo si el esquema es compatible.
9. `collectstatic` y recargar.
10. Verificar login, tareas, imágenes, conteos y logs.
11. Reconciliar datos nuevos según 6.8 y registrar el resultado.

### 6.6 Despliegue limpio

1. Preflight: código, pruebas, backup verificado, prueba de restauración, ventana y rollback con datos nuevos.
2. Crear release nueva y virtualenv.
3. Instalar dependencias y `pip check`.
4. Copiar `.env` desde una fuente segura, con permisos `600`; quitar claves Mongo; ajustar producción; no versionarlo.
5. Copiar base con `.backup` al nuevo `DATA_DIR`; no mover la original.
6. Copiar multimedia preservando permisos; si no existe, registrar la ausencia.
7. Verificar integridad y conteos.
8. `manage.py check`, `migrate --plan`, `migrate`, `collectstatic`.
9. Configurar WSGI y pestaña Web: source, working dir, venv, estáticos, HTTPS.
10. Recargar.
11. Ejecutar matriz de verificación.
12. Mantener release anterior y backup.
13. Registrar el punto de escritura de la nueva versión y el plan de reconciliación por si se requiere rollback.
14. Limpiar solo tras periodo de estabilidad y retención.

### 6.7 Verificación

- Login/registro, CRUD, filtros, estadísticas, imágenes y admin.
- Anónimo redirigido; API 401.
- Usuario A no accede a B; imágenes privadas.
- CSRF ausente → 403; logout GET → 405.
- `/.env` y `/db.sqlite3` → 404.
- `DEBUG=False`; errores sin trazas.
- HTTPS y cookies seguras.
- Conteos e integridad SQLite correctos.
- Backup externo cifrado, checksum verificado y prueba de restauración documentada.
- Rollback con datos nuevos documentado y, si es posible, ensayado.
- Logs sin errores 500 repetidos.
- `check --deploy` y `showmigrations` correctos.

### 6.8 Rollback y datos nuevos

Conservar WSGI anterior, release anterior, venv, mappings, commit, base y multimedia. No borrar nada hasta estabilizar.

Antes de restaurar:

- Si la versión nueva no recibió escrituras: rollback directo a la release anterior y, si el esquema no es compatible, restaurar la base del backup.
- Si recibió escrituras: congelar escrituras, exportar los registros nuevos o un diff y decidir explícitamente:
  - **forward-fix** si el esquema es compatible;
  - restaurar la base anterior y reimportar o reconciliar los datos nuevos tras validar compatibilidad;
  - mantener la base nueva y revertir solo el código si el esquema es compatible.
- No restaurar la base anterior sobre datos nuevos sin aprobación y sin registrar la posible pérdida.
- Documentar decisión, responsable, conteos, evidencia y datos reconciliados.

Después del rollback: restaurar mappings, recargar y verificar login, tareas, imágenes y logs.

### 6.9 Limpieza

Tras 7–30 días: eliminar releases y venv antiguos, conservar backups según retención y no borrar web app, dominio, base principal, multimedia ni `.env` de producción. No eliminar backups antes de la retención aprobada ni sin una prueba de restauración vigente.

---

## 7. Documentación y estructura

### 7.1 Documentos

| Archivo | Contenido |
|---|---|
| `README.md` | Producto, características, stack, instalación, comandos, enlaces |
| `ARCHITECTURE.md` | Diagramas, capas, modelo, auth, API, medios, SQLite/PA, ADRs |
| `SECURITY.md` | Amenazas, authz, CSRF, IDOR, uploads, secretos, cabeceras, incidentes |
| `DEPLOYMENT.md` | Inventario, backup, deploy, WSGI, env, migraciones, verificación y rollback |
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
│   ├── settings/{__init__,base,dev,prod}.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── todos/
│   ├── models.py
│   ├── forms.py
│   ├── validators.py
│   ├── services.py
│   ├── selectors.py
│   ├── views/{__init__,web,auth,api}.py
│   ├── urls.py
│   ├── admin.py
│   ├── management/commands/
│   ├── migrations/
│   └── tests/
├── templates/{todos,errors}/
├── static/
├── docs/adr/
└── .github/workflows/ci.yml
```

Eliminar `todos/db.py`; sustituir `PYTHONANYWHERE_DEPLOY.md` por `DEPLOYMENT.md`.

Dependencias de producción: Django, Pillow y python-dotenv, con versiones fijadas. Mongo fuera. Desarrollo opcional: `coverage`, `ruff`. Sin DRF, Celery, Redis, Sentry ni servicios externos sin aprobación.

### 7.3 Credenciales

Documentar ubicación y rotación, nunca valores: GitHub (cuenta, 2FA, PAT/SSH), PythonAnywhere (cuenta, 2FA, Web, WSGI, venv, API token), `.env` (permisos 600, gestor de secretos), SQLite (archivo, backups), dominio/WSGI y backups cifrados. No incluir secretos en Markdown, Git, logs ni chat.

---

## 8. Fases de ejecución

El orden prioriza la seguridad: F1 corrige autenticación, autorización y exposición de datos antes de F2 (identidad y limpieza de MongoDB). La numeración de gates sigue el orden de ejecución: G1 corresponde a F1 (seguridad) y G2 a F2 (identidad).

### 8.1 F0 — Operaciones separadas y autorizaciones

| Operación | Tipo | Escribe | Autorización | No autoriza |
|---|---|---|---|---|
| F0.1 Inventario | Solo lectura | No | G0 | Backup, tag, bundle, código, Git, GitHub o producción |
| F0.2 Backup | Escritura de respaldo | Archivos de backup y almacenamiento | G0-B; indicar alcance local, producción o ambos | Tag, bundle, cambios de app/base o deploy |
| F0.3 Tag local | Escritura local de Git | Ref local | G0-T | Push, bundle, renombrado o deploy |
| F0.4 Bundle local | Escritura local de Git | Archivo bundle | G0-U | Push, tag, renombrado o deploy |

G0 no autoriza automáticamente backup, tag ni bundle. Cada operación de escritura requiere una autorización separada y registrada. El backup de producción requiere además ventana y confirmación de producción.

### 8.2 Fases

| Fase | Gate | Objetivo y cambios | Depende | Pruebas / aceptación | Impacto |
|---|---|---|---|---|---|
| **F0** | G0; G0-B/T/U según se autoricen | Gobernanza: inventario de solo lectura, backup autorizado, baseline y decisiones. Tag/bundle solo con G0-T/G0-U. | — | Inventario completo; si G0-B se autoriza, backup con checksums, integridad y restauración probada; autorizaciones registradas. | Escritura de respaldo y consumo de almacenamiento; tag/bundle son escrituras locales de Git; no modifica la aplicación ni la base. |
| **F1** | G1 | Seguridad I: login obligatorio, propiedad estricta, 404, CSRF, logout POST, API 401, multimedia privada, settings seguros, rotación de clave. | F0.1 y F0.2 | Matriz anónimo/A/B, IDOR, CSRF, imágenes, `check --deploy`. | Alto: mantenimiento, datos y mappings. |
| **F2** | G2 | Identidad TaskPilot: renombrar repo/carpeta, quitar MongoDB y dependencias, actualizar docs/marca, fijar versiones. | F1 aceptada; F0.3/F0.4 si se autorizan | Cero refs Mongo, `check`, tests, `makemigrations --check`. | Rutas PA/WSGI; coordinar F6. |
| **F3** | G3 | Seguridad II: formularios/JSON, uploads, transacciones, huérfanos, errores, logging, SQLite. | F1 | Entradas inválidas, imágenes, transacciones, errores, integridad. | Medio: migraciones y backup. |
| **F4** | G4 | Seguridad III/Calidad: módulos, API versionada, paginación, tests, cobertura, lint, correcciones JS/fechas. | F1 y F3 | Suite verde, cobertura ≥80 % crítico, API documentada. | Bajo. |
| **F5** | G5 | Documentación completa, ADRs, entorno, runbook y changelog. | F1–F4 | Comandos reproducibles, sin secretos, enlaces válidos. | Ninguno. |
| **F6** | G6 | Despliegue PA: backup, release paralela, venv, env, datos, migraciones, estáticos, WSGI, verificación. | F0–F5 | Matriz funcional/seguridad/datos, rollback con datos nuevos. | Alto: producción. |
| **F7** | G7 | Cierre: rotación final, 2FA, backups, monitoreo, retención, tag `v1.0.0`, limpieza. | F6 + estabilidad | Operación estable, backup verificado. | Bajo. |

**Ruta crítica:** F0 → F1 → F2 → F3 → F4 → F5 → F6 → F7.
**Ruta crítica de seguridad:** F0 → F1 → F3 → F6.
**Nota de prioridad:** F2 (identidad y MongoDB) no bloquea F1 ni F3; la corrección de acceso anónimo, autorización y multimedia pública se ejecuta primero.

---

## 9. Clasificación de comandos y operaciones

| Categoría | Ejemplos | Estado actual |
|---|---|---|
| **Solo lectura** | Inventario F0.1, `git status`, `git log`, `git remote -v`, `git ls-remote`, `ls`, `du`, `pip freeze`, `sqlite3 ... PRAGMA integrity_check`, `SELECT count(*)`, `manage.py check`, `showmigrations`, leer archivos y `curl` GET | Permitido solo con alcance autorizado; no incluye backup |
| **Cambios locales** | Crear/editar archivos, backup local, instalar dependencias, ejecutar pruebas, migraciones locales, `collectstatic`, renombrar carpeta, commits, tags, ramas, bundles | Requiere gate específico: G0-B backup, G0-T tag, G0-U bundle, G1 seguridad, G2 identidad, etc. |
| **Cambios en GitHub** | Renombrar repositorio, push, tags, ramas, configuración, tokens, branch protection | Requiere G2 o gate de GitHub explícito; G0-T/G0-U no autorizan push |
| **Cambios en producción** | Backup de producción, crear release, venv, `pip install`, `.env`, migraciones, copia de base/media, WSGI, mappings, reload, limpieza | Requiere G0-B si es backup y G6/G7 para deploy/limpieza; ventana obligatoria |

La creación y corrección de `MASTER_PLAN.md` no autoriza ninguna de estas operaciones. No se ejecutaron backups, tags, bundles, migraciones, Git, GitHub ni PythonAnywhere.

---

## Approval Gates

La numeración de gates sigue el orden cronológico de ejecución: G1 corresponde a F1 (seguridad) y G2 a F2 (identidad TaskPilot y limpieza MongoDB).

| Gate | Autorización explícita necesaria | Autoriza | No autoriza | Evidencia previa |
|---|---|---|---|---|
| **G0** | Aprobar este plan maestro y el orden de fases | F0.1: inventario de solo lectura y revisión | Backup, tag, bundle, código, Git, GitHub o producción | Plan revisado |
| **G0-B** | Autorizar backup y especificar alcance (local, producción o ambos) | F0.2: crear backups, checksums, cifrado de `.env` y prueba de restauración | Tag, bundle, cambios de app/base o deploy | G0, alcance definido y ventana si es producción |
| **G0-T** | Autorizar tag local | F0.3: crear tag local | Push, bundle, renombrado o deploy | G0 y árbol limpio |
| **G0-U** | Autorizar bundle local | F0.4: crear bundle local | Push, tag, renombrado o deploy | G0 y árbol limpio |
| **G1** | Aprobar F1: seguridad de autenticación y autorización | Código auth/authz, CSRF, multimedia privada, migraciones locales y pruebas | Producción | F0.1/F0.2 y diseño de autorización, datos y huérfanas aprobado |
| **G2** | Aprobar F2: identidad TaskPilot y limpieza MongoDB | Renombrar local/GitHub, quitar Mongo, actualizar marca/docs, commits y push | Producción | F1 aceptada, backup verificado y repo limpio |
| **G3** | Aprobar F3: robustez | Validación, uploads, transacciones, errores, logging y migraciones locales | Producción | F1 aceptada |
| **G4** | Aprobar F4: calidad | Refactor, API, pruebas, lint y cobertura | Producción | F1 y F3 aceptadas |
| **G5** | Aprobar F5: documentación | Documentación y ADRs | Producción | F1–F4 |
| **G6** | Aprobar ventana de producción | Backup de producción, deploy, migraciones, mappings, reload y rollback ensayado | Limpieza definitiva | F5, backup verificado y rollback con datos nuevos documentado |
| **G7** | Aprobar cierre y limpieza | Rotación final, tag `v1.0.0`, push de tag y eliminación de releases antiguas | Borrar datos, dominio o backups dentro de retención | Estabilidad y backups verificados |

G0 **no** autoriza backup, tag ni bundle. G0-B, G0-T y G0-U son autorizaciones independientes y deben registrarse por separado. La aprobación del diseño **no** equivale a autorización de implementación. Cada gate requiere confirmación explícita y separada.

---

## 10. Riesgos y criterios globales

### 10.1 Riesgos

| Riesgo | Mitigación |
|---|---|
| Pérdida de datos al cambiar ruta de base | `DATA_DIR` fuera de releases, backup y verificación |
| Acceso cruzado entre usuarios | Tests de autorización, filtros por propietario y 404 |
| Imágenes públicas | Sin mapping `/media/`; `FileResponse` autenticado |
| Bloqueo SQLite | Timeout, un solo worker cuando la cuenta lo permita, transacciones cortas, WAL evaluado |
| Migración irreversible | Backup, plan y restauración documentada |
| Renombrado rompe WSGI/rutas | Checklist de PA y release paralela |
| Secreto expuesto | Rotación, `.env` 600, escaneo y 2FA |
| API rota | Versionado y pruebas de contrato |
| Disco lleno o cuota distinta a la esperada | Verificar cuota real; retención y monitoreo |
| Supuestos de PythonAnywhere no verificados | Verificar plan, cuotas, herramientas, almacenamiento y dominio en la cuenta real antes de F0.2/F6 |
| Backup no restaurable | Checksums, `integrity_check`, prueba de restauración y registro |
| Herramientas de backup ausentes | Preflight; alternativas GPG/OpenSSL y rutas reales de venv |
| Rollback pierde escrituras nuevas | Congelar escrituras, exportar/diff, forward-fix o reconciliación aprobada |
| Tag/bundle sin autorización | G0-T/G0-U separados; G0 no los autoriza |
| Migración de huérfanas sin propietario | Propietario aprobado y trazable antes de migrar |
| Pérdida de historial Git | Renombrar, no recrear; no force push |

### 10.2 Criterios globales de aceptación

- Sin acceso anónimo salvo login/registro.
- Sin acceso cruzado entre usuarios.
- CSRF en todas las escrituras; logout POST.
- Multimedia privada y uploads validados.
- Sin secretos en repo, historial, docs ni logs.
- `DEBUG=False`, hosts exactos y HTTPS en producción.
- Cero referencias y dependencias MongoDB.
- Cuotas, herramientas y capacidades de PythonAnywhere verificadas en la cuenta real.
- Backup con checksums, integridad y restauración probada; `.env` externo cifrado.
- Conteos de datos coincidentes e integridad SQLite correcta.
- Pruebas de autorización, CSRF, uploads y API en verde.
- Cobertura crítica ≥ 80 %.
- `check --deploy` sin advertencias críticas.
- Documentación completa y sin credenciales.
- Rollback documentado, con política para datos nuevos y, si es posible, ensayado.
- Tareas huérfanas asignadas solo con propietario aprobado y trazable.
- F0: G0 no autoriza backup, tag ni bundle; cada escritura tiene gate propio.
- F1 (seguridad) ejecutada antes de F2 (identidad).
- Sin servicios de pago; SQLite y plan gratuito aceptados solo después de verificar cuotas y riesgos.

### 10.3 No-go

No se cierra la modernización si hay acceso cruzado, secreto expuesto, backup sin prueba de restauración, rollback sin tratamiento de datos nuevos, migración de huérfanas sin propietario aprobado, `DEBUG=True`, multimedia privada pública, diferencias de datos inexplicadas, errores 500 repetidos, uso de cuotas o capacidades de PythonAnywhere no verificadas como garantía, o tag/bundle creado sin G0-T/G0-U.

---

## 11. Próximo paso

Revisar y aprobar este documento y las decisiones pendientes de la sección 3.3. G0 solo habilita F0.1 (inventario de solo lectura). Backup, tag y bundle requieren G0-B, G0-T y G0-U, respectivamente. La primera fase de implementación es F1 (seguridad, G1), antes de F2 (identidad, G2). Ninguna aprobación de este plan autoriza por sí sola cambios en código, Git, GitHub o PythonAnywhere.
