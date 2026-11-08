import random
import string
from collections import deque
from datetime import timedelta

from django.db.models import Avg, Count, Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ai.algorithms import select_ai_move
from game.config import AI_LEVELS, BOARD_CONFIGS, DIRECTIONS, MODES, ROOM_CODE_LENGTH, SKINS, TELEPORT_RANGE
from game.models import AIStat, Game, GameResult, Move, Player


class GameError(ValueError):
    pass


def generate_room_code():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choice(alphabet) for _ in range(ROOM_CODE_LENGTH))
        if not Game.objects.filter(room_code=code).exists():
            return code


def validate_create_options(mode, board_size, ai_level, skin):
    if mode not in MODES:
        raise GameError("Nepoznat režim igre.")
    if board_size not in BOARD_CONFIGS:
        raise GameError("Dimenzija mape mora biti 5, 6, 7 ili 8.")
    if mode in ("1vAI", "2vAI") and ai_level not in AI_LEVELS:
        raise GameError("AI nivo je obavezan za AI režime.")
    if mode == "1v1" and ai_level:
        raise GameError("1v1 režim nema AI nivo.")
    if skin not in SKINS:
        raise GameError("Nepoznat skin.")


def required_players(mode):
    return 1 if mode == "1vAI" else 2


def create_game(mode, board_size, ai_level, skin, seed=None):
    validate_create_options(mode, board_size, ai_level, skin)
    game = Game.objects.create(
        room_code=generate_room_code(),
        mode=mode,
        board_size=board_size,
        ai_level=ai_level if mode in ("1vAI", "2vAI") else "",
        seed=seed if seed is not None else random.randint(10_000, 999_999),
        status=Game.STATUS_WAITING,
    )
    player = Player.objects.create(game=game, role=Player.ROLE_HERO, entity_id="hero1", skin=skin)
    if required_players(mode) == 1:
        initialize_game(game)
    return game, player


def join_game(room_code, skin):
    if skin not in SKINS:
        raise GameError("Nepoznat skin.")
    try:
        game = Game.objects.get(room_code=room_code)
    except Game.DoesNotExist as exc:
        raise GameError("Partija sa tim kodom ne postoji.") from exc

    if game.status != Game.STATUS_WAITING:
        raise GameError("Partija je već pokrenuta ili završena.")
    if game.players.count() >= required_players(game.mode):
        raise GameError("Soba je popunjena.")

    if game.mode == "1v1":
        player = Player.objects.create(game=game, role=Player.ROLE_MONSTER, entity_id="monster", skin="")
    elif game.mode == "2vAI":
        player = Player.objects.create(game=game, role=Player.ROLE_HERO, entity_id="hero2", skin=skin)
    else:
        raise GameError("Ovaj režim ne traži drugog igrača.")

    if game.players.count() == required_players(game.mode):
        initialize_game(game)
    return game, player


def update_waiting_settings(game, mode=None, board_size=None, ai_level=None):
    if game.status != Game.STATUS_WAITING:
        raise GameError("Podešavanja se mogu menjati samo pre početka partije.")
    new_mode = mode or game.mode
    new_size = board_size or game.board_size
    new_ai = ai_level if ai_level is not None else game.ai_level
    creator = game.players.first()
    skin = creator.skin if creator else SKINS[0]
    validate_create_options(new_mode, new_size, new_ai, skin)
    if game.players.count() > required_players(new_mode):
        raise GameError("Novi režim ima manje mesta od trenutnog broja igrača.")
    game.mode = new_mode
    game.board_size = new_size
    game.ai_level = new_ai if new_mode in ("1vAI", "2vAI") else ""
    game.save(update_fields=["mode", "board_size", "ai_level", "updated_at"])
    if game.players.count() == required_players(game.mode):
        initialize_game(game)
    return game


def initialize_game(game):
    players = list(game.players.order_by("created_at"))
    if len(players) < required_players(game.mode):
        return game

    state = _generate_state(game, players)
    game.state = state
    game.status = Game.STATUS_PLAYING
    game.result = {}
    game.save(update_fields=["state", "status", "result", "updated_at"])
    return game


