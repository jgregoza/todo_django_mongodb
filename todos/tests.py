import json
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from . import services, views
from .models import TodoTask


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
