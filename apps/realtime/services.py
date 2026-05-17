from __future__ import annotations

from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.realtime.serializers import make_json_safe, serialize_agent_event


class RealtimeEventPublisher:
    """
    Publish research-agent events to WebSocket subscribers.

    The consumer subscribes to:
        research_session_<session_id>

    Your agent/research services can call:
        RealtimeEventPublisher.publish(session.id, event_data)
    """

    @staticmethod
    def group_name(session_id: str) -> str:
        return "research_session_%s" % str(session_id)

    @classmethod
    def publish(cls, session_id, event_data: dict[str, Any]) -> None:
        channel_layer = get_channel_layer()

        if channel_layer is None:
            return

        safe_data = make_json_safe(event_data)

        async_to_sync(channel_layer.group_send)(
            cls.group_name(str(session_id)),
            {
                "type": "agent.event",
                "data": safe_data,
            },
        )

    @classmethod
    def publish_event_model(cls, event) -> None:
        cls.publish(
            session_id=event.session_id,
            event_data=serialize_agent_event(event),
        )