from django.urls import re_path

from game.consumers import GameConsumer


websocket_urlpatterns = [
    re_path(r"^ws/game/(?P<room_code>[A-Z0-9]+)/$", GameConsumer.as_asgi()),
]
