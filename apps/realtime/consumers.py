from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.realtime.serializers import make_json_safe, serialize_agent_event
from apps.realtime.services import RealtimeEventPublisher
from apps.research.models import AgentEvent, ResearchSession


class ResearchSessionConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket endpoint:

        ws://localhost:8000/ws/research/sessions/<session_id>/

    What it does:
    - validates the session exists
    - joins a session-specific WebSocket group
    - sends recent event history immediately
    - streams new AgentEvent updates in real time
    """

    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.group_name = RealtimeEventPublisher.group_name(self.session_id)

        session_exists = await self.session_exists(self.session_id)

        if not session_exists:
            await self.close(code=4404)
            return

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

        await self.send_json(
            {
                "type": "connection_ready",
                "session_id": self.session_id,
                "message": "Connected to research session realtime stream.",
            }
        )

        history = await self.get_recent_events(self.session_id)

        await self.send_json(
            {
                "type": "event_history",
                "session_id": self.session_id,
                "events": history,
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

    async def receive_json(self, content, **kwargs):
        """
        Optional client messages.

        Supported:
        - {"type": "ping"}
        - {"type": "history", "limit": 50}
        """

        message_type = content.get("type")

        if message_type == "ping":
            await self.send_json(
                {
                    "type": "pong",
                    "session_id": self.session_id,
                }
            )
            return

        if message_type == "history":
            limit = int(content.get("limit", 50) or 50)
            history = await self.get_recent_events(self.session_id, limit=limit)

            await self.send_json(
                {
                    "type": "event_history",
                    "session_id": self.session_id,
                    "events": history,
                }
            )
            return

        await self.send_json(
            {
                "type": "error",
                "message": "Unsupported websocket message type.",
                "received": content,
            }
        )

    async def agent_event(self, event):
        """
        Called when RealtimeEventPublisher sends:

            {
                "type": "agent.event",
                "data": {...}
            }

        Channels maps "agent.event" to this method: agent_event().
        """

        data = make_json_safe(event.get("data", {}))

        await self.send_json(
            {
                "type": "agent_event",
                "session_id": self.session_id,
                "event": data,
            }
        )

    @database_sync_to_async
    def session_exists(self, session_id: str) -> bool:
        return ResearchSession.objects.filter(id=session_id).exists()

    @database_sync_to_async
    def get_recent_events(self, session_id: str, limit: int = 50) -> list[dict]:
        events = (
            AgentEvent.objects.filter(
                session_id=session_id,
                is_public=True,
            )
            .order_by("-created_at")[:limit]
        )

        return [
            serialize_agent_event(event)
            for event in reversed(list(events))
        ]