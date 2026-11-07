"""
URL configuration for config project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("todos.urls")),
]

if settings.DEBUG:
    # Los estáticos pueden servirse en desarrollo. La multimedia NO se publica:
    # se entrega mediante la vista privada `todo_image` con comprobación de propietario.
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
