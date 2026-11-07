import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("todos", "0002_todotask_user"),
    ]

    operations = [
        migrations.AlterField(
            model_name="todotask",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="todos",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Usuario",
            ),
        ),
    ]