def _generate_state(game, players):
    cfg = BOARD_CONFIGS[game.board_size]
    rng = random.Random(game.seed)
    size = game.board_size
    hero_count = 2 if game.mode == "2vAI" else 1

    for _ in range(600):
        walls = _place_walls(rng, size, cfg["wall_count"])
        if not _all_non_wall_cells_connected(size, walls):
            continue

        blocked = set(walls)
        vines = _choose_positions(rng, size, blocked, cfg["initial_vines"])
        blocked.update(vines)

        memory_positions = _choose_positions(rng, size, blocked, cfg["memory_count"])
        blocked.update(memory_positions)

        portal = _choose_positions(rng, size, blocked, 1)[0]
        blocked.add(portal)

        hero_positions = _choose_positions(rng, size, blocked, hero_count)
        blocked.update(hero_positions)

        monster = _choose_positions(rng, size, blocked, 1)[0]
        if min(_manhattan(monster, hero) for hero in hero_positions) < 2:
            continue

        targets = set(memory_positions + [portal])
        if not all(_targets_reachable_without_teleport(size, walls, hero_position, targets) for hero_position in hero_positions):
            continue

        now = timezone.now()
        entities = {}
        for index, position in enumerate(hero_positions, start=1):
            player = next(player for player in players if player.entity_id == f"hero{index}")
            entities[f"hero{index}"] = {
                "kind": "hero",
                "skin": player.skin,
                "pos": list(position),
                "active": True,
                "escaped": False,
                "skip_turns": 0,
                "teleport_cooldown": 0,
            }

        monster_is_ai = game.mode != "1v1"
        entities["monster"] = {
            "kind": "monster",
            "ai": monster_is_ai,
            "name": AI_LEVELS.get(game.ai_level, {"opponent": "Čudovište"})["opponent"] if monster_is_ai else "Čudovište",
            "pos": list(monster),
            "active": True,
            "teleport_cooldown": 0,
        }

        order = ["hero1"]
        if game.mode == "2vAI":
            order.append("hero2")
        order.append("monster")

        return {
            "version": 1,
            "seed": game.seed,
            "mode": game.mode,
            "ai_level": game.ai_level,
            "status": Game.STATUS_PLAYING,
            "winner": None,
            "reason": "",
            "turn_order": order,
            "current_turn": "hero1",
            "turn_number": 1,
            "start_at": now.isoformat(),
            "turn_started_at": now.isoformat(),
            "turn_deadline_at": (now + timedelta(seconds=cfg["turn_limit_seconds"])).isoformat(),
            "game_deadline_at": (now + timedelta(seconds=cfg["total_game_seconds"])).isoformat(),
            "board": {
                "size": size,
                "walls": [list(pos) for pos in sorted(walls)],
                "vines": [list(pos) for pos in sorted(vines)],
                "memories": [
                    {"id": f"mem-{index}", "pos": list(pos), "collected": False}
                    for index, pos in enumerate(memory_positions, start=1)
                ],
                "portal": list(portal),
            },
            "entities": entities,
            "last_events": [{"type": "game_started"}],
            "metrics": {
                "teleports_used": 0,
                "hero_teleports": 0,
                "monster_teleports": 0,
                "vines_hits": 0,
                "portal_shifts": 0,
                "timeouts": 0,
            },
            "config": {
                "turn_limit_seconds": cfg["turn_limit_seconds"],
                "total_game_seconds": cfg["total_game_seconds"],
                "hero_teleport_cooldown": cfg["hero_teleport_cooldown"],
                "monster_teleport_cooldown": cfg["monster_teleport_cooldown"],
                "vine_growth_interval": cfg["vine_growth_interval"],
                "vine_growth_count": cfg["vine_growth_count"],
                "portal_shift_interval": cfg["portal_shift_interval"],
                "memory_count": cfg["memory_count"],
            },
        }

    raise GameError("Nije moguće generisati validnu mapu za dati seed.")


