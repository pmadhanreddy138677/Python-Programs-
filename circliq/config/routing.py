from apps.messaging.routing import websocket_urlpatterns as chat_ws
from apps.notifications.routing import websocket_urlpatterns as notif_ws

websocket_urlpatterns = chat_ws + notif_ws
