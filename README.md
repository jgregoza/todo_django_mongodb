# TaskPilot — Gestor Personal de Tareas

TaskPilot es una aplicación moderna y segura de gestión de tareas construida con **Python**, **Django 5.2 LTS**, **SQLite**, **Tailwind CSS** y **Lucide Icons**, optimizada para su despliegue en **PythonAnywhere**.

---

## Características Principales

- **Gestión Completa de Tareas (CRUD)**: Creación, lectura, edición y eliminación de tareas con aislamiento estricto por usuario.
- **Autenticación y Autorización**: Sistema nativo de login, registro y logout seguro (POST) con protección CSRF en todos los formularios y endpoints.
- **Soporte de Imágenes Privadas**: Adjunta imágenes a cada tarea con visualizador modal integrado (Lightbox), servidas mediante control de acceso por propietario.
- **Prioridades y Categorías**: Niveles de prioridad (Alta, Media, Baja) con badges visuales e insignias de categorías (General, Trabajo, Personal, Urgente, etc.).
- **Fechas Límite**: Control de plazos y visualización de fechas de vencimiento.
- **Métricas y Estadísticas**: Conteo total, tareas pendientes, completadas y barra porcentual de progreso.
- **Filtros y Búsqueda**: Filtrado instantáneo por estado, prioridad, categoría y búsqueda por texto.
- **API REST Protegida**: Endpoints JSON en `/api/todos/` con autenticación obligatoria (401 JSON) y protección CSRF.
- **Diseñado para PythonAnywhere**: Configuración con SQLite nativo, separación de datos mutables (`DATA_DIR`) y WSGI optimizado.

---

## Estructura del Proyecto

```text
taskpilot/
├── config/                  # Configuración principal de Django (settings, urls, wsgi)
├── todos/                   # Aplicación de tareas (modelos, vistas, servicios, tests)
│   ├── migrations/          # Migraciones de base de datos
│   ├── models.py            # Modelo TodoTask con soporte de imágenes y propietario
│   ├── services.py          # Lógica de negocio y consultas aisladas por usuario
│   ├── views.py             # Vistas HTML, autenticación y endpoints API JSON
│   ├── urls.py              # Rutas de la aplicación
│   ├── admin.py             # Panel de administración de Django
│   └── tests.py             # Suite de pruebas automatizadas
├── templates/todos/         # Plantillas HTML con Tailwind CSS y Lucide Icons
├── static/                  # Archivos estáticos base
├── staticfiles/             # Archivos estáticos recolectados para producción
├── pythonanywhere_wsgi.py   # Plantilla de configuración WSGI para PythonAnywhere
├── PYTHONANYWHERE_DEPLOY.md # Guía paso a paso para despliegue
├── seed_data.py             # Script para inicializar tareas de prueba asignadas a un usuario
├── requirements.txt         # Dependencias exactas de producción
└── manage.py                # Interfaz CLI de Django
```

---

## Ejecución Local

### 1. Activar el Entorno Virtual
En Windows (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Configurar el Entorno
Copia el archivo de variables de entorno y ajusta tus valores locales:
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

## Endpoints de la API REST

Todos los endpoints requieren autenticación de sesión y envío de token CSRF para peticiones mutativas (`POST`, `PUT`, `PATCH`, `DELETE`).

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/todos/` | Listar tareas del usuario (`?status=`, `?priority=`, `?category=`, `?q=`) |
| `POST` | `/api/todos/` | Crear una nueva tarea (JSON o multipart con imagen) |
| `GET` | `/api/todos/<id>/` | Obtener detalle de una tarea propia |
| `PUT` | `/api/todos/<id>/` | Actualizar una tarea propia |
| `DELETE` | `/api/todos/<id>/` | Eliminar una tarea propia |
| `POST` / `PATCH` | `/api/todos/<id>/toggle/` | Alternar estado completada/pendiente |
| `GET` | `/api/todos/stats/` | Estadísticas del usuario autenticado |

---

## Despliegue en PythonAnywhere

Consulta la guía detallada en [PYTHONANYWHERE_DEPLOY.md](PYTHONANYWHERE_DEPLOY.md).
