from urllib.parse import parse_qs

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from game.engine import GameError, apply_player_action, apply_turn_timeout, maybe_run_ai_turns, serialize_game
from game.models import Game, Player


class GameConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
        self.group_name = f"game_{self.room_code}"
        query = parse_qs(self.scope.get("query_string", b"").decode("utf-8"))
        self.player_token = query.get("token", [None])[0]

        if not Game.objects.filter(room_code=self.room_code).exists():
            self.close(code=4404)
            return

        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()
        self._set_connected(True)
        game = Game.objects.get(room_code=self.room_code)
        self.send_json({"type": "state", "payload": serialize_game(game)})

    def disconnect(self, close_code):
        self._set_connected(False)
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    def receive_json(self, content, **kwargs):
        message_type = content.get("type")
        try:
            game = Game.objects.get(room_code=self.room_code)
            if message_type == "move":
                token = content.get("player_token") or self.player_token
                if not token:
                    raise GameError("Token igrača je obavezan za potez.")
                apply_player_action(game, token, content.get("action", {}))
                maybe_run_ai_turns(game)
                game.refresh_from_db()
                self._broadcast(game)
            elif message_type == "timeout":
                apply_turn_timeout(game)
                maybe_run_ai_turns(game)
                game.refresh_from_db()
                self._broadcast(game)
            elif message_type == "sync":
                self.send_json({"type": "state", "payload": serialize_game(game)})
            else:
                raise GameError("Nepoznata WebSocket poruka.")
        except Game.DoesNotExist:
            self.send_json({"type": "error", "message": "Partija ne postoji."})
        except GameError as exc:
            self.send_json({"type": "error", "message": str(exc)})

    def game_update(self, event):
        self.send_json({"type": "state", "payload": event["payload"]})

    def _broadcast(self, game):
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {"type": "game.update", "payload": serialize_game(game)},
        )

    def _set_connected(self, connected):
        if not self.player_token:
            return
        Player.objects.filter(game__room_code=self.room_code, token=self.player_token).update(connected=connected)
