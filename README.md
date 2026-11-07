# TaskPilot — Gestor Personal de Tareas

TaskPilot es una aplicación moderna y segura de gestión de tareas construida con **Python**, **Django 5.2 LTS**, **SQLite**, **Tailwind CSS** y **Lucide Icons**, optimizada para su despliegue en **PythonAnywhere**.

---

## Características Principales

- **Gestión Completa de Tareas (CRUD)**: Creación, lectura, edición y eliminación de tareas con aislamiento estricto por usuario.
- **Autenticación y Autorización**: Sistema nativo de login, registro y logout seguro (POST) con protección CSRF en todos los formularios y endpoints.
- **Soporte de Imágenes Privadas**: Adjunta imágenes a cada tarea con visualizador modal integrado (Lightbox), servidas mediante control de acceso por propietario.
- **Validación de Archivos**: Verificación real de imágenes mediante Pillow (`Image.verify()`), límite de 5 MB y limpieza automática de huérfanas al reemplazar o borrar.
- **Prioridades y Categorías**: Niveles de prioridad (Alta, Media, Baja) con badges visuales e insignias de categorías (General, Trabajo, Personal, Urgente, etc.).
- **Fechas Límite y Métricas**: Control de plazos y cálculo de métricas en tiempo real (conteo total, pendientes, completadas y porcentaje).
- **Filtros y Búsqueda**: Filtrado instantáneo por estado, prioridad, categoría y búsqueda por texto.
- **API REST Protegida (v1)**: Endpoints JSON versionados en `/api/v1/todos/` con autenticación obligatoria (401 JSON), soporte de paginación y protección CSRF.
- **Diseñado para PythonAnywhere**: Configuración con SQLite nativo, separación de datos mutables (`DATA_DIR`) y WSGI optimizado.

---

## Índice de Documentación

| Documento | Descripción |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Diagramas de arquitectura, capas (MVT/CQRS), modelos, selectores, servicios y persistencia SQLite. |
| [`SECURITY.md`](SECURITY.md) | Matriz de autorización, prevención de IDOR/BOLA, CSRF, privacidad de multimedia y políticas de producción. |
| [`DEPLOYMENT.md`](DEPLOYMENT.md) | Procedimiento de despliegue paso a paso en PythonAnywhere, configuración WSGI, estáticos y rollback. |
| [`ENVIRONMENT.md`](ENVIRONMENT.md) | Variables de entorno, plantillas de desarrollo y producción, y rotación de `SECRET_KEY`. |
| [`RUNBOOK.md`](RUNBOOK.md) | Operación en producción, monitoreo de logs, respaldo/restauración de datos y resolución de incidencias. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Guía para desarrolladores, ramas, commits convencionales, pruebas automatizadas y estándares de código. |
| [`CHANGELOG.md`](CHANGELOG.md) | Historial de versiones y cambios del proyecto (SemVer y Keep a Changelog). |
| [`docs/adr/`](docs/adr/) | Registro de Decisiones de Arquitectura (ADRs 0001 a 0005). |

---

## Estructura del Proyecto

```text
taskpilot/
├── manage.py                # Interfaz CLI de Django
├── requirements.txt         # Dependencias exactas de producción (Django 5.2.19, Pillow, etc.)
├── requirements-dev.txt     # Dependencias de desarrollo (coverage, ruff)
├── pyproject.toml           # Configuración de linter (Ruff) y cobertura (Coverage)
├── .env.example             # Plantilla de variables de entorno seguras
├── .gitignore               # Archivos ignorados por Git
├── README.md                # Portada y visión general del proyecto
├── ARCHITECTURE.md          # Especificación y diagramas de arquitectura
├── SECURITY.md              # Políticas y controles de seguridad
├── DEPLOYMENT.md            # Guía oficial de despliegue en PythonAnywhere
├── ENVIRONMENT.md           # Referencia de variables de entorno
├── CHANGELOG.md             # Registro de cambios por versión
├── CONTRIBUTING.md          # Guía de contribución y calidad
├── RUNBOOK.md               # Guía operativa y resolución de problemas
├── docs/adr/                # Registros de decisiones de arquitectura (ADRs)
├── config/                  # Configuración principal de Django (settings, urls, wsgi)
├── todos/                   # Aplicación principal de tareas
│   ├── models.py            # Modelo TodoTask con titularidad obligatoria
│   ├── selectors.py         # Consultas y lecturas (Clean Architecture / CQRS)
│   ├── services.py          # Mutaciones de dominio y transacciones atómicas
│   ├── forms.py             # Formulario TaskForm con validaciones de servidor
│   ├── validators.py        # Validación de imágenes (Pillow) y analizador booleano
│   ├── views.py             # Vistas MVT, autenticación y API REST JSON
│   ├── urls.py              # Rutas web, API directa y API v1
│   ├── admin.py             # Configuración del panel de administración
│   ├── migrations/          # Historial de migraciones (0001, 0002, 0003)
│   └── tests.py             # Suite automatizada (47 pruebas, 79% cobertura)
├── templates/               # Plantillas HTML
│   ├── todos/               # Interfaz web (index, login, register)
│   └── *.html               # Plantillas de error personalizadas (400, 403, 404, 500)
└── pythonanywhere_wsgi.py   # Plantilla WSGI para PythonAnywhere
```

---

## Ejecución Local

### 1. Activar el Entorno Virtual
En Windows (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Configurar el Entorno
```powershell
cp .env.example .env
```

### 3. Aplicar migraciones
```bash
python manage.py migrate
```

### 4. (Opcional) Crear superusuario y sembrar datos de prueba
```bash
python manage.py createsuperuser
python seed_data.py <tu-usuario>
```

### 5. Iniciar el Servidor de Desarrollo
```bash
python manage.py runserver
```

Abre en tu navegador: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## Endpoints de la API REST v1

Todos los endpoints exigen autenticación de sesión y envío de token CSRF (`X-CSRFToken`) para métodos mutativos (`POST`, `PUT`, `DELETE`). Accesos anónimos devuelven `401 Unauthorized` JSON.

| Método | Endpoint | Parámetros / Cuerpo | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/todos/` | `?page=1&per_page=10&status=&priority=&category=&q=` | Listar tareas paginadas del usuario autenticado. |
| `POST` | `/api/v1/todos/` | JSON o Multipart con `image` | Crear una nueva tarea asignada al usuario. |
| `GET` | `/api/v1/todos/<id>/` | — | Obtener el detalle de una tarea propia. |
| `PUT` | `/api/v1/todos/<id>/` | JSON con campos a actualizar | Actualizar una tarea propia. |
| `DELETE` | `/api/v1/todos/<id>/` | — | Eliminar una tarea propia y su imagen. |
| `POST` | `/api/v1/todos/<id>/toggle/` | — | Alternar estado completada / pendiente. |
| `GET` | `/api/v1/todos/stats/` | — | Métricas y estadísticas personales. |

*(Nota: Las rutas sin prefijo `/api/todos/` se mantienen activas por compatibilidad hacia atrás).*

---

## Despliegue en PythonAnywhere

Para el despliegue en producción, consulta la guía paso a paso en [DEPLOYMENT.md](DEPLOYMENT.md).
