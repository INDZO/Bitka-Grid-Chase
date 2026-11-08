import copy
import heapq
import math
import random
import time
from collections import deque

from game.config import DIRECTIONS, TELEPORT_RANGE


def select_ai_move(state, ai_level, board_config, time_budget_ms):
    started = time.perf_counter()
    deadline = started + max(time_budget_ms, 1) / 1000.0
    if ai_level == "minmax":
        action, nodes, debug = _minmax_decision(state, board_config, deadline, use_alpha_beta=False)
        algorithm = "MinMax"
    elif ai_level == "alphabeta":
        action, nodes, debug = _minmax_decision(state, board_config, deadline, use_alpha_beta=True)
        algorithm = "MinMax + Alpha-Beta"
    elif ai_level == "astar":
        action, nodes, debug = _astar_decision(state)
        algorithm = "A*"
    elif ai_level == "mcts":
        action, nodes, debug = _mcts_decision(state, board_config, deadline)
        algorithm = "MCTS"
    else:
        action, nodes, debug = _astar_decision(state)
        algorithm = "A*"

    elapsed_ms = (time.perf_counter() - started) * 1000
    debug.update(
        {
            "algorithm": algorithm,
            "time_budget_ms": time_budget_ms,
            "time_ms": round(elapsed_ms, 3),
            "nodes_expanded": nodes,
            "selected_action": action,
            "used_teleport": action.get("type") == "teleport",
        }
    )
    if elapsed_ms > time_budget_ms:
        debug["timed_out"] = True
        return {
            "algorithm": algorithm,
            "action": {"type": "timeout"},
            "nodes": nodes,
            "decision_ms": elapsed_ms,
            "used_teleport": False,
            "debug": debug,
        }
    debug["timed_out"] = False
    return {
        "algorithm": algorithm,
        "action": action,
        "nodes": nodes,
        "decision_ms": elapsed_ms,
        "used_teleport": action.get("type") == "teleport",
        "debug": debug,
    }


def _size(state):
    return state["board"]["size"]


def _walls(state):
    return {tuple(pos) for pos in state["board"]["walls"]}


def _in_bounds(state, pos):
    r, c = pos
    return 0 <= r < _size(state) and 0 <= c < _size(state)


def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _active_heroes(state):
    return [
        (entity_id, entity)
        for entity_id, entity in state["entities"].items()
        if entity["kind"] == "hero" and entity.get("active", True) and not entity.get("escaped", False)
    ]


def _monster_pos(state):
    return tuple(state["entities"]["monster"]["pos"])


def _is_captured(state):
    monster = _monster_pos(state)
    return any(tuple(hero["pos"]) == monster for _, hero in _active_heroes(state))


def _nearest_hero_distance(state, pos=None):
    heroes = _active_heroes(state)
    if not heroes:
        return 0
    origin = _monster_pos(state) if pos is None else tuple(pos)
    return min(_manhattan(origin, tuple(hero["pos"])) for _, hero in heroes)


def _safe_score(value):
    if value in (math.inf, -math.inf):
        return None
    return round(value, 3)


def _action_target(state, actor_id, action):
    if action.get("type") == "teleport":
        return tuple(action["target"])
    if action.get("type") == "move":
        origin = tuple(state["entities"][actor_id]["pos"])
        delta = DIRECTIONS[action["direction"]]
        return (origin[0] + delta[0], origin[1] + delta[1])
    return tuple(state["entities"][actor_id]["pos"])


def _candidate_row(state, actor_id, action, score=None, extra=None):
    target = _action_target(state, actor_id, action)
    sim = _apply_action(state, actor_id, action)
    row = {
        "action": action,
        "target": list(target),
        "score": _safe_score(score) if score is not None else None,
        "distance_after": _nearest_hero_distance(sim, target),
        "teleport": action.get("type") == "teleport",
    }
    if extra:
        row.update(extra)
    return row


def _rank_candidates(candidates, key_name="score", reverse=True, limit=8):
    ranked = sorted(
        candidates,
        key=lambda item: item.get(key_name) if item.get(key_name) is not None else -math.inf,
        reverse=reverse,
    )
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked[:limit]