def apply_player_action(game, player_token, action):
    game.refresh_from_db()
    state = game.state
    if game.status != Game.STATUS_PLAYING:
        raise GameError("Partija nije aktivna.")
    if _expire_total_time_if_needed(state):
        return _persist(game, state)
    if _turn_deadline_passed(state):
        _resolve_current_turn_as_timeout(game, state, "turn_timeout")
        return _persist(game, state)

    try:
        player = Player.objects.get(game=game, token=player_token)
    except Player.DoesNotExist as exc:
        raise GameError("Neispravan token igrača.") from exc

    actor_id = state["current_turn"]
    if player.entity_id != actor_id:
        raise GameError("Nije tvoj potez.")
    if state["entities"][actor_id].get("ai", False):
        raise GameError("AI potez ne sme doći sa frontenda.")

    events = []
    used_teleport = _validate_and_apply_action(state, actor_id, action, events, allow_timeout=False)
    Move.objects.create(
        game=game,
        turn_number=state["turn_number"],
        actor_entity_id=actor_id,
        actor_role=state["entities"][actor_id]["kind"],
        action_type=action["type"],
        payload=action,
        valid=True,
    )
    _finish_resolved_turn(game, state, actor_id, action, used_teleport, events)
    return _persist(game, state)


def apply_turn_timeout(game):
    game.refresh_from_db()
    state = game.state
    if game.status != Game.STATUS_PLAYING:
        return game
    if _expire_total_time_if_needed(state):
        return _persist(game, state)
    if not _turn_deadline_passed(state):
        raise GameError("Vreme za potez još nije isteklo.")
    _resolve_current_turn_as_timeout(game, state, "turn_timeout")
    return _persist(game, state)


def maybe_run_ai_turns(game):
    game.refresh_from_db()
    state = game.state
    changed = False
    while game.status == Game.STATUS_PLAYING and state.get("status") == Game.STATUS_PLAYING:
        if _expire_total_time_if_needed(state):
            changed = True
            break
        actor_id = state["current_turn"]
        actor = state["entities"][actor_id]
        if not actor.get("ai", False):
            break

        cfg = BOARD_CONFIGS[state["board"]["size"]]
        budget_ms = cfg["turn_limit_seconds"] * 1000
        decision = select_ai_move(state, state["ai_level"], cfg, budget_ms)
        action = decision["action"]
        events = [
            {
                "type": "ai_decision",
                "algorithm": decision["algorithm"],
                "nodes": decision["nodes"],
                "decision_ms": round(decision["decision_ms"], 3),
                "used_teleport": decision["used_teleport"],
            }
        ]
        used_teleport = _validate_and_apply_action(state, actor_id, action, events, allow_timeout=True)
        AIStat.objects.create(
            game=game,
            algorithm=decision["algorithm"],
            move_number=state["turn_number"],
            decision_ms=decision["decision_ms"],
            nodes=decision["nodes"],
            selected_move={"action": action, "debug": decision.get("debug", {})},
            used_teleport=used_teleport,
        )
        Move.objects.create(
            game=game,
            turn_number=state["turn_number"],
            actor_entity_id=actor_id,
            actor_role=actor["kind"],
            action_type=action["type"],
            payload=action,
            valid=True,
            skipped_reason="ai_timeout" if action.get("type") == "timeout" else "",
        )
        _finish_resolved_turn(game, state, actor_id, action, used_teleport, events)
        changed = True
        game.state = state
        game.status = state["status"]
    if changed:
        return _persist(game, state)
    return game


