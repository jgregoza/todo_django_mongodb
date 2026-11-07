# Política y Arquitectura de Seguridad — TaskPilot

TaskPilot adopta una postura de seguridad restrictiva (*Secure by Default*), aplicando el principio de mínimo privilegio, denegación por defecto y aislamiento estricto de datos entre usuarios.

---

## 1. Matriz de Autorización

| Recurso / Acción | Usuario Anónimo | Usuario Propietario (A) | Usuario Tercero (B) | Administrador / Staff |
|---|---|---|---|---|
| **Página principal (`/`)** | Redirige a `/login/` (`302`) | Acceso a sus tareas | Acceso a sus tareas | Acceso a sus tareas |
| **Crear tarea** | Redirige a `/login/` (`302`) | Permitido (asigna a A) | Permitido (asigna a B) | Permitido |
| **Ver / Editar / Borrar tarea de A** | `302` al login | Permitido | `404 Not Found` | Permitido en `/admin/` |
| **API `GET /api/v1/todos/`** | `401 JSON` | Solo tareas de A | Solo tareas de B | Solo tareas propias |
| **API mutaciones sobre tarea de A** | `401 JSON` / `403` (CSRF) | Permitido | `404 Not Found` | `404 Not Found` (vía API) |
| **Imagen de tarea de A** | Redirige a `/login/` (`302`) | `200 OK` (descarga segura) | `404 Not Found` | `200 OK` |
| **Panel Admin (`/admin/`)** | Redirige a login admin | Denegado (`403`/redirect) | Denegado (`403`/redirect) | Permitido |
| **Cierre de sesión (`/logout/`)** | No aplica | `POST` + CSRF obligatorio | `POST` + CSRF obligatorio | `POST` + CSRF obligatorio |

---

## 2. Medidas de Seguridad Implementadas

### 2.1 Aislamiento Estricto y Prevención de IDOR / BOLA
- Cada consulta en `todos/selectors.py` se filtra forzosamente por `user=request.user`.
- No existen consultas globales o tareas sin propietario.
- Al solicitar o intentar modificar una tarea ajena, el sistema devuelve `404 Not Found` en lugar de `403 Forbidden`, evitando la enumeración de IDs válidos o la revelación de existencia de datos de otros usuarios.

### 2.2 Protección contra Falsificación de Peticiones (CSRF)
- `CsrfViewMiddleware` habilitado globalmente para formularios web y endpoints API.
- Directiva `@csrf_exempt` eliminada de todos los endpoints de la API.
- Peticiones AJAX y llamadas a la API deben incluir el encabezado `X-CSRFToken`. Peticiones sin token son rechazadas con `403 Forbidden` antes de llegar a la lógica de negocio.

### 2.3 Privacidad de Archivos Multimedia
- Eliminación del servicio estático directo de `/media/` en `config/urls.py` y en la configuración web de producción.
- Las imágenes se sirven exclusivamente a través de la vista protegida `todo_image` (`todos/<int:todo_id>/image/`), la cual valida la sesión del usuario y la propiedad de la tarea antes de transmitir bytes mediante `FileResponse`.

### 2.4 Validación de Archivos y Prevención de Carga Maliciosa
- **Límite de tamaño:** Rechazo de archivos superiores a 5 MB (`validate_task_image`).
- **Verificación real de contenido:** Inspección del archivo mediante Pillow (`Image.verify()`) para garantizar que sea una imagen válida y no un ejecutable o script malicioso camuflado con extensión de imagen.
- **Lista blanca de formatos:** Exclusivamente `JPEG`, `PNG`, `WEBP` y `GIF`.
- **Limpieza de huérfanas:** Eliminación física del archivo anterior del disco cuando una imagen es reemplazada o la tarea es eliminada.

### 2.5 Cierre de Sesión Seguro
- La vista de logout (`logout_view`) está decorada con `@require_POST` y requiere token CSRF. Peticiones `GET` responden con `405 Method Not Allowed`, mitigando ataques de cierre de sesión involuntario forzado vía prefetching o etiquetas `<img>`.

### 2.6 Configuración de Producción Segura (`DEBUG=False`)
Cuando `DEBUG=False` está configurado en `config/settings.py`:
- `SECRET_KEY` es obligatoria; la aplicación no inicia si está vacía.
- `ALLOWED_HOSTS` no puede contener comodines (`*`).
- Redirección automática a HTTPS (`SECURE_SSL_REDIRECT = True`).
- Cookies protegidas: `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `SESSION_COOKIE_HTTPONLY = True`, `SameSite = 'Lax'`.
- Cabeceras de seguridad activas: `HSTS` (31536000 s), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`.

---

## 3. Manejo de Secretos

- Las credenciales nunca se versionan en Git ni se almacenan en código fuente.
- El archivo `.env` debe residir fuera del control de versiones con permisos restrictivos (`chmod 600 .env`).
- Las claves y contraseñas temporales mostradas en documentación o ejemplos son estrictamente referenciales (`change-me-...`).
