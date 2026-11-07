"""
Vistas web, autenticación de usuarios y endpoints de API con validaciones robustas, paginación y logging.
"""

import json
import logging
import mimetypes
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from . import selectors, services
from .forms import TaskForm
from .models import TodoTask
from .validators import validate_api_payload, validate_task_image

logger = logging.getLogger("todos")


def _read_api_payload(request, allowed_fields):
    """Lee y valida datos JSON o formularios de la API."""
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, JsonResponse(
                {"error": "JSON no valido en el cuerpo de la solicitud."},
                status=400,
            )
    else:
        data = request.POST

    try:
        validate_api_payload(data, allowed_fields)
    except ValidationError as exc:
        message = exc.messages[0] if exc.messages else str(exc)
        return None, JsonResponse({"error": message}, status=400)

    return data, None



def api_login_required(view_func):
    """Exige autenticación en API y responde 401 JSON (sin redirección HTML)."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            logger.warning("Intento de acceso anónimo a endpoint de API: %s", request.path)
            return JsonResponse({"error": "Autenticación requerida"}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
def index_view(request):
    """Vista principal con interfaz visual completa y paginación."""
    status = request.GET.get("status", "all")
    priority = request.GET.get("priority", "")
    category = request.GET.get("category", "")
    search = request.GET.get("q", "")
    page_number = request.GET.get("page", 1)

    queryset = selectors.list_todos_queryset(
        user=request.user,
        status=status,
        priority=priority,
        category=category,
        search=search,
    )
    page_obj = selectors.paginate_queryset(queryset, page=page_number, per_page=12)
    todos = [t.to_dict() for t in page_obj]
    stats = selectors.get_stats(user=request.user)
    categories = selectors.get_categories(user=request.user)

    context = {
        "todos": todos,
        "page_obj": page_obj,
        "stats": stats,
        "categories": categories,
        "current_status": status,
        "current_priority": priority,
        "current_category": category,
        "search_query": search,
    }
    return render(request, "todos/index.html", context)


@login_required
@require_http_methods(["POST"])
def create_todo_view(request):
    """Acción de formulario web para crear una tarea con validación en servidor."""
    form = TaskForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            services.create_todo(
                title=form.cleaned_data["title"],
                description=form.cleaned_data.get("description", ""),
                priority=form.cleaned_data.get("priority", "media"),
                category=form.cleaned_data.get("category", "General"),
                due_date=form.cleaned_data.get("due_date"),
                image=form.cleaned_data.get("image"),
                user=request.user,
            )
            messages.success(request, "Tarea creada exitosamente.")
        except (ValueError, ValidationError) as e:
            msg = e.message if hasattr(e, "message") else str(e)
            messages.error(request, msg)
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{error}")

    return redirect("index")


@login_required
@require_http_methods(["POST"])
def toggle_todo_view(request, todo_id):
    """Acción de alternar estado de completado."""
    updated = services.toggle_todo(todo_id, user=request.user)
    if not updated:
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept") == "application/json":
            return JsonResponse({"success": False, "error": "Tarea no encontrada"}, status=404)
        raise Http404("Tarea no encontrada")
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept") == "application/json":
        stats = selectors.get_stats(user=request.user)
        return JsonResponse({"success": True, "todo": updated, "stats": stats})
    return redirect("index")


@login_required
@require_http_methods(["POST"])
def update_todo_view(request, todo_id):
    """Acción de formulario web para editar una tarea y su imagen con validación."""
    title = request.POST.get("title", "").strip()
    if not title:
        messages.error(request, "El título de la tarea es obligatorio.")
        return redirect("index")

    image = request.FILES.get("image")
    if image:
        try:
            validate_task_image(image)
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, "message") else str(e))
            return redirect("index")

    clear_image = request.POST.get("clear_image") == "on"

    try:
        updated = services.update_todo(
            todo_id,
            title=title,
            description=request.POST.get("description", "").strip(),
            priority=request.POST.get("priority", "media"),
            category=request.POST.get("category", "General").strip() or "General",
            due_date=request.POST.get("due_date", "").strip() or None,
            image=image,
            clear_image=clear_image,
            user=request.user,
        )
    except (ValueError, ValidationError) as e:
        messages.error(request, e.message if hasattr(e, "message") else str(e))
        return redirect("index")

    if not updated:
        raise Http404("Tarea no encontrada")

    messages.success(request, "Tarea actualizada correctamente.")
    return redirect("index")


@login_required
@require_http_methods(["POST"])
def delete_todo_view(request, todo_id):
    """Acción de eliminar tarea."""
    deleted = services.delete_todo(todo_id, user=request.user)
    if not deleted:
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept") == "application/json":
            return JsonResponse({"success": False, "error": "Tarea no encontrada"}, status=404)
        raise Http404("Tarea no encontrada")
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept") == "application/json":
        stats = selectors.get_stats(user=request.user)
        return JsonResponse({"success": True, "stats": stats})
    return redirect("index")


@login_required
def todo_image(request, todo_id):
    """Entrega una imagen privada solo a su propietario o al staff."""
    todo = get_object_or_404(TodoTask, id=todo_id)

    if not (request.user.is_staff or todo.user_id == request.user.id):
        logger.warning(
            "Usuario %s intentó acceder a imagen no autorizada de tarea ID %s",
            request.user.username,
            todo_id,
        )
        raise Http404("Imagen no encontrada")

    if not todo.image:
        raise Http404("Imagen no encontrada")

    try:
        image_file = todo.image.open("rb")
    except FileNotFoundError:
        logger.error("Archivo físico de imagen no encontrado para tarea ID %s", todo_id)
        raise Http404("Imagen no encontrada")

    content_type = mimetypes.guess_type(todo.image.name)[0] or "application/octet-stream"
    return FileResponse(image_file, content_type=content_type)


# ==========================================
# Autenticación de Usuarios (Logins)
# ==========================================

def login_view(request):
    """Inicio de sesión de usuarios."""
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            logger.info("Inicio de sesión exitoso: %s", user.username)
            messages.success(request, f"¡Bienvenido de nuevo, {user.username}!")
            return redirect("index")
        else:
            logger.warning("Fallo en inicio de sesión para formulario enviado.")
            messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()

    return render(request, "todos/login.html", {"form": form})


def register_view(request):
    """Registro de nuevas cuentas."""
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            logger.info("Nueva cuenta registrada: %s", user.username)
            messages.success(request, f"¡Cuenta creada con éxito! Bienvenido, {user.username}.")
            return redirect("index")
        else:
            messages.error(request, "Por favor corrige los errores del formulario.")
    else:
        form = UserCreationForm()

    return render(request, "todos/register.html", {"form": form})


@require_POST
def logout_view(request):
    """Cierre de sesión; solo por POST y con CSRF."""
    username = request.user.username if request.user.is_authenticated else "anónimo"
    logout(request)
    logger.info("Sesión cerrada para: %s", username)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect("login")


# ==========================================
# API REST (JSON)
# ==========================================

@api_login_required
@require_http_methods(["GET", "POST"])
def api_todos(request):
    """API para listar y crear tareas vía JSON o multipart, con soporte de paginación."""
    if request.method == "GET":
        status = request.GET.get("status", "all")
        priority = request.GET.get("priority", "")
        category = request.GET.get("category", "")
        search = request.GET.get("q", "")
        page = request.GET.get("page")

        queryset = selectors.list_todos_queryset(
            user=request.user,
            status=status,
            priority=priority,
            category=category,
            search=search,
        )

        if page is not None:
            per_page = request.GET.get("per_page") or request.GET.get("page_size") or 10
            try:
                per_page = int(per_page)
            except (ValueError, TypeError):
                per_page = 10

            page_obj = selectors.paginate_queryset(queryset, page=page, per_page=per_page)
            return JsonResponse({
                "todos": [t.to_dict() for t in page_obj],
                "count": queryset.count(),
                "page": page_obj.number,
                "total_pages": page_obj.paginator.num_pages,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            })

        todos = [t.to_dict() for t in queryset]
        return JsonResponse({"todos": todos, "count": len(todos)})

    elif request.method == "POST":
        image = request.FILES.get("image")
        if request.content_type == "application/json":
            data, error_response = _read_api_payload(
                request,
                ("title", "description", "priority", "category", "due_date"),
            )
            if error_response:
                return error_response
        else:
            data = request.POST

        title = (data.get("title") or "").strip()
        if not title:
            return JsonResponse({"error": "El título de la tarea es obligatorio"}, status=400)

        try:
            todo = services.create_todo(
                title=title,
                description=data.get("description", ""),
                priority=data.get("priority", "media"),
                category=data.get("category", "General"),
                due_date=data.get("due_date"),
                image=image,
                user=request.user,
            )
            return JsonResponse(todo, status=201)
        except (ValueError, ValidationError) as e:
            msg = e.message if hasattr(e, "message") else str(e)
            return JsonResponse({"error": msg}, status=400)


@api_login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def api_todo_detail(request, todo_id):
    """API para ver, actualizar o borrar tarea específica."""
    todo = selectors.get_todo(todo_id, user=request.user)
    if not todo:
        return JsonResponse({"error": "Tarea no encontrada"}, status=404)

    if request.method == "GET":
        return JsonResponse(todo)

    elif request.method == "PUT":
        if request.content_type == "application/json":
            data, error_response = _read_api_payload(
                request,
                ("title", "description", "priority", "category", "completed", "due_date"),
            )
            if error_response:
                return error_response
        else:
            data = request.POST

        try:
            updated = services.update_todo(
                todo_id,
                title=data.get("title"),
                description=data.get("description"),
                priority=data.get("priority"),
                category=data.get("category"),
                completed=data.get("completed"),
                due_date=data.get("due_date"),
                user=request.user,
            )
            if not updated:
                return JsonResponse({"error": "Tarea no encontrada"}, status=404)
            return JsonResponse(updated)
        except (ValueError, ValidationError) as e:
            msg = e.message if hasattr(e, "message") else str(e)
            return JsonResponse({"error": msg}, status=400)

    elif request.method == "DELETE":
        services.delete_todo(todo_id, user=request.user)
        return JsonResponse({"deleted": True, "id": todo_id})


@api_login_required
@require_http_methods(["POST", "PATCH"])
def api_toggle_todo(request, todo_id):
    """API para alternar completado."""
    updated = services.toggle_todo(todo_id, user=request.user)
    if not updated:
        return JsonResponse({"error": "Tarea no encontrada"}, status=404)
    return JsonResponse(updated)


@api_login_required
@require_http_methods(["GET"])
def api_stats(request):
    """API con estadísticas generales."""
    stats = selectors.get_stats(user=request.user)
    return JsonResponse(stats)