def serialize_game(game, player_token=None):
    game.refresh_from_db()
    payload = {
        "id": game.id,
        "room_code": game.room_code,
        "mode": game.mode,
        "board_size": game.board_size,
        "ai_level": game.ai_level,
        "seed": game.seed,
        "status": game.status,
        "state": game.state,
        "result": game.result,
        "players": [
            {
                "role": player.role,
                "entity_id": player.entity_id,
                "skin": player.skin,
                "connected": player.connected,
            }
            for player in game.players.order_by("created_at")
        ],
        "server_time": timezone.now().isoformat(),
        "ai_stats": game_ai_stats(game),
        "match_stats": match_stats(game),
    }
    if player_token:
        payload["player_token"] = str(player_token)
        player = game.players.filter(token=player_token).first()
        if player:
            payload["current_player"] = {
                "role": player.role,
                "entity_id": player.entity_id,
                "skin": player.skin,
            }
    return payload


def game_ai_stats(game):
    stats = list(game.ai_stats.all())
    if not stats:
        return {
            "moves": [],
            "summary": {
                "total_time_ms": 0,
                "avg_time_ms": 0,
                "total_nodes": 0,
                "avg_nodes": 0,
                "move_count": 0,
            },
        }
    total_time = sum(item.decision_ms for item in stats)
    total_nodes = sum(item.nodes for item in stats)
    return {
        "moves": [
            _serialize_ai_stat(item)
            for item in stats
        ],
        "summary": {
            "total_time_ms": round(total_time, 3),
            "avg_time_ms": round(total_time / len(stats), 3),
            "total_nodes": total_nodes,
            "avg_nodes": round(total_nodes / len(stats), 3),
            "move_count": len(stats),
        },
    }


def _serialize_ai_stat(item):
    selected = item.selected_move or {}
    if isinstance(selected, dict) and "action" in selected:
        action = selected.get("action") or {"type": "timeout"}
        debug = selected.get("debug") or {}
    else:
        action = selected
        debug = {}
    return {
        "move_number": item.move_number,
        "algorithm": item.algorithm,
        "decision_ms": round(item.decision_ms, 3),
        "nodes": item.nodes,
        "selected_move": action,
        "used_teleport": item.used_teleport,
        "debug": debug,
    }


def match_stats(game):
    state = game.state or {}
    metrics = state.get("metrics", {})
    memories = state.get("board", {}).get("memories", [])
    result = game.result or state.get("result", {})
    duration_ms = result.get("duration_ms")
    if duration_ms is None and state.get("start_at"):
        duration_ms = int((timezone.now() - _parse_dt(state["start_at"])).total_seconds() * 1000)
    return {
        "total_moves": game.moves.count(),
        "duration_ms": max(duration_ms or 0, 0),
        "winner": result.get("winner", ""),
        "reason": result.get("reason", ""),
        "memories_collected": sum(1 for memory in memories if memory.get("collected", False)),
        "memories_total": len(memories),
        "teleports_used": metrics.get("teleports_used", game.moves.filter(action_type="teleport").count()),
        "hero_teleports": metrics.get("hero_teleports", 0),
        "monster_teleports": metrics.get("monster_teleports", 0),
        "vines_hits": metrics.get("vines_hits", game.moves.filter(skipped_reason="vines").count()),
        "portal_shifts": metrics.get("portal_shifts", 0),
        "timeouts": metrics.get("timeouts", game.moves.filter(skipped_reason__in=["turn_timeout", "ai_timeout"]).count()),
    }


def algorithm_history():
    rows = []
    for algorithm in AIStat.objects.order_by().values_list("algorithm", flat=True).distinct():
        stats = AIStat.objects.filter(algorithm=algorithm)
        aggregate = stats.aggregate(
            total_time_ms=Sum("decision_ms"),
            avg_time_ms=Avg("decision_ms"),
            total_nodes=Sum("nodes"),
            avg_nodes=Avg("nodes"),
            move_count=Count("id"),
        )
        game_ids = set(stats.values_list("game_id", flat=True))
        finished = Game.objects.filter(id__in=game_ids, status=Game.STATUS_FINISHED)
        wins = sum(1 for game in finished if game.result.get("winner") == "monster")
        rows.append(
            {
                "algorithm": algorithm,
                "total_time_ms": round(aggregate["total_time_ms"] or 0, 3),
                "avg_time_ms": round(aggregate["avg_time_ms"] or 0, 3),
                "total_nodes": aggregate["total_nodes"] or 0,
                "avg_nodes": round(aggregate["avg_nodes"] or 0, 3),
                "move_count": aggregate["move_count"],
                "games": len(game_ids),
                "finished_games": finished.count(),
                "wins": wins,
                "win_rate": round(wins / finished.count(), 3) if finished.count() else 0,
            }
        )
    return rows


