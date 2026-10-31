# TODO List Pro — Django 5 & PythonAnywhere

Una aplicación moderna y completa de lista de tareas (TODO List) construida con **Python 3.12**, **Django 5**, **Tailwind CSS**, soporte para **subida y visualización de imágenes**, API REST completa y lista para desplegar en **PythonAnywhere**.

---

## Características Principales

- **Gestión Completa de Tareas (CRUD)**: Creación, lectura, edición y eliminación de tareas.
- **Soporte de Imágenes**: Adjunta fotos/capturas a cada tarea con visualizador modal integrado (Lightbox).
- **Prioridades y Categorías**: Niveles de prioridad (Alta, Media, Baja) con badges visuales e insignias de categorías (General, Trabajo, Personal, etc.).
- **Fechas Límite**: Control de plazos y visualización de fechas de vencimiento.
- **Métricas en Tiempo Real**: Tarjetas con conteo total, pendientes, completadas y barra porcentual de progreso.
- **Filtros y Búsqueda**: Filtrado instantáneo por estado (Todas / Pendientes / Completadas), prioridad, categoría y búsqueda por texto.
- **API REST Integrada**: Endpoints JSON en `/api/todos/` y `/api/todos/stats/` para integración externa.
- **Optimizado para PythonAnywhere**: Configuración lista con WSGI, manejo de estáticos y medios, sin necesidad de clusters externos.

---

## Estructura del Proyecto

```text
todo_django_mongodb/
├── config/                  # Configuración principal de Django (settings, urls, wsgi)
├── todos/                   # Aplicación de tareas (modelos, vistas, servicios, tests)
│   ├── migrations/          # Migraciones de base de datos
│   ├── models.py            # Modelo TodoTask con soporte de imágenes
│   ├── services.py          # Lógica de negocio y consultas
│   ├── views.py             # Vistas HTML y endpoints JSON de la API
│   ├── urls.py              # Rutas de la aplicación
│   └── tests.py             # Pruebas unitarias automatizadas
├── templates/todos/         # Interfaz visual responsive con Tailwind CSS y Lucide Icons
├── static/                  # Archivos estáticos personalizados
├── staticfiles/             # Archivos estáticos recolectados para producción
├── media/                   # Imágenes subidas por los usuarios
├── pythonanywhere_wsgi.py   # Plantilla WSGI para PythonAnywhere
├── PYTHONANYWHERE_DEPLOY.md # Guía paso a paso para desplegar en PythonAnywhere
├── seed_data.py             # Script para insertar tareas de ejemplo
├── requirements.txt         # Dependencias del proyecto
└── manage.py                # CLI de Django
```

---

## Ejecución Local

### 1. Activar el Entorno Virtual
En Windows (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Aplicar migraciones y datos de prueba
```bash
python manage.py migrate
python seed_data.py
```

### 3. Iniciar el Servidor de Desarrollo
```bash
python manage.py runserver
```

Abre en tu navegador: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## Endpoints de la API REST

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/todos/` | Listar tareas (soporta `?status=`, `?priority=`, `?category=`, `?q=`) |
| `POST` | `/api/todos/` | Crear una nueva tarea (soporta multipart con imagen) |
| `GET` | `/api/todos/<id>/` | Obtener detalle de una tarea |
| `PUT` | `/api/todos/<id>/` | Actualizar una tarea |
| `DELETE` | `/api/todos/<id>/` | Eliminar una tarea |
| `POST` | `/api/todos/<id>/toggle/` | Alternar estado completado/pendiente |
| `GET` | `/api/todos/stats/` | Resumen estadístico y porcentajes |

---

## Despliegue en PythonAnywhere

Consulta la guía detallada en [PYTHONANYWHERE_DEPLOY.md](file:///C:/Users/JZAMORA/.gemini/antigravity/scratch/todo_django_mongodb/PYTHONANYWHERE_DEPLOY.md).
