"""
Formularios de validación para tareas en TaskPilot.
"""

from django import forms

from .models import TodoTask
from .validators import validate_task_image


class TaskForm(forms.ModelForm):
    """Formulario para creación y edición de tareas."""

    class Meta:
        model = TodoTask
        fields = ["title", "description", "priority", "category", "due_date", "image"]

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if not title:
            raise forms.ValidationError("El título de la tarea es obligatorio.")
        if len(title) > 200:
            raise forms.ValidationError("El título no puede exceder 200 caracteres.")
        return title

    def clean_priority(self):
        priority = self.cleaned_data.get("priority", "media")
        if priority not in ("baja", "media", "alta"):
            priority = "media"
        return priority

    def clean_category(self):
        category = self.cleaned_data.get("category", "").strip()
        return category if category else "General"

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            validate_task_image(image)
        return image
