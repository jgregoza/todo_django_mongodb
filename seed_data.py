"""
Script para inicializar datos de prueba en la base de datos.
Ejecutar con: python seed_data.py <username>

El propietario es obligatorio: no se asignan tareas a usuarios genéricos ni
se ejecuta este script en producción.
"""

import os
import sys
from datetime import date, timedelta

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User

from todos.models import TodoTask


def seed(username=None):
    if not username:
        print("Uso: python seed_data.py <username>")
        return

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"No existe el usuario '{username}'. Créalo antes de sembrar datos.")
        return

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
        TodoTask.objects.create(user=user, **item)

    print(f"[OK] Se crearon {len(sample_tasks)} tareas de prueba para '{username}'.")

if __name__ == "__main__":
    seed(sys.argv[1] if len(sys.argv) > 1 else None)
