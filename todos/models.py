"""
Modelos de datos para TODO List.
Utiliza el ORM nativo de Django para máxima compatibilidad con PythonAnywhere,
soporte nativo de subida de imágenes y cero latencia de conexión.
"""

from django.db import models
from django.contrib.auth.models import User


class TodoTask(models.Model):
    """Modelo de tarea con soporte para imágenes, prioridades y usuarios."""

    PRIORITY_CHOICES = [
        ("baja", "Baja"),
        ("media", "Media"),
        ("alta", "Alta"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="todos",
        null=True,
        blank=True,
        verbose_name="Usuario",
    )
    title = models.CharField(max_length=200, verbose_name="Título")
    description = models.TextField(blank=True, default="", verbose_name="Descripción")
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="media",
        verbose_name="Prioridad",
    )
    category = models.CharField(
        max_length=50,
        default="General",
        verbose_name="Categoría",
    )
    completed = models.BooleanField(default=False, verbose_name="¿Completada?")
    due_date = models.DateField(null=True, blank=True, verbose_name="Fecha límite")
    image = models.ImageField(
        upload_to="todo_images/",
        blank=True,
        null=True,
        verbose_name="Imagen adjunta",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")

    class Meta:
        verbose_name = "Tarea"
        verbose_name_plural = "Tareas"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({'✓' if self.completed else '○'})"

    def to_dict(self):
        """Devuelve representación en diccionario para APIs y frontend."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "priority": self.priority,
            "category": self.category or "General",
            "completed": self.completed,
            "due_date": self.due_date.strftime("%Y-%m-%d") if self.due_date else None,
            "image_url": self.image.url if self.image else None,
            "username": self.user.username if self.user else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M") if self.updated_at else None,
        }
