from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from game.engine import serialize_game


def broadcast_game(game):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f"game_{game.room_code}",
        {"type": "game.update", "payload": serialize_game(game)},
    )