def _persist(game, state):
    game.state = state
    game.status = state["status"]
    game.result = state.get("result", {})
    game.save(update_fields=["state", "status", "result", "updated_at"])
    if game.status == Game.STATUS_FINISHED:
        _sync_game_result(game)
    return game


def _sync_game_result(game):
    if not game.result:
        return
    GameResult.objects.update_or_create(
        game=game,
        defaults={
            "winner": game.result.get("winner", ""),
            "reason": game.result.get("reason", ""),
            "duration_ms": game.result.get("duration_ms", 0),
            "stats": game_ai_stats(game)["summary"],
        },
    )


def _place_walls(rng, size, count):
    cells = [(r, c) for r in range(size) for c in range(size)]
    rng.shuffle(cells)
    return set(cells[:count])


def _choose_positions(rng, size, blocked, count):
    candidates = [(r, c) for r in range(size) for c in range(size) if (r, c) not in blocked]
    if len(candidates) < count:
        raise GameError("Nema dovoljno polja za generisanje mape.")
    rng.shuffle(candidates)
    return candidates[:count]


def _all_non_wall_cells_connected(size, walls):
    start = next(((r, c) for r in range(size) for c in range(size) if (r, c) not in walls), None)
    if start is None:
        return False
    seen = _flood(size, walls, start)
    return len(seen) == size * size - len(walls)


def _targets_reachable_without_teleport(size, walls, start, targets):
    seen = _flood(size, walls, start)
    return all(target in seen for target in targets)


def _flood(size, walls, start):
    queue = deque([start])
    seen = {start}
    while queue:
        r, c = queue.popleft()
        for dr, dc in DIRECTIONS.values():
            nxt = (r + dr, c + dc)
            if 0 <= nxt[0] < size and 0 <= nxt[1] < size and nxt not in walls and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def _validate_and_apply_action(state, actor_id, action, events, allow_timeout):
    if not isinstance(action, dict) or "type" not in action:
        raise GameError("Potez mora imati type.")
    if action["type"] == "timeout":
        if not allow_timeout:
            raise GameError("Frontend ne sme namerno poslati čekanje.")
        events.append({"type": "timeout", "entity": actor_id})
        return False

    if action["type"] == "skip":
        actor = state["entities"][actor_id]
        if actor.get("ai", False):
            raise GameError("AI ne koristi ručno preskakanje poteza.")
        events.append({"type": "skip", "entity": actor_id})
        return False

    actor = state["entities"][actor_id]
    origin = tuple(actor["pos"])
    if action["type"] == "move":
        direction = action.get("direction")
        if direction not in DIRECTIONS:
            raise GameError("Nepoznat smer.")
        delta = DIRECTIONS[direction]
        target = (origin[0] + delta[0], origin[1] + delta[1])
        _validate_target(state, actor_id, target, is_teleport=False)
        actor["pos"] = list(target)
        events.append({"type": "move", "entity": actor_id, "to": list(target)})
        _apply_tile_effects(state, actor_id, target, events)
        return False

    if action["type"] == "teleport":
        if actor.get("teleport_cooldown", 0) > 0:
            raise GameError("Teleport je na hlađenju.")
        raw_target = action.get("target", [])
        if not isinstance(raw_target, (list, tuple)) or len(raw_target) != 2:
            raise GameError("Teleport target mora biti [row, col].")
        target = tuple(raw_target)
        if _manhattan(origin, target) > TELEPORT_RANGE:
            raise GameError("Teleport domet je najviše 2 polja.")
        _validate_target(state, actor_id, target, is_teleport=True)
        actor["pos"] = list(target)
        events.append({"type": "teleport", "entity": actor_id, "to": list(target)})
        _apply_tile_effects(state, actor_id, target, events)
        return True

    raise GameError("Nepoznat tip poteza.")