def _legal_monster_actions(state):
    monster = state["entities"]["monster"]
    origin = tuple(monster["pos"])
    walls = _walls(state)
    actions = []
    for direction, delta in DIRECTIONS.items():
        target = (origin[0] + delta[0], origin[1] + delta[1])
        if _in_bounds(state, target) and target not in walls:
            actions.append({"type": "move", "direction": direction})

    if monster.get("teleport_cooldown", 0) <= 0:
        for r in range(_size(state)):
            for c in range(_size(state)):
                target = (r, c)
                if target == origin or target in walls:
                    continue
                if _manhattan(origin, target) <= TELEPORT_RANGE:
                    actions.append({"type": "teleport", "target": [r, c]})
    return actions


def _legal_hero_actions(state, hero_id):
    hero = state["entities"][hero_id]
    origin = tuple(hero["pos"])
    walls = _walls(state)
    monster_pos = _monster_pos(state)
    occupied_heroes = {
        tuple(entity["pos"])
        for entity_id, entity in state["entities"].items()
        if entity_id != hero_id
        and entity["kind"] == "hero"
        and entity.get("active", True)
        and not entity.get("escaped", False)
    }
    actions = []
    for direction, delta in DIRECTIONS.items():
        target = (origin[0] + delta[0], origin[1] + delta[1])
        if not _in_bounds(state, target) or target in walls or target in occupied_heroes:
            continue
        if target != monster_pos:
            actions.append({"type": "move", "direction": direction})

    if hero.get("teleport_cooldown", 0) <= 0:
        for r in range(_size(state)):
            for c in range(_size(state)):
                target = (r, c)
                if target == origin or target in walls or target in occupied_heroes or target == monster_pos:
                    continue
                if _manhattan(origin, target) <= TELEPORT_RANGE:
                    actions.append({"type": "teleport", "target": [r, c]})
    return actions


def _apply_action(state, actor_id, action):
    sim = copy.deepcopy(state)
    if action.get("type") == "timeout":
        return sim

    actor = sim["entities"][actor_id]
    origin = tuple(actor["pos"])
    if action["type"] == "move":
        delta = DIRECTIONS[action["direction"]]
        actor["pos"] = [origin[0] + delta[0], origin[1] + delta[1]]
    elif action["type"] == "teleport":
        actor["pos"] = list(action["target"])
    return sim


def _evaluate(state):
    if _is_captured(state):
        return 10_000
    distance = _nearest_hero_distance(state)
    memories_left = sum(1 for memory in state["board"]["memories"] if not memory.get("collected", False))
    escaped = sum(1 for _, hero in _active_heroes(state) if hero.get("escaped", False))
    return -distance * 12 + memories_left * 2 - escaped * 50


def _minmax_decision(state, board_config, deadline, use_alpha_beta):
    actions = _legal_monster_actions(state)
    if not actions:
        return {"type": "timeout"}, 0, {"candidates": [], "considered_cells": [], "depth": board_config["ai_depth"]}

    depth = board_config["ai_depth"]
    nodes = {"count": 0}
    best_action = actions[0]
    best_value = -math.inf
    alpha = -math.inf
    beta = math.inf
    candidates = []

    for action in actions:
        if time.perf_counter() >= deadline:
            break
        sim = _apply_action(state, "monster", action)
        value = _min_value(sim, depth - 1, alpha, beta, nodes, deadline, use_alpha_beta)
        candidates.append(_candidate_row(state, "monster", action, value))
        if value > best_value:
            best_value = value
            best_action = action
        alpha = max(alpha, best_value)
    if not candidates:
        candidates.append(_candidate_row(state, "monster", best_action, _evaluate(_apply_action(state, "monster", best_action))))
    ranked = _rank_candidates(candidates)
    debug = {
        "depth": depth,
        "use_alpha_beta": use_alpha_beta,
        "candidates": ranked,
        "considered_cells": [item["target"] for item in ranked],
        "best_score": _safe_score(best_value),
    }
    return best_action, nodes["count"], debug


def _min_value(state, depth, alpha, beta, nodes, deadline, use_alpha_beta):
    nodes["count"] += 1
    if time.perf_counter() >= deadline or depth <= 0 or _is_captured(state):
        return _evaluate(state)

    heroes = _active_heroes(state)
    hero_actions = []
    for hero_id, _ in heroes:
        for action in _legal_hero_actions(state, hero_id):
            hero_actions.append((hero_id, action))
    if not hero_actions:
        return _evaluate(state)

    value = math.inf
    for hero_id, action in hero_actions:
        value = min(value, _max_value(_apply_action(state, hero_id, action), depth - 1, alpha, beta, nodes, deadline, use_alpha_beta))
        if use_alpha_beta and value <= alpha:
            return value
        beta = min(beta, value)
    return value


