from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from django.utils import timezone

from ai.algorithms import select_ai_move
from config.asgi import application
from game.config import BOARD_CONFIGS, DIRECTIONS
from game.engine import GameError, apply_player_action, create_game, join_game, maybe_run_ai_turns
from game.models import Game


class EngineTests(TestCase):
    def test_generates_valid_map_with_reachable_targets(self):
        game, _ = create_game("1vAI", 6, "astar", "Scout", seed=12345)
        state = game.state
        walls = {tuple(pos) for pos in state["board"]["walls"]}
        start = tuple(state["entities"]["hero1"]["pos"])
        targets = [tuple(memory["pos"]) for memory in state["board"]["memories"]] + [tuple(state["board"]["portal"])]
        reached = self._flood(state["board"]["size"], walls, start)

        self.assertEqual(game.status, Game.STATUS_PLAYING)
        self.assertTrue(all(target in reached for target in targets))
        self.assertGreaterEqual(
            self._manhattan(tuple(state["entities"]["hero1"]["pos"]), tuple(state["entities"]["monster"]["pos"])),
            2,
        )

    def test_wall_is_impassable(self):
        game, player = create_game("1vAI", 5, "astar", "Scout", seed=22)
        state = game.state
        wall, hero_pos, direction = self._place_actor_next_to_wall(state, "hero1")
        state["entities"]["hero1"]["pos"] = list(hero_pos)
        self._fresh_turn(state, "hero1")
        game.state = state
        game.save()

        with self.assertRaises(GameError):
            apply_player_action(game, player.token, {"type": "move", "direction": direction})
        self.assertEqual(tuple(game.state["entities"]["hero1"]["pos"]), hero_pos)
        self.assertIn(wall, {tuple(pos) for pos in game.state["board"]["walls"]})

    def test_vines_affect_only_heroes(self):
        game, hero = create_game("1v1", 5, "", "Scout", seed=330)
        game, monster = join_game(game.room_code, "Guide")
        state = game.state
        vine = tuple(state["board"]["vines"][0])
        hero_pos, hero_direction = self._adjacent_clear_position(state, vine)
        state["entities"]["hero1"]["pos"] = list(hero_pos)
        state["entities"]["monster"]["pos"] = [4, 4]
        self._fresh_turn(state, "hero1")
        game.state = state
        game.save()

        apply_player_action(game, hero.token, {"type": "move", "direction": hero_direction})
        game.refresh_from_db()
        self.assertEqual(game.state["entities"]["hero1"]["skip_turns"], 1)

        state = game.state
        monster_pos, monster_direction = self._adjacent_clear_position(state, vine, avoid_heroes=True)
        state["entities"]["monster"]["pos"] = list(monster_pos)
        self._fresh_turn(state, "monster")
        game.state = state
        game.save()

        apply_player_action(game, monster.token, {"type": "move", "direction": monster_direction})
        game.refresh_from_db()
        self.assertEqual(game.state["entities"]["monster"].get("skip_turns", 0), 0)

    def test_teleport_range_is_two_cells(self):
        game, player = create_game("1vAI", 5, "astar", "Scout", seed=44)
        state = game.state
        state["board"]["walls"] = []
        state["entities"]["hero1"]["pos"] = [0, 0]
        state["entities"]["monster"]["pos"] = [4, 4]
        self._fresh_turn(state, "hero1")
        game.state = state
        game.save()

        apply_player_action(game, player.token, {"type": "teleport", "target": [0, 2]})
        game.refresh_from_db()
        self.assertEqual(game.state["entities"]["hero1"]["pos"], [0, 2])

        state = game.state
        self._fresh_turn(state, "hero1")
        state["entities"]["hero1"]["teleport_cooldown"] = 0
        game.state = state
        game.save()
        with self.assertRaises(GameError):
            apply_player_action(game, player.token, {"type": "teleport", "target": [4, 4]})

    def test_monster_teleport_range_is_two_cells(self):
        game, _ = create_game("1v1", 5, "", "Scout", seed=45)
        game, monster = join_game(game.room_code, "Guide")
        state = game.state
        state["board"]["walls"] = []
        state["entities"]["hero1"]["pos"] = [4, 4]
        state["entities"]["monster"]["pos"] = [0, 0]
        self._fresh_turn(state, "monster")
        game.state = state
        game.save()

        apply_player_action(game, monster.token, {"type": "teleport", "target": [0, 2]})
        game.refresh_from_db()
        self.assertEqual(game.state["entities"]["monster"]["pos"], [0, 2])

        state = game.state
        self._fresh_turn(state, "monster")
        state["entities"]["monster"]["teleport_cooldown"] = 0
        game.state = state
        game.save()
        with self.assertRaises(GameError):
            apply_player_action(game, monster.token, {"type": "teleport", "target": [4, 4]})

    def test_monster_teleport_can_capture_instantly(self):
        game, _ = create_game("1v1", 5, "", "Scout", seed=78)
        game, monster = join_game(game.room_code, "Guide")
        state = game.state
        state["board"]["walls"] = []
        state["entities"]["hero1"]["pos"] = [2, 2]
        state["entities"]["monster"]["pos"] = [2, 4]
        self._fresh_turn(state, "monster")
        game.state = state
        game.save()

        apply_player_action(game, monster.token, {"type": "teleport", "target": [2, 2]})
        game.refresh_from_db()
        self.assertEqual(game.status, Game.STATUS_FINISHED)
        self.assertEqual(game.result["winner"], "monster")

    def test_monster_move_can_capture_adjacent_hero(self):
        game, _ = create_game("1v1", 5, "", "Scout", seed=79)
        game, monster = join_game(game.room_code, "Guide")
        state = game.state
        state["board"]["walls"] = []
        state["entities"]["hero1"]["pos"] = [2, 2]
        state["entities"]["monster"]["pos"] = [2, 3]
        self._fresh_turn(state, "monster")
        game.state = state
        game.save()

        apply_player_action(game, monster.token, {"type": "move", "direction": "left"})
        game.refresh_from_db()
        self.assertEqual(game.status, Game.STATUS_FINISHED)
        self.assertEqual(game.result["winner"], "monster")

    def test_invalid_teleport_payload_is_rejected_cleanly(self):
        game, player = create_game("1vAI", 5, "astar", "Scout", seed=81)
        state = game.state
        state["board"]["walls"] = []
        state["entities"]["hero1"]["pos"] = [0, 0]
        state["entities"]["monster"]["pos"] = [4, 4]
        self._fresh_turn(state, "hero1")
        game.state = state
        game.save()

        with self.assertRaises(GameError) as error:
            apply_player_action(game, player.token, {"type": "teleport", "target": None})
        self.assertIn("Teleport target", str(error.exception))

    def test_ai_turn_records_stats_after_player_move(self):
        game, player = create_game("1vAI", 5, "astar", "Scout", seed=82)
        state = game.state
        state["board"]["walls"] = []
        state["board"]["vines"] = []
        state["entities"]["hero1"]["pos"] = [0, 0]
        state["entities"]["monster"]["pos"] = [4, 4]
        self._fresh_turn(state, "hero1")
        game.state = state
        game.save()

        apply_player_action(game, player.token, {"type": "move", "direction": "right"})
        maybe_run_ai_turns(game)
        game.refresh_from_db()

        self.assertGreater(game.ai_stats.count(), 0)
        self.assertTrue(game.state["last_events"])
        self.assertTrue(game.ai_stats.first().selected_move.get("debug"))

    def test_2vai_loses_when_any_hero_is_captured(self):
        game, _ = create_game("2vAI", 5, "astar", "Scout", seed=98)
        game, _ = join_game(game.room_code, "Runner")
        state = game.state
        state["board"]["walls"] = []
        state["entities"]["hero1"]["pos"] = [1, 1]
        state["entities"]["hero2"]["pos"] = [4, 4]
        state["entities"]["monster"]["pos"] = [1, 3]
        self._fresh_turn(state, "monster")
        game.state = state
        game.save()

        maybe_run_ai_turns(game)
        game.refresh_from_db()
        self.assertEqual(game.status, Game.STATUS_FINISHED)
        self.assertEqual(game.result["winner"], "monster")

    def test_2vai_wins_only_after_both_heroes_enter_portal(self):
        game, hero1 = create_game("2vAI", 5, "astar", "Scout", seed=111)
        game, hero2 = join_game(game.room_code, "Runner")
        state = game.state
        state["board"]["walls"] = []
        state["board"]["vines"] = []
        for memory in state["board"]["memories"]:
            memory["collected"] = True
        state["board"]["portal"] = [0, 1]
        state["entities"]["hero1"]["pos"] = [0, 0]
        state["entities"]["hero2"]["pos"] = [1, 1]
        state["entities"]["monster"]["pos"] = [4, 4]
        self._fresh_turn(state, "hero1")
        game.state = state
        game.save()

        apply_player_action(game, hero1.token, {"type": "move", "direction": "right"})
        game.refresh_from_db()
        self.assertEqual(game.status, Game.STATUS_PLAYING)
        self.assertFalse(game.state["entities"]["hero1"]["active"])

        state = game.state
        state["board"]["portal"] = [1, 2]
        state["entities"]["hero2"]["pos"] = [1, 1]
        self._fresh_turn(state, "hero2")
        game.state = state
        game.save()

        apply_player_action(game, hero2.token, {"type": "move", "direction": "right"})
        game.refresh_from_db()
        self.assertEqual(game.status, Game.STATUS_FINISHED)
        self.assertEqual(game.result["winner"], "hero")

    def test_ai_algorithms_return_valid_actions(self):
        for level in ("minmax", "alphabeta", "astar", "mcts"):
            game, _ = create_game("1vAI", 5, level, "Scout", seed=2024)
            state = game.state
            state["current_turn"] = "monster"
            decision = select_ai_move(state, level, BOARD_CONFIGS[5], 500)
            self.assertIn(decision["action"]["type"], {"move", "teleport", "timeout"})
            self.assertGreaterEqual(decision["nodes"], 0)
            self.assertIn("debug", decision)
            self.assertIn("candidates", decision["debug"])

    def test_player_skip_turn_advances_and_logs_event(self):
        game, hero = create_game("1v1", 5, "", "Scout", seed=5050)
        game, _ = join_game(game.room_code, "Guide")
        state = game.state
        state["board"]["walls"] = []
        state["board"]["vines"] = []
        state["entities"]["hero1"]["pos"] = [0, 0]
        state["entities"]["monster"]["pos"] = [4, 4]
        self._fresh_turn(state, "hero1")
        game.state = state
        game.save()

        apply_player_action(game, hero.token, {"type": "skip"})
        game.refresh_from_db()

        self.assertEqual(game.state["current_turn"], "monster")
        self.assertEqual(game.moves.last().action_type, "skip")
        self.assertIn({"type": "skip", "entity": "hero1"}, game.state["last_events"])

    def test_mcts_captures_adjacent_hero_immediately(self):
        game, _ = create_game("1vAI", 5, "mcts", "Scout", seed=6060)
        state = game.state
        state["board"]["walls"] = []
        state["board"]["vines"] = []
        state["entities"]["hero1"]["pos"] = [2, 2]
        state["entities"]["monster"]["pos"] = [2, 3]
        state["entities"]["monster"]["teleport_cooldown"] = 9
        state["current_turn"] = "monster"

        decision = select_ai_move(state, "mcts", BOARD_CONFIGS[5], 500)

        self.assertEqual(decision["action"], {"type": "move", "direction": "left"})
        self.assertIn("sigurno hvatanje", decision["debug"].get("reason", ""))

    def test_mcts_uses_teleport_capture_when_available(self):
        game, _ = create_game("1vAI", 5, "mcts", "Scout", seed=6061)
        state = game.state
        state["board"]["walls"] = []
        state["board"]["vines"] = []
        state["entities"]["hero1"]["pos"] = [2, 2]
        state["entities"]["monster"]["pos"] = [2, 4]
        state["entities"]["monster"]["teleport_cooldown"] = 0
        state["current_turn"] = "monster"

        decision = select_ai_move(state, "mcts", BOARD_CONFIGS[5], 500)

        self.assertEqual(decision["action"], {"type": "teleport", "target": [2, 2]})
        self.assertTrue(decision["used_teleport"])

    def test_room_create_join_starts_realtime_ready_match(self):
        game, hero = create_game("1v1", 6, "", "Scout", seed=3030)
        self.assertEqual(game.status, Game.STATUS_WAITING)
        self.assertEqual(game.players.count(), 1)

        game, monster = join_game(game.room_code, "Guide")
        game.refresh_from_db()

        self.assertEqual(game.status, Game.STATUS_PLAYING)
        self.assertEqual(hero.entity_id, "hero1")
        self.assertEqual(monster.entity_id, "monster")
        self.assertIn("monster", game.state["entities"])

    def test_websocket_game_state_update_after_move(self):
        game, player = create_game("1vAI", 5, "astar", "Scout", seed=4040)
        state = game.state
        state["board"]["walls"] = []
        state["board"]["vines"] = []
        state["entities"]["hero1"]["pos"] = [0, 0]
        state["entities"]["monster"]["pos"] = [4, 4]
        self._fresh_turn(state, "hero1")
        game.state = state
        game.save()

        payload = async_to_sync(self._websocket_move_roundtrip)(game.room_code, str(player.token))
        self.assertEqual(payload["type"], "state")
        self.assertEqual(payload["payload"]["status"], Game.STATUS_PLAYING)
        self.assertGreaterEqual(payload["payload"]["ai_stats"]["summary"]["move_count"], 1)

    async def _websocket_move_roundtrip(self, room_code, token):
        communicator = WebsocketCommunicator(application, f"/ws/game/{room_code}/?token={token}")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.receive_json_from()
        await communicator.send_json_to(
            {"type": "move", "player_token": token, "action": {"type": "move", "direction": "right"}}
        )
        payload = await communicator.receive_json_from()
        await communicator.disconnect()
        return payload

    def _fresh_turn(self, state, actor_id):
        now = timezone.now()
        state["current_turn"] = actor_id
        state["turn_started_at"] = now.isoformat()
        state["turn_deadline_at"] = (now + timedelta(seconds=60)).isoformat()
        state["game_deadline_at"] = (now + timedelta(seconds=600)).isoformat()

    def _flood(self, size, walls, start):
        queue = [start]
        seen = {start}
        while queue:
            r, c = queue.pop(0)
            for dr, dc in DIRECTIONS.values():
                nxt = (r + dr, c + dc)
                if 0 <= nxt[0] < size and 0 <= nxt[1] < size and nxt not in walls and nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen

    def _place_actor_next_to_wall(self, state, actor_id):
        walls = {tuple(pos) for pos in state["board"]["walls"]}
        for wall in walls:
            for direction, delta in DIRECTIONS.items():
                candidate = (wall[0] - delta[0], wall[1] - delta[1])
                if self._clear_for_actor(state, candidate, actor_id):
                    return wall, candidate, direction
        self.fail("Generated map had no reachable wall-adjacent clear cell.")

    def _adjacent_clear_position(self, state, target, avoid_heroes=False):
        for direction, delta in DIRECTIONS.items():
            candidate = (target[0] - delta[0], target[1] - delta[1])
            if self._clear_cell(state, candidate, avoid_heroes=avoid_heroes):
                return candidate, direction
        self.fail("No adjacent clear position found.")

    def _clear_for_actor(self, state, candidate, actor_id):
        if not self._clear_cell(state, candidate):
            return False
        if actor_id == "hero1" and tuple(state["entities"]["monster"]["pos"]) == candidate:
            return False
        return True

    def _clear_cell(self, state, candidate, avoid_heroes=False):
        size = state["board"]["size"]
        if not (0 <= candidate[0] < size and 0 <= candidate[1] < size):
            return False
        if candidate in {tuple(pos) for pos in state["board"]["walls"]}:
            return False
        if avoid_heroes:
            heroes = {
                tuple(entity["pos"])
                for entity in state["entities"].values()
                if entity["kind"] == "hero" and entity.get("active", True)
            }
            if candidate in heroes:
                return False
        return True

    def _manhattan(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
