from django.urls import path
from . import views

urlpatterns = [
    # UI Web endpoints
    path("", views.index_view, name="index"),
    path("todos/create/", views.create_todo_view, name="create_todo"),
    path("todos/<int:todo_id>/toggle/", views.toggle_todo_view, name="toggle_todo"),
    path("todos/<int:todo_id>/update/", views.update_todo_view, name="update_todo"),
    path("todos/<int:todo_id>/delete/", views.delete_todo_view, name="delete_todo"),
    path("todos/<int:todo_id>/image/", views.todo_image, name="todo_image"),

    # Autenticación (Logins)
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),

    # REST API endpoints
    path("api/todos/", views.api_todos, name="api_todos"),
    path("api/todos/stats/", views.api_stats, name="api_stats"),
    path("api/todos/<int:todo_id>/", views.api_todo_detail, name="api_todo_detail"),
    path("api/todos/<int:todo_id>/toggle/", views.api_toggle_todo, name="api_toggle_todo"),
]
