from django.urls import path

from game.views import (
    AlgorithmStatsView,
    GameCreateView,
    GameDetailView,
    GameMoveView,
    GameSettingsView,
    GameStatsView,
    GameTimeoutView,
    JoinGameView,
)


urlpatterns = [
    path("games/", GameCreateView.as_view(), name="game-create"),
    path("games/<str:room_code>/", GameDetailView.as_view(), name="game-detail"),
    path("games/<str:room_code>/join/", JoinGameView.as_view(), name="game-join"),
    path("games/<str:room_code>/settings/", GameSettingsView.as_view(), name="game-settings"),
    path("games/<str:room_code>/move/", GameMoveView.as_view(), name="game-move"),
    path("games/<str:room_code>/timeout/", GameTimeoutView.as_view(), name="game-timeout"),
    path("games/<str:room_code>/stats/", GameStatsView.as_view(), name="game-stats"),
    path("stats/algorithms/", AlgorithmStatsView.as_view(), name="algorithm-stats"),
]