def _validate_target(state, actor_id, target, is_teleport):
    size = state["board"]["size"]
    if not isinstance(target[0], int) or not isinstance(target[1], int):
        raise GameError("Koordinate moraju biti brojevi.")
    if not (0 <= target[0] < size and 0 <= target[1] < size):
        raise GameError("Potez izlazi van mape.")
    if target in _pos_set(state["board"]["walls"]):
        raise GameError("Wall of Darkness je neprohodan.")

    actor = state["entities"][actor_id]
    if actor["kind"] == "hero":
        if tuple(state["entities"]["monster"]["pos"]) == target:
            raise GameError("Heroj ne može ući na polje čudovišta.")
        occupied_heroes = {
            tuple(entity["pos"])
            for entity_id, entity in state["entities"].items()
            if entity_id != actor_id
            and entity["kind"] == "hero"
            and entity.get("active", True)
            and not entity.get("escaped", False)
        }
        if target in occupied_heroes:
            raise GameError("Polje je zauzeto drugim herojem.")


def _apply_tile_effects(state, actor_id, target, events):
    actor = state["entities"][actor_id]
    if actor["kind"] != "hero":
        return

    for memory in state["board"]["memories"]:
        if not memory.get("collected", False) and tuple(memory["pos"]) == target:
            memory["collected"] = True
            events.append({"type": "memory_collected", "entity": actor_id, "memory": memory["id"]})

    if target in _pos_set(state["board"]["vines"]):
        actor["skip_turns"] = max(actor.get("skip_turns", 0), 1)
        events.append({"type": "vines_snared", "entity": actor_id})

    if _all_memories_collected(state) and list(target) == state["board"]["portal"]:
        actor["escaped"] = True
        actor["active"] = False
        events.append({"type": "portal_entered", "entity": actor_id})


def _finish_resolved_turn(game, state, actor_id, action, used_teleport, events):
    if used_teleport:
        _set_teleport_cooldown(state, actor_id)
    _check_capture_or_win(state, events)
    if state["status"] == Game.STATUS_FINISHED:
        _record_metrics(state, actor_id, action, used_teleport, events)
        state["last_events"] = events
        return

    _tick_cooldowns(state, actor_id, used_teleport)
    state["turn_number"] += 1
    _grow_vines_if_due(state, events)
    _shift_portal_if_due(state, events)
    _check_capture_or_win(state, events)
    if state["status"] == Game.STATUS_FINISHED:
        _record_metrics(state, actor_id, action, used_teleport, events)
        state["last_events"] = events
        return

    _set_next_turn(state, actor_id)
    _consume_forced_skips(game, state, events)
    if state["status"] != Game.STATUS_FINISHED:
        _refresh_turn_deadline(state)
    _record_metrics(state, actor_id, action, used_teleport, events)
    state["last_events"] = events


def _resolve_current_turn_as_timeout(game, state, reason):
    actor_id = state["current_turn"]
    events = [{"type": "timeout", "entity": actor_id}]
    Move.objects.create(
        game=game,
        turn_number=state["turn_number"],
        actor_entity_id=actor_id,
        actor_role=state["entities"][actor_id]["kind"],
        action_type="timeout",
        payload={"type": "timeout"},
        valid=True,
        skipped_reason=reason,
    )
    _finish_resolved_turn(game, state, actor_id, {"type": "timeout"}, False, events)


