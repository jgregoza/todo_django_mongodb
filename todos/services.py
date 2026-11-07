"""
Capa de servicios para operaciones CRUD y estadísticas con Django ORM, soporte de imágenes y usuarios.
"""

from datetime import datetime
from django.db.models import Q
from .models import TodoTask


def _user_todos(user):
    """Devuelve únicamente las tareas del usuario autenticado."""
    if not user or not user.is_authenticated:
        return TodoTask.objects.none()
    return TodoTask.objects.filter(user=user)


def list_todos(user=None, status="all", priority="", category="", search=""):
    """Lista las tareas del usuario aplicando filtros de estado, prioridad, categoría y búsqueda."""
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

    return [t.to_dict() for t in queryset.order_by("-created_at")]


def get_todo(todo_id, user=None):
    """Obtiene una tarea del usuario por su ID."""
    try:
        return _user_todos(user).get(id=todo_id).to_dict()
    except (TodoTask.DoesNotExist, ValueError, TypeError):
        return None


def create_todo(title, description="", priority="media", category="General", due_date=None, image=None, user=None):
    """Crea una nueva tarea con soporte de imagen y asociación obligatoria al usuario."""
    if not user or not user.is_authenticated:
        raise ValueError("Se requiere un usuario autenticado para crear tareas.")

    parsed_due = None
    if due_date:
        try:
            parsed_due = datetime.strptime(due_date, "%Y-%m-%d").date()
        except ValueError:
            parsed_due = None

    todo = TodoTask.objects.create(
        user=user,
        title=title.strip(),
        description=description.strip() if description else "",
        priority=priority if priority in ("baja", "media", "alta") else "media",
        category=category.strip() if category else "General",
        due_date=parsed_due,
        image=image if image else None,
    )
    return todo.to_dict()


def update_todo(todo_id, title=None, description=None, priority=None, category=None, completed=None, due_date=None, image=None, clear_image=False, user=None):
    """Actualiza una tarea existente del usuario."""
    try:
        todo = _user_todos(user).get(id=todo_id)

        if title is not None and title.strip():
            todo.title = title.strip()
        if description is not None:
            todo.description = description.strip()
        if priority is not None and priority in ("baja", "media", "alta"):
            todo.priority = priority
        if category is not None and category.strip():
            todo.category = category.strip()
        if completed is not None:
            todo.completed = bool(completed)
        if due_date is not None:
            if due_date:
                try:
                    todo.due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
                except ValueError:
                    pass
            else:
                todo.due_date = None

        if clear_image:
            todo.image.delete(save=False)
            todo.image = None
        elif image:
            todo.image = image

        todo.save()
        return todo.to_dict()
    except (TodoTask.DoesNotExist, ValueError, TypeError):
        return None


def toggle_todo(todo_id, user=None):
    """Invierte el estado de completado de una tarea del usuario."""
    try:
        todo = _user_todos(user).get(id=todo_id)
        todo.completed = not todo.completed
        todo.save(update_fields=["completed", "updated_at"])
        return todo.to_dict()
    except (TodoTask.DoesNotExist, ValueError, TypeError):
        return None


def delete_todo(todo_id, user=None):
    """Elimina una tarea del usuario y su imagen si existe."""
    try:
        todo = _user_todos(user).get(id=todo_id)
        if todo.image:
            todo.image.delete(save=False)
        todo.delete()
        return True
    except (TodoTask.DoesNotExist, ValueError, TypeError):
        return False


def get_categories(user=None):
    """Devuelve la lista única de categorías del usuario, ordenadas."""
    defaults = {"General", "Trabajo", "Personal", "Estudio", "Urgente"}
    queryset = _user_todos(user)
    existing = set(queryset.values_list("category", flat=True).distinct())
    all_cats = defaults.union({c for c in existing if c})
    return sorted(list(all_cats))


def get_stats(user=None):
    """Calcula estadísticas de las tareas del usuario."""
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
