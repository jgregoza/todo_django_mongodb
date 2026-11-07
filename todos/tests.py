import json
import os
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.template.loader import render_to_string
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from . import services, views
from .models import TodoTask
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
