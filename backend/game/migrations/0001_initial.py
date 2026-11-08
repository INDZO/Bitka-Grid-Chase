# Generated manually for the Bitka Grid Chase project scaffold.

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Game",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("room_code", models.CharField(max_length=12, unique=True)),
                ("mode", models.CharField(max_length=10)),
                ("board_size", models.PositiveSmallIntegerField()),
                ("ai_level", models.CharField(blank=True, max_length=20)),
                ("seed", models.PositiveIntegerField()),
                ("status", models.CharField(default="waiting", max_length=20)),
                ("state", models.JSONField(blank=True, default=dict)),
                ("result", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="GameResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("winner", models.CharField(max_length=20)),
                ("reason", models.CharField(max_length=120)),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("stats", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "game",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="game_result", to="game.game"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AIStat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("algorithm", models.CharField(max_length=40)),
                ("move_number", models.PositiveIntegerField()),
                ("decision_ms", models.FloatField()),
                ("nodes", models.PositiveIntegerField(default=0)),
                ("selected_move", models.JSONField(blank=True, default=dict)),
                ("used_teleport", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "game",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_stats", to="game.game"),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="Move",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("turn_number", models.PositiveIntegerField()),
                ("actor_entity_id", models.CharField(max_length=20)),
                ("actor_role", models.CharField(max_length=20)),
                ("action_type", models.CharField(max_length=20)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("valid", models.BooleanField(default=True)),
                ("skipped_reason", models.CharField(blank=True, max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "game",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="moves", to="game.game"),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="Player",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("role", models.CharField(max_length=20)),
                ("entity_id", models.CharField(max_length=20)),
                ("skin", models.CharField(blank=True, max_length=40)),
                ("connected", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "game",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="players", to="game.game"),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
