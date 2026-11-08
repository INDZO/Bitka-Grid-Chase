"""Centralne vrednosti igre.

Brojevi nisu zadati u specifikaciji, pa su ovde izdvojeni kao razumni default-i
za lakše podešavanje i objašnjenje na odbrani projekta.
"""

BOARD_CONFIGS = {
    5: {
        "wall_count": 3,
        "initial_vines": 2,
        "memory_count": 3,
        "vine_growth_interval": 3,
        "vine_growth_count": 1,
        "portal_shift_interval": 6,
        "turn_limit_seconds": 18,
        "total_game_seconds": 180,
        "hero_teleport_cooldown": 4,
        "monster_teleport_cooldown": 6,
        "ai_depth": 3,
        "mcts_rollouts": 70,
    },
    6: {
        "wall_count": 5,
        "initial_vines": 3,
        "memory_count": 4,
        "vine_growth_interval": 3,
        "vine_growth_count": 1,
        "portal_shift_interval": 7,
        "turn_limit_seconds": 20,
        "total_game_seconds": 240,
        "hero_teleport_cooldown": 4,
        "monster_teleport_cooldown": 7,
        "ai_depth": 3,
        "mcts_rollouts": 90,
    },
    7: {
        "wall_count": 7,
        "initial_vines": 4,
        "memory_count": 5,
        "vine_growth_interval": 4,
        "vine_growth_count": 2,
        "portal_shift_interval": 8,
        "turn_limit_seconds": 22,
        "total_game_seconds": 300,
        "hero_teleport_cooldown": 5,
        "monster_teleport_cooldown": 8,
        "ai_depth": 4,
        "mcts_rollouts": 110,
    },
    8: {
        "wall_count": 10,
        "initial_vines": 5,
        "memory_count": 6,
        "vine_growth_interval": 4,
        "vine_growth_count": 2,
        "portal_shift_interval": 9,
        "turn_limit_seconds": 24,
        "total_game_seconds": 360,
        "hero_teleport_cooldown": 5,
        "monster_teleport_cooldown": 9,
        "ai_depth": 4,
        "mcts_rollouts": 130,
    },
}

AI_LEVELS = {
    "minmax": {"label": "MinMax", "opponent": "Sentinel"},
    "alphabeta": {"label": "MinMax + Alpha-Beta", "opponent": "AlfaAI"},
    "astar": {"label": "A* pretraga", "opponent": "ShadowMonster"},
    "mcts": {"label": "Monte Carlo Tree Search", "opponent": "MindFlyer"},
}

SKINS = ["Scout", "Guide", "Runner", "Builder", "Ranger", "Pilot"]
MODES = ["1vAI", "1v1", "2vAI"]

DIRECTIONS = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}

TELEPORT_RANGE = 2
ROOM_CODE_LENGTH = 6
