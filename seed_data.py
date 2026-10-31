"""
Script para inicializar datos de prueba en la base de datos.
Ejecutar con: python seed_data.py
"""

import os
import django
from datetime import date, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from todos.models import TodoTask

def seed():
    if TodoTask.objects.exists():
        print(f"Ya existen {TodoTask.objects.count()} tareas en la base de datos.")
        return

    sample_tasks = [
        {
            "title": "Configurar y desplegar en PythonAnywhere",
            "description": "Subir el código a GitHub, clonar en la consola Bash de PythonAnywhere y configurar la app Web.",
            "priority": "alta",
            "category": "Despliegue",
            "completed": False,
            "due_date": date.today() + timedelta(days=1),
        },
        {
            "title": "Subir una imagen a una tarea de prueba",
            "description": "Comprobar el funcionamiento del almacenamiento de imágenes y el visor lightbox.",
            "priority": "media",
            "category": "Frontend",
            "completed": False,
            "due_date": date.today() + timedelta(days=3),
        },
        {
            "title": "Explorar el panel de administración de Django",
            "description": "Crear un superusuario con 'python manage.py createsuperuser' y acceder a /admin/",
            "priority": "baja",
            "category": "Admin",
            "completed": True,
            "due_date": None,
        },
        {
            "title": "Probar los endpoints de la API REST",
            "description": "Consumir GET /api/todos/ y GET /api/todos/stats/ para integración con otros clientes.",
            "priority": "media",
            "category": "API",
            "completed": True,
            "due_date": None,
        },
    ]

    for item in sample_tasks:
        TodoTask.objects.create(**item)

    print(f"[OK] Se crearon {len(sample_tasks)} tareas de prueba exitosamente.")

if __name__ == "__main__":
    seed()
