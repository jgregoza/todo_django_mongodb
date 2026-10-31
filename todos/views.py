"""
Vistas web y endpoints de API para la gestión de tareas con soporte de imágenes.
"""

import json
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from . import services


def index_view(request):
    """Vista principal con interfaz visual completa."""
    status = request.GET.get("status", "all")
    priority = request.GET.get("priority", "")
    category = request.GET.get("category", "")
    search = request.GET.get("q", "")

    todos = services.list_todos(
        status=status,
        priority=priority,
        category=category,
        search=search,
    )
    stats = services.get_stats()
    categories = services.get_categories()

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


@require_http_methods(["POST"])
def create_todo_view(request):
    """Acción de formulario web para crear una tarea, incluyendo subida de imágenes."""
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
        )
    return redirect("index")


@require_http_methods(["POST"])
def toggle_todo_view(request, todo_id):
    """Acción de alternar estado de completado desde formulario o fetch AJAX."""
    updated = services.toggle_todo(todo_id)
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept") == "application/json":
        if updated:
            stats = services.get_stats()
            return JsonResponse({"success": True, "todo": updated, "stats": stats})
        return JsonResponse({"success": False, "error": "Tarea no encontrada"}, status=404)
    return redirect("index")


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

    services.update_todo(
        todo_id,
        title=title,
        description=description,
        priority=priority,
        category=category,
        due_date=due_date,
        image=image,
        clear_image=clear_image,
    )
    return redirect("index")


@require_http_methods(["POST"])
def delete_todo_view(request, todo_id):
    """Acción de eliminar tarea."""
    deleted = services.delete_todo(todo_id)
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept") == "application/json":
        stats = services.get_stats()
        return JsonResponse({"success": deleted, "stats": stats})
    return redirect("index")


# ==========================================
# API REST (JSON)
# ==========================================

@require_http_methods(["GET", "POST"])
@csrf_exempt
def api_todos(request):
    """API para listar y crear tareas vía JSON o multipart."""
    if request.method == "GET":
        status = request.GET.get("status", "all")
        priority = request.GET.get("priority", "")
        category = request.GET.get("category", "")
        search = request.GET.get("q", "")
        todos = services.list_todos(status=status, priority=priority, category=category, search=search)
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
        )
        return JsonResponse(todo, status=201)


@require_http_methods(["GET", "PUT", "DELETE"])
@csrf_exempt
def api_todo_detail(request, todo_id):
    """API para ver, actualizar o borrar tarea específica."""
    todo = services.get_todo(todo_id)
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
        )
        return JsonResponse(updated)

    elif request.method == "DELETE":
        services.delete_todo(todo_id)
        return JsonResponse({"deleted": True, "id": todo_id})


@require_http_methods(["POST", "PATCH"])
@csrf_exempt
def api_toggle_todo(request, todo_id):
    """API para alternar completado."""
    updated = services.toggle_todo(todo_id)
    if not updated:
        return JsonResponse({"error": "Tarea no encontrada"}, status=404)
    return JsonResponse(updated)


def api_stats(request):
    """API con estadísticas generales."""
    stats = services.get_stats()
    return JsonResponse(stats)
