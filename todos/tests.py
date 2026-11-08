import json
import os
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.template.loader import render_to_string
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from PIL import Image

from . import selectors, services, views
from .forms import TaskForm
from .models import Category, TodoTask
from .validators import parse_bool, validate_task_image


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)
class F1SecurityTests(TestCase):
    """Pruebas mínimas de F1 (autenticación, propiedad, CSRF e imágenes privadas)."""

    def setUp(self):
        self.media_dir = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir)
        self.media_override.enable()
        self.addCleanup(shutil.rmtree, self.media_dir, ignore_errors=True)
        self.addCleanup(self.media_override.disable)

        self.user_a = User.objects.create_user("alice", password="Passw0rd!123")
        self.user_b = User.objects.create_user("bob", password="Passw0rd!123")
        self.staff = User.objects.create_user(
            "staff", password="Passw0rd!123", is_staff=True
        )

        self.todo_a = TodoTask.objects.create(
            user=self.user_a,
            title="Tarea de Alice",
            description="Solo Alice",
            priority="alta",
            category="Test",
        )
        self.todo_b = TodoTask.objects.create(
            user=self.user_b,
            title="Tarea de Bob",
            description="Solo Bob",
            priority="media",
            category="Test",
        )
        self.image_todo_a = TodoTask.objects.create(
            user=self.user_a,
            title="Tarea con imagen de Alice",
            image=SimpleUploadedFile(
                "alice.png", self._png_bytes(), content_type="image/png"
            ),
        )

    @staticmethod
    def _png_bytes():
        buffer = BytesIO()
        Image.new("RGB", (2, 2), "red").save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def _csrf_token(client, path):
        client.get(path)
        return client.cookies["csrftoken"].value

    def test_web_anonymous_redirects_to_login(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("login")))

    def test_api_anonymous_get_returns_401_json(self):
        response = self.client.get(reverse("api_todos"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertNotIn("Location", response)
        self.assertIn("error", response.json())

    def test_api_anonymous_post_with_csrf_returns_401(self):
        client = Client(enforce_csrf_checks=True)
        token = self._csrf_token(client, reverse("login"))
        before = TodoTask.objects.count()

        response = client.post(
            reverse("api_todos"),
            data=json.dumps({"title": "No debe crearse"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(TodoTask.objects.count(), before)

    def test_api_authenticated_only_returns_own_tasks(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("api_todos"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        ids = {todo["id"] for todo in payload["todos"]}
        self.assertEqual(ids, {self.todo_a.id, self.image_todo_a.id})
        self.assertNotIn(self.todo_b.id, ids)

    def test_api_cannot_access_or_modify_other_users_task(self):
        self.client.force_login(self.user_b)

        response = self.client.get(
            reverse("api_todo_detail", args=[self.todo_a.id])
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.delete(
            reverse("api_todo_detail", args=[self.todo_a.id])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(TodoTask.objects.filter(id=self.todo_a.id).exists())

        response = self.client.post(
            reverse("api_toggle_todo", args=[self.todo_a.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_web_cannot_modify_other_users_task(self):
        self.client.force_login(self.user_b)

        for url in (
            reverse("toggle_todo", args=[self.todo_a.id]),
            reverse("update_todo", args=[self.todo_a.id]),
            reverse("delete_todo", args=[self.todo_a.id]),
        ):
            response = self.client.post(url, {"title": "Intento ajeno"})
            self.assertEqual(response.status_code, 404)

        self.assertTrue(TodoTask.objects.filter(id=self.todo_a.id).exists())
        self.todo_a.refresh_from_db()
        self.assertFalse(self.todo_a.completed)

    def test_web_post_without_csrf_is_forbidden(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user_a)
        response = client.post(
            reverse("create_todo"),
            {"title": "Sin CSRF", "priority": "media", "category": "Test"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(TodoTask.objects.filter(title="Sin CSRF").exists())

    def test_api_post_without_csrf_is_forbidden(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user_a)
        response = client.post(
            reverse("api_todos"),
            data=json.dumps({"title": "Sin CSRF API"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(TodoTask.objects.filter(title="Sin CSRF API").exists())

    def test_logout_get_is_not_allowed(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)

    def test_logout_post_with_csrf_logs_out(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user_a)
        token = self._csrf_token(client, reverse("index"))

        response = client.post(reverse("logout"), HTTP_X_CSRFTOKEN=token)

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", client.session)

    def test_owner_can_view_private_image(self):
        self.client.force_login(self.user_a)
        response = self.client.get(
            reverse("todo_image", args=[self.image_todo_a.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    def test_other_user_gets_404_for_private_image(self):
        self.client.force_login(self.user_b)
        response = self.client.get(
            reverse("todo_image", args=[self.image_todo_a.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_anonymous_gets_login_redirect_for_private_image(self):
        response = self.client.get(
            reverse("todo_image", args=[self.image_todo_a.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("login")))

    def test_staff_can_view_private_image(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("todo_image", args=[self.image_todo_a.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_api_views_are_not_csrf_exempt(self):
        for name in ("api_todos", "api_todo_detail", "api_toggle_todo", "api_stats"):
            self.assertFalse(getattr(getattr(views, name), "csrf_exempt", False))

    def test_user_field_is_mandatory(self):
        field = TodoTask._meta.get_field("user")
        self.assertFalse(field.null)
        self.assertFalse(field.blank)

    def test_services_filter_strictly_by_user(self):
        self.assertEqual(
            {todo["id"] for todo in services.list_todos(self.user_a)},
            {self.todo_a.id, self.image_todo_a.id},
        )
        self.assertIsNone(services.get_todo(self.todo_b.id, user=self.user_a))
        self.assertEqual(services.get_stats(user=self.user_a)["total"], 2)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)
class F3RobustnessTests(TestCase):
    """Pruebas de robustez F3: validación de imágenes, uploads, booleanos, transacciones y errores."""

    def setUp(self):
        self.media_dir = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir)
        self.media_override.enable()
        self.addCleanup(shutil.rmtree, self.media_dir, ignore_errors=True)
        self.addCleanup(self.media_override.disable)

        self.user = User.objects.create_user("charlie", password="Passw0rd!123")
        self.client.force_login(self.user)

    @staticmethod
    def _create_image(format="PNG", size=(10, 10), color="blue"):
        buffer = BytesIO()
        Image.new("RGB", size, color).save(buffer, format=format)
        return buffer.getvalue()

    def test_valid_image_upload_succeeds(self):
        image_bytes = self._create_image("JPEG")
        uploaded = SimpleUploadedFile("photo.jpg", image_bytes, content_type="image/jpeg")

        todo = services.create_todo(
            title="Tarea con JPEG válido",
            image=uploaded,
            user=self.user,
        )
        self.assertIsNotNone(todo["image_url"])
        task = TodoTask.objects.get(id=todo["id"])
        self.assertTrue(task.image)
        self.assertTrue(os.path.exists(task.image.path))

    def test_fake_image_file_is_rejected(self):
        fake_file = SimpleUploadedFile(
            "exploit.png",
            b"<?php echo 'malicioso'; ?>",
            content_type="image/png",
        )
        with self.assertRaises(ValidationError):
            services.create_todo(
                title="Intento de script",
                image=fake_file,
                user=self.user,
            )

    def test_oversized_image_is_rejected(self):
        fake_big_image = SimpleUploadedFile(
            "large.png",
            b"0" * (6 * 1024 * 1024),  # 6 MB
            content_type="image/png",
        )
        with self.assertRaises(ValidationError):
            validate_task_image(fake_big_image)

    def test_boolean_parser_prevents_false_evaluating_to_true(self):
        self.assertFalse(parse_bool("false"))
        self.assertFalse(parse_bool("0"))
        self.assertFalse(parse_bool(False))
        self.assertFalse(parse_bool(""))
        self.assertTrue(parse_bool("true"))
        self.assertTrue(parse_bool("1"))
        self.assertTrue(parse_bool(True))

    def test_api_put_boolean_parsing(self):
        todo = services.create_todo(title="Tarea para toggle", user=self.user)
        # Activar completado
        services.update_todo(todo["id"], completed=True, user=self.user)
        task = TodoTask.objects.get(id=todo["id"])
        self.assertTrue(task.completed)

        # Actualizar con string "false"
        response = self.client.put(
            reverse("api_todo_detail", args=[todo["id"]]),
            data=json.dumps({"completed": "false"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertFalse(task.completed)

    def test_orphan_image_cleaned_up_on_replacement(self):
        img1 = SimpleUploadedFile(
            "first.png", self._create_image("PNG"), content_type="image/png"
        )
        todo = services.create_todo(
            title="Tarea con imagen inicial", image=img1, user=self.user
        )
        task = TodoTask.objects.get(id=todo["id"])
        old_path = task.image.path
        self.assertTrue(os.path.exists(old_path))

        img2 = SimpleUploadedFile(
            "second.png",
            self._create_image("PNG", color="green"),
            content_type="image/png",
        )

        # El callback se ejecuta al simular la confirmaci?n de la transacci?n.
        with self.captureOnCommitCallbacks(execute=True):
            services.update_todo(todo["id"], image=img2, user=self.user)

        task.refresh_from_db()
        new_path = task.image.path

        self.assertNotEqual(old_path, new_path)
        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(os.path.exists(new_path))

    def test_orphan_image_cleaned_up_on_deletion(self):
        img = SimpleUploadedFile(
            "to_delete.png", self._create_image("PNG"), content_type="image/png"
        )
        todo = services.create_todo(
            title="Tarea a eliminar", image=img, user=self.user
        )
        task = TodoTask.objects.get(id=todo["id"])
        path = task.image.path
        self.assertTrue(os.path.exists(path))

        with self.captureOnCommitCallbacks(execute=True):
            result = services.delete_todo(todo["id"], user=self.user)

        self.assertTrue(result)
        self.assertFalse(os.path.exists(path))

    def test_old_image_is_preserved_when_outer_transaction_rolls_back(self):
        img1 = SimpleUploadedFile(
            "rollback_original.png",
            self._create_image("PNG"),
            content_type="image/png",
        )
        todo = services.create_todo(
            title="Tarea para rollback", image=img1, user=self.user
        )
        task = TodoTask.objects.get(id=todo["id"])
        old_path = task.image.path
        old_name = task.image.name
        self.assertTrue(os.path.exists(old_path))

        img2 = SimpleUploadedFile(
            "rollback_new.png",
            self._create_image("PNG", color="green"),
            content_type="image/png",
        )

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    services.update_todo(todo["id"], image=img2, user=self.user)
                    raise RuntimeError("Simulaci?n de rollback externo")

        task.refresh_from_db()

        self.assertEqual(task.image.name, old_name)
        self.assertTrue(os.path.exists(old_path))
        self.assertEqual(len(callbacks), 0)

    def test_create_rejects_unauthenticated_user(self):
        with self.assertRaises(ValueError):
            services.create_todo(title="Sin usuario", user=None)

    def test_create_rejects_title_over_200_characters(self):
        with self.assertRaises(ValueError):
            services.create_todo(title="X" * 201, user=self.user)

    def test_create_handles_invalid_due_date(self):
        result = services.create_todo(
            title="Fecha inválida",
            due_date="fecha-invalida",
            user=self.user,
        )
        task = TodoTask.objects.get(id=result["id"])
        self.assertIsNone(task.due_date)

    def test_update_returns_none_for_missing_task(self):
        self.assertIsNone(
            services.update_todo(999999, title="No existe", user=self.user)
        )

    def test_update_returns_none_for_invalid_title(self):
        todo = services.create_todo(title="Título válido", user=self.user)
        result = services.update_todo(todo["id"], title="   ", user=self.user)
        self.assertIsNone(result)

    def test_update_ignores_invalid_due_date(self):
        todo = services.create_todo(title="Fecha", user=self.user)
        result = services.update_todo(
            todo["id"], due_date="fecha-invalida", user=self.user
        )
        self.assertIsNotNone(result)
        task = TodoTask.objects.get(id=todo["id"])
        self.assertIsNone(task.due_date)

    def test_toggle_returns_none_for_missing_task(self):
        self.assertIsNone(services.toggle_todo(999999, user=self.user))

    def test_delete_returns_false_for_missing_task(self):
        self.assertFalse(services.delete_todo(999999, user=self.user))

    def test_update_clear_image_removes_image_after_commit(self):
        uploaded = SimpleUploadedFile(
            "clear.png", self._create_image("PNG"), content_type="image/png"
        )
        todo = services.create_todo(
            title="Limpiar imagen", image=uploaded, user=self.user
        )
        task = TodoTask.objects.get(id=todo["id"])
        old_path = task.image.path

        with self.captureOnCommitCallbacks(execute=True):
            result = services.update_todo(
                todo["id"], clear_image=True, user=self.user
            )

        self.assertIsNotNone(result)
        task.refresh_from_db()
        self.assertFalse(task.image)
        self.assertFalse(os.path.exists(old_path))
    def test_empty_or_whitespace_title_rejected(self):
        with self.assertRaises(ValueError):
            services.create_todo(title="   ", user=self.user)

        response = self.client.post(
            reverse("api_todos"),
            data=json.dumps({"title": "   "}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_title_longer_than_200_chars_rejected(self):
        long_title = "A" * 201
        with self.assertRaises(ValueError):
            services.create_todo(title=long_title, user=self.user)

        response = self.client.post(
            reverse("api_todos"),
            data=json.dumps({"title": long_title}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_json_body_returns_400(self):
        response = self.client.post(
            reverse("api_todos"),
            data="Esto no es JSON válido {{{",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_error_templates_exist_and_render(self):
        for template_name in ("400.html", "403.html", "404.html", "500.html"):
            rendered = render_to_string(template_name)
            self.assertIn("TaskPilot", rendered)
            self.assertIn("<!DOCTYPE html>", rendered)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)
class F4QualityTests(TestCase):
    """Pruebas de calidad F4: API v1 versionada, selectores, paginación y suite completa."""

    def setUp(self):
        self.media_dir = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir)
        self.media_override.enable()
        self.addCleanup(shutil.rmtree, self.media_dir, ignore_errors=True)
        self.addCleanup(self.media_override.disable)

        self.user = User.objects.create_user("daniela", password="Passw0rd!123")
        self.client.force_login(self.user)

        # Crear 15 tareas para pruebas de paginación
        self.tasks = []
        for i in range(15):
            self.tasks.append(
                TodoTask.objects.create(
                    user=self.user,
                    title=f"Tarea {i+1:02d}",
                    priority="alta" if i % 2 == 0 else "baja",
                    category="Trabajo" if i % 3 == 0 else "Personal",
                )
            )

    def test_api_v1_endpoints_availability(self):
        # GET /api/v1/todos/
        response = self.client.get(reverse("api_v1_todos"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 15)

        # GET /api/v1/todos/stats/
        stats_response = self.client.get(reverse("api_v1_stats"))
        self.assertEqual(stats_response.status_code, 200)
        self.assertEqual(stats_response.json()["total"], 15)

        # GET /api/v1/todos/<id>/
        detail_response = self.client.get(
            reverse("api_v1_todo_detail", args=[self.tasks[0].id])
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["id"], self.tasks[0].id)

    def test_api_pagination_structure(self):
        # Solicitar página 1 con 5 elementos
        response = self.client.get(
            reverse("api_v1_todos"),
            {"page": 1, "per_page": 5},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["todos"]), 5)
        self.assertEqual(data["count"], 15)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["total_pages"], 3)
        self.assertTrue(data["has_next"])
        self.assertFalse(data["has_previous"])

        # Solicitar página 3
        response_page3 = self.client.get(
            reverse("api_v1_todos"),
            {"page": 3, "per_page": 5},
        )
        data3 = response_page3.json()
        self.assertEqual(data3["page"], 3)
        self.assertFalse(data3["has_next"])
        self.assertTrue(data3["has_previous"])

    def test_selectors_layer_isolation(self):
        from . import selectors

        qs = selectors.list_todos_queryset(user=self.user, priority="alta")
        self.assertTrue(qs.count() > 0)
        for t in qs:
            self.assertEqual(t.priority, "alta")

        stats = selectors.get_stats(user=self.user)
        self.assertEqual(stats["total"], 15)

        categories = selectors.get_categories(user=self.user)
        self.assertIn("Trabajo", categories)
        self.assertIn("Personal", categories)

    def test_web_index_pagination_context(self):
        response = self.client.get(reverse("index"), {"page": 1})
        self.assertEqual(response.status_code, 200)
        self.assertIn("page_obj", response.context)
        self.assertEqual(len(response.context["todos"]), 12)  # 12 por página por defecto
        self.assertTrue(response.context["page_obj"].has_next())

    def test_web_crud_views_coverage(self):
        # 1. Crear tarea vía formulario web
        res = self.client.post(
            reverse("create_todo"),
            {
                "title": "Nueva Tarea Web",
                "description": "Detalle",
                "priority": "alta",
                "category": "Trabajo",
                "due_date": "2026-12-31",
            },
        )
        self.assertEqual(res.status_code, 302)
        created = TodoTask.objects.get(title="Nueva Tarea Web")

        # 2. Alternar estado vía web (POST regular y AJAX)
        res = self.client.post(reverse("toggle_todo", args=[created.id]))
        self.assertEqual(res.status_code, 302)
        created.refresh_from_db()
        self.assertTrue(created.completed)

        res_ajax = self.client.post(
            reverse("toggle_todo", args=[created.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(res_ajax.status_code, 200)
        self.assertTrue(res_ajax.json()["success"])

        # 3. Actualizar tarea vía formulario web
        res = self.client.post(
            reverse("update_todo", args=[created.id]),
            {
                "title": "Tarea Web Editada",
                "priority": "baja",
                "category": "Personal",
                "due_date": "",
            },
        )
        self.assertEqual(res.status_code, 302)
        created.refresh_from_db()
        self.assertEqual(created.title, "Tarea Web Editada")

        # 4. Eliminar vía AJAX y web
        res_del_ajax = self.client.post(
            reverse("delete_todo", args=[created.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(res_del_ajax.status_code, 200)
        self.assertFalse(TodoTask.objects.filter(id=created.id).exists())

    def test_auth_views_login_register(self):
        # Cliente sin autenticar
        anon_client = Client()

        # GET login y register
        self.assertEqual(anon_client.get(reverse("login")).status_code, 200)
        self.assertEqual(anon_client.get(reverse("register")).status_code, 200)

        # Login inválido
        res_fail = anon_client.post(
            reverse("login"),
            {"username": "noexiste", "password": "wrong"},
        )
        self.assertEqual(res_fail.status_code, 200)

        # Login exitoso
        res_login = anon_client.post(
            reverse("login"),
            {"username": "daniela", "password": "Passw0rd!123"},
        )
        self.assertEqual(res_login.status_code, 302)

    def test_filter_and_search_queries(self):
        # Filtro status=completed
        res = self.client.get(reverse("index"), {"status": "completed"})
        self.assertEqual(res.status_code, 200)

        # Filtro status=pending
        res = self.client.get(reverse("index"), {"status": "pending"})
        self.assertEqual(res.status_code, 200)

        # Filtro de búsqueda y categoría
        res = self.client.get(reverse("index"), {"q": "Tarea 01", "category": "Trabajo"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context["todos"]), 1)

    def test_admin_badges_and_preview(self):
        from django.contrib.admin.sites import AdminSite

        from .admin import TodoTaskAdmin

        admin_instance = TodoTaskAdmin(TodoTask, AdminSite())
        task = self.tasks[0]

        badge = admin_instance.priority_badge(task)
        self.assertIn("span", badge)

        preview_none = admin_instance.image_preview(task)
        self.assertEqual(preview_none, "-")

    def test_views_edge_cases_and_auth_redirects(self):
        # 1. Redirección de usuario ya autenticado en login y register
        self.assertEqual(self.client.get(reverse("login")).status_code, 302)
        self.assertEqual(self.client.get(reverse("register")).status_code, 302)

        # 2. Update con título vacío
        res_empty = self.client.post(
            reverse("update_todo", args=[self.tasks[0].id]),
            {"title": "   "},
        )
        self.assertEqual(res_empty.status_code, 302)

        # 3. Update con clear_image
        res_clear = self.client.post(
            reverse("update_todo", args=[self.tasks[0].id]),
            {"title": "Con imagen limpia", "clear_image": "on"},
        )
        self.assertEqual(res_clear.status_code, 302)

        # 4. Toggle y Delete AJAX de tarea inexistente (404 JSON)
        res_toggle_404 = self.client.post(
            reverse("toggle_todo", args=[99999]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(res_toggle_404.status_code, 404)

        res_del_404 = self.client.post(
            reverse("delete_todo", args=[99999]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(res_del_404.status_code, 404)

        # 5. Registro exitoso de nuevo usuario
        anon = Client()
        res_reg = anon.post(
            reverse("register"),
            {
                "username": "nuevo_usuario",
                "password1": "Secr3tP@ssw0rd!99",
                "password2": "Secr3tP@ssw0rd!99",
            },
        )
        self.assertEqual(res_reg.status_code, 302)
        self.assertTrue(User.objects.filter(username="nuevo_usuario").exists())


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)
class FilterPartialUpdateTests(TestCase):
    """Pruebas de la actualización dinámica de filtros mediante fragmento HTML."""

    def setUp(self):
        self.user = User.objects.create_user("filters", password="Passw0rd!123")
        self.client.force_login(self.user)
        for i in range(15):
            TodoTask.objects.create(
                user=self.user,
                title=f"Tarea {i + 1:02d}",
                priority="alta" if i % 2 == 0 else "baja",
                category="Trabajo" if i % 3 == 0 else "Personal",
            )

    def test_ajax_request_returns_only_task_list_fragment(self):
        response = self.client.get(
            reverse("index"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "todos/_task_list.html")
        content = response.content.decode()
        self.assertNotIn("<!DOCTYPE html>", content)
        self.assertNotIn("<title>", content)
        self.assertIn("Tarea 15", content)

    def test_ajax_request_applies_combined_filters(self):
        response = self.client.get(
            reverse("index"),
            {
                "priority": "alta",
                "category": "Trabajo",
                "q": "Tarea",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        titles = {todo["title"] for todo in response.context["todos"]}
        self.assertEqual(titles, {"Tarea 01", "Tarea 07", "Tarea 13"})

    def test_ajax_pagination_links_keep_active_filters(self):
        response = self.client.get(
            reverse("index"),
            {"status": "pending", "q": "Tarea"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["todos"]), 12)
        content = response.content.decode()
        self.assertIn("status=pending", content)
        self.assertIn("q=Tarea", content)
        self.assertIn('data-page="2"', content)

    def test_ajax_search_returns_matching_task(self):
        response = self.client.get(
            reverse("index"),
            {"q": "Tarea 07"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {todo["title"] for todo in response.context["todos"]},
            {"Tarea 07"},
        )

    def test_ajax_second_page_keeps_combined_filters(self):
        for i in range(15):
            TodoTask.objects.create(
                user=self.user,
                title=f"Extra {i + 1:02d}",
                priority="alta",
                category="Trabajo",
            )

        response = self.client.get(
            reverse("index"),
            {
                "priority": "alta",
                "category": "Trabajo",
                "page": 2,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["todos"]), 6)
        content = response.content.decode()
        self.assertIn("priority=alta", content)
        self.assertIn("category=Trabajo", content)
        self.assertIn("page=1", content)

    def test_full_page_exposes_category_combo_with_user_categories_only(self):
        services.create_todo(title="Con categoría", category="Trabajo", user=self.user)
        other = User.objects.create_user("otro_usuario", password="Passw0rd!123")
        services.create_todo(
            title="Tarea ajena", category="SoloOtro", user=other
        )

        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="category-options"')
        self.assertContains(response, 'list="category-options"')
        self.assertContains(response, "Trabajo")
        self.assertNotContains(response, "SoloOtro")


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)
class CategoryTests(TestCase):
    """Categorías privadas por usuario, normalización y validaciones."""

    def setUp(self):
        self.alice = User.objects.create_user("alice_cat", password="Passw0rd!123")
        self.bob = User.objects.create_user("bob_cat", password="Passw0rd!123")

    def test_new_category_is_created_automatically(self):
        todo = services.create_todo(
            title="Tarea nueva", category="Proyectos 2027", user=self.alice
        )

        category = Category.objects.get(user=self.alice)
        self.assertEqual(category.name, "Proyectos 2027")
        self.assertEqual(category.normalized_name, "proyectos 2027")
        self.assertEqual(todo["category"], "Proyectos 2027")

    def test_existing_category_is_reused_ignoring_case_and_spaces(self):
        services.create_todo(title="Primera", category="Trabajo", user=self.alice)
        second = services.create_todo(
            title="Segunda", category="   trabajo   ", user=self.alice
        )

        self.assertEqual(Category.objects.filter(user=self.alice).count(), 1)
        self.assertEqual(second["category"], "Trabajo")
        self.assertEqual(selectors.get_categories(self.alice), ["Trabajo"])

    def test_category_names_collapse_internal_whitespace(self):
        services.create_todo(
            title="Con espacios", category="  Mi   Categoría  ", user=self.alice
        )

        category = Category.objects.get(user=self.alice)
        self.assertEqual(category.name, "Mi Categoría")
        self.assertEqual(category.normalized_name, "mi categoría")

    def test_duplicate_constraint_is_enforced_by_database(self):
        Category.objects.create(user=self.alice, name="Repetida")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(user=self.alice, name="  repetida ")

        self.assertEqual(Category.objects.filter(user=self.alice).count(), 1)

    def test_categories_are_isolated_between_users(self):
        services.create_todo(title="Alice", category="Privada", user=self.alice)
        services.create_todo(title="Bob", category="SoloBob", user=self.bob)

        self.assertEqual(selectors.get_categories(self.alice), ["Privada"])
        self.assertEqual(selectors.get_categories(self.bob), ["SoloBob"])
        self.assertEqual(Category.objects.filter(user=self.alice).count(), 1)
        self.assertEqual(Category.objects.filter(user=self.bob).count(), 1)

    def test_foreign_category_name_creates_current_users_own_category(self):
        services.create_todo(title="De Bob", category="SoloBob", user=self.bob)
        bob_category = Category.objects.get(user=self.bob, name="SoloBob")

        todo = services.create_todo(
            title="De Alice", category="solobob", user=self.alice
        )

        alice_category = Category.objects.get(user=self.alice, name="solobob")
        self.assertNotEqual(alice_category.id, bob_category.id)
        self.assertEqual(todo["category"], "solobob")
        self.assertEqual(selectors.get_categories(self.alice), ["solobob"])
        self.assertEqual(selectors.get_categories(self.bob), ["SoloBob"])

    def test_empty_category_defaults_to_general(self):
        todo = services.create_todo(
            title="Sin categoría", category="   ", user=self.alice
        )

        self.assertEqual(todo["category"], "General")
        self.assertTrue(
            Category.objects.filter(
                user=self.alice, normalized_name="general"
            ).exists()
        )

    def test_overlong_category_is_rejected_on_create(self):
        with self.assertRaises(ValueError):
            services.create_todo(
                title="Categoría inválida", category="x" * 51, user=self.alice
            )

        self.assertFalse(TodoTask.objects.filter(user=self.alice).exists())

    def test_overlong_category_is_rejected_on_update(self):
        todo = services.create_todo(
            title="Original", category="Original", user=self.alice
        )

        result = services.update_todo(
            todo["id"], category="y" * 51, user=self.alice
        )

        self.assertIsNone(result)
        task = TodoTask.objects.get(id=todo["id"])
        self.assertEqual(task.category, "Original")

    def test_update_reuses_existing_category_without_duplicates(self):
        services.create_todo(title="Uno", category="Trabajo", user=self.alice)
        todo = services.create_todo(
            title="Dos", category="Personal", user=self.alice
        )

        updated = services.update_todo(
            todo["id"], category="  trabajo  ", user=self.alice
        )

        self.assertEqual(updated["category"], "Trabajo")
        self.assertEqual(Category.objects.filter(user=self.alice).count(), 2)

    def test_form_validates_category_length(self):
        form = TaskForm(
            data={
                "title": "Tarea",
                "priority": "media",
                "category": "z" * 51,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_form_defaults_empty_category_to_general(self):
        form = TaskForm(
            data={
                "title": "Tarea",
                "priority": "media",
                "category": "   ",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["category"], "General")

    def test_web_form_uses_existing_category(self):
        services.create_todo(title="Previa", category="Trabajo", user=self.alice)
        self.client.force_login(self.alice)

        response = self.client.post(
            reverse("create_todo"),
            {
                "title": "Creada desde web",
                "priority": "media",
                "category": "trabajo",
            },
        )

        self.assertEqual(response.status_code, 302)
        task = TodoTask.objects.get(title="Creada desde web")
        self.assertEqual(task.category, "Trabajo")
        self.assertEqual(Category.objects.filter(user=self.alice).count(), 1)

    def test_api_creates_category_and_rejects_invalid_names(self):
        self.client.force_login(self.alice)

        response = self.client.post(
            reverse("api_v1_todos"),
            data=json.dumps({"title": "Desde API", "category": "Nueva API"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["category"], "Nueva API")
        self.assertTrue(
            Category.objects.filter(
                user=self.alice, normalized_name="nueva api"
            ).exists()
        )

        invalid = self.client.post(
            reverse("api_v1_todos"),
            data=json.dumps({"title": "Inválida", "category": "q" * 51}),
            content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertFalse(TodoTask.objects.filter(title="Inválida").exists())

    def test_existing_tasks_keep_their_category(self):
        legacy = TodoTask.objects.create(
            user=self.alice, title="Legacy", category="Categoría antigua"
        )
        TodoTask.objects.create(
            user=self.alice, title="Otra", category="Otra categoría"
        )

        updated = services.update_todo(
            legacy.id, title="Legacy actualizada", user=self.alice
        )

        self.assertEqual(updated["category"], "Categoría antigua")
        legacy.refresh_from_db()
        self.assertEqual(legacy.title, "Legacy actualizada")
        self.assertIn("Categoría antigua", selectors.get_categories(self.alice))


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
class NavigationAndFilterSafetyTests(TestCase):
    """Página 404 real y tolerancia a parámetros de filtros inválidos."""

    def setUp(self):
        self.user = User.objects.create_user("nav_user", password="Passw0rd!123")
        for i in range(3):
            TodoTask.objects.create(
                user=self.user,
                title=f"Tarea {i + 1}",
                priority="media",
                category="General",
            )

    def _assert_404_page(self, response):
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Página no encontrada", status_code=404)
        self.assertContains(response, reverse("index"), status_code=404)
        self.assertNotIn("Location", response)

    def test_unknown_route_returns_404_for_anonymous_user(self):
        self._assert_404_page(self.client.get("/ruta-que-no-existe/"))

    def test_unknown_route_returns_404_for_authenticated_user(self):
        self.client.force_login(self.user)
        self._assert_404_page(self.client.get("/otra-ruta-inexistente/"))

    def test_invalid_filter_parameters_do_not_break_index(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("index"),
            {
                "status": "inventado",
                "priority": "urgente",
                "category": "c" * 200,
                "q": "<script>alert(1)</script>",
                "page": "no-es-un-numero",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_out_of_range_pages_are_clamped(self):
        self.client.force_login(self.user)

        for page in ("999999", "-5", "0"):
            response = self.client.get(reverse("index"), {"page": page})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["page_obj"].number, 1)

    def test_api_invalid_pagination_parameters_are_safe(self):
        self.client.force_login(self.user)

        for per_page in ("0", "-10", "abc", "1000000"):
            response = self.client.get(
                reverse("api_v1_todos"),
                {"page": 1, "per_page": per_page},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["count"], 3)

    def test_valid_routes_still_work(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("index")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("api_v1_todos")).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("api_v1_stats")).status_code, 200
        )

        anonymous = Client()
        self.assertEqual(anonymous.get(reverse("login")).status_code, 200)
        self.assertEqual(anonymous.get(reverse("register")).status_code, 200)


class CategoryMigrationTests(TransactionTestCase):
    """La migración registra categorías sin alterar las tareas existentes."""

    migrate_from = [("todos", "0003_todotask_user_required")]
    migrate_to = [("todos", "0004_category")]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        UserModel = old_apps.get_model("auth", "User")
        OldTodoTask = old_apps.get_model("todos", "TodoTask")

        self.user = UserModel.objects.create(username="legacy_user")
        self.task_ids = [
            OldTodoTask.objects.create(
                user_id=self.user.id, title="Uno", category="Trabajo"
            ).id,
            OldTodoTask.objects.create(
                user_id=self.user.id, title="Dos", category=" trabajo "
            ).id,
            OldTodoTask.objects.create(
                user_id=self.user.id, title="Tres", category="Personal"
            ).id,
        ]

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_migration_preserves_tasks_and_seeds_categories(self):
        apps = MigrationExecutor(connection).loader.project_state(
            self.migrate_to
        ).apps
        TodoTaskModel = apps.get_model("todos", "TodoTask")
        CategoryModel = apps.get_model("todos", "Category")

        self.assertEqual(
            list(
                TodoTaskModel.objects.filter(id__in=self.task_ids)
                .order_by("id")
                .values_list("category", flat=True)
            ),
            ["Trabajo", " trabajo ", "Personal"],
        )
        self.assertEqual(
            CategoryModel.objects.filter(user_id=self.user.id).count(), 2
        )

    def test_migration_reversal_keeps_task_data(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        apps = executor.loader.project_state(self.migrate_from).apps
        TodoTaskModel = apps.get_model("todos", "TodoTask")

        self.assertEqual(
            TodoTaskModel.objects.filter(id__in=self.task_ids).count(), 3
        )
        self.assertEqual(
            list(
                TodoTaskModel.objects.filter(id__in=self.task_ids)
                .order_by("id")
                .values_list("category", flat=True)
            ),
            ["Trabajo", " trabajo ", "Personal"],
        )
