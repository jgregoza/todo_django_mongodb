"""
Vistas web, autenticación de usuarios y endpoints de API.
"""

import json
import mimetypes
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from . import services
from .models import TodoTask


def api_login_required(view_func):
    """Exige autenticación en API y responde 401 JSON (sin redirección HTML)."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Autenticación requerida"}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
def index_view(request):
    """Vista principal con interfaz visual completa."""
    status = request.GET.get("status", "all")
    priority = request.GET.get("priority", "")
    category = request.GET.get("category", "")
    search = request.GET.get("q", "")

    todos = services.list_todos(
        user=request.user,
        status=status,
        priority=priority,
        category=category,
        search=search,
    )
    stats = services.get_stats(user=request.user)
    categories = services.get_categories(user=request.user)

    context = {
        "todos": todos,
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
    """Acción de formulario web para crear una tarea."""
    title = request.POST.get("title", "").strip()
    description = request.POST.get("description", "").strip()
    priority = request.POST.get("priority", "media")
    category = request.POST.get("category", "General").strip() or "General"
    due_date = request.POST.get("due_date", "").strip() or None
    image = request.FILES.get("image")

    if title:
        services.create_todo(
            title=title,
            description=description,
            priority=priority,
            category=category,
            due_date=due_date,
            image=image,
            user=request.user,
        )
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
        stats = services.get_stats(user=request.user)
        return JsonResponse({"success": True, "todo": updated, "stats": stats})
    return redirect("index")


@login_required
@require_http_methods(["POST"])
def update_todo_view(request, todo_id):
    """Acción de formulario web para editar una tarea y su imagen."""
    title = request.POST.get("title", "").strip()
    description = request.POST.get("description", "").strip()
    priority = request.POST.get("priority", "media")
    category = request.POST.get("category", "General").strip() or "General"
    due_date = request.POST.get("due_date", "").strip() or None
    image = request.FILES.get("image")
    clear_image = request.POST.get("clear_image") == "on"

    updated = services.update_todo(
        todo_id,
        title=title,
        description=description,
        priority=priority,
        category=category,
        due_date=due_date,
        image=image,
        clear_image=clear_image,
        user=request.user,
    )
    if not updated:
        raise Http404("Tarea no encontrada")
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
        stats = services.get_stats(user=request.user)
        return JsonResponse({"success": True, "stats": stats})
    return redirect("index")


@login_required
def todo_image(request, todo_id):
    """Entrega una imagen privada solo a su propietario o al staff."""
    todo = get_object_or_404(TodoTask, id=todo_id)

    if not (request.user.is_staff or todo.user_id == request.user.id):
        raise Http404("Imagen no encontrada")

    if not todo.image:
        raise Http404("Imagen no encontrada")

    try:
        image_file = todo.image.open("rb")
    except FileNotFoundError:
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
            messages.success(request, f"¡Bienvenido de nuevo, {user.username}!")
            return redirect("index")
        else:
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
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect("login")


# ==========================================
# API REST (JSON)
# ==========================================

@api_login_required
@require_http_methods(["GET", "POST"])
def api_todos(request):
    """API para listar y crear tareas vía JSON o multipart."""
    if request.method == "GET":
        status = request.GET.get("status", "all")
        priority = request.GET.get("priority", "")
        category = request.GET.get("category", "")
        search = request.GET.get("q", "")
        todos = services.list_todos(user=request.user, status=status, priority=priority, category=category, search=search)
        return JsonResponse({"todos": todos, "count": len(todos)})

    elif request.method == "POST":
        image = request.FILES.get("image")
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body.decode("utf-8"))
            except Exception:
                data = {}
        else:
            data = request.POST

        title = data.get("title", "").strip()
        if not title:
            return JsonResponse({"error": "El título es obligatorio"}, status=400)

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


@api_login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def api_todo_detail(request, todo_id):
    """API para ver, actualizar o borrar tarea específica."""
    todo = services.get_todo(todo_id, user=request.user)
    if not todo:
        return JsonResponse({"error": "Tarea no encontrada"}, status=404)

    if request.method == "GET":
        return JsonResponse(todo)

    elif request.method == "PUT":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            data = request.POST

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
        return JsonResponse(updated)

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
    stats = services.get_stats(user=request.user)
    return JsonResponse(stats)
