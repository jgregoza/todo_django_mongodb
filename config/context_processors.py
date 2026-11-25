from django.conf import settings


def app_meta(request):
    """Expone metadatos de la aplicación a todas las plantillas."""
    return {"APP_VERSION": settings.APP_VERSION}
