import uuid

from django.db import models


class Game(models.Model):
    STATUS_WAITING = "waiting"
    STATUS_PLAYING = "playing"
    STATUS_FINISHED = "finished"

    MODE_1VAI = "1vAI"
    MODE_1V1 = "1v1"
    MODE_2VAI = "2vAI"

    room_code = models.CharField(max_length=12, unique=True)
    mode = models.CharField(max_length=10)
    board_size = models.PositiveSmallIntegerField()
    ai_level = models.CharField(max_length=20, blank=True)
    seed = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default=STATUS_WAITING)
    state = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.room_code} ({self.mode})"


class Player(models.Model):
    ROLE_HERO = "hero"
    ROLE_MONSTER = "monster"

    game = models.ForeignKey(Game, related_name="players", on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    role = models.CharField(max_length=20)
    entity_id = models.CharField(max_length=20)
    skin = models.CharField(max_length=40, blank=True)
    connected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}:{self.entity_id}@{self.game.room_code}"


class Move(models.Model):
    game = models.ForeignKey(Game, related_name="moves", on_delete=models.CASCADE)
    turn_number = models.PositiveIntegerField()
    actor_entity_id = models.CharField(max_length=20)
    actor_role = models.CharField(max_length=20)
    action_type = models.CharField(max_length=20)
    payload = models.JSONField(default=dict, blank=True)
    valid = models.BooleanField(default=True)
    skipped_reason = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class AIStat(models.Model):
    game = models.ForeignKey(Game, related_name="ai_stats", on_delete=models.CASCADE)
    algorithm = models.CharField(max_length=40)
    move_number = models.PositiveIntegerField()
    decision_ms = models.FloatField()
    nodes = models.PositiveIntegerField(default=0)
    selected_move = models.JSONField(default=dict, blank=True)
    used_teleport = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class GameResult(models.Model):
    game = models.OneToOneField(Game, related_name="game_result", on_delete=models.CASCADE)
    winner = models.CharField(max_length=20)
    reason = models.CharField(max_length=120)
    duration_ms = models.PositiveIntegerField(default=0)
    stats = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.game.room_code}: {self.winner}"
