# Changelog — TaskPilot

Todas las modificaciones notables de este proyecto están documentadas en este archivo.
El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto se adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-06

### Seguridad (Fase 1)
- **Autenticación obligatoria:** Protección de todas las vistas web (`@login_required`) y endpoints de API con redirección adecuada o respuesta JSON.
- **API sin redirecciones HTML:** Creación del decorador `@api_login_required` para responder `401 Unauthorized` JSON ante accesos no autenticados en `/api/` y `/api/v1/`.
- **Mitigación total de IDOR / BOLA:** Aislamiento estricto de tareas y categorías a través de `_user_todos(user)`. Peticiones a recursos ajenos devuelven `404 Not Found`.
- **Protección CSRF completa:** Eliminación de `@csrf_exempt` en la API; requerimiento obligatorio de token CSRF en formularios web y peticiones API.
- **Logout restringido:** El cierre de sesión exige el método `POST` y token CSRF con `@require_POST`, rechazando peticiones `GET` con `405 Method Not Allowed`.
- **Multimedia privada:** Eliminación del mapeo público de `/media/`. Creación de la vista autenticada `todo_image` con validación de propietario o staff para la entrega de imágenes mediante `FileResponse`.
- **Migración 0003:** Campo `user` de `TodoTask` transformado en obligatorio (`NOT NULL`, sin valores nulos ni tareas huérfanas).

### Identidad y Arquitectura (Fase 2)
- **Consolidación de marca:** Renombrado integral del producto a **TaskPilot** en títulos, navbar, metadatos y documentación.
- **Eliminación de MongoDB:** Supresión de `todos/db.py`, de variables `MONGO_*` en `settings.py` y `.env.example`, y de dependencias innecesarias (`pymongo`, `mongoengine`, `dnspython`).
- **Arquitectura SQLite:** Confirmación de persistencia con SQLite relacional nativo y Django 5.2.19 LTS.
- **Desacoplamiento de almacenamiento:** Soporte para `DATA_DIR` separando la base de datos y la multimedia (`taskpilot-data`) del código fuente.
- **Dependencias exactas:** Fijación de versiones compatibles con Python 3.10 en `requirements.txt`.

### Robustez y Manejo de Errores (Fase 3)
- **Transacciones atómicas:** Mutaciones de estado envueltas en `@transaction.atomic` (`create_todo`, `update_todo`, `toggle_todo`, `delete_todo`).
- **Validación de imágenes con Pillow:** Inspección real de contenido (`Image.verify()`), límite de 5 MB y lista blanca de formatos (`JPEG`, `PNG`, `WEBP`, `GIF`).
- **Limpieza de archivos huérfanos:** Eliminación automática del archivo anterior en disco al reemplazar una imagen o al borrar una tarea.
- **Corrección booleana:** Implementación de `parse_bool` para corregir la evaluación errónea de strings `"false"` como `True`.
- **Validación de entradas:** Creación de `TaskForm` con validación de longitud de título (máx. 200 caracteres, no vacío).
- **Manejo de errores amigable:** Creación de plantillas personalizadas `400.html`, `403.html`, `404.html` y `500.html` con diseño estilizado que impiden la fuga de trazas internas.
- **Logging estructurado:** Configuración de logs formateados para eventos críticos, autenticación y errores.

### Calidad y Refactorización (Fase 4)
- **Separación de responsabilidades (CQRS ligero):** Creación del módulo `todos/selectors.py` para todas las lecturas y consultas optimizadas, dejando `todos/services.py` centrado en mutaciones.
- **Paginación:** Implementación de paginación tanto en la vista web principal (`page_obj`) como en la API REST (`?page=1&per_page=10`).
- **Versionado de API:** Introducción de rutas versionadas `/api/v1/todos/` preservando compatibilidad con `/api/todos/`.
- **Cobertura de pruebas:** Suite automatizada de 47 pruebas (`100 % pass`), con una cobertura global del **79 %**.
- **Herramientas de calidad:** Incorporación de `pyproject.toml` con configuración de linter **Ruff** y **Coverage**, más `requirements-dev.txt`.
