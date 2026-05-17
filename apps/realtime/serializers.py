from __future__ import annotations

import json
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder

from apps.research.models import AgentEvent


def make_json_safe(value: Any) -> Any:
    """
    Convert UUID, datetime, Decimal, and other Django/Python objects
    into JSON-safe values before sending through WebSocket.
    """
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder, default=str))


def serialize_agent_event(event: AgentEvent) -> dict[str, Any]:
    return make_json_safe(
        {
            "id": str(event.id),
            "session_id": str(event.session_id),
            "event_type": event.event_type,
            "title": event.title,
            "message": event.message,
            "payload": event.payload or {},
            "step_number": event.step_number,
            "is_public": event.is_public,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
    )