def _record_metrics(state, actor_id, action, used_teleport, events):
    metrics = state.setdefault(
        "metrics",
        {
            "teleports_used": 0,
            "hero_teleports": 0,
            "monster_teleports": 0,
            "vines_hits": 0,
            "portal_shifts": 0,
            "timeouts": 0,
        },
    )
    if used_teleport:
        metrics["teleports_used"] = metrics.get("teleports_used", 0) + 1
        actor_kind = state["entities"][actor_id]["kind"]
        if actor_kind == "hero":
            metrics["hero_teleports"] = metrics.get("hero_teleports", 0) + 1
        else:
            metrics["monster_teleports"] = metrics.get("monster_teleports", 0) + 1
    if action.get("type") == "timeout":
        metrics["timeouts"] = metrics.get("timeouts", 0) + 1
    metrics["vines_hits"] = metrics.get("vines_hits", 0) + sum(
        1 for event in events if event.get("type") in {"vines_snared", "vines_grew_on_hero"}
    )
    metrics["portal_shifts"] = metrics.get("portal_shifts", 0) + sum(
        1 for event in events if event.get("type") == "portal_shifted"
    )


def _consume_forced_skips(game, state, events):
    guard = 0
    while state["status"] == Game.STATUS_PLAYING and guard < 20:
        guard += 1
        actor_id = state["current_turn"]
        actor = state["entities"][actor_id]
        if actor["kind"] != "hero" or actor.get("skip_turns", 0) <= 0:
            break

        actor["skip_turns"] -= 1
        events.append({"type": "vines_skip", "entity": actor_id})
        Move.objects.create(
            game=game,
            turn_number=state["turn_number"],
            actor_entity_id=actor_id,
            actor_role="hero",
            action_type="timeout",
            payload={"type": "vines_skip"},
            valid=True,
            skipped_reason="vines",
        )
        _tick_cooldowns(state, actor_id, used_teleport=False)
        state["turn_number"] += 1
        _grow_vines_if_due(state, events)
        _shift_portal_if_due(state, events)
        _check_capture_or_win(state, events)
        if state["status"] == Game.STATUS_FINISHED:
            break
        _set_next_turn(state, actor_id)


def _set_next_turn(state, actor_id):
    order = state["turn_order"]
    start = order.index(actor_id) if actor_id in order else -1
    for offset in range(1, len(order) + 1):
        candidate = order[(start + offset) % len(order)]
        if _can_take_turn(state, candidate):
            state["current_turn"] = candidate
            return
    _finish_game(state, "hero", "Svi heroji su izašli kroz portal.")


def _can_take_turn(state, entity_id):
    entity = state["entities"][entity_id]
    if entity["kind"] == "monster":
        return True
    return entity.get("active", True) and not entity.get("escaped", False)


def _refresh_turn_deadline(state):
    now = timezone.now()
    state["turn_started_at"] = now.isoformat()
    state["turn_deadline_at"] = (now + timedelta(seconds=state["config"]["turn_limit_seconds"])).isoformat()


def _tick_cooldowns(state, actor_id, used_teleport):
    for entity_id, entity in state["entities"].items():
        if entity_id == actor_id and used_teleport:
            continue
        if entity.get("teleport_cooldown", 0) > 0:
            entity["teleport_cooldown"] -= 1


def _set_teleport_cooldown(state, actor_id):
    actor = state["entities"][actor_id]
    if actor["kind"] == "hero":
        actor["teleport_cooldown"] = state["config"]["hero_teleport_cooldown"]
    else:
        actor["teleport_cooldown"] = state["config"]["monster_teleport_cooldown"]


def _grow_vines_if_due(state, events):
    interval = state["config"]["vine_growth_interval"]
    if state["turn_number"] % interval != 0:
        return
    rng = random.Random(state["seed"] + state["turn_number"] * 17)
    vines = _pos_set(state["board"]["vines"])
    walls = _pos_set(state["board"]["walls"])
    memories = {tuple(memory["pos"]) for memory in state["board"]["memories"] if not memory.get("collected", False)}
    portal = tuple(state["board"]["portal"])
    candidates = set()
    for vine in vines:
        for dr, dc in DIRECTIONS.values():
            target = (vine[0] + dr, vine[1] + dc)
            if _valid_vine_target(state, target, walls, memories, portal, vines):
                candidates.add(target)
    if not candidates:
        for r in range(state["board"]["size"]):
            for c in range(state["board"]["size"]):
                target = (r, c)
                if _valid_vine_target(state, target, walls, memories, portal, vines):
                    candidates.add(target)
    if not candidates:
        return

    selected = list(candidates)
    rng.shuffle(selected)
    grown = selected[: state["config"]["vine_growth_count"]]
    for pos in grown:
        vines.add(pos)
        for entity_id, entity in state["entities"].items():
            if entity["kind"] == "hero" and entity.get("active", True) and not entity.get("escaped", False):
                if tuple(entity["pos"]) == pos:
                    entity["skip_turns"] = max(entity.get("skip_turns", 0), 1)
                    events.append({"type": "vines_grew_on_hero", "entity": entity_id, "to": list(pos)})
    state["board"]["vines"] = [list(pos) for pos in sorted(vines)]
    events.append({"type": "vines_grew", "positions": [list(pos) for pos in grown]})


