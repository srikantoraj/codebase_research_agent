from django.urls import re_path

from apps.realtime.consumers import ResearchSessionConsumer


websocket_urlpatterns = [
    re_path(
        r"^ws/research/sessions/(?P<session_id>[0-9a-f-]+)/$",
        ResearchSessionConsumer.as_asgi(),
    ),
]