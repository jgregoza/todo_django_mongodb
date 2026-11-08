"""
Capa de servicios (mutaciones de dominio y transacciones) para TaskPilot.
"""

import logging
from datetime import datetime

from django.db import IntegrityError, transaction

from .models import Category, TodoTask, clean_category_name, normalize_category_name
from .selectors import (
    _user_todos,
    get_categories,
    get_stats,
    get_todo,
    list_todos,
    list_todos_queryset,
    paginate_queryset,
)
from .validators import parse_bool, validate_task_image

logger = logging.getLogger("todos")

__all__ = [
    "_user_todos",
    "list_todos_queryset",
    "list_todos",
    "paginate_queryset",
    "get_todo",
    "get_categories",
    "get_stats",
    "resolve_category",
    "create_todo",
    "update_todo",
    "toggle_todo",
    "delete_todo",
]


def resolve_category(user, name):
    """
    Devuelve el nombre canónico de una categoría del usuario.

    La búsqueda y creación siempre se limitan al usuario autenticado, por lo que
    nunca se reutiliza una categoría ajena. La restricción única de base de datos
    evita duplicados ante solicitudes simultáneas.
    """
    cleaned = clean_category_name(name)
    normalized = normalize_category_name(cleaned)

    try:
        # El savepoint mantiene usable la transacción externa si otra solicitud
        # crea la misma categoría al mismo tiempo.
        with transaction.atomic():
            return Category.objects.create(user=user, name=cleaned).name
    except IntegrityError:
        return Category.objects.get(
            user=user, normalized_name=normalized
        ).name


def _delete_file_safely(storage, name):
    """Elimina un archivo sin convertir un fallo de limpieza en un fallo de negocio."""
    if not name:
        return

    try:
        storage.delete(name)
    except Exception:
        logger.exception("No se pudo limpiar el archivo de imagen: %s", name)


def create_todo(
    title,
    description="",
    priority="media",
    category="General",
    due_date=None,
    image=None,
    user=None,
):
    """Crea una tarea y limpia una imagen nueva si la transacción falla."""
    if not user or not user.is_authenticated:
        raise ValueError("Se requiere un usuario autenticado para crear tareas.")

    title_clean = (title or "").strip()
    if not title_clean:
        raise ValueError("El título de la tarea es obligatorio.")
    if len(title_clean) > 200:
        raise ValueError("El título no puede superar 200 caracteres.")

    parsed_due = None
    if due_date:
        if isinstance(due_date, str):
            try:
                parsed_due = datetime.strptime(due_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                parsed_due = None
        elif hasattr(due_date, "strftime"):
            parsed_due = due_date

    category_clean = clean_category_name(category)

    if image:
        validate_task_image(image)

    todo = None

    try:
        with transaction.atomic(durable=True):
            todo = TodoTask(
                user=user,
                title=title_clean,
                description=description.strip() if description else "",
                priority=priority if priority in ("baja", "media", "alta") else "media",
                category=resolve_category(user, category_clean),
                due_date=parsed_due,
                image=image if image else None,
            )
            todo.save()
            result = todo.to_dict()
    except Exception:
        if (
            todo
            and todo.image
            and todo.image.name
            and getattr(todo.image, "_committed", False)
        ):
            _delete_file_safely(todo.image.storage, todo.image.name)
        raise

    logger.info("Tarea creada: ID %s por usuario %s", todo.id, user.username)
    return result


def update_todo(
    todo_id,
    title=None,
    description=None,
    priority=None,
    category=None,
    completed=None,
    due_date=None,
    image=None,
    clear_image=False,
    user=None,
):
    """Actualiza una tarea; elimina imágenes anteriores solo después del commit."""
    todo = None
    new_image_name = None
    new_image_storage = None

    try:
        category_clean = (
            clean_category_name(category)
            if category is not None and category.strip()
            else None
        )

        with transaction.atomic(durable=True):
            todo = _user_todos(user).get(id=todo_id)
            old_image_name = todo.image.name if todo.image else None
            old_image_storage = todo.image.storage if todo.image else None

            if title is not None:
                title_clean = title.strip()
                if not title_clean:
                    raise ValueError("El título de la tarea no puede estar vacío.")
                if len(title_clean) > 200:
                    raise ValueError("El título no puede superar 200 caracteres.")
                todo.title = title_clean

            if description is not None:
                todo.description = description.strip()

            if priority is not None and priority in ("baja", "media", "alta"):
                todo.priority = priority

            if category_clean is not None:
                todo.category = resolve_category(user, category_clean)

            if completed is not None:
                todo.completed = parse_bool(completed)

            if due_date is not None:
                if isinstance(due_date, str) and due_date.strip():
                    try:
                        todo.due_date = datetime.strptime(
                            due_date.strip(), "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        pass
                elif not due_date:
                    todo.due_date = None

            if clear_image:
                todo.image = None
            elif image:
                validate_task_image(image)
                todo.image = image

            todo.save()

            if image and todo.image:
                new_image_name = todo.image.name
                new_image_storage = todo.image.storage

            if (
                old_image_name
                and old_image_storage
                and (clear_image or (image and old_image_name != new_image_name))
            ):
                transaction.on_commit(
                    lambda storage=old_image_storage, name=old_image_name:
                        _delete_file_safely(storage, name)
                )

            result = todo.to_dict()

    except (TodoTask.DoesNotExist, ValueError, TypeError) as exc:
        logger.warning(
            "Fallo al actualizar tarea ID %s por usuario %s: %s",
            todo_id,
            getattr(user, "username", "anónimo"),
            exc,
        )
        return None
    except Exception:
        if new_image_name and new_image_storage:
            _delete_file_safely(new_image_storage, new_image_name)
        elif (
            todo
            and image
            and todo.image
            and todo.image.name
            and getattr(todo.image, "_committed", False)
        ):
            _delete_file_safely(todo.image.storage, todo.image.name)
        raise

    logger.info("Tarea actualizada: ID %s por usuario %s", todo.id, user.username)
    return result


def toggle_todo(todo_id, user=None):
    """Invierte el estado de completado de una tarea del usuario."""
    try:
        with transaction.atomic(durable=True):
            todo = _user_todos(user).get(id=todo_id)
            todo.completed = not todo.completed
            todo.save(update_fields=["completed", "updated_at"])
            result = todo.to_dict()
    except (TodoTask.DoesNotExist, ValueError, TypeError):
        return None

    logger.info(
        "Tarea alternada: ID %s a completed=%s", todo.id, todo.completed
    )
    return result


def delete_todo(todo_id, user=None):
    """Elimina una tarea y su imagen solo después de confirmar la transacción."""
    try:
        with transaction.atomic(durable=True):
            todo = _user_todos(user).get(id=todo_id)
            image_name = todo.image.name if todo.image else None
            image_storage = todo.image.storage if todo.image else None

            todo.delete()

            if image_name and image_storage:
                transaction.on_commit(
                    lambda storage=image_storage, name=image_name:
                        _delete_file_safely(storage, name)
                )

    except (TodoTask.DoesNotExist, ValueError, TypeError):
        return False

    logger.info(
        "Tarea eliminada: ID %s por usuario %s",
        todo_id,
        getattr(user, "username", "anónimo"),
    )
    return True
