# Runbook de Operación y Mantenimiento — TaskPilot

Este runbook detalla los procedimientos operativos, diagnóstico de incidencias, rutinas de mantenimiento y recuperación de desastres para **TaskPilot** en **PythonAnywhere**.

---

## 1. Monitoreo de Salud y Logs

PythonAnywhere genera tres archivos de registro clave en `/var/log/`:
- **Log de errores de la aplicación:**
  `/var/log/<usuario>.pythonanywhere.com.error.log`
  *(Revisar cuando ocurran errores 500 o fallos al iniciar la aplicación).*
- **Log del servidor WSGI:**
  `/var/log/<usuario>.pythonanywhere.com.server.log`
  *(Contiene trazas del ciclo de vida de los workers y reinicios).*
- **Log de acceso HTTP:**
  `/var/log/<usuario>.pythonanywhere.com.access.log`
  *(Muestra las peticiones entrantes, códigos HTTP y tiempos de respuesta).*

### Comando para inspección rápida en tiempo real:
```bash
tail -n 100 -f /var/log/<usuario>.pythonanywhere.com.error.log
```

---

## 2. Rutina de Recarga de la Aplicación

Ante cualquier actualización de código, dependencias o variables de entorno:
1. Ir a la pestaña **Web** del panel de PythonAnywhere.
2. Hacer clic en el botón verde **"Reload <usuario>.pythonanywhere.com"**.
3. O mediante comando en consola (tocando el archivo WSGI):
   ```bash
   touch /var/www/<usuario>_pythonanywhere_com_wsgi.py
   ```

---

## 3. Procedimiento de Respaldo y Restauración de Datos

Los datos mutables residen exclusivamente en `/home/<usuario>/taskpilot-data/`.

### 3.1 Creación de Respaldo Manual

Realizar el respaldo durante una ventana controlada, evitando escrituras concurrentes para mantener coherencia entre la base de datos y los archivos multimedia.

```bash
set -e

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_DIR="/home/<usuario>/backups/$TIMESTAMP"
DATA_DIR="/home/<usuario>/taskpilot-data"

# No reutilizar una carpeta de respaldo existente.
mkdir "$BACKUP_DIR"

# 1. Respaldar SQLite mediante el mecanismo de backup de SQLite.
sqlite3 "$DATA_DIR/db.sqlite3" ".backup '$BACKUP_DIR/db.sqlite3'"

# 2. Respaldar el directorio multimedia.
tar -czf "$BACKUP_DIR/media.tar.gz" -C "$DATA_DIR" media

# 3. Generar sumas de verificación.
cd "$BACKUP_DIR"
sha256sum db.sqlite3 media.tar.gz > SHA256SUMS

echo "Respaldo generado en: $BACKUP_DIR"
```

Conservar juntos `db.sqlite3`, `media.tar.gz` y `SHA256SUMS`. Representan un mismo punto de recuperación y deben restaurarse como un conjunto.

### 3.2 Restauración de Respaldo

> **Precaución:** este procedimiento reemplaza la base de datos y el directorio multimedia actuales. Ejecutarlo únicamente durante una ventana de mantenimiento, sin escrituras concurrentes y después de confirmar que se dispone de un respaldo reciente del estado actual.

1. Definir las rutas del respaldo y preparar un directorio temporal:

   ```bash
   set -e

   TIMESTAMP="<TIMESTAMP_DEL_RESPALDO>"
   BACKUP_DIR="/home/<usuario>/backups/$TIMESTAMP"
   DATA_DIR="/home/<usuario>/taskpilot-data"
   RESTORE_DIR="$DATA_DIR/.restore-$TIMESTAMP"
   DB_PREVIOUS="$DATA_DIR/db.pre-restore-$TIMESTAMP.sqlite3"
   MEDIA_PREVIOUS="$DATA_DIR/media.pre-restore-$TIMESTAMP"

   test -f "$BACKUP_DIR/db.sqlite3"
   test -f "$BACKUP_DIR/media.tar.gz"
   test -f "$BACKUP_DIR/SHA256SUMS"
   test -f "$DATA_DIR/db.sqlite3"
   test -d "$DATA_DIR/media"

   test ! -e "$RESTORE_DIR"
   test ! -e "$DB_PREVIOUS"
   test ! -e "$MEDIA_PREVIOUS"

   mkdir "$RESTORE_DIR"
   ```

