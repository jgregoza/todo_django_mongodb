"""
Capa de selección y consultas (lecturas) para TaskPilot.
Separación limpia de responsabilidades (Clean Architecture / CQRS).
"""

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q

from .models import TodoTask


def _user_todos(user):
    """Devuelve el queryset base para las tareas del usuario autenticado."""
    if not user or not user.is_authenticated:
        return TodoTask.objects.none()
    return TodoTask.objects.filter(user=user)


def list_todos_queryset(user=None, status="all", priority="", category="", search=""):
    """Construye el queryset filtrado de tareas pertenecientes al usuario."""
    queryset = _user_todos(user)

    if status == "pending":
        queryset = queryset.filter(completed=False)
    elif status == "completed":
        queryset = queryset.filter(completed=True)

    if priority and priority in ("baja", "media", "alta"):
        queryset = queryset.filter(priority=priority)

    if category and category != "all":
        queryset = queryset.filter(category__iexact=category)

    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    return queryset.order_by("-created_at")


def list_todos(user=None, status="all", priority="", category="", search=""):
    """Lista serializada de todas las tareas filtradas del usuario."""
    return [
        t.to_dict()
        for t in list_todos_queryset(
            user=user,
            status=status,
            priority=priority,
            category=category,
            search=search,
        )
    ]


def paginate_queryset(queryset, page=1, per_page=12):
    """Aplica paginación segura a un queryset."""
    paginator = Paginator(queryset, per_page)
    try:
        return paginator.page(page)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)


def get_todo(todo_id, user=None):
    """Obtiene una tarea individual serializada si pertenece al usuario."""
    try:
        return _user_todos(user).get(id=todo_id).to_dict()
    except (TodoTask.DoesNotExist, ValueError, TypeError):
        return None


def get_categories(user=None):
    """Devuelve las categorías únicas disponibles para el usuario."""
    defaults = {"General", "Trabajo", "Personal", "Estudio", "Urgente"}
    queryset = _user_todos(user)
    existing = set(queryset.values_list("category", flat=True).distinct())
    all_cats = defaults.union({c for c in existing if c})
    return sorted(list(all_cats))


def get_stats(user=None):
    """Calcula las métricas y estadísticas de tareas del usuario."""
    queryset = _user_todos(user)

    total = queryset.count()
    completed = queryset.filter(completed=True).count()
    pending = total - completed
    percentage = round((completed / total * 100), 1) if total > 0 else 0

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "percentage": percentage,
    }