def _max_value(state, depth, alpha, beta, nodes, deadline, use_alpha_beta):
    nodes["count"] += 1
    if time.perf_counter() >= deadline or depth <= 0 or _is_captured(state):
        return _evaluate(state)

    actions = _legal_monster_actions(state)
    if not actions:
        return _evaluate(state)

    value = -math.inf
    for action in actions:
        value = max(value, _min_value(_apply_action(state, "monster", action), depth - 1, alpha, beta, nodes, deadline, use_alpha_beta))
        if use_alpha_beta and value >= beta:
            return value
        alpha = max(alpha, value)
    return value


def _astar_decision(state):
    start = _monster_pos(state)
    hero_positions = {tuple(hero["pos"]) for _, hero in _active_heroes(state)}
    if not hero_positions:
        return {"type": "timeout"}, 0, {"candidates": [], "path": [], "considered_cells": []}
    if start in hero_positions:
        return {"type": "timeout"}, 0, {"candidates": [], "path": [list(start)], "considered_cells": [list(start)]}

    walls = _walls(state)
    frontier = []
    counter = 0
    heapq.heappush(frontier, (0, counter, start, None, 0))
    best_cost = {start: 0}
    parent = {start: None}
    expanded = 0
    expanded_cells = []
    can_teleport_now = state["entities"]["monster"].get("teleport_cooldown", 0) <= 0
    start_candidates = [
        _candidate_row(
            state,
            "monster",
            action,
            -(_manhattan(_action_target(state, "monster", action), min(hero_positions, key=lambda hero: _manhattan(_action_target(state, "monster", action), hero)))),
            {"heuristic": min(_manhattan(_action_target(state, "monster", action), goal) for goal in hero_positions)},
        )
        for action in _legal_monster_actions(state)
    ]

    while frontier:
        _, _, position, first_action, cost = heapq.heappop(frontier)
        expanded += 1
        expanded_cells.append(list(position))
        if position in hero_positions and first_action is not None:
            path = _reconstruct_path(parent, position)
            debug = {
                "candidates": _rank_candidates(start_candidates, key_name="heuristic", reverse=False),
                "path": [list(pos) for pos in path],
                "considered_cells": expanded_cells[:80],
                "path_cost": cost,
            }
            return first_action, expanded, debug

        neighbors = []
        for direction, delta in DIRECTIONS.items():
            target = (position[0] + delta[0], position[1] + delta[1])
            if _in_bounds(state, target) and target not in walls:
                neighbors.append((target, {"type": "move", "direction": direction}, 1))

        if can_teleport_now and position == start:
            for r in range(_size(state)):
                for c in range(_size(state)):
                    target = (r, c)
                    if target != start and target not in walls and _manhattan(start, target) <= TELEPORT_RANGE:
                        neighbors.append((target, {"type": "teleport", "target": [r, c]}, 1))

        for target, action, step_cost in neighbors:
            new_cost = cost + step_cost
            if new_cost >= best_cost.get(target, math.inf):
                continue
            best_cost[target] = new_cost
            parent[target] = position
            first = first_action or action
            priority = new_cost + min(_manhattan(target, goal) for goal in hero_positions)
            counter += 1
            heapq.heappush(frontier, (priority, counter, target, first, new_cost))

    fallback = _legal_monster_actions(state)
    action = fallback[0] if fallback else {"type": "timeout"}
    debug = {
        "candidates": _rank_candidates(start_candidates, key_name="heuristic", reverse=False),
        "path": [],
        "considered_cells": expanded_cells[:80],
        "path_cost": None,
    }
    return action, expanded, debug


def _reconstruct_path(parent, target):
    path = [target]
    current = target
    while parent.get(current) is not None:
        current = parent[current]
        path.append(current)
    return list(reversed(path))


