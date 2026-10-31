from django.contrib import admin
from django.utils.html import format_html
from .models import TodoTask


@admin.register(TodoTask)
class TodoTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "priority_badge", "category", "completed", "due_date", "image_preview", "created_at")
    list_filter = ("completed", "priority", "category", "created_at")
    search_fields = ("title", "description", "category")
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
            return format_html(f'<img src="{obj.image.url}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px;" />')
        return "-"
    image_preview.short_description = "Imagen"
