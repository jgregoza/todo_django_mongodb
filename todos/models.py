"""
Modelos de datos para TaskPilot.
Utiliza el ORM relacional de Django con SQLite para máxima compatibilidad con PythonAnywhere,
soporte nativo de subida de imágenes y cero latencia de conexión.
"""

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

MAX_CATEGORY_LENGTH = 50


def normalize_category_name(value):
    """Normaliza una categoría para compararla sin distinguir mayúsculas ni espacios."""
    return " ".join((value or "").split()).casefold()


def clean_category_name(value, default="General"):
    """Limpia y valida el nombre visible de una categoría."""
    cleaned = " ".join((value or "").split())
    if not cleaned:
        cleaned = default
    if len(cleaned) > MAX_CATEGORY_LENGTH:
        raise ValueError(
            f"La categoría no puede superar {MAX_CATEGORY_LENGTH} caracteres."
        )
    return cleaned


class Category(models.Model):
    """Categoría privada de un usuario, única por nombre normalizado."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="task_categories",
        verbose_name="Usuario",
    )
    name = models.CharField(max_length=MAX_CATEGORY_LENGTH, verbose_name="Nombre")
    normalized_name = models.CharField(
        max_length=MAX_CATEGORY_LENGTH * 3,
        editable=False,
        verbose_name="Nombre normalizado",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "normalized_name"],
                name="unique_category_per_user",
            ),
            models.CheckConstraint(
                condition=~models.Q(normalized_name=""),
                name="category_normalized_name_not_empty",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = clean_category_name(self.name)
        self.normalized_name = normalize_category_name(self.name)
        super().save(*args, **kwargs)


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
            "image_url": (
                reverse("todo_image", kwargs={"todo_id": self.pk})
                if self.image
                else None
            ),
            "username": self.user.username if self.user else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M") if self.updated_at else None,
        }