def _mcts_decision(state, board_config, deadline):
    actions = _legal_monster_actions(state)
    if not actions:
        return {"type": "timeout"}, 0, {"candidates": [], "considered_cells": [], "rollout_limit": board_config["mcts_rollouts"]}

    immediate_capture = _capture_action(state, actions, teleport=False)
    if immediate_capture:
        candidate = _candidate_row(state, "monster", immediate_capture, 10_000, {"reason": "Heroj je susedan, hvatanje ima prioritet."})
        debug = {
            "rollout_limit": board_config["mcts_rollouts"],
            "rollouts": 0,
            "candidates": [candidate | {"rank": 1}],
            "considered_cells": [candidate["target"]],
            "reason": "MCTS preskače simulaciju jer postoji sigurno hvatanje običnim potezom.",
        }
        return immediate_capture, 1, debug

    teleport_capture = _capture_action(state, actions, teleport=True)
    if teleport_capture:
        candidate = _candidate_row(state, "monster", teleport_capture, 9_500, {"reason": "Teleport hvatanje je dostupno."})
        debug = {
            "rollout_limit": board_config["mcts_rollouts"],
            "rollouts": 0,
            "candidates": [candidate | {"rank": 1}],
            "considered_cells": [candidate["target"]],
            "reason": "MCTS bira teleport jer odmah hvata heroja.",
        }
        return teleport_capture, 1, debug

    rng = random.Random(state["seed"] + state["turn_number"] * 1009)
    scores = {index: 0.0 for index in range(len(actions))}
    visits = {index: 0 for index in range(len(actions))}
    rollout_limit = board_config["mcts_rollouts"]
    rollouts = 0

    while rollouts < rollout_limit and time.perf_counter() < deadline:
        index = rollouts % len(actions)
        sim = _apply_action(state, "monster", actions[index])
        reward = _rollout(sim, rng, max_depth=8)
        scores[index] += reward
        visits[index] += 1
        rollouts += 1

    best_index = max(range(len(actions)), key=lambda i: scores[i] / max(visits[i], 1))
    candidates = []
    normalizer = 1000 + _size(state) * 2
    for index, action in enumerate(actions):
        avg_reward = scores[index] / max(visits[index], 1)
        winrate = max(0, min(1, (avg_reward + _size(state) * 2) / normalizer))
        candidates.append(
            _candidate_row(
                state,
                "monster",
                action,
                avg_reward,
                {
                    "visits": visits[index],
                    "avg_reward": round(avg_reward, 3),
                    "winrate": round(winrate, 3),
                },
            )
        )
    ranked = _rank_candidates(candidates, key_name="avg_reward")
    chosen = actions[best_index]
    current_distance = _nearest_hero_distance(state)
    chosen_distance = _nearest_hero_distance(_apply_action(state, "monster", chosen))
    chase = _chase_action(state, actions)
    chase_distance = _nearest_hero_distance(_apply_action(state, "monster", chase)) if chase else chosen_distance
    reason = "Izabran kandidat sa najboljim prosečnim rollout rezultatom."
    if chase and chosen_distance > current_distance and chase_distance <= current_distance:
        chosen = chase
        reason = "MCTS kandidat je udaljavao čudovište, pa je aktiviran fallback ka najbližem heroju."
    debug = {
        "rollout_limit": rollout_limit,
        "rollouts": rollouts,
        "candidates": ranked,
        "considered_cells": [item["target"] for item in ranked],
        "reason": reason,
    }
    return chosen, rollouts, debug


def _capture_action(state, actions, teleport=None):
    for action in actions:
        if teleport is not None and (action.get("type") == "teleport") != teleport:
            continue
        if _is_captured(_apply_action(state, "monster", action)):
            return action
    return None


def _chase_action(state, actions):
    if not actions:
        return None
    return min(actions, key=lambda action: _nearest_hero_distance(_apply_action(state, "monster", action)))


def _rollout(state, rng, max_depth):
    sim = copy.deepcopy(state)
    if _is_captured(sim):
        return 1000

    for _ in range(max_depth):
        for hero_id, _ in _active_heroes(sim):
            actions = _legal_hero_actions(sim, hero_id)
            if actions:
                sim = _apply_action(sim, hero_id, rng.choice(actions))
        if _is_captured(sim):
            return 1000

        monster_actions = _legal_monster_actions(sim)
        if monster_actions:
            greedy = min(
                monster_actions,
                key=lambda action: _nearest_hero_distance(_apply_action(sim, "monster", action)),
            )
            sim = _apply_action(sim, "monster", greedy)
        if _is_captured(sim):
            return 1000

    return -_nearest_hero_distance(sim)
