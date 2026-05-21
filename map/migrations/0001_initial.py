from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CommunityFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(blank=True, max_length=120)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("suggestion", "Suggestion"),
                            ("correction", "Resource correction"),
                            ("bug", "Bug report"),
                            ("experience", "Service experience"),
                        ],
                        max_length=24,
                    ),
                ),
                ("title", models.CharField(max_length=160)),
                ("body", models.TextField()),
                ("approved", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
