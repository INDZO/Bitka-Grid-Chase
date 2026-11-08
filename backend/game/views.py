from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from game.engine import (
    GameError,
    algorithm_history,
    apply_player_action,
    apply_turn_timeout,
    create_game,
    game_ai_stats,
    join_game,
    match_stats,
    maybe_run_ai_turns,
    serialize_game,
    update_waiting_settings,
)
from game.models import Game
from game.realtime import broadcast_game
from game.serializers import GameCreateSerializer, GameSettingsSerializer, JoinGameSerializer, MoveSerializer


def error_response(exc, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": str(exc)}, status=code)


class GameCreateView(APIView):
    def post(self, request):
        serializer = GameCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            game, player = create_game(**serializer.validated_data)
            maybe_run_ai_turns(game)
        except GameError as exc:
            return error_response(exc)
        return Response(serialize_game(game, player.token), status=status.HTTP_201_CREATED)


class GameDetailView(APIView):
    def get(self, request, room_code):
        try:
            game = Game.objects.get(room_code=room_code)
        except Game.DoesNotExist:
            return error_response(GameError("Partija ne postoji."), status.HTTP_404_NOT_FOUND)
        return Response(serialize_game(game))


class JoinGameView(APIView):
    def post(self, request, room_code):
        serializer = JoinGameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            game, player = join_game(room_code, serializer.validated_data["skin"])
            maybe_run_ai_turns(game)
            broadcast_game(game)
        except GameError as exc:
            return error_response(exc)
        return Response(serialize_game(game, player.token))


class GameSettingsView(APIView):
    def patch(self, request, room_code):
        serializer = GameSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            game = Game.objects.get(room_code=room_code)
            game = update_waiting_settings(game, **serializer.validated_data)
            broadcast_game(game)
        except Game.DoesNotExist:
            return error_response(GameError("Partija ne postoji."), status.HTTP_404_NOT_FOUND)
        except GameError as exc:
            return error_response(exc)
        return Response(serialize_game(game))


class GameMoveView(APIView):
    def post(self, request, room_code):
        serializer = MoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            game = Game.objects.get(room_code=room_code)
            apply_player_action(game, serializer.validated_data["player_token"], serializer.validated_data["action"])
            maybe_run_ai_turns(game)
            game.refresh_from_db()
            broadcast_game(game)
        except Game.DoesNotExist:
            return error_response(GameError("Partija ne postoji."), status.HTTP_404_NOT_FOUND)
        except GameError as exc:
            return error_response(exc)
        return Response(serialize_game(game))


class GameTimeoutView(APIView):
    def post(self, request, room_code):
        try:
            game = Game.objects.get(room_code=room_code)
            apply_turn_timeout(game)
            maybe_run_ai_turns(game)
            game.refresh_from_db()
            broadcast_game(game)
        except Game.DoesNotExist:
            return error_response(GameError("Partija ne postoji."), status.HTTP_404_NOT_FOUND)
        except GameError as exc:
            return error_response(exc)
        return Response(serialize_game(game))


class GameStatsView(APIView):
    def get(self, request, room_code):
        try:
            game = Game.objects.get(room_code=room_code)
        except Game.DoesNotExist:
            return error_response(GameError("Partija ne postoji."), status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "room_code": game.room_code,
                "status": game.status,
                "result": game.result,
                "ai_stats": game_ai_stats(game),
                "match_stats": match_stats(game),
            }
        )


class AlgorithmStatsView(APIView):
    def get(self, request):
        return Response({"algorithms": algorithm_history()})