2. Verificar el respaldo antes de reemplazar datos:

   ```bash
   cd "$BACKUP_DIR"
   sha256sum -c SHA256SUMS

   sqlite3 "$BACKUP_DIR/db.sqlite3" "PRAGMA integrity_check;"
   tar -tzf "$BACKUP_DIR/media.tar.gz" > /dev/null
   ```

   La comprobación de SQLite debe devolver `ok`. Si falla alguna verificación, detenerse.

3. Preparar y validar la restauración en el directorio temporal:

   ```bash
   sqlite3 "$BACKUP_DIR/db.sqlite3" ".backup '$RESTORE_DIR/db.sqlite3'"
   sqlite3 "$RESTORE_DIR/db.sqlite3" "PRAGMA integrity_check;"

   tar -xzf "$BACKUP_DIR/media.tar.gz" -C "$RESTORE_DIR"
   test -d "$RESTORE_DIR/media"
   ```

   La segunda comprobación de SQLite también debe devolver `ok`.

4. Crear un respaldo reciente del estado actual siguiendo la sección 3.1. No omitir este paso.

5. Sustituir la base y los archivos multimedia conservando temporalmente las versiones anteriores:

   ```bash
   mv "$DATA_DIR/db.sqlite3" "$DB_PREVIOUS"
   mv "$RESTORE_DIR/db.sqlite3" "$DATA_DIR/db.sqlite3"

   mv "$DATA_DIR/media" "$MEDIA_PREVIOUS"
   mv "$RESTORE_DIR/media" "$DATA_DIR/media"
   ```

   Los directorios temporales y las versiones anteriores deben permanecer disponibles hasta completar las verificaciones posteriores. Si algún comando `mv` falla, detener el procedimiento y no recargar la aplicación hasta recuperar un estado coherente.

6. Recargar la aplicación desde la pestaña **Web** de PythonAnywhere y comprobar su funcionamiento, los registros y la correspondencia entre tareas e imágenes.

7. Conservar `DB_PREVIOUS` y `MEDIA_PREVIOUS` hasta confirmar que la restauración fue satisfactoria. Eliminarlos posteriormente sólo mediante un procedimiento de limpieza autorizado.

No extraer el archivo multimedia directamente encima del directorio activo: eso puede dejar archivos nuevos que no existían en el respaldo. Tampoco restaurar SQLite como parte automática de un rollback de código.

---
---

## 4. Diagnóstico y Resolución de Incidencias Frecuentes

### A. Error 502 Bad Gateway
- **Causa común:** El archivo WSGI contiene un error de sintaxis, no encuentra el virtualenv o falla al importar `config.settings`.
- **Diagnóstico:** Consultar `/var/log/<usuario>.pythonanywhere.com.error.log`.
- **Solución:**
  1. Verificar que el virtualenv en la pestaña Web sea `/home/<usuario>/.virtualenvs/taskpilot-env`.
  2. Verificar que `pythonanywhere_wsgi.py` tenga configurado el `path` correcto (`/home/<usuario>/taskpilot`).

### B. Error "OperationalError: database is locked"
- **Causa común:** Concurrencia sobre SQLite en el sistema de archivos de red o transacción prolongada.
- **Diagnóstico:** Ocurre si múltiples peticiones intentan escribir simultáneamente durante más del timeout configurado.
- **Solución:**
  1. Confirmar que `OPTIONS: {"timeout": 20}` esté activo en `config/settings.py`.
  2. Evitar transacciones largas o scripts en consola bloqueando la base viva.
  3. Ejecutar verificación de integridad:
     ```bash
     sqlite3 /home/<usuario>/taskpilot-data/db.sqlite3 "PRAGMA integrity_check;"
     ```

### C. Alerta de Cuota de Disco
- **Causa:** Acumulación de logs antiguos o imágenes subidas.
- **Diagnóstico:**
  ```bash
  du -sh /home/<usuario>/taskpilot-data/* /var/log/*
  ```
- **Solución:**
  1. Vaciar o truncar archivos de logs antiguos en `/var/log/` (e.g., `> /var/log/<usuario>.pythonanywhere.com.access.log`).
  2. Purgar respaldos caducados respetando la política de retención.

### D. Estáticos no se visualizan (CSS/Iconos rotos)
- **Causa:** No se ejecutó `collectstatic` tras actualizar plantillas o estáticos.
- **Solución:**
  ```bash
  cd /home/<usuario>/taskpilot
  python manage.py collectstatic --noinput
  ```
  Verificar que el mapeo en la pestaña Web sea `/static/` → `/home/<usuario>/taskpilot/staticfiles`.
