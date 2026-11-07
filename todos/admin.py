import logging

from django.contrib import admin
from django.db import transaction
from django.urls import reverse
from django.utils.html import format_html

from .models import TodoTask

logger = logging.getLogger('todos')

def _delete_image_if_unused(storage, name):
    if not name or TodoTask.objects.filter(image=name).exists():
        return
    try:
        storage.delete(name)
    except Exception:
        logger.exception('No se pudo limpiar imagen desde Django Admin: %s', name)


@admin.register(TodoTask)
class TodoTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "priority_badge", "category", "completed", "due_date", "image_preview", "created_at")
    list_filter = ("completed", "priority", "category", "created_at", "user")
    search_fields = ("title", "description", "category", "user__username")
    list_editable = ("completed",)

    def priority_badge(self, obj):
        colors = {
            "alta": "background: #fee2e2; color: #991b1b; padding: 3px 8px; border-radius: 6px; font-weight: bold;",
            "media": "background: #fef3c7; color: #92400e; padding: 3px 8px; border-radius: 6px; font-weight: bold;",
            "baja": "background: #e0f2fe; color: #075985; padding: 3px 8px; border-radius: 6px; font-weight: bold;",
        }
        style = colors.get(obj.priority, "")
        return format_html(
            '<span style="{}">{}</span>',
            style,
            obj.get_priority_display(),
        )
    priority_badge.short_description = "Prioridad"

    def image_preview(self, obj):
        if obj.image:
            image_url = reverse("todo_image", kwargs={"todo_id": obj.pk})
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; '
                'object-fit: cover; border-radius: 6px;" />',
                image_url,
            )
        return "-"
    image_preview.short_description = "Imagen"


    def delete_model(self, request, obj):
        image = obj.image
        storage = image.storage if image else None
        name = image.name if image else None

        super().delete_model(request, obj)

        if storage and name:
            transaction.on_commit(
                lambda s=storage, n=name: _delete_image_if_unused(s, n)
            )

    def delete_queryset(self, request, queryset):
        images = []
        for obj in queryset.only("image"):
            if obj.image:
                images.append((obj.image.storage, obj.image.name))

        super().delete_queryset(request, queryset)

        seen = set()
        for storage, name in images:
            if name and name not in seen:
                seen.add(name)
                transaction.on_commit(
                    lambda s=storage, n=name: _delete_image_if_unused(s, n)
                )
