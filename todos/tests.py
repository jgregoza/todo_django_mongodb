from django.test import TestCase, Client
from django.urls import reverse
from .models import TodoTask
from . import services


class TodoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.todo = TodoTask.objects.create(
            title="Tarea de prueba inicial",
            description="Descripción de prueba",
            priority="alta",
            category="Test",
        )

    def test_index_view(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tarea de prueba inicial")

    def test_create_todo(self):
        response = self.client.post(
            reverse("create_todo"),
            {
                "title": "Nueva tarea desde test",
                "description": "Detalles",
                "priority": "media",
                "category": "Trabajo",
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue(TodoTask.objects.filter(title="Nueva tarea desde test").exists())

    def test_toggle_todo(self):
        self.assertFalse(self.todo.completed)
        response = self.client.post(reverse("toggle_todo", args=[self.todo.id]))
        self.assertEqual(response.status_code, 302)
        self.todo.refresh_from_db()
        self.assertTrue(self.todo.completed)

    def test_update_todo(self):
        response = self.client.post(
            reverse("update_todo", args=[self.todo.id]),
            {
                "title": "Título Modificado",
                "description": "Nueva descripción",
                "priority": "baja",
                "category": "Personal",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.todo.refresh_from_db()
        self.assertEqual(self.todo.title, "Título Modificado")
        self.assertEqual(self.todo.priority, "baja")

    def test_delete_todo(self):
        todo_to_delete = TodoTask.objects.create(title="Para borrar")
        response = self.client.post(reverse("delete_todo", args=[todo_to_delete.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TodoTask.objects.filter(id=todo_to_delete.id).exists())

    def test_api_todos_get_and_post(self):
        # GET
        response = self.client.get(reverse("api_todos"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("todos", data)

        # POST
        response = self.client.post(
            reverse("api_todos"),
            {"title": "Tarea API", "priority": "alta"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["title"], "Tarea API")

    def test_api_stats(self):
        response = self.client.get(reverse("api_stats"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total", data)
        self.assertIn("completed", data)
        self.assertIn("pending", data)