def _valid_vine_target(state, target, walls, memories, portal, vines):
    size = state["board"]["size"]
    return (
        0 <= target[0] < size
        and 0 <= target[1] < size
        and target not in walls
        and target not in vines
        and target not in memories
        and target != portal
    )


def _shift_portal_if_due(state, events):
    interval = state["config"]["portal_shift_interval"]
    if state["turn_number"] % interval != 0:
        return
    rng = random.Random(state["seed"] + state["turn_number"] * 31)
    walls = _pos_set(state["board"]["walls"])
    vines = _pos_set(state["board"]["vines"])
    memories = {tuple(memory["pos"]) for memory in state["board"]["memories"] if not memory.get("collected", False)}
    occupied = {
        tuple(entity["pos"])
        for entity in state["entities"].values()
        if entity.get("active", True) and not entity.get("escaped", False)
    }
    candidates = []
    for r in range(state["board"]["size"]):
        for c in range(state["board"]["size"]):
            pos = (r, c)
            if pos not in walls and pos not in vines and pos not in memories and pos not in occupied:
                candidates.append(pos)
    if not candidates:
        return
    rng.shuffle(candidates)
    state["board"]["portal"] = list(candidates[0])
    events.append({"type": "portal_shifted", "to": list(candidates[0])})


def _check_capture_or_win(state, events):
    monster_pos = tuple(state["entities"]["monster"]["pos"])
    for entity_id, entity in state["entities"].items():
        if entity["kind"] == "hero" and entity.get("active", True) and not entity.get("escaped", False):
            if tuple(entity["pos"]) == monster_pos:
                events.append({"type": "captured", "entity": entity_id})
                label = entity.get("skin") or "Heroj"
                _finish_game(state, "monster", f"{label} je uhvaćen.")
                return

    heroes = [entity for entity in state["entities"].values() if entity["kind"] == "hero"]
    if heroes and all(hero.get("escaped", False) for hero in heroes):
        _finish_game(state, "hero", "Sva sećanja su skupljena i svi heroji su ušli u portal.")


def _expire_total_time_if_needed(state):
    if timezone.now() >= _parse_dt(state["game_deadline_at"]):
        _finish_game(state, "monster", "Isteklo je ukupno vreme partije.")
        return True
    return False


def _turn_deadline_passed(state):
    return timezone.now() >= _parse_dt(state["turn_deadline_at"])


def _finish_game(state, winner, reason):
    if state["status"] == Game.STATUS_FINISHED:
        return
    now = timezone.now()
    start = _parse_dt(state["start_at"])
    duration_ms = int((now - start).total_seconds() * 1000)
    state["status"] = Game.STATUS_FINISHED
    state["winner"] = winner
    state["reason"] = reason
    state["result"] = {"winner": winner, "reason": reason, "duration_ms": max(duration_ms, 0)}


def _all_memories_collected(state):
    return all(memory.get("collected", False) for memory in state["board"]["memories"])


def _pos_set(items):
    return {tuple(item) for item in items}


def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _parse_dt(value):
    parsed = parse_datetime(value)
    if parsed is None:
        raise GameError("Neispravan timestamp u stanju igre.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.utc)
    return parsed
