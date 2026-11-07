from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import TodoTask


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
        return format_html(f'<span style="{style}">{obj.get_priority_display()}</span>')
    priority_badge.short_description = "Prioridad"

    def image_preview(self, obj):
        if obj.image:
            image_url = reverse("todo_image", kwargs={"todo_id": obj.pk})
            return format_html(f'<img src="{image_url}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px;" />')
        return "-"
    image_preview.short_description = "Imagen"
