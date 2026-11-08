from rest_framework import serializers

from game.config import AI_LEVELS, BOARD_CONFIGS, MODES, SKINS


class GameCreateSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=MODES)
    board_size = serializers.ChoiceField(choices=list(BOARD_CONFIGS.keys()))
    ai_level = serializers.ChoiceField(choices=list(AI_LEVELS.keys()), required=False, allow_blank=True, default="")
    skin = serializers.ChoiceField(choices=SKINS)
    seed = serializers.IntegerField(required=False, min_value=1)


class JoinGameSerializer(serializers.Serializer):
    skin = serializers.ChoiceField(choices=SKINS, default="Scout")


class GameSettingsSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=MODES, required=False)
    board_size = serializers.ChoiceField(choices=list(BOARD_CONFIGS.keys()), required=False)
    ai_level = serializers.ChoiceField(choices=list(AI_LEVELS.keys()), required=False, allow_blank=True)


class MoveSerializer(serializers.Serializer):
    player_token = serializers.UUIDField()
    action = serializers.DictField()